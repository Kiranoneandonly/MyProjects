# -*- coding: utf-8 -*-
from django.test import TestCase
from projects.states import TASK_COMPLETED_STATUS
from shared.datafactory import TaskFactory, create_project
from tasks.models import TaskLocaleTranslationKit, Task, TaskLocalizedAsset
from vendor_portal.authorization import task_owns_tltk, task_owns_tla


class TestTaskOwnsTLTK(TestCase):
    def setUp(self):
        project = create_project(self.id())
        self.task_factory = TaskFactory(project)
        self.task = self.task_factory.create_tep_task(TASK_COMPLETED_STATUS)


    def test_task_owns_tltk(self):
        tltk = TaskLocaleTranslationKit.objects.create(task=self.task)
        task = Task.objects.get(id=self.task.id)
        self.assertTrue(task_owns_tltk(task, tltk.id))


    def test_task_owns_tltk_false(self):
        tltk = TaskLocaleTranslationKit.objects.create(task=self.task)
        other_task = self.task_factory.create_tep_task(TASK_COMPLETED_STATUS)
        self.assertFalse(task_owns_tltk(other_task, tltk.id))



class TestTaskOwnsTLA(TestCase):
    def setUp(self):
        project = create_project(self.id())
        self.task_factory = TaskFactory(project)
        self.task = self.task_factory.create_tep_task(TASK_COMPLETED_STATUS)


    def test_task_owns_tla(self):
        tla_1 = TaskLocalizedAsset.objects.create(task=self.task)
        tla_2 = TaskLocalizedAsset.objects.create(task=self.task)
        task = Task.objects.get(id=self.task.id)
        self.assertTrue(task_owns_tla(task, tla_1.id))
        self.assertTrue(task_owns_tla(task, tla_2.id))


    def test_task_owns_tla_false(self):
        tla_1 = TaskLocalizedAsset.objects.create(task=self.task)
        other_task = self.task_factory.create_tep_task(TASK_COMPLETED_STATUS)
        self.assertFalse(task_owns_tla(other_task, tla_1.id))
