# -*- coding: utf-8 -*-
from posixpath import dirname
from urlparse import urlparse
from datetime import datetime
from django.conf import settings
from django.contrib.messages import get_messages, SUCCESS
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.exceptions import SuspiciousOperation
from django.core.urlresolvers import resolve, reverse
from django.test import RequestFactory, TestCase
from mock import patch

from localization_kits.models import LocalizationKit, LocaleTranslationKit
from projects.states import TASK_COMPLETED_STATUS, TASK_ACTIVE_STATUS, \
    COMPLETED_STATUS
from services.models import Locale
from shared.datafactory import create_project, TaskFactory, create_via_user, \
    create_client, create_client_user
from shared.unittest_help import ViewTestCase, PageObject
from tasks.models import Task

from via_portal.views import ltk_reference_upload_redirect, ViaDashboardView, ProjectListView
from via_portal import views


class TestLTKReferenceUploadRedirect(TestCase):
    def setUp(self):
        self.loc_kit = LocalizationKit.objects.create()
        self.project = create_project(self.id(), kit=self.loc_kit)
        self.ltk = LocaleTranslationKit.objects.create(
            kit=self.loc_kit,
            target_locale=Locale.objects.get(lcid=1049))


    def make_request(self, s3_params):
        request = RequestFactory().get('', s3_params)
        SessionMiddleware().process_request(request)
        MessageMiddleware().process_request(request)
        return request


    def test_happy(self):
        filename = 'newt.txt'
        expected_asset_path = self.ltk.reference_file.field.generate_filename(self.ltk, filename)
        import re
        if re.search(r"\\+", expected_asset_path):
            expected_asset_path = re.sub(r"\\+", '/', expected_asset_path)
        s3_key = settings.MEDIA_URL[1:] + expected_asset_path
        s3_params = {'key': s3_key,
                     'bucket': settings.AWS_STORAGE_BUCKET_NAME}
        request = self.make_request(s3_params)

        response = ltk_reference_upload_redirect(request, str(self.ltk.id))
        # req comes in with
        #  key='the path'
        #  tltk=id

        ltk = LocaleTranslationKit.objects.get(id=self.ltk.id)

        # reference_file should not have leading media directory
        self.assertEqual(expected_asset_path, ltk.reference_file)

        # redirect
        self.assertEqual(302, response.status_code)
        response_url = urlparse(response.url)
        view_on_success = resolve(response_url.path)
        self.assertEqual({'pk': str(self.project.id)},
                         view_on_success.kwargs)
        self.assertEqual('via_job_detail_files', view_on_success.url_name)
        self.assertEqual('active_tab=loc_kit', response_url.query)

        messages = list(get_messages(request))
        self.assertEqual(1, len(messages))

        self.assertIn(filename, messages[0].message)
        self.assertNotIn(dirname(expected_asset_path), messages[0].message)
        self.assertEqual(SUCCESS, messages[0].level)


    def test_funny_bucket(self):
        s3_key = 'media/foo/bar/baz/newt.txt'
        s3_params = {'bucket': 'weird_thing', 'key': s3_key}
        request = self.make_request(s3_params)

        with self.assertRaises(SuspiciousOperation):
            ltk_reference_upload_redirect(request, str(self.ltk.id))

        # reference_file should remain unchanged
        ltk = LocaleTranslationKit.objects.get(id=self.ltk.id)
        self.assertFalse(ltk.reference_file)


    def test_funny_key(self):
        # req comes in with funny key
        s3_key = settings.MEDIA_URL[1:] + 'blah/quux/snow.txt'
        s3_params = {'bucket': settings.AWS_STORAGE_BUCKET_NAME,
                     'key': s3_key}

        request = self.make_request(s3_params)

        with self.assertRaises(SuspiciousOperation):
            ltk_reference_upload_redirect(request, str(self.ltk.id))

        # reference_file should remain unchanged
        tltk = LocaleTranslationKit.objects.get(id=self.ltk.id)
        self.assertFalse(tltk.reference_file)


    def test_bad_id(self):
        filename = 'newt.txt'
        bad_ltk_id = (self.ltk.id + 37) * 13
        asset_path = self.ltk.reference_file.field.generate_filename(
            self.ltk, filename)
        import re
        if re.search(r"\\+", asset_path):
            asset_path = re.sub(r"\\+", '/', asset_path)
        s3_key = settings.MEDIA_URL[1:] + asset_path
        s3_params = {'key': s3_key,
                     'bucket': settings.AWS_STORAGE_BUCKET_NAME}
        request = self.make_request(s3_params)

        with self.assertRaises(Exception):
            ltk_reference_upload_redirect(request, bad_ltk_id)

        # reference_file should remain unchanged
        tltk = LocaleTranslationKit.objects.get(id=self.ltk.id)
        self.assertFalse(tltk.reference_file)


    # CSRF attacks we currently *don't* protect against:
    #
    #  * Setting reference_file to a nonexistent file in the same directory.
    #
    #  * If user uploads file A, later replaces it with uploading file B,
    #    the redirect from A may be replayed to effectively undo the later
    #    setting.


