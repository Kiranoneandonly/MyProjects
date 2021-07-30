# -*- coding: utf-8 -*-
from decimal import Decimal
from datetime import timedelta
from dateutil.parser import parse as parse_date
from unittest import skip
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.test import TestCase
from django.utils.timezone import now
from dwh_reports.management.commands.refresh_dwh_reports import populate_dwh_reports_data
from dwh_reports.models import ClientsReporting
from localization_kits.models import FileAsset, SOURCEFILE_ASSET, FileAnalysis
from people.models import AccountType
from projects.states import TASK_COMPLETED_STATUS, CREATED_STATUS, STARTED_STATUS
from services.managers import THIRD_PARTY_REVIEW_SERVICE_TYPE
from services.models import Locale, Industry, ServiceType
from shared.datafactory import create_client, create_client_user, create_project, TaskFactory, create_project_details
from shared.utils import remove_html_tags
from tasks.models import TranslationTaskAnalysis, TranslationTaskClientPrice, TaskLocaleTranslationKit
from dwh_reports import exports as ex


class TestClientActivityReport(TestCase):

    def setUp(self):
        self.client = create_client(u"LexCorp")
        self.user = create_client_user(
            u"lex@lexcorp.example.com", self.client,
            first_name=u'Lex',
            last_name=u'Luthor')

        self.russian = Locale.objects.get(lcid=1049)

        VENDOR_ACCOUNT_TYPE, created = AccountType.objects.get_or_create(code=settings.VENDOR_USER_TYPE, description=settings.VENDOR_USER_TYPE)
        VIA_ACCOUNT_TYPE, created = AccountType.objects.get_or_create(code=settings.VIA_USER_TYPE, description=settings.VIA_USER_TYPE)

        populate_dwh_reports_data()

    def create_project(self, *a, **kwargs):
        return create_project(*a, **kwargs)

    def create_project_details(self, *a, **kwargs):
        return create_project_details(*a, **kwargs)

    def test_job_with_pm(self):
        # no departments, one document, one target
        targets = [self.russian]

        instructions = "Opportunity Identifier November Alpha Victor"

        project = self.create_project(
            u"Charter.rtf with PM",
            targets=targets,
            client_poc=self.user,
            started_timestamp=now() - timedelta(days=6),
            due=now() + timedelta(hours=1),
            delivered=now(),
            instructions=instructions
        )
        self.create_project_details(project, True)

        quote = project.quote()
        populate_dwh_reports_data()
        client_reporting = get_object_or_404(ClientsReporting, pk=self.client.id)

        records = ex.get_client_activity_records(client_reporting)

        self.assertEqual(2, len(records))

        r = records[0]

    def test_one_record(self):
        # no departments, one document, one target
        targets = [self.russian]

        instructions = "Opportunity Identifier November Alpha Victor"

        project = self.create_project(
            u"Charters",
            targets=targets,
            client_poc=self.user,
            started_timestamp=now() - timedelta(days=6),
            due=now() + timedelta(hours=1),
            delivered=now(),
            instructions=instructions
        )

        self.create_project_details(project)

        # Only generates new Price if In Estimate status.
        project.status = CREATED_STATUS
        project.save()
        quote = project.quote()
        project.status = STARTED_STATUS
        project.save()

        populate_dwh_reports_data()
        client_reporting = get_object_or_404(ClientsReporting, pk=self.client.id)

        records = ex.get_client_activity_records(client_reporting)

        self.assertEqual(1, len(records))

        r = records[0]

        self.assertEqual(project.job_number, r[ex.COL_JOB_NUMBER])
        self.assertEqual(self.client.name, r[ex.COL_CLIENT_NAME])
        self.assertEqual(u'LexCorp', r[ex.COL_DEPARTMENT])
        self.assertEqual(u"Lex Luthor", r[ex.COL_USER_FULL_NAME])
        self.assertEqual(self.user.email, r[ex.COL_USER_EMAIL])

        self.assertEqual(project.started_timestamp, parse_date(r[ex.COL_START_DATE]))
        self.assertEqual(project.due, parse_date(r[ex.COL_DUE_DATE]))
        self.assertEqual(project.delivered, parse_date(r[ex.COL_DELIVERED_DATE]))

        self.assertEqual(project.get_project_speed_display(), r[ex.COL_PRIORITY])

        self.assertEqual(project.get_estimate_type_display(), r[ex.COL_ESTIMATE_TYPE])

        self.assertEqual(project.price(), r[ex.COL_PRICE])

        self.assertEqual(project.payment_details.get_payment_method_display(), r[ex.COL_PAYMENT_METHOD])

        self.assertEqual(project.industry.description, r[ex.COL_INDUSTRY])

        self.assertEqual(project.source_locale.description, r[ex.COL_SOURCE])
        self.assertEqual(targets[0].description, r[ex.COL_TARGET])

        self.assertEqual(u"Charter.rtf", r[ex.COL_FILENAME])

        self.assertEqual(u"Active", r[ex.COL_PROJECT_STATUS])
        self.assertEqual(remove_html_tags(project.instructions), r[ex.COL_CLIENT_INSTRUCTIONS])

        # The above equality comparisons may not be worth much if all the fields
        # are None or zero.
        nones = [key for (key, value) in r.iteritems() if value is None]
        self.assertEqual(2, len(nones), "Some records are None: %s" % (nones,))
        zeros = [key for (key, value) in r.iteritems() if value == 0]
        self.assertEqual(0, len(zeros), "Some records are zero: %s" % (zeros,))

    def test_date_cutoff(self):
        targets = [self.russian]
        current_project = self.create_project(
            u"Current", client_poc=self.user,
            started_timestamp=now())

        self.create_project_details(current_project)

        recent_project = self.create_project(
            u"Recent", client_poc=self.user,
            started_timestamp=now() - timedelta(days=3))

        self.create_project_details(recent_project)

        old_project = self.create_project(
            u"Old", client_poc=self.user,
            started_timestamp=now() - timedelta(days=369))

        self.create_project_details(old_project)

        current_project.quote()
        recent_project.quote()
        old_project.quote()

        populate_dwh_reports_data()
        client_reporting = get_object_or_404(ClientsReporting, pk=self.client.id)

        records = ex.get_client_activity_records(client_reporting, from_days=28, to_days=None)

        jobs = [r[ex.COL_JOB_NUMBER] for r in records]

        expected_jobs = [p.job_number for p in
                         [current_project, recent_project]]

        self.assertEqual(set(expected_jobs), set(jobs))

    def test_departments(self):
        media_dept = create_client(u"LexCorp Media")
        media_dept.parent = self.client
        media_dept.save()
        security_dept = create_client(u"LexCorp Security")
        security_dept.parent = self.client
        security_dept.save()
        media_contact = create_client_user(
            u'llang@lexcorp.example.com', media_dept,
            first_name=u'Lana',
            last_name=u'Lang')
        security_contact = create_client_user(
            u'alghul@lexcorp.example.com', security_dept,
            first_name=u'Talia',
            last_name=u'al Ghul')

        # make sure we aren't just getting *all* the projects by creating an
        # entirely different client.
        different_client = create_client(u"Quark's Bar")
        quark = create_client_user(u"owner@quarks.example.com", different_client)

        top_level_project = self.create_project("Memo",
                                                client_poc=self.user,
                                                started_timestamp=now())
        self.create_project_details(top_level_project)

        media_project = self.create_project("Press Release",
                                            client_poc=media_contact,
                                            started_timestamp=now())
        self.create_project_details(media_project)

        security_project = self.create_project(u"Reimbursement Form",
                                               client_poc=security_contact,
                                               started_timestamp=now())
        self.create_project_details(security_project)

        other_project = self.create_project(u"Menu",
                                            client_poc=quark,
                                            started_timestamp=now())
        self.create_project_details(other_project)

        top_level_project.quote()
        media_project.quote()
        security_project.quote()
        other_project.quote()

        populate_dwh_reports_data()
        client_reporting = get_object_or_404(ClientsReporting, pk=self.client.id)

        records = ex.get_client_activity_records(client_reporting)

        jobs = [r[ex.COL_JOB_NUMBER] for r in records]

        # expected jobs does not include other_project.
        expected_jobs = [p.job_number for p in
                         [top_level_project, media_project, security_project]]

        self.assertEqual(set(expected_jobs), set(jobs))

        def record_for(project):
            for rec in records:
                if rec[ex.COL_JOB_NUMBER] == project.job_number:
                    return rec
            raise ValueError("Record not found for %r" % (project.job_number,))

        self.assertEqual(self.user.account.name, record_for(top_level_project)[ex.COL_DEPARTMENT])
        self.assertEqual(security_dept.name, record_for(security_project)[ex.COL_DEPARTMENT])
        self.assertEqual(media_dept.name, record_for(media_project)[ex.COL_DEPARTMENT])

        for rec in records:
            self.assertEqual(self.client.name, rec[ex.COL_CLIENT_NAME])

    def test_multiple_documents(self):
        targets = [self.russian]
        project = self.create_project(
            u"Charter and Bylaws",
            targets=targets,
            client_poc=self.user,
            started_timestamp=now() - timedelta(days=6),
            delivered=now()
        )

        word_rate = Decimal('0.230')

        task_factory = TaskFactory(project)

        client_price = task_factory.create_ttcp(
            source_of_client_prices=-1,
            word_rate=word_rate,
            expansion_rate=1.25,
            minimum_price=0.0
        )

        source_docs = [
            ('Charter.odt', 1000),
            ('Bylaws.odt', 3000),
        ]

        for filename, word_count in source_docs:
            source_file = FileAsset.objects.create(
                kit=project.kit,
                asset_type=SOURCEFILE_ASSET,
                orig_name=filename,
            )
            FileAnalysis.objects.create(
                asset=source_file,
                no_match=word_count,
                source_locale=project.source_locale,
                target_locale=targets[0]
            )

        task_analysis = TranslationTaskAnalysis.objects.create_from_kit(
            project.kit, targets[0]
        )
        task = task_factory.create_tep_task(
            TASK_COMPLETED_STATUS,
            analysis=task_analysis,
            client_price=client_price)

        TaskLocaleTranslationKit.objects.create(
            task=task,
        )

        quote = project.quote()
        populate_dwh_reports_data()
        client_reporting = get_object_or_404(ClientsReporting, pk=self.client.id)

        records = ex.get_client_activity_records(client_reporting)

        self.assertEqual(2, len(records))

        expansion_rate = Decimal(1.25)
        for filename, word_count in source_docs:
            subset = [r for r in records if filename in r[ex.COL_FILENAME]]
            self.assertEqual(1, len(subset), "expected one record for %r" % (filename,))
            record = subset[0]
            price = record[ex.COL_PRICE]
            expected_price = word_count * expansion_rate * Decimal(word_rate)
            self.assertEqual(word_count, record[ex.COL_WORD_COUNT])
            self.assertEqual(expected_price, price)

    def _create_multitarget_project_with_pricing(self, targets, rates,
                                                 word_count, filename):
        project = self.create_project(
            u"Rights and Responsibilities",
            targets=targets,
            client_poc=self.user,
            started_timestamp=now() - timedelta(days=6),
            delivered=now()
        )
        task_factory = TaskFactory(project)
        source_file = FileAsset.objects.create(
            kit=project.kit,
            asset_type=SOURCEFILE_ASSET,
            orig_name=filename,
        )
        for target in targets:
            word_rate = rates[target.lcid]

            FileAnalysis.objects.create(
                asset=source_file,
                no_match=word_count,
                source_locale=project.source_locale,
                target_locale=target
            )
            task_analysis = TranslationTaskAnalysis.objects.create_from_kit(
                project.kit, target
            )

            client_price = task_factory.create_ttcp(
                source_of_client_prices=-1,
                word_rate=word_rate,
                expansion_rate=1.25,
                minimum_price=0.0
            )

            task = task_factory.create_tep_task(
                TASK_COMPLETED_STATUS,
                target=target,
                analysis=task_analysis,
                client_price=client_price)

            TaskLocaleTranslationKit.objects.create(
                task=task,
            )

        return project

    def test_multiple_targets(self):
        # one document, two targets
        turkish = Locale.objects.get(lcid=1055)
        #: :type: list of Locale
        targets = [self.russian, turkish]
        filename = 'R-and-R.odt'
        word_count = 10000
        rates = {
            self.russian.lcid: Decimal('0.170'),
            turkish.lcid: Decimal('0.320')
        }

        project = self._create_multitarget_project_with_pricing(
            targets, rates, word_count, filename)

        quote = project.quote()
        populate_dwh_reports_data()
        client_reporting = get_object_or_404(ClientsReporting, pk=self.client.id)

        records = ex.get_client_activity_records(client_reporting)

        self.assertEqual(len(targets), len(records))

        expansion_rate = Decimal(1.25)
        for target in targets:
            word_rate = rates[target.lcid]
            subset = [r for r in records if target.description in r[ex.COL_TARGET]]
            self.assertEqual(1, len(subset),
                             "expected one record for %r" % (target.description,))

            record = subset[0]
            price = record[ex.COL_PRICE]
            expected_price = Decimal(word_rate) * expansion_rate * word_count
            self.assertEqual(
                expected_price, price,
                "Wrong price for %r, expected %r, got %r" % (
                    target.description, expected_price, price))

    def test_nontranslation_breakdown(self):
        # one document, two targets, plus third-party review on turkish
        turkish = Locale.objects.get(lcid=1055)
        #: :type: list of Locale
        targets = [self.russian, turkish]
        filename = 'R-and-R.odt'
        word_count = 10000
        rates = {
            self.russian.lcid: Decimal('0.170'),
            turkish.lcid: Decimal('0.320')
        }
        review_rate = Decimal('0.125')

        project = self._create_multitarget_project_with_pricing(
            targets, rates, word_count, filename)

        translation_task = project.task_set.get(translationtask__analysis__target=turkish)

        review_task = TaskFactory(project, turkish).create_review_task(
            TASK_COMPLETED_STATUS,
            predecessor=translation_task,
            unit_price=review_rate,
            quantity=word_count
        )

        quote = project.quote()
        populate_dwh_reports_data()
        client_reporting = get_object_or_404(ClientsReporting, pk=self.client.id)

        records = ex.get_client_activity_records(client_reporting)

        self.assertEqual(len(targets) + 1, len(records))

        tpr = ServiceType.objects.get(code=THIRD_PARTY_REVIEW_SERVICE_TYPE)

        subset = [r for r in records if r[ex.COL_TASK_TYPE] == tpr.description]

        self.assertEqual(1, len(subset), "expected one record for review task")

        record = subset[0]
        self.assertEqual(word_count * review_rate, record[ex.COL_PRICE])
        self.assertEqual(turkish.description, record[ex.COL_TARGET])
