# -*- coding: utf-8 -*-
from decimal import Decimal
from django.test import TestCase
from localization_kits.models import FileAnalysis, FileAsset, SOURCEFILE_ASSET
from projects.states import TASK_COMPLETED_STATUS
from shared.datafactory import create_project, TaskFactory
from tasks.models import Task, TranslationTaskClientPrice, \
    TranslationTaskAnalysis


class TestTaskManagerMixin(TestCase):
    def setUp(self):
        self.project = create_project(self.id())
        self.task_factory = TaskFactory(self.project)

    def test_select_for_pricing_translation_task(self):
        target = self.task_factory.target
        word_rate=Decimal('0.10')

        client_price = self.task_factory.create_ttcp(
            source_of_client_prices=-1,
            word_rate=word_rate,
            expansion_rate=1.25,
            minimum_price=0.0
        )

        source_file = FileAsset.objects.create(
            kit=self.project.kit,
            asset_type=SOURCEFILE_ASSET,
            orig_name='hello.xlsx',
        )

        FileAnalysis.objects.create(
            asset=source_file,
            no_match=1000,
            source_locale=self.project.source_locale,
            target_locale=target
        )
        task_analysis = TranslationTaskAnalysis.objects.create_from_kit(
            self.project.kit, target
        )

        task = self.task_factory.create_tep_task(
            TASK_COMPLETED_STATUS,
            analysis=task_analysis,
            client_price=client_price)

        # 3 is about as low as we can get as long as we're summing itemized
        # prices. An optimized TranslationTaskClientPrice.total_price
        # might knock it down to 2, or we could cache the calculated value
        # instead of going back to analysis all the time.
        with self.assertNumQueries(8):
            fetched_task = Task.objects.select_for_pricing().get(id=task.id)
            price = fetched_task.itemized_price_details()

        self.assertIsNotNone(price)


    def test_select_for_pricing_nontranslation_task(self):
        task = self.task_factory.create_review_task(
            TASK_COMPLETED_STATUS,
            unit_price=Decimal('0.060'),
            quantity=1000
        )

        with self.assertNumQueries(1):
            fetched_task = Task.objects.select_for_pricing().get(id=task.id)
            price = fetched_task.nontranslationtask.standard_price()

        self.assertIsNotNone(price)