class TestApproveTask(ViewTestCase):

    def setUp(self):
        self.project = create_project(self.id())
        task_factory = TaskFactory(self.project)
        self.tep = task_factory.create_tep_task(TASK_COMPLETED_STATUS)
        self.fa = task_factory.create_fa_task(TASK_ACTIVE_STATUS, predecessor=self.tep)

        self.task = self.fa

        self.url = reverse('via_approve_task', kwargs={'pk': self.task.id})
        self.update_url = reverse('projects_tasks_edit', kwargs={'pk': self.task.id})

        self.user, credentials = create_via_user('pm@viadelivers.com')
        self.client.login(**credentials)

    def test_delivery_all_tasks_rated_yes(self):
        self.tep.rating = 5
        self.tep.save()

        # noinspection PyUnresolvedReferences
        with patch.object(views, 'notify_client_job_ready') as notify_client:
            response = self.client.post(self.url, {'make_delivery': '1'})

        notify_client.assert_called_once_with(self.project)
        self.assertRedirectsToName(response, 'via_job_detail_overview',
                                   pk=str(self.project.id))
        task = Task.objects.get(id=self.task.id)
        self.assertEqual(TASK_COMPLETED_STATUS, task.status)
        self.assertEqual(COMPLETED_STATUS, task.project.status)
        # assert notify_client_job_ready

    def test_delivery_all_tasks_rated_no(self):
        self.tep.rating = 0
        self.tep.save()
        response = self.client.post(self.update_url, {'task_completed': '1'})
        task = Task.objects.get(id=self.task.id)
        self.assertEqual(TASK_COMPLETED_STATUS, task.status)
        self.assertEqual(COMPLETED_STATUS, task.project.status)

    def test_redelivery(self):
        # Start with project and task already Completed.
        self.project.status = COMPLETED_STATUS
        self.project.save()
        self.task.status = TASK_COMPLETED_STATUS
        self.task.save()
        self.tep.rating = 5
        self.tep.save()

        # noinspection PyUnresolvedReferences
        with patch.object(views, 'notify_client_job_ready') as notify_client:
            response = self.client.post(self.url, {'make_delivery': '1'})

        notify_client.assert_called_once_with(self.project)
        self.assertRedirectsToName(response, 'via_job_detail_overview',
                                   pk=str(self.project.id))
        task = Task.objects.get(id=self.task.id)
        self.assertEqual(TASK_COMPLETED_STATUS, task.status)
        self.assertEqual(COMPLETED_STATUS, task.project.status)


class DashboardPageObject(PageObject):

    view_name = 'via_dashboard'

    @classmethod
    def credentials(cls):
        user, credentials = create_via_user('pm@viadelivers.com')
        return credentials

    def completed_project_count(self):
        return int(self.doc('#completed_count').text())

    def breadcrumb_text(self):
        return self.doc(".breadcrumb").text()


