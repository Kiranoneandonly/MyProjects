"""Testing tasks.models."""
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import AnonymousUser
from mock import patch

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils import timezone

from clients.models import Client
from localization_kits.models import LocaleTranslationKit, FileAnalysis, \
    LocalizationKit, FileAsset, SOURCEFILE_ASSET
from prices.constants import TWO_PLACES, MINIMUM_JOB_SURCHARGE
from prices.models import ClientTranslationPrice, ClientNonTranslationPrice
from projects.states import TASK_COMPLETED_STATUS, TASK_ACTIVE_STATUS, TASK_CREATED_STATUS
from services.managers import HOURS_UNITS, PERCENT_UNITS, PM_SERVICE_TYPE, TARGET_BASIS
from services.models import Service, ScopeUnit, Locale, ServiceType, PricingBasis
from shared.datafactory import create_project, TaskFactory, create_via_user, create_vendor_user, \
    create_client
from tasks.models import Task, TaskLocaleTranslationKit, NonTranslationTask


class TestTask(TestCase):
    def setUp(self):
        self.task = Task(status=TASK_ACTIVE_STATUS)

    def test_is_overdue(self):
        self.task.due = timezone.now() - relativedelta(months=1)
        self.assertTrue(self.task.is_overdue())

    def test_is_not_overdue(self):
        self.task.due = timezone.now() + relativedelta(months=1)
        self.assertFalse(self.task.is_overdue())

    def test_is_not_overdue_when_completed(self):
        self.task.due = timezone.now() - relativedelta(months=1)
        self.task.status = TASK_COMPLETED_STATUS
        self.assertFalse(self.task.is_overdue())

    def test_duration_with_whole_days(self):
        self.task.standard_days = 2
        self.task.express_days = 1
        self.assertEqual(self.task.duration('standard'), 2)
        self.assertEqual(self.task.duration('express'), 1)

    def test_duration_hourly_tasks(self):
        hours = ScopeUnit(code=HOURS_UNITS, description="Hours")
        self.task.service = Service(unit_of_measure=hours)

        self.task.standard_days = 0
        self.task.express_days = 0
        self.task.quantity = lambda: Decimal(2.00)
        self.assertEqual(self.task.duration('standard'), 2.0 / 24)
        self.assertEqual(self.task.duration('express'), 2.0 / 24)

    def test_reference_file_name(self):
        self.task.reference_file = "foo/bar/baz/The Reasons.ppt"
        self.assertEqual(self.task.reference_file_name, "The Reasons.ppt")


class TestTaskWithDatabase(TestCase):
    def setUp(self):
        self.project = create_project(self.id())
        self.task_factory = TaskFactory(self.project)

    def test_duration_with_children(self):
        task_1 = self.task_factory.create_tep_task(
            TASK_ACTIVE_STATUS, standard_days=1, express_days=1)
        task_2 = self.task_factory.create_tep_task(
            TASK_ACTIVE_STATUS, standard_days=1, express_days=1,
            predecessor=task_1)
        task_3 = self.task_factory.create_tep_task(
            TASK_ACTIVE_STATUS, standard_days=7, express_days=4,
            predecessor=task_2)

        task_2b = self.task_factory.create_tep_task(
            TASK_ACTIVE_STATUS, standard_days=1, express_days=1,
            predecessor=task_1)

        self.assertEqual(task_1.duration_with_children('standard'), 9)
        self.assertEqual(task_1.duration_with_children('express'), 6)

    def test_copy_trans_kit_from_analysis_with_reference_file(self):
        ttask = self.task_factory.create_tep_task(TASK_CREATED_STATUS)
        task = Task.objects.get(id=ttask.id)

        trans_kit = TaskLocaleTranslationKit.objects.create(task=task)

        reference_file = "A Really Great Reference.doc"

        ltk = LocaleTranslationKit.objects.create(
            kit=self.project.kit,
            target_locale=task.service.target,
            reference_file=reference_file)

        # A brittle patch, but that calls a thing that does S3 stuff, which
        # we really don't want to happen in the test.
        with patch('tasks.models.copy_file_asset'):
            task.copy_trans_kit_assets_from_lockit()

        self.assertEqual(ltk.reference_file, task.reference_file)

    def test_copy_trans_kit_from_analysis_without_reference_file(self):
        ttask = self.task_factory.create_tep_task(TASK_CREATED_STATUS)
        task = Task.objects.get(id=ttask.id)

        trans_kit = TaskLocaleTranslationKit.objects.create(task=task)

        ltk = LocaleTranslationKit.objects.create(
            kit=self.project.kit,
            target_locale=task.service.target)

        # A brittle patch, but that calls a thing that does S3 stuff, which
        # we really don't want to happen in the test.
        with patch('tasks.models.copy_file_asset'):
            task.copy_trans_kit_assets_from_lockit()

        self.assertFalse(task.reference_file)

    def test_reference_file(self):
        ttask = self.task_factory.create_tep_task(TASK_CREATED_STATUS)
        self.task = Task.objects.get(id=ttask.id)
        self.assertFalse(self.task.reference_file)

        my_file = "something_reference.doc"
        self.task.reference_file = my_file

        self.task.save()

        # reload
        self.task = Task.objects.get(id=self.task.id)

        self.assertEqual(self.task.reference_file, my_file)

    def test_is_assignee_user(self):
        task = self.task_factory.create_fa_task(TASK_ACTIVE_STATUS)
        via_user = create_via_user()[0]
        task.assigned_to = via_user

        self.assertTrue(task.is_assignee(via_user))

        # test for negative
        other_via_user = create_via_user('grapefruit@via.example.com')[0]
        self.assertFalse(task.is_assignee(other_via_user))

        anon_user = AnonymousUser()
        # noinspection PyTypeChecker
        self.assertFalse(task.is_assignee(anon_user))

    def test_is_assignee_account(self):
        task = self.task_factory.create_tep_task(TASK_ACTIVE_STATUS)
        vendor_user = create_vendor_user()[0]

        # assigned to an *account*, not user
        task.assigned_to = vendor_user.account

        self.assertTrue(task.is_assignee(vendor_user))

        # test for negative
        vendor_account_type = vendor_user.account.account_type

        vendor = Client.objects.create(
            name="Kiki's Localization Service",
            account_type=vendor_account_type,
        )
        other_vendor_user = create_vendor_user('kiki@k.example.com', vendor)[0]
        self.assertFalse(task.is_assignee(other_vendor_user))

        anon_user = AnonymousUser()
        # noinspection PyTypeChecker
        self.assertFalse(task.is_assignee(anon_user))



