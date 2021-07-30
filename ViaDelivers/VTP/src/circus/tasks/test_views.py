# -*- coding: utf-8 -*-
from posixpath import dirname
from urlparse import urlsplit
from django.conf import settings
from django.contrib.messages import get_messages, SUCCESS
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import SuspiciousOperation

from django.core.urlresolvers import resolve, reverse
from django.test import TestCase, RequestFactory
from mock import patch
from accounts.models import CircusUser

from projects.states import TASK_ACTIVE_STATUS, TASK_CREATED_STATUS
from shared.datafactory import create_project, TaskFactory, create_via_user
from shared.unittest_help import PageObject, ViewTestCase
from tasks.models import TaskLocaleTranslationKit, Task
from tasks.views import TaskUpdateView, supplier_reference_redirect
from via_portal.authorization import any_via_user


class TaskEditPage(PageObject):
    view_name = 'projects_tasks_edit'


    @classmethod
    def credentials(cls):
        return create_via_user()[1]


    def reference_file_link(self):
        a = self.doc("a.reference_file")
        if a:
            href = a[0].attrib['href']
            text = a[0].text
            return href, text

        return None



class TestTaskUpdateView(TestCase):
    def setUp(self):
        self.project = create_project(self.id())
        task_factory = TaskFactory(self.project)
        # TODO: Test with both Translation and Non-Translation tasks
        self.task = task_factory.create_tep_task(TASK_ACTIVE_STATUS)
        # normalize to Task rather than the TranslationTask
        self.task = Task.objects.get(id=self.task.id)
        self.tltk = TaskLocaleTranslationKit.objects.create(task=self.task)


    def test_reference_file_absent(self):
        page = TaskEditPage.get(self.client, self.task.id)
        self.assertIsNone(page.reference_file_link())


    def test_reference_file_shown(self):
        filename = "foo/bar/baz.doc"
        self.task.reference_file = filename
        self.task.save()

        page = TaskEditPage.get(self.client, self.task.id)

        response = page.response
        self.assertEqual(response.status_code, 200, response.get('location'))

        link = page.reference_file_link()
        self.assertIsNotNone(link)

        text = link[1]

        self.assertIn('baz.doc', text)
        self.assertNotIn('foo/bar', text)


    def test_reference_upload_form(self):
        view = TaskUpdateView()
        form = view.reference_upload_form(self.task)
        # loose tests at least make sure we're in the right ballpark
        self.assertTrue(form.key.startswith('media/'), form.key)
        path = urlsplit(form.success_action_redirect)[2]
        view_on_success = resolve(path)
        self.assertEqual({'task_id': str(self.task.id)},
                         view_on_success.kwargs)