class TestViaDashboardView(ViewTestCase):

    def test_minimal(self):
        page = DashboardPageObject.get(self.client)
        response = page.response
        self.assert_200(response)
        self.assertTemplateUsed(response, ViaDashboardView.template_name)
        self.assertIn('calendar_events', response.context)
        self.assertIn('status_counts', response.context)
        self.assertEqual(0, page.completed_project_count())
        self.assertIn('filter_form', response.context)


    def test_all(self):
        # create projects for multiple clients, they all should appear.
        client_1 = create_client(u'Alphabet')
        client_2 = create_client(u'Soup')
        contact_1 = create_client_user(u'one@alphabet.test', client=client_1)
        contact_2 = create_client_user(u'two@soup.test', client=client_2)
        project_1 = create_project(u'ABCs', client_poc=contact_1)
        project_2 = create_project(u'Noodles', client_poc=contact_2)

        page = DashboardPageObject.get(self.client)
        response = page.response
        self.assert_200(response)

        self.assertEqual(2, response.context['status_counts']['unassigned']['count'])

        titles = [e['title'] for e in response.context['calendar_events']]
        self.assertEqual([project_1.job_number, project_2.job_number], titles)


    def test_client(self):
        # create projects for two different clients, assert only the one
        # for the specified client appears in the dash.
        client_1 = create_client(u'Alphabet')
        client_2 = create_client(u'Soup')
        contact_1 = create_client_user(u'one@alphabet.test', client=client_1)
        contact_2 = create_client_user(u'two@soup.test', client=client_2)
        project_1 = create_project(u'ABCs', client_poc=contact_1)
        project_2 = create_project(u'Noodles', client_poc=contact_2)

        the_past = datetime(1999, 1, 1)
        task_1 = TaskFactory(project_1).create_tep_task(TASK_ACTIVE_STATUS,
                                                        due=the_past)
        task_2 = TaskFactory(project_2).create_tep_task(TASK_ACTIVE_STATUS,
                                                        due=the_past)

        page = DashboardPageObject.get_query(self.client, client=str(client_2.account_number))
        response = page.response
        self.assert_200(response)

        self.assertEqual(1, response.context['status_counts']['unassigned']['count'])

        titles = [e['title'] for e in response.context['calendar_events']]
        self.assertEqual([project_2.job_number], titles)

        # self.assertEqual([task_2.id], [task.id for task in response.context['overdue_tasks']])

        self.assertIn(client_2.name, page.breadcrumb_text())


class TestProjectOverviewView(ViewTestCase):
    def test_projectdates(self):
        # create projects for two different clients, assert only the one
        # for the specified client appears in the dash.
        client_1 = create_client(u'Alphabet')
        contact_1 = create_client_user(u'one@alphabet.test', client=client_1)
        import pytz
        PST = pytz.timezone(settings.PST_TIME_ZONE)  # "America/Los_Angeles"
        est_due = datetime(2013, 12, 24, 15, tzinfo=PST)
        job_due = datetime(2013, 12, 30, 15, tzinfo=PST)
        started = datetime(2013, 12, 26, 9, tzinfo=PST)

        project1 = create_project(u'Row One', client_poc=contact_1,
                                  started_timestamp=started,
                                  quote_due=est_due, due=job_due)
        contact_1.timezone = 'UTC'
        via_admin_timezone = "US/Pacific"

        expected_estimate_due = est_due.astimezone(pytz.timezone(contact_1.timezone))
        expected_job_due = job_due.astimezone(pytz.timezone(via_admin_timezone))
        expected_started = started.astimezone(pytz.timezone(via_admin_timezone))

        project1.quote_due = pytz.timezone(contact_1.timezone).normalize(est_due)
        project1.started_timestamp = pytz.timezone(via_admin_timezone).normalize(started)
        project1.due = pytz.timezone(via_admin_timezone).normalize(job_due)

        self.assertEqual(project1.quote_due, expected_estimate_due)
        self.assertEqual(project1.started_timestamp, expected_started)
        self.assertEqual(project1.due, expected_job_due)


class JobListPageObject(PageObject):

    view_name = 'via_jobs_list'

    @classmethod
    def credentials(cls):
        user, credentials = create_via_user('pm@viadelivers.com')
        return credentials


class TestViaJobListView(ViewTestCase):

    def test_minimal(self):
        page = JobListPageObject.get(self.client)
        response = page.response
        self.assert_200(response)
        self.assertTemplateUsed(response, ProjectListView.template_name)
        self.assertTrue('Active' in response.rendered_content)
        self.assertIn('Active', response.rendered_content)
