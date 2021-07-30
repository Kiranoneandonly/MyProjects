# -*- coding: utf-8 -*-
from django.test import TestCase
from prices.models import ClientTranslationPrice, ClientNonTranslationPrice, \
    VendorNonTranslationRate
from projects.set_prices import set_price
from projects.states import TASK_CREATED_STATUS
from services.managers import PRICING_SCHEMES_HEALTHCARE, VERTICAL_LEP
from services.models import Vertical, PricingScheme, Locale, Service
from shared.datafactory import create_project, TaskFactory, TranslationPriceFactory, create_client, NonTranslationPriceFactory, \
    create_vendor_user

default_price = 0.230
default_client_price = 0.250
healthcare_price = 0.200

review_default_price = 75
review_default_client_price = 55
review_healthcare_price = 65
review_all_langs_price = 80

review_default_rate = 35
review_all_langs_client_rate = 36
review_all_langs_rate = 37


class TestClientPrices(TestCase):
    def setUp(self):
        project = create_project(self.id())
        self.task_factory = TaskFactory(project)
        self.task = self.task_factory.create_tep_task(TASK_CREATED_STATUS)
        TranslationPriceFactory(default_price, default_client_price, healthcare_price, project.client)
        self.review_task = self.task_factory.create_review_task(TASK_CREATED_STATUS)
        NonTranslationPriceFactory(review_default_price,
                                   review_default_client_price,
                                   review_healthcare_price,
                                   review_all_langs_price,
                                   client=project.client)

    def test_a_task_set_price_mbd_false(self):
        self.task.project.client.manifest.pricing_memory_bank_discount = False
        self.task.project.client.save()
        set_price(self.task)
        # price = ClientTranslationPrice.objects.for_task(self.task)
        # self.task.set_from_client_price(price)
        self.assertEquals(float(self.task.client_price.guaranteed), 1)

    def test_a_task_set_price_mbd_true(self):
        self.task.project.client.manifest.pricing_memory_bank_discount = True
        self.task.project.client.save()
        set_price(self.task)
        self.assertEquals(float(self.task.client_price.guaranteed), 0)

    # TRANSLATION PRICE
    def test_translation_pricing_default(self):
        client2 = create_client(
            name=u"Super Friends",
            vertical=None,
            via_team_jobs_email=u"super-friends@example.com"
        )

        self.task.project.client = client2
        self.task.project.save()
        price = ClientTranslationPrice.objects.for_task(self.task)
        self.assertEquals(float(price.word_rate), default_price)

    def test_client_translation_pricing_default(self):
        client = self.task.project.client
        client.manifest.vertical = None
        client.manifest.pricing_scheme = None
        client.manifest.save()
        price = ClientTranslationPrice.objects.for_task(self.task)
        self.assertEquals(float(price.word_rate), default_client_price)

    def test_client_translation_pricing_healthcare(self):
        client = self.task.project.client
        vertical = Vertical.objects.get(code=VERTICAL_LEP)
        client.manifest.vertical = vertical
        pricing_scheme, created = PricingScheme.objects.get_or_create(code=PRICING_SCHEMES_HEALTHCARE)
        client.manifest.pricing_scheme = pricing_scheme
        client.manifest.save()
        price = ClientTranslationPrice.objects.for_task(self.task)
        self.assertEquals(float(price.word_rate), healthcare_price)

    # NON-TRANSLATION PRICE
    def test_non_translation_pricing_default(self):
        client3 = create_client(
            name=u"Xmen",
            vertical=None,
            via_team_jobs_email=u"xmen@example.com"
        )

        self.review_task.project.client = client3
        self.review_task.project.save()

        price = ClientNonTranslationPrice.objects.for_task(self.review_task)
        self.assertEquals(float(price.unit_price), review_default_price)

    def test_client_non_translation_pricing_default(self):
        client = self.review_task.project.client
        client.manifest.vertical = None
        client.manifest.pricing_scheme = None
        client.manifest.save()
        price = ClientNonTranslationPrice.objects.for_task(self.review_task)
        self.assertEquals(float(price.unit_price), review_default_client_price)

    def test_client_non_translation_pricing_healthcare(self):
        client = self.review_task.project.client
        vertical = Vertical.objects.get(code=VERTICAL_LEP)
        client.manifest.vertical = vertical
        pricing_scheme, created = PricingScheme.objects.get_or_create(code=PRICING_SCHEMES_HEALTHCARE)
        client.manifest.pricing_scheme = pricing_scheme
        client.manifest.save()
        price = ClientNonTranslationPrice.objects.for_task(self.review_task)
        self.assertEquals(float(price.unit_price), review_healthcare_price)


    def test_non_translation_pricing_all_language_catchall(self):
        # There is no review price specifically for this target. It should get
        # the catch all rate (with service.target=None).
        filipino = Locale.objects.get(lcid=1124)
        task = self.task_factory.create_review_task(TASK_CREATED_STATUS,
                                                    target=filipino)
        price = ClientNonTranslationPrice.objects.for_task(task)
        self.assertEquals(float(price.unit_price), review_all_langs_price)


class TestVendorRates(TestCase):
    def setUp(self):
        project = create_project(self.id())
        self.task_factory = TaskFactory(project)

        vendor_user = create_vendor_user()[0]
        self.vendor = vendor_user.account

        self.review_task = self.task_factory.create_review_task(
            TASK_CREATED_STATUS,
            assigned_to=self.vendor
        )

        # A rate exactly matching our client and service.
        VendorNonTranslationRate.objects.create(
            vendor=self.vendor,
            client=project.client,
            service=self.review_task.service,
            unit_cost=review_default_rate,
        )

        all_languages_service = Service.objects.create(
            service_type=self.review_task.service.service_type,
            unit_of_measure=self.review_task.service.unit_of_measure,
            source=None,
            target=None
        )
        # Rate for all languages for this particular client.
        VendorNonTranslationRate.objects.create(
            vendor=self.vendor,
            client=project.client,
            service=all_languages_service,
            unit_cost=review_all_langs_client_rate,
        )
        # Rate for all review tasks for all clients.
        VendorNonTranslationRate.objects.create(
            vendor=self.vendor,
            service=all_languages_service,
            unit_cost=review_all_langs_rate,
        )


    # todo need to implement vendor rate tests

    def test_search_by_basic_vendor(self):
        rate = VendorNonTranslationRate.objects.for_task(self.review_task)
        self.assertEqual(review_default_rate, rate.unit_cost)


    def test_all_langs(self):
        # There is no review rate specifically for this target. It should get
        # the catch all rate for this client (with service.target=None).
        filipino = Locale.objects.get(lcid=1124)
        task = self.task_factory.create_review_task(
            TASK_CREATED_STATUS,
            assigned_to=self.vendor,
            target=filipino
        )
        rate = VendorNonTranslationRate.objects.for_task(task)
        self.assertEqual(review_all_langs_client_rate, rate.unit_cost)