class TestTranslationTask(TestCase):

    def setUp(self):
        self.project = create_project(self.id())
        task_factory = TaskFactory(self.project)
        self.task = task_factory.create_tep_task(TASK_ACTIVE_STATUS)

    def test_files_with_input_file(self):
        filename = "something/something/blub.xls"

        tltk = TaskLocaleTranslationKit.objects.create(task=self.task)
        tltk.input_file = filename

        expected_url = reverse('download_tasklocaletranslationkit_in_file',
                               kwargs={'task_id': self.task.id,
                                       'tltk_id': tltk.id})

        files = self.task.files
        reference = files[0]['input']

        self.assertEqual(reference['file'], filename)
        self.assertEqual(reference['name'](), 'blub.xls')
        self.assertEqual(reference['url'], expected_url)

    def test_set_from_client_price(self):
        service = self.task.service
        minimum_price = Decimal('110.00')
        word_rate = Decimal('0.21')
        client_price = ClientTranslationPrice.objects.create(
            service=service,
            minimum_price=minimum_price,
            word_rate=word_rate
        )
        success = self.task.set_from_client_price(client_price)

        self.assertTrue(success)
        self.assertEqual(word_rate, self.task.client_price.word_rate)
        self.assertEqual(minimum_price, self.task.client_price.minimum_price)

    def test_set_from_client_price_manifest_overrides_minimum(self):
        client_minimum_price = Decimal('0.05')
        minimum_price = Decimal('99.99')
        word_rate = Decimal('0.21')

        manifest = self.project.client.manifest
        manifest.minimum_price = client_minimum_price
        manifest.save()

        # This CTP matches the service, but not the client.
        client_price = ClientTranslationPrice.objects.create(
            service=self.task.service,
            minimum_price=minimum_price,
            word_rate=word_rate
        )
        success = self.task.set_from_client_price(client_price)

        self.assertTrue(success)

        # assert this is the minimum price from the manifest, not from the CTP
        self.assertEqual(client_minimum_price,
                         self.task.client_price.minimum_price)

    def test_set_from_client_price_minimum_overrides_manifest(self):
        client_minimum_price = Decimal('0.05')
        minimum_price = Decimal('0.01')
        word_rate = Decimal('0.21')

        manifest = self.project.client.manifest
        manifest.minimum_price = client_minimum_price
        manifest.save()

        # This CTP matches the service *and* the client, thus it should win
        # over the manifest.
        client_price = ClientTranslationPrice.objects.create(
            client=self.project.client,
            service=self.task.service,
            minimum_price=minimum_price,
            word_rate=word_rate
        )
        success = self.task.set_from_client_price(client_price)

        self.assertTrue(success)

        # assert this is the minimum price from the the CTP
        self.assertEqual(minimum_price, self.task.client_price.minimum_price)

    def test_set_from_client_price_parent_minimum_overrides_manifest(self):
        client_minimum_price = Decimal('0.05')
        minimum_price = Decimal('0.01')
        word_rate = Decimal('0.21')

        client = self.project.client
        manifest = client.manifest
        manifest.minimum_price = client_minimum_price
        manifest.save()

        client.parent = create_client(
            u"Shell Company",
            vertical=client.manifest.vertical,
            pricing_scheme=client.manifest.pricing_scheme,
            pricing_basis=client.manifest.pricing_basis)
        client.save()

        # This CTP matches the client's parent; it still wins over the client
        # manifest.
        client_parent = client.parent
        assert client_parent is not None
        client_price = ClientTranslationPrice.objects.create(
            client=client_parent,
            service=self.task.service,
            minimum_price=minimum_price,
            word_rate=word_rate
        )
        success = self.task.set_from_client_price(client_price)

        self.assertTrue(success)

        # assert this is the minimum price from the CTP
        self.assertEqual(minimum_price, self.task.client_price.minimum_price)

    def test_set_from_client_price_manifest_overrides_fuzzy(self):
        ctp_fuzzy = Decimal(1)
        manifest_fuzzy = Decimal('0.90')
        word_rate = Decimal('0.21')

        manifest = self.project.client.manifest
        manifest.pricing_memory_bank_discount = True
        manifest.fuzzy9599 = manifest_fuzzy
        manifest.save()

        # This CTP matches the service, but not the client.
        client_price = ClientTranslationPrice.objects.create(
            service=self.task.service,
            fuzzy9599=ctp_fuzzy,
            word_rate=word_rate
        )
        success = self.task.set_from_client_price(client_price)

        self.assertTrue(success)

        # assert this is the minimum price from the manifest, not from the CTP
        self.assertEqual(manifest_fuzzy,
                         self.task.client_price.fuzzy9599)

    def test_set_from_client_price_fuzzy_overrides_manifest(self):
        ctp_fuzzy = Decimal('0.80')
        manifest_fuzzy = Decimal('0.90')
        word_rate = Decimal('0.21')

        manifest = self.project.client.manifest
        manifest.pricing_memory_bank_discount = True
        manifest.fuzzy9599 = manifest_fuzzy
        manifest.save()

        # This CTP matches the service *and* the client, thus it should win
        # over the manifest.
        client_price = ClientTranslationPrice.objects.create(
            client=self.project.client,
            service=self.task.service,
            fuzzy9599=ctp_fuzzy,
            word_rate=word_rate
        )
        success = self.task.set_from_client_price(client_price)

        self.assertTrue(success)

        # assert this is the minimum price from the the CTP
        self.assertEqual(ctp_fuzzy, self.task.client_price.fuzzy9599)


