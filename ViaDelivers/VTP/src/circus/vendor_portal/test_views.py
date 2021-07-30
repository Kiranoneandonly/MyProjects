from django.test import TestCase
from django.core.urlresolvers import reverse
from mock import patch
from projects.states import TASK_COMPLETED_STATUS
from shared.datafactory import create_project, TaskFactory, create_vendor_user
from shared.unittest_help import PageObject
from tasks.models import TaskLocalizedAsset
from vendor_portal.views import VendorTaskDetailView
import vendor_portal.urls


class TaskDetailViewPage(PageObject):
    view_name = 'vendor_task_detail'

    def __init__(self, response, *view_args, **view_kwargs):
        super(TaskDetailViewPage, self).__init__(response, *view_args, **view_kwargs)
        self.task_id = view_kwargs['pk']

    @classmethod
    def credentials(cls):
        return create_vendor_user()[1]


    @property
    def task_files_section(self):
        return self.doc('#task_files_section')


    @property
    def output_zip_link(self):
        output_zip_url = reverse('task_output_files_zip', args=(self.task_id,))
        section = self.task_files_section
        return section("a[href='%s']" % (output_zip_url,))


class TestVendorTaskDetailView(TestCase):

    def setUp(self):
        task_status = TASK_COMPLETED_STATUS
        project = create_project(self.id(), )
        task_factory = TaskFactory(project, project.target_locales.first())
        # FA tasks may have multiple delivery files
        self.task = task_factory.create_fa_task(task_status)

        # noinspection PyUnresolvedReferences
        patcher = patch.object(vendor_portal.urls.protected_task, 'condition',
                               lambda model, user: True)
        patcher.start()
        self.addCleanup(patcher.stop)


    def test_download_all_output_not_shown_for_single_output(self):
        names = ['All_Chapters']
        for name in names:
            TaskLocalizedAsset.objects.create(
                task=self.task,
                name=name,
                input_file=name + '_in.txt',
                output_file=name + '_out.txt',
            )

        # sanity check
        self.assertEqual(len(self.task.files), len(names))

        # Get the page!
        page = TaskDetailViewPage.get(self.client, pk=self.task.id)
        response = page.response

        # Assertions
        self.assertEqual(response.status_code, 200, response.get('location'))
        self.assertTemplateUsed(response, VendorTaskDetailView.template_name)

        self.assertFalse(page.output_zip_link)


    def test_download_all_output_for_multiple_outputs(self):
        names = ['Chapter_1', 'Chapter_2']
        for name in names:
            TaskLocalizedAsset.objects.create(
                task=self.task,
                name=name,
                input_file=name + '_in.txt',
                output_file=name + '_out.txt',
            )

        # sanity check
        self.assertEqual(len(self.task.files), len(names))

        # Get the page!
        page = TaskDetailViewPage.get(self.client, pk=self.task.id)
        response = page.response

        # Assertions
        self.assertEqual(response.status_code, 200, response.get('location'))
        self.assertTemplateUsed(response, VendorTaskDetailView.template_name)

        self.assertTrue(page.output_zip_link)


    def test_download_all_output_not_shown_when_output_not_ready(self):
        names = ['Chapter_1', 'Chapter_2']
        for name in names:
            TaskLocalizedAsset.objects.create(
                task=self.task,
                name=name,
                input_file=name + '_in.txt',
                # This task has no output files.
            )

        # sanity check
        self.assertEqual(len(self.task.files), len(names))

        # Get the page!
        page = TaskDetailViewPage.get(self.client, pk=self.task.id)
        response = page.response

        # Assertions
        self.assertEqual(response.status_code, 200, response.get('location'))
        self.assertTemplateUsed(response, VendorTaskDetailView.template_name)

        self.assertFalse(page.output_zip_link)
