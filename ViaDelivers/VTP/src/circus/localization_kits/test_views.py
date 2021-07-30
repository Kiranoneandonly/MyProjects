# -*- coding: utf-8 -*-
import json
from django.core.urlresolvers import reverse
from django.utils.timezone import now
from mock import patch
from localization_kits import authorization as authz
from localization_kits.views import ANALYSIS_COOKIE_NAME, \
    via_check_analysis_status
from projects.models import BackgroundTask
from shared.datafactory import create_project, create_client_user
from shared.unittest_help import ViewTestCase


class TestQueueAnalysis(ViewTestCase):
    def setUp(self):
        self.project = create_project(self.id())
        self.url = reverse('queue_analysis', args=(self.project.kit_id,))

        # noinspection PyUnresolvedReferences
        authz_condition = patch.object(authz.any_via_user, 'condition')
        authz_condition.return_value = True
        authz_condition.start()
        self.addCleanup(authz_condition.stop)

    def test_queue_analysis(self):
        response = self.client.post(self.url)

        self.assertRedirectsToName(response, 'via_job_detail_estimate', pk=str(self.project.kit_id))

        expected_cookie = json.dumps([self.project.id])
        self.assertEqual(expected_cookie, self.client.cookies[ANALYSIS_COOKIE_NAME].value)


