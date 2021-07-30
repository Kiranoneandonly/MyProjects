from django.test import TestCase
from projects.states import TASK_ACTIVE_STATUS, TASK_CREATED_STATUS
from services.models import Locale
from shared.datafactory import create_project, TaskFactory
from shared.viewmodels import ProjectTargetViewModel


class TestProjectTargetViewModel(TestCase):

    def setUp(self):
        portugal = Locale.objects.get(lcid=2070)
        self.russian = Locale.objects.get(lcid=1049)
        self.project = create_project(u"The Encyclopedia",
                                      [self.russian, portugal])

        russian_task_factory = TaskFactory(self.project, self.russian)
        self.task_tep_russian = russian_task_factory.create_tep_task(
            TASK_ACTIVE_STATUS)
        self.task_fa_russian = russian_task_factory.create_fa_task(
            TASK_CREATED_STATUS)

        portugal_task_factory = TaskFactory(self.project, portugal)
        self.task_tep_portugal = portugal_task_factory.create_tep_task(
            TASK_ACTIVE_STATUS)
        self.task_fa_portugal = portugal_task_factory.create_fa_task(
            TASK_CREATED_STATUS)


    def test_tasks_has_only_target_locale(self):
        view_model = ProjectTargetViewModel(
            self.project, self.russian
        )
        tasks = view_model.tasks
        self.assertEqual(len(tasks), 2)
        # compare tasks by ID because Task != TranslationTask
        self.assertEqual([t.id for t in tasks], [self.task_tep_russian.id, self.task_fa_russian.id])
