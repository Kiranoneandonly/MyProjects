# -*- coding: utf-8 -*-
from decimal import Decimal
import json
from urlparse import urljoin
from celery.canvas import Signature
from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import TestCase
from mock import Mock

from projects.models import SalesforceOpportunity, BackgroundTask
from projects.managers import SalesforceOpportunityManager, \
    BackgroundTaskManager
from projects.states import CREATED_STATUS
from shared.datafactory import create_project, create_via_user


class TestSalesforceOpportunityManager(TestCase):
    def test_is_manager(self):
        self.assertIsInstance(SalesforceOpportunity.objects,
                              SalesforceOpportunityManager)

    def test_from_project(self):
        # from_project doesn't do a save() so we should be able to do it without
        # needing a backend for the salesforce DB.
        account_id = "ACC004321"
        owner_id = "U000013"

        account_exec = create_via_user('ae@via.example.com',
                                       salesforce_user_id=owner_id)[0]

        project = create_project(self.id(), account_executive=account_exec,
                                 approved=True)
        project.client.salesforce_account_id = account_id
        project.client.save()

        price = Decimal('249999.97')
        project.price = lambda speed=None: price

        opportunity = SalesforceOpportunity.objects.from_project(project)

        expected_name = u'Legion of Doom VTP 1 (client@test.com)'

        self.assertEqual(expected_name, opportunity.name)
        self.assertEqual(account_id, opportunity.account_id)
        self.assertEqual(owner_id, opportunity.owner_id)
        self.assertEqual(price, opportunity.amount)
        self.assertTrue(opportunity.close_date)
        self.assertEqual(SalesforceOpportunity.STAGE_Closed_Won, opportunity.stage)

        project_url = urljoin(
            settings.BASE_URL,
            reverse('via_job_detail_overview', args=(project.id,)))

        self.assertIn(project_url, opportunity.description)


    def test_from_project_awaiting_quote(self):
        project = create_project(self.id(), status=CREATED_STATUS)

        price = None
        project.price = lambda speed=None: price

        opportunity = SalesforceOpportunity.objects.from_project(project)

        self.assertEqual(SalesforceOpportunity.STAGE_P1_Wildcard,
                         opportunity.stage)
        self.assertEqual(price, opportunity.amount)
        self.assertTrue(opportunity.close_date)



class TestBackgroundTaskManager(TestCase):
    def test_start_with_callback(self):
        func = Mock(name="some_function")
        func.return_value = None
        project = create_project(self.id())
        callback = Signature('foo_bar', (123, 45))
        errback = Signature('quux', kwargs={"x": "yzzy"})

        self.assertIsInstance(BackgroundTask.objects, BackgroundTaskManager)

        bg_task = BackgroundTask.objects.start_with_callback(
            BackgroundTask.ANALYSIS, project, func, callback, errback)

        func.assert_called_once_with(bg_task=bg_task)

        callback_dict = json.loads(bg_task.callback_sig)
        errback_dict = json.loads(bg_task.errback_sig)

        # Signature doesn't have a useful __eq__, so spot check some things.

        self.assertEqual(callback.task, callback_dict['task'])
        self.assertEqual(callback.args, tuple(callback_dict['args']))
        self.assertEqual(callback.kwargs, callback_dict['kwargs'])

        self.assertEqual(errback.task, errback_dict['task'])
        self.assertEqual(errback.args, tuple(errback_dict['args']))
        self.assertEqual(errback.kwargs, errback_dict['kwargs'])
