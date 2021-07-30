# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.messages import SUCCESS
from django.test import TestCase
from django.utils import timezone

from localization_kits.models import FileAsset, SOURCEFILE_ASSET, FileAnalysis
from projects.models import MANUAL_ESTIMATE
from projects.states import TASK_CREATED_STATUS
from services.managers import TRANSLATION_EDIT_PROOF_SERVICE_TYPE, \
    POST_PROCESS_SERVICE_TYPE, FINAL_APPROVAL_SERVICE_TYPE, \
    FEEDBACK_MANAGEMENT_SERVICE_TYPE, DISCOUNT_SERVICE_TYPE
from services.models import ServiceType
from shared.datafactory import create_project, TaskFactory
from tasks import make_tasks
from tasks.make_tasks import _get_client_discount, _add_client_discount, _verify_add_client_discount_task, \
    _verify_client_discount_task, _delete_client_discount
from tasks.models import Task


class TestInsertPostProcessingTask(TestCase):
    def setUp(self):
        self.project = create_project(self.id())
        self.target = self.project.target_locales.first()
        task_factory = TaskFactory(self.project)
        self.tep_task = task_factory.create_tep_task(TASK_CREATED_STATUS)
        self.fa_task = task_factory.create_fa_task(TASK_CREATED_STATUS,
                                                   predecessor=self.tep_task)

    def test_tep(self):
        # noinspection PyProtectedMember
        pp_task = make_tasks._insert_post_processing_task(
            self.project, self.target)

        self.assertIsNotNone(pp_task)

        # We want to reload fa_task as it should have been modified,
        # and .predecessor is easier to compare to a Task than a
        # [Non]TranslationTask.

        tep_task = Task.objects.get(id=self.tep_task.id)
        fa_task = Task.objects.get(id=self.fa_task.id)
        pp_task = Task.objects.get(id=pp_task.id)

        self.assertEqual(tep_task, pp_task.predecessor)
        self.assertEqual(pp_task, fa_task.predecessor)


    def test_do_not_duplicate_post_process(self):
        # noinspection PyProtectedMember
        pp_task = make_tasks._insert_post_processing_task(self.project, self.target)

        self.assertIsNotNone(pp_task)

        # noinspection PyProtectedMember
        pp_task = make_tasks._insert_post_processing_task(self.project, self.target)

        self.assertIsNone(pp_task)

        self.assertEqual(3, self.project.task_set.count())


class TestMakeTasksForTarget(TestCase):

    def setUp(self):
        self.project = create_project(self.id(), estimate_type=MANUAL_ESTIMATE)

        # need an analysis to make tasks (for setting quantities and turn-around)
        asset = FileAsset.objects.create(
            kit=self.project.kit,
            orig_name="source.txt",
            asset_type=SOURCEFILE_ASSET)
        FileAnalysis.objects.create(
            asset=asset,
            source_locale=self.project.source_locale,
            target_locale=self.project.target_locales.first(),
            no_match=1200
        )


    def test_manual_estimate(self):
        project = self.project

        tep_service = ServiceType.objects.get(
            code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE)
        project.services.add(tep_service)

        target = project.target_locales.first()

        # noinspection PyProtectedMember
        status, msg = make_tasks._make_tasks_for_target(project, target)

        self.assertEqual(SUCCESS, status, msg)

        root_task = project.all_root_tasks().first()

        self.assertEqual(TRANSLATION_EDIT_PROOF_SERVICE_TYPE,
                         root_task.service.service_type.code)

        pp_task = project.task_set.get(predecessor=root_task)

        self.assertEqual(POST_PROCESS_SERVICE_TYPE,
                         pp_task.service.service_type.code)

        fa_task = project.task_set.get(predecessor=pp_task)

        self.assertEqual(FINAL_APPROVAL_SERVICE_TYPE,
                         fa_task.service.service_type.code)

        self.assertEqual(3, project.task_set.count())



class TestMakeNonWorkflowTasks(TestCase):
    def setUp(self):
        self.project = create_project(self.id(), estimate_type=MANUAL_ESTIMATE)

        # need an analysis to make tasks (for setting quantities and turn-around)
        asset = FileAsset.objects.create(
            kit=self.project.kit,
            orig_name="source.txt",
            asset_type=SOURCEFILE_ASSET)
        FileAnalysis.objects.create(
            asset=asset,
            source_locale=self.project.source_locale,
            target_locale=self.project.target_locales.first(),
            no_match=1200
        )

    def test_feedback_task(self):
        project = self.project
        feedback_service = ServiceType.objects.get(
            code=FEEDBACK_MANAGEMENT_SERVICE_TYPE)
        project.services.add(feedback_service)

        target = project.target_locales.first()

        # noinspection PyProtectedMember
        make_tasks._make_non_workflow_tasks(project, target, 1200, False)

        feedback_tasks = project.task_set.filter(
            service__service_type=feedback_service)

        self.assertEqual(1, len(feedback_tasks))
        feedback_task = feedback_tasks[0]
        self.assertEqual(settings.FEEDBACK_MANAGEMENT_MIN_HOURS, feedback_task.quantity())

    def test_get_client_discount_yes(self):
        project = self.project
        cd = _get_client_discount(project.client.id, '2017-01-15')
        self.assertEqual(1, len(cd))

    def test_get_client_discount_no(self):
        project = self.project
        cd = _get_client_discount(project.client.id, '2017-02-15')
        self.assertEqual(0, len(cd))

    def test_add_client_discount(self):
        project = self.project
        cd = _add_client_discount(project)
        self.assertEqual(True, cd)

    def test_verify_add_client_discount_task_yes(self):
        project = self.project
        project.created = '2017-01-15'
        project.save()
        _delete_client_discount(project)
        cd = _verify_add_client_discount_task(project)
        self.assertEqual(True, cd)

    def test_verify_add_client_discount_task_no(self):
        project = self.project
        project.created = '2017-02-15'
        project.save()
        cd = _verify_add_client_discount_task(project)
        self.assertEqual(False, cd)

    def test_verify_client_discount_task_yes(self):
        project = self.project
        project.created = '2017-01-15'
        project.save()
        cd = _verify_client_discount_task(project)
        self.assertEqual(False, cd)

    def test_verify_client_discount_task_no(self):
        project = self.project
        project.created = '2017-02-15'
        project.save()
        cd = _verify_client_discount_task(project)
        self.assertEqual(False, cd)