class TestNonTranslationTask(TestCase):
    def test_itemized_price(self):
        total_price = Decimal('110.00')
        task = NonTranslationTask()
        task.standard_price = lambda *a: total_price

        loc_kit = LocalizationKit.objects.create()

        asset_spec = [
            ('First.ods', 200),
            ('Second.odt', 800)
        ]
        total_words = sum(words for name, words in asset_spec)

        target = Locale.objects.get(lcid=1049)

        for name, word_count in asset_spec:
            asset = FileAsset.objects.create(
                kit=loc_kit,
                asset_type=SOURCEFILE_ASSET,
                orig_name=name,
            )
            FileAnalysis.objects.create(
                asset=asset,
                no_match=word_count,
                target_locale=target
            )

        prices = task._itemized_price_details(loc_kit, target, 1)

        self.assertEqual(len(asset_spec), len(prices))

        self.assertEqual(asset_spec[0][0], prices[0].analysis.asset.orig_name)
        self.assertEqual(asset_spec[1][0], prices[1].analysis.asset.orig_name)

        self.assertEqual(asset_spec[0][1] * total_price / total_words, prices[0].net)
        self.assertEqual(asset_spec[1][1] * total_price / total_words, prices[1].net)

        self.assertTrue(TWO_PLACES.same_quantum(prices[0].net), prices[0].net.as_tuple())

        recalc_total_price = sum(price.net for price in prices)

        self.assertEqual(total_price, recalc_total_price)

    def test_itemized_price_rounding(self):
        total_price = Decimal('100.00')
        task = NonTranslationTask()
        task.standard_price = lambda *a: total_price

        loc_kit = LocalizationKit.objects.create()

        asset_spec = [
            ('First.ods', 200),
            ('Second.odt', 200),
            ('Third.ods', 200),
        ]

        target = Locale.objects.get(lcid=1049)

        for name, word_count in asset_spec:
            asset = FileAsset.objects.create(
                kit=loc_kit,
                asset_type=SOURCEFILE_ASSET,
                orig_name=name,
            )
            FileAnalysis.objects.create(
                asset=asset,
                no_match=word_count,
                target_locale=target
            )

        prices = task._itemized_price_details(loc_kit, target, 1)

        # These all had equal word counts, all had 1/3 cent rounded off of them.
        # Assert that cent was added back on at the end.
        self.assertEqual(Decimal('33.33'), prices[0].net)
        self.assertEqual(Decimal('33.33'), prices[1].net)
        self.assertEqual(Decimal('33.34'), prices[2].net)

        self.assertTrue(TWO_PLACES.same_quantum(prices[-1].net), prices[-1].net.as_tuple())

        recalc_total_price = sum(price.net for price in prices)

        self.assertEqual(total_price, recalc_total_price)

    def test_set_from_client_price_percentage_based(self):
        service_type = ServiceType.objects.get(code=PM_SERVICE_TYPE)
        percent_unit = ScopeUnit.objects.get(code=PERCENT_UNITS)

        service = Service(service_type=service_type,
                          unit_of_measure=percent_unit)

        price_percentage = Decimal('0.125')

        client_price = ClientNonTranslationPrice(
            service=service,
            unit_price=price_percentage,
        )

        task = NonTranslationTask()

        # noinspection PyUnresolvedReferences
        with patch.object(task, 'save') as save:
            task.set_from_client_price(client_price)
            self.assertTrue(save.called)

        self.assertEqual(price_percentage, task.unit_price)
        self.assertTrue(task.price_is_percentage)