class TestCheckAnalysisStatus(ViewTestCase):

    def setUp(self):
        self.url = reverse('via_check_analysis_status')

        # noinspection PyUnresolvedReferences
        authz_condition = patch.object(authz.any_via_user, 'condition')
        authz_condition.return_value = True
        authz_condition.start()
        self.addCleanup(authz_condition.stop)


    def complete_project(self, **kwargs):
        project = create_project(self.id(), **kwargs)
        project.kit.analysis_started = now()
        project.kit.analysis_finished = now()
        project.kit.analysis_code = '123456'
        project.kit.save()
        return project


    def incomplete_project(self, **kwargs):
        project = create_project(self.id(), **kwargs)
        project.kit.analysis_started = now()
        project.kit.save()
        BackgroundTask.objects.create(
            name=BackgroundTask.ANALYSIS,
            celery_task_id="blahblah-%s" % (project.id,),
            project=project
        )
        return project


    def test_not_complete(self):
        # one project, analysis not yet complete
        project = self.incomplete_project()
        project_ids = [project.id]

        # set client cookie
        self.client.login(email='client@test.com', password='test')
        self.client.cookies[ANALYSIS_COOKIE_NAME] = json.dumps(project_ids)

        response = self.client.get(self.url, {'projects': json.dumps(project_ids)})

        self.assert_200(response)

        response_data = json.loads(response.content)

        self.assertEqual(1, len(response_data))

        response_project = response_data[0]
        # check data for project 0
        self.assertEqual(project.id, response_project['id'])
        self.assertEqual(project.name, response_project['name'])
        self.assertFalse(response_project['complete'])

        # check url for project 0
        self.assertEqual(via_check_analysis_status.project_ready_url(project),
                         response_project['url'])

        # assert cookie still has the in-progress project in it
        self.assertEqual(json.dumps(project_ids),
                         self.client.cookies[ANALYSIS_COOKIE_NAME].value)


    def test_complete(self):
        # one project, analysis is complete
        project = self.complete_project()
        project_ids = [project.id]

        # set client cookie
        self.client.login(email='client@test.com', password='test')
        self.client.cookies[ANALYSIS_COOKIE_NAME] = json.dumps(project_ids)

        response = self.client.get(self.url, {'projects': json.dumps(project_ids)})

        self.assert_200(response)

        response_data = json.loads(response.content)

        self.assertEqual(1, len(response_data))

        response_project = response_data[0]
        # check data for project 0
        self.assertEqual(project.id, response_project['id'])
        self.assertEqual(project.name, response_project['name'])
        self.assertTrue(response_project['complete'])

        # check url for project 0
        self.assertEqual(via_check_analysis_status.project_ready_url(project),
                         response_project['url'])

        # cookie should have no value when all are complete
        self.assertEqual('', self.client.cookies[ANALYSIS_COOKIE_NAME].value)


    def test_not_your_project(self):
        # one project, analysis is complete
        project = self.complete_project()
        # this project and some random number as well
        project_ids = [project.id, 9726234]

        # this is some other user who doesn't own the project
        create_client_user(u'mallory@other.example.com')
        self.client.login(email='mallory@other.example.com', password='test')
        self.client.cookies[ANALYSIS_COOKIE_NAME] = json.dumps(project_ids)

        url = reverse('check_analysis_status')
        response = self.client.get(url, {'projects': json.dumps(project_ids)})

        self.assert_200(response)

        response_data = json.loads(response.content)

        # It should omit projects you don't have access to.
        self.assertEqual(0, len(response_data))

        # cookie should not include projects you don't have access to.
        self.assertEqual('', self.client.cookies[ANALYSIS_COOKIE_NAME].value)


    def test_two_projects_one_complete(self):
        incomplete_project = self.incomplete_project()
        complete_project = self.complete_project(
            client_poc=incomplete_project.client_poc)
        project_ids = [incomplete_project.id, complete_project.id]

        # set client cookie
        self.client.login(email='client@test.com', password='test')
        self.client.cookies[ANALYSIS_COOKIE_NAME] = json.dumps(project_ids)

        response = self.client.get(self.url, {'projects': json.dumps(project_ids)})

        self.assert_200(response)

        response_data = json.loads(response.content)

        self.assertEqual(2, len(response_data))

        response_project = response_data[0]
        self.assertEqual(incomplete_project.id, response_project['id'])
        self.assertFalse(response_project['complete'])

        response_project = response_data[1]
        self.assertEqual(complete_project.id, response_project['id'])
        self.assertTrue(response_project['complete'])

        # assert cookie has only the in-progress project in it
        self.assertEqual(json.dumps([incomplete_project.id]),
                         self.client.cookies[ANALYSIS_COOKIE_NAME].value)


    def test_cookie_added_new_project(self):
        # project included in cookie, but not query
        #    (another tab created a new project, add it to poll list.)
        first_project = self.incomplete_project()
        new_project = self.incomplete_project(
            client_poc=first_project.client_poc)

        query_project_ids = [first_project.id]
        cookie_project_ids = [first_project.id, new_project.id]

        self.client.login(email='client@test.com', password='test')
        self.client.cookies[ANALYSIS_COOKIE_NAME] = json.dumps(cookie_project_ids)

        response = self.client.get(self.url,
                                   {'projects': json.dumps(query_project_ids)})

        self.assert_200(response)

        response_data = json.loads(response.content)

        self.assertEqual(2, len(response_data))

        self.assertEqual(first_project.id, response_data[0]['id'])
        self.assertEqual(new_project.id, response_data[1]['id'])

        # cookie should still have both projects
        self.assertEqual(json.dumps(cookie_project_ids),
                         self.client.cookies[ANALYSIS_COOKIE_NAME].value)


    def test_cookie_removed_project(self):
        # project included in query, but not cookie
        # (another tab polled this already, but the notification still needs to
        # appear in this one.)
        complete_project = self.complete_project()
        incomplete_project = self.incomplete_project(
            client_poc=complete_project.client_poc)

        query_project_ids = [complete_project.id, incomplete_project.id]
        cookie_project_ids = [incomplete_project.id]

        self.client.login(email='client@test.com', password='test')
        self.client.cookies[ANALYSIS_COOKIE_NAME] = json.dumps(cookie_project_ids)

        response = self.client.get(self.url,
                                   {'projects': json.dumps(query_project_ids)})

        self.assert_200(response)

        response_data = json.loads(response.content)

        self.assertEqual(2, len(response_data))

        self.assertEqual(complete_project.id, response_data[0]['id'])
        self.assertEqual(incomplete_project.id, response_data[1]['id'])

        # cookie should still have just the incomplete project
        self.assertEqual(json.dumps(cookie_project_ids),
                         self.client.cookies[ANALYSIS_COOKIE_NAME].value)
