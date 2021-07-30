# -*- coding: utf-8 -*-
from decimal import Decimal
from django.test import TestCase
from localization_kits.models import FileAsset, SOURCEFILE_ASSET, FileAnalysis
from prices.models import ClientTranslationPrice, ClientNonTranslationPrice, \
    VendorTranslationRate
from projects.models import STANDARD_SPEED
from projects.quote import QuoteItem, LEVEL_TASK, LEVEL_ASSET, \
    LEVEL_LANGUAGE, LEVEL_PROJECT
from projects.states import CREATED_STATUS, TASK_CREATED_STATUS
from services.managers import TRANSLATION_EDIT_PROOF_SERVICE_TYPE
from services.models import Locale
from shared.datafactory import create_project, TaskFactory
from tasks.models import Task

LCID_ES = 1034
LCID_RU = 1049


def scenario(project_name):
    # construct big honking integration test scenario
    # two targets, two assets, TEP and PM tasks.

    es = Locale.objects.get(lcid=LCID_ES)
    ru = Locale.objects.get(lcid=LCID_RU)
    targets = [es, ru]
    project = create_project(project_name, targets, status=CREATED_STATUS)
    asset1 = FileAsset.objects.create(
        orig_name='File One.odt', kit=project.kit,
        asset_type=SOURCEFILE_ASSET)
    asset2 = FileAsset.objects.create(
        orig_name='File Two.odt', kit=project.kit,
        asset_type=SOURCEFILE_ASSET)
    assets = [asset1, asset2]
    word_count = 3000
    task_factory = TaskFactory(project)
    tasks = []
    for target in targets:
        tep_task = task_factory.create_tep_task(TASK_CREATED_STATUS, target, standard_days=2)
        pm_task = task_factory.create_pm_task(TASK_CREATED_STATUS, target)
        cd_task = task_factory.create_client_discount_task(TASK_CREATED_STATUS, target)

        tasks.extend([tep_task, pm_task, cd_task])

        tep_price = ClientTranslationPrice.objects.create(
            service=tep_task.service,
            minimum_price=0,
            word_rate=Decimal('0.30')
        )
        tep_task.set_from_client_price(tep_price)

        tep_cost = VendorTranslationRate.objects.create(
            service=tep_task.service,
            word_rate=Decimal('0.12')
        )
        tep_task.set_from_vendor_rate(tep_cost)

        pm_price = ClientNonTranslationPrice.objects.create(
            service=pm_task.service,
            unit_price=Decimal('0.10')
        )
        pm_task.set_from_client_price(pm_price)

        cd_price = ClientNonTranslationPrice.objects.create(
            service=cd_task.service,
            unit_price=Decimal('-0.20')
        )
        cd_task.set_from_client_price(cd_price)

        for asset in assets:
            FileAnalysis.objects.create(
                asset=asset,
                no_match=word_count,
                target_locale=target
            )
    return project, tasks


class TestProjectQuote(TestCase):
    def setUp(self):
        project, tasks = scenario(self.id())

        self.project = project
        self.tasks = tasks

    def test_total(self):
        quote = self.project.quote()
        self.assertEqual(LEVEL_PROJECT, quote.total.level)
        self.assertEqual(Decimal('3168.00'), quote.total.price)
        self.assertEqual(2, quote.total.turn_around_time)

    def test_targets(self):
        quote = self.project.quote()
        target_quotes = quote.targets.items()

        self.assertEqual(2, len(target_quotes))

        self.assertEqual(LCID_RU, target_quotes[0][0].lcid)
        self.assertEqual(LCID_ES, target_quotes[1][0].lcid)

        self.assertEqual(Decimal('1584.00'), target_quotes[0][1].price)
        self.assertEqual(Decimal('1584.00'), target_quotes[1][1].price)

    def test_project_pricequote(self):
        quote = self.project.quote()
        pq = quote.project.project_pricequote()
        self.assertIsNotNone(pq)
        self.assertEqual(pq.price, Decimal('3168.00'))
        self.assertEqual(pq.express_price, Decimal('4752.00'))

    def test_project_original_price(self):
        quote = self.project.quote()
        original_price_standard, original_price_express = quote.project.project_original_price()
        self.assertNotEquals(original_price_standard, original_price_express)
        self.assertEqual(original_price_standard, Decimal('3960.00'))
        self.assertEqual(original_price_express, Decimal('5940.00'))


class TestQuoteItem(TestCase):

    def setUp(self):
        project, tasks = scenario(self.id())

        self.project = project
        # convert from Task subclass to generic Task
        self.tasks = [Task.objects.get(id=t.id) for t in tasks]

    def test_create_from_task(self):
        tep_task = self.tasks[0]
        summary, items = QuoteItem.create_from_task(tep_task, STANDARD_SPEED)
        self.assertEqual(LEVEL_TASK, summary.level)
        self.assertEqual(STANDARD_SPEED, summary.speed)
        self.assertEqual(LCID_ES, summary.target.lcid)
        self.assertEqual(None, summary.asset)
        self.assertEqual(6000, summary.analysis.no_match)
        self.assertEqual(1800, summary.raw_price)
        self.assertEqual(1800, summary.price)
        self.assertEqual(0, summary.memory_bank_discount)
        self.assertEqual(720, summary.cost)
        self.assertEqual(2, summary.turn_around_time)

        self.assertEqual(2, len(items))
        self.assertEqual(LEVEL_ASSET, items[0].level)
        self.assertEqual("File One.odt", items[0].asset.orig_name)
        self.assertEqual(3000, items[0].analysis.no_match)
        self.assertEqual(360, items[0].cost)

    def test_create_from_percentage_task(self):
        pm_task = self.tasks[1]

        base_tasks = [t for t in self.tasks if
                      t.service.service_type.code == TRANSLATION_EDIT_PROOF_SERVICE_TYPE]

        base_quote_items = [QuoteItem.create_from_task(t, STANDARD_SPEED)[0]
                            for t in base_tasks]

        summary, items = QuoteItem.create_from_percentage_task(
            pm_task, base_quote_items, STANDARD_SPEED)
        self.assertEqual(LEVEL_TASK, summary.level)
        self.assertEqual(STANDARD_SPEED, summary.speed)
        self.assertEqual(LCID_ES, summary.target.lcid)
        self.assertEqual(None, summary.asset)
        self.assertEqual(180, summary.price)

        self.assertEqual(2, len(items))
        self.assertEqual("File One.odt", items[0].asset.orig_name)
        self.assertEqual(LEVEL_ASSET, items[0].level)
        self.assertEqual(90, items[0].price)

    def test_summarize_tasks_to_target(self):
        speed = STANDARD_SPEED
        tep_task, pm_task = self.tasks[:2]
        tep_item = QuoteItem.create_from_task(tep_task, speed)[0]
        pm_item = QuoteItem.create_from_percentage_task(pm_task, [tep_item], speed)[0]

        target_item = QuoteItem.summarize([tep_item, pm_item])
        self.assertEqual(LEVEL_LANGUAGE, target_item.level)
        self.assertEqual(1980, target_item.price)
        self.assertEqual(6000, target_item.analysis.no_match)