class TestReferenceS3FileRedirectHandler(TestCase):
    def setUp(self):
        self.project = create_project(self.id())
        task_factory = TaskFactory(self.project)
        # TODO: Test with both Translation and Non-Translation tasks
        self.task = task_factory.create_tep_task(TASK_ACTIVE_STATUS)
        # normalize to Task rather than the TranslationTask
        self.task = Task.objects.get(id=self.task.id)
        self.tltk = TaskLocaleTranslationKit.objects.create(task=self.task)
        self.user = CircusUser.objects.create_user(email='jacob@…', password='top_secret')

    def make_request(self, s3_params):
        request = RequestFactory().get('', s3_params)
        # Recall that middleware are not supported. You can simulate a logged-in user by setting request.user manually.
        request.user = self.user
        SessionMiddleware().process_request(request)
        MessageMiddleware().process_request(request)
        return request

    def test_happy(self):
        filename = 'frog.txt'
        expected_asset_path = self.task.reference_file.field.generate_filename(
            self.task, filename)
        import re
        if re.search(r"\\+", expected_asset_path):
            expected_asset_path = re.sub(r"\\+", '/', expected_asset_path)

        s3_key = settings.MEDIA_URL[1:] + expected_asset_path

        s3_params = {'key': s3_key,
                     'bucket': settings.AWS_STORAGE_BUCKET_NAME}

        request = self.make_request(s3_params)

        response = supplier_reference_redirect(request, str(self.task.id))

        # req comes in with
        #  key='the path'
        #  tltk=id

        task = Task.objects.get(id=self.task.id)

        # reference_file should not have leading media directory
        self.assertEqual(expected_asset_path, task.reference_file)

        # redirect
        self.assertEqual(302, response.status_code)
        view_on_success = resolve(response.url)
        self.assertEqual({'pk': str(self.task.id)},
                         view_on_success.kwargs)
        self.assertEqual('projects_tasks_edit', view_on_success.url_name)

        messages = list(get_messages(request))
        self.assertEqual(1, len(messages))

        self.assertIn(filename, messages[0].message)
        self.assertNotIn(dirname(expected_asset_path), messages[0].message)
        self.assertEqual(SUCCESS, messages[0].level)


    def test_funny_bucket(self):
        s3_key = 'media/foo/bar/baz/frog.txt'
        s3_params = {'bucket': 'weird_thing', 'key': s3_key}
        request = self.make_request(s3_params)

        with self.assertRaises(SuspiciousOperation):
            supplier_reference_redirect(request, str(self.task.id))

        # reference_file should remain unchanged
        task = Task.objects.get(id=self.task.id)
        self.assertFalse(task.reference_file)


    def test_funny_key(self):
        # req comes in with funny key
        s3_key = settings.MEDIA_URL[1:] + 'blah/quux/snow.txt'
        s3_params = {'bucket': settings.AWS_STORAGE_BUCKET_NAME,
                     'key': s3_key}

        request = self.make_request(s3_params)

        with self.assertRaises(SuspiciousOperation):
            supplier_reference_redirect(request, str(self.task.id))

        # reference_file should remain unchanged
        task = Task.objects.get(id=self.task.id)
        self.assertFalse(task.reference_file)


    def test_bad_id(self):
        filename = 'frog.txt'
        bad_task_id = (self.task.id + 37) * 13
        asset_path = self.task.reference_file.field.generate_filename(
            self.task, filename)
        import re
        if re.search(r"\\+", asset_path):
            asset_path = re.sub(r"\\+", '/', asset_path)
        s3_key = settings.MEDIA_URL[1:] + asset_path
        s3_params = {'key': s3_key,
                     'bucket': settings.AWS_STORAGE_BUCKET_NAME}
        request = self.make_request(s3_params)

        with self.assertRaises(Exception):
            supplier_reference_redirect(request, bad_task_id)

        # reference_file should remain unchanged
        task = Task.objects.get(id=self.task.id)
        self.assertFalse(task.reference_file)


    # CSRF attacks we currently *don't* protect against:
    #
    #  * Setting reference_file to a nonexistent file in the same directory.
    #
    #  * If user uploads file A, later replaces it with uploading file B,
    #    the redirect from A may be replayed to effectively undo the later
    #    setting.


class TestDeleteTask(ViewTestCase):
    def test_delete_task_can_delete_task_no(self):
        project = create_project(self.id())
        task = TaskFactory(project).create_tep_task(TASK_ACTIVE_STATUS)
        task_id = task.id
        url = reverse('projects_tasks_delete', args=(task_id,))

        # noinspection PyUnresolvedReferences
        with patch.object(any_via_user, 'condition') as protector_condition:
            protector_condition.return_value = True
            response = self.client.get(url)

        # assert it does still exist
        self.assertTrue(Task.objects.filter(id=task_id).exists())

        self.assertRedirectsToName(response, 'via_job_detail_tasks',
                                   pk=str(project.id))

    def test_delete_task_can_delete_task_yes(self):
        project = create_project(self.id())
        task = TaskFactory(project).create_tep_task(TASK_ACTIVE_STATUS)
        task_r = TaskFactory(project).create_review_task(TASK_CREATED_STATUS)
        task_r.predecessor = task
        task_r.save()
        task_r_id = task_r.id

        url = reverse('projects_tasks_delete', args=(task_r_id,))

        # noinspection PyUnresolvedReferences
        with patch.object(any_via_user, 'condition') as protector_condition:
            protector_condition.return_value = True
            response = self.client.get(url)

        # assert it doesn't still exist
        self.assertFalse(Task.objects.filter(id=task_r_id).exists())

        self.assertRedirectsToName(response, 'via_job_detail_tasks',
                                   pk=str(project.id))