class TestTranslationTaskClientPrice(TestCase):

    def setUp(self):
        self.word_rate = 0.25

        self.project = create_project(self.id())
        task_factory = TaskFactory(self.project)

        self.client_price = task_factory.create_ttcp(
            source_of_client_prices=-1,
            word_rate=self.word_rate,
            expansion_rate=1.25,
            minimum_price=0.0
        )

        self.loc_kit = LocalizationKit.objects.create()
        self.target = Locale.objects.get(lcid=1049)
        self.client_price._assets = lambda: self.loc_kit.source_files()
        self.client_price._get_analysis = lambda asset: asset.analysis_for_target(self.target)

        self.task = task_factory.create_tep_task(TASK_ACTIVE_STATUS)

    def test_itemized_price(self):
        asset_spec = [
            ('First.ods', 200),
            ('Second.odt', 1000)
        ]

        expansion_rate = 1.25

        for name, word_count in asset_spec:
            asset = FileAsset.objects.create(
                kit=self.loc_kit,
                asset_type=SOURCEFILE_ASSET,
                orig_name=name,
            )
            FileAnalysis.objects.create(
                asset=asset,
                no_match=word_count,
                target_locale=self.target
            )

        prices = self.client_price.itemized_price_details()

        self.assertEqual(len(asset_spec), len(prices))

        self.assertEqual(asset_spec[0][0], prices[0].analysis.asset.orig_name)
        self.assertEqual(asset_spec[1][0], prices[1].analysis.asset.orig_name)

        self.assertEqual(asset_spec[0][1] * expansion_rate * self.word_rate, prices[0].net)
        self.assertEqual(asset_spec[1][1] * expansion_rate * self.word_rate, prices[1].net)

    def test_itemized_price_with_minimum(self):
        self.client_price.minimum_price = Decimal(10000)

        asset_spec = [
            ('First.ods', 200),
            ('Second.odt', 1000)
        ]

        expansion_rate = 1.25

        for name, word_count in asset_spec:
            asset = FileAsset.objects.create(
                kit=self.loc_kit,
                asset_type=SOURCEFILE_ASSET,
                orig_name=name,
            )
            FileAnalysis.objects.create(
                asset=asset,
                no_match=word_count,
                target_locale=self.target
            )

        prices = self.client_price.itemized_price_details()

        self.assertEqual(len(asset_spec) + 1, len(prices))

        self.assertEqual(asset_spec[0][0], prices[0].analysis.asset.orig_name)
        self.assertEqual(asset_spec[1][0], prices[1].analysis.asset.orig_name)

        self.assertEqual(asset_spec[0][1] * expansion_rate * self.word_rate, prices[0].net)
        self.assertEqual(asset_spec[1][1] * expansion_rate * self.word_rate, prices[1].net)

        expected_minimum_surcharge = (
            self.client_price.minimum_price - prices[0].net - prices[1].net)

        # minimum surcharge
        self.assertEqual(prices[2].analysis, MINIMUM_JOB_SURCHARGE)
        self.assertEqual(prices[2].net, expected_minimum_surcharge)

    def test_total_price_with_multiplier(self):
        self.word_rate = Decimal('0.11')
        self.client_price.word_rate = self.word_rate

        asset_spec = [
            ('First.ods', 303),
            ('Second.odt', 303),
        ]

        for name, word_count in asset_spec:
            asset = FileAsset.objects.create(
                kit=self.loc_kit,
                asset_type=SOURCEFILE_ASSET,
                orig_name=name,
            )
            FileAnalysis.objects.create(
                asset=asset,
                duplicate=word_count,  # get half-price words
                target_locale=self.target
            )

        express_multiplier = Decimal('1.5')

        express_price = self.client_price.total_price(
            multiplier=express_multiplier)

        express_itemized_price = self.client_price.itemized_price_details(
            multiplier=express_multiplier)

        itemized_total = sum(price.net for price in express_itemized_price)

        # depending on when you do the rounding, the total may differ. Assert
        # the total is the sum of the express items.
        self.assertEqual(itemized_total, express_price)

    def test_analysis_price(self):
        expansion_rate = Decimal(1.0)
        self.client_price.expansion_rate = expansion_rate

        analysis = FileAnalysis(
            no_match=1000,
            duplicate=20,
        )
        price = self.client_price.analysis_price_details(analysis)

        # 1000 words at full rate plus 20 words at half rate
        self.assertEqual(self.client_price.word_rate, 0.25)
        self.assertEqual(self.word_rate, 0.25)
        self.assertEqual(expansion_rate, 1.0)
        net_price = Decimal(Decimal(self.word_rate) * 1010 * expansion_rate).quantize(TWO_PLACES)
        self.assertEqual(net_price, price.net)
        # raw price doesn't get the half rate.
        raw_price = Decimal(Decimal(self.word_rate) * 1020 * expansion_rate).quantize(TWO_PLACES)
        self.assertEqual(raw_price, price.raw)

        self.assertTrue(TWO_PLACES.same_quantum(price.net))

    def test_analysis_price_expansion(self):
        expansion_rate = Decimal(1.25)
        self.client_price.expansion_rate = expansion_rate

        analysis = FileAnalysis(
            no_match=1000,
            duplicate=20,
        )
        price = self.client_price.analysis_price_details(analysis)

        # 1000 words at full rate plus 20 words at half rate
        self.assertEqual(self.client_price.word_rate, 0.25)
        self.assertEqual(self.word_rate, 0.25)
        self.assertEqual(expansion_rate, 1.25)

        net_price = Decimal(Decimal(self.word_rate) * 1010 * expansion_rate).quantize(TWO_PLACES)
        self.assertEqual(net_price, price.net)
        # raw price doesn't get the half rate.
        raw_price = Decimal(Decimal(self.word_rate) * 1020 * expansion_rate).quantize(TWO_PLACES)
        self.assertEqual(raw_price, price.raw)

        self.assertTrue(TWO_PLACES.same_quantum(price.net))

    def test_analysis_price_expansion_rate_floor(self):
        expansion_rate = Decimal(0.8)
        self.client_price.expansion_rate = expansion_rate

        analysis = FileAnalysis(
            no_match=1000,
            duplicate=20,
        )
        self.client_price.expansion_rate = expansion_rate
        self.client_price.basis = PricingBasis.objects.get(code=TARGET_BASIS)
        self.client_price.translationtask = self.task

        price = self.client_price.analysis_price_details(analysis)

        # 1000 words at full rate plus 20 words at half rate
        self.assertEqual(self.client_price.word_rate, 0.25)
        self.assertEqual(self.word_rate, 0.25)
        self.assertEqual(expansion_rate, 0.8)

        net_price = Decimal(Decimal(self.word_rate) * 1010 * expansion_rate).quantize(TWO_PLACES)
        self.assertEqual(net_price, price.net)
        # raw price doesn't get the half rate.
        raw_price = Decimal(Decimal(self.word_rate) * 1020 * expansion_rate).quantize(TWO_PLACES)
        self.assertEqual(raw_price, price.raw)

        self.assertTrue(TWO_PLACES.same_quantum(price.net))
