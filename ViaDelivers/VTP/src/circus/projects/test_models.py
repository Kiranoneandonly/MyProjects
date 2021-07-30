# coding=utf-8
"""Test projects.models."""
import json
from celery import shared_task
from mock import patch
import pytz

from datetime import datetime
from django.conf import settings
from django.contrib.messages import ERROR, SUCCESS, WARNING
from django.test import TestCase

from accounts.models import CircusUser
import projects.models
from projects.models import BackgroundTask, Project, ProjectTeamRole, Delivery, \
    SalesforceOpportunity, get_project_delivery_path
from clients.models import Client, PM_ROLE, VLE_ENG_ROLE
from people.models import AccountType
from projects.states import TASK_CREATED_STATUS, STARTED_STATUS, HOLD_STATUS
from services.models import Locale
from shared.datafactory import create_project, TaskFactory
from vendors.models import Vendor
from projects.start_tasks import set_task_dates

PST = pytz.timezone(settings.PST_TIME_ZONE)  # "America/Los_Angeles"


class TestProjectActions(TestCase):
    def test_reschedule_due_dates_fails_with_no_tasks(self):
        started_timestamp = datetime(2013, 11, 12, 9, tzinfo=PST)

        self.en_US = Locale.objects.get(lcid=1033)
        self.ru = Locale.objects.get(lcid=1049)
        project = create_project(self.id(),
                                 started_timestamp=started_timestamp,
                                 source=self.en_US,
                                 targets=[self.ru]
                                 )

        status, message = project.reschedule_due_dates()
        self.assertEqual(status, ERROR)

    def test_reschedule_due_dates_warns_with_no_start_date(self):
        # The schedule is based on the project start date, so if there's no start date,
        # we can't build a schedule around it.

        self.en_US = Locale.objects.get(lcid=1033)
        self.ru = Locale.objects.get(lcid=1049)
        project = create_project(self.id(),
                                 started_timestamp=None,
                                 source=self.en_US,
                                 targets=[self.ru]
                                 )

        status, message = project.reschedule_due_dates()
        self.assertEqual(status, WARNING)

    def test_reschedule_due_dates(self):
        # When should the start date be?
        #  - now or project.started_timestamp?
        # Should started_timestamp change?
        # Should it care about the status of the tasks?
        #  - if they're already accepted
        #  - or completed
        started_timestamp = datetime(2013, 11, 12, 9, tzinfo=PST)
        project = create_project(name=self.id(),
                                 started_timestamp=started_timestamp)
        task_factory = TaskFactory(project)
        task_1 = task_factory.create_tep_task(
            TASK_CREATED_STATUS, standard_days=3)

        #noinspection PyUnresolvedReferences
        with patch.object(projects.models, 'set_task_dates') as set_task_dates:
            new_task_due = datetime(2013, 11, 15, 9, tzinfo=PST)
            set_task_dates.return_value = new_task_due
            success, message = project.reschedule_due_dates()
            self.assertEqual(success, SUCCESS)

            set_task_dates.called_once_with(task_1, started_timestamp, project.ignore_holiday_flag, False)
            success, message = project.reschedule_due_dates()
            self.assertEqual(success, SUCCESS)

    def test_reschedule_all_due_dates_when_due_date_changed(self):
        #When due date is changed and reschedule due dates is yes.
        started_timestamp = datetime(2015, 05, 18, 11, tzinfo=PST)
        due = datetime(2015, 05, 26, 17, tzinfo=PST)
        self.ru = Locale.objects.get(lcid=1049)
        project = create_project(name=self.id(), started_timestamp=started_timestamp, due=due, targets=[self.ru])
        task_factory = TaskFactory(project)
        task_1 = task_factory.create_tep_task(
            TASK_CREATED_STATUS, standard_days=2)
        task_2 = task_factory.create_pp_task(
            TASK_CREATED_STATUS, standard_days=0, predecessor=task_1)
        task_3 = task_factory.create_dtp_task(
            TASK_CREATED_STATUS, standard_days=1, predecessor=task_2)
        task_4 = task_factory.create_review_task(
            TASK_CREATED_STATUS, standard_days=1, predecessor=task_3)
        task_5 = task_factory.create_fa_task(
            TASK_CREATED_STATUS, standard_days=1, predecessor=task_4)

        task_4.scheduled_start_timestamp = datetime(2015, 05, 22, 16, tzinfo=PST)
        task_4.due = datetime(2015, 05, 26, 16, tzinfo=PST)
        task_4_changed_date = datetime(2015, 05, 27, 16, tzinfo=PST)
        task_5_expected_due = datetime(2015, 05, 28, 16, tzinfo=PST)

        self.assertEqual(task_4.children.count(), 1)
        task_4.reschedule_all_due_dates = True
        if task_4.reschedule_all_due_dates:
            success, message = project.reschedule_due_dates(None, task_4, "Due")
            project_due = set_task_dates(task_4, task_4.scheduled_start_timestamp,  False, False, task_4_changed_date)
            task_5 = task_5.__class__.objects.get(id=task_5.id)

        self.assertEqual(task_5_expected_due, task_5.due)
        self.assertNotEquals(project_due, due)
        self.assertEqual(success, ERROR)

    def test_reschedule_only_particular_task_due_date(self):
        #When due date is changed and reschedule due dates is No
        started_timestamp = datetime(2015, 05, 18, 11, tzinfo=PST)
        due = datetime(2015, 05, 26, 17, tzinfo=PST)
        self.ru = Locale.objects.get(lcid=1049)
        project = create_project(name=self.id(),
                                 started_timestamp=started_timestamp, due=due, targets=[self.ru])
        task_factory = TaskFactory(project)
        task_1 = task_factory.create_tep_task(
            TASK_CREATED_STATUS, standard_days=2)
        task_2 = task_factory.create_pp_task(
            TASK_CREATED_STATUS, standard_days=0, predecessor=task_1)
        task_3 = task_factory.create_dtp_task(
            TASK_CREATED_STATUS, standard_days=1, predecessor=task_2)
        task_4 = task_factory.create_review_task(
            TASK_CREATED_STATUS, standard_days=1, predecessor=task_3)
        task_5 = task_factory.create_fa_task(
            TASK_CREATED_STATUS, standard_days=1, predecessor=task_4)

        task_4.scheduled_start_timestamp = datetime(2015, 05, 22, 16, tzinfo=PST)
        task_4.due = datetime(2015, 05, 26, 16, tzinfo=PST)
        task_4_changed_date = datetime(2015, 05, 27, 16, tzinfo=PST)

        task_4.reschedule_all_due_dates = False
        if not task_4.reschedule_all_due_dates:
            task_4.due = task_4_changed_date

        self.assertEqual(project.due, due)
        self.assertEqual(task_4_changed_date, task_4.due)


class TestProjectCleanTasks(TestCase):

    def setUp(self):
        self.en_US = Locale.objects.get(lcid=1033)
        self.en_UK = Locale.objects.get(lcid=2057)

        self.ru = Locale.objects.get(lcid=1049)
        self.de = Locale.objects.get(lcid=1031)

        self.project = create_project(self.id(),
                                      source=self.en_US,
                                      targets=[self.ru, self.de])
        self.task_factory = TaskFactory(self.project)

        self.task_ids = set()
        for locale in [self.ru, self.de]:
            tep_task = self.task_factory.create_tep_task(
                TASK_CREATED_STATUS, target=locale)
            fa_task = self.task_factory.create_fa_task(
                TASK_CREATED_STATUS, predecessor=tep_task)

            self.task_ids.add(tep_task.id)
            self.task_ids.add(fa_task.id)

    def test_no_changes_not_removed(self):
        # if locales have not changed, their tasks remain untouched.
        self.project.clean_tasks()
        self.assertEqual(self.task_ids,
                         set(self.project.task_set.values_list('id', flat=True)))

    def test_change_target(self):
        # remove a target
        self.project.target_locales.filter(id=self.ru.id).delete()

        self.project.clean_tasks()

        # the remaining tasks should all be for the not-removed language.
        self.assertEqual(2, self.project.task_set.count())
        self.assertEqual(2, self.project.task_set.filter(
            service__target=self.de).count())

    def test_change_source(self):
        self.project.source_locale = self.en_UK
        self.project.save()

        self.project.clean_tasks()

        # should have removed all the en_US tasks
        self.assertEqual(0, self.project.task_set.count())


class TestProjectTransitions(TestCase):
    def setUp(self):
        self.project = create_project(self.id(), status=STARTED_STATUS)

    def test_transition_started(self):
        with patch('projects.models.notify_new_job_ordered', autospec=True) as notify, \
                patch('projects.managers.SalesforceOpportunityManager.create_for_project',
                      autospec=True) as create_for_project:
            self.project._transition_started()
        self.assertTrue(self.project.approved)
        notify.assert_called_once_with(self.project)
        if settings.SALESFORCE_ENABLED:
            create_for_project.assert_called_once_with(SalesforceOpportunity.objects, self.project)

    def test_transition_hold(self):
        self.project.transition(HOLD_STATUS)
        self.assertTrue(self.project.is_hold_status())


class TestProjectDisplayName(TestCase):
    def test_short_name(self):
        name = "Bob"
        self.project = Project(name=name)
        self.assertEqual(self.project.job_name_display_name(), name)

    def test_long_name_is_truncated(self):
        name = (u"Taumatawhakatangihangakoauauotamateaturi"
            u"pukakapikimaungahoronukupokaiwhenuakitanatahu explorer of the "
            u"land and father of Kahungunu")
        truncated = (u'Taumatawhakatangihangakoauauotamateaturipukakapiki'
                     u'maungahoronukupokaiwhenuakitanatahu expl...')
        self.project = Project(name=name)
        self.assertEqual(self.project.job_name_display_name(), truncated)


class TestProjectTeam(TestCase):
    def setUp(self):
        self.project = create_project(u"Team Project")

        self.via_user = CircusUser.objects.create(
            email='via-ae@example.com',
        )
        self.team = ProjectTeamRole.objects.create(
            project=self.project,
            contact=self.via_user,
            role=VLE_ENG_ROLE
        )

    def test_team(self):
        self.assertEqual(self.project.team.first(), self.team)

    def test_get_pm_team_with_PM(self):
        pm_user = CircusUser.objects.create(
            email='via-pm@example.com',
        )
        self.project.project_manager = pm_user
        self.assertEqual(self.project.get_pm_team(), [pm_user.email])

    def test_get_pm_team_with_PM_role(self):
        pm_user = CircusUser.objects.create(
            email='via-pm@example.com',
        )
        ProjectTeamRole.objects.create(
            project=self.project,
            contact=pm_user,
            role=PM_ROLE
        )
        # team email should be just the PM, not the AE
        self.assertEqual(self.project.get_pm_team(), [pm_user.email])

    def test_get_pm_team_with_client_default(self):
        pm_team = self.project.get_pm_team()
        self.assertEqual(pm_team, [self.project.client.via_team_jobs_email])
        self.assertIsNotNone(pm_team[0])


class TestDelivery(TestCase):
    def setUp(self):
        vendor_account_type = AccountType.objects.create(
            code='vendor',
            description='Vendor'
        )
        self.vendor = Vendor.objects.create(
            name="Vendor",
            account_type=vendor_account_type,
        )
        client_user = CircusUser.objects.create(
            user_type=settings.CLIENT_USER_TYPE,
            email='hello@example.com',
        )
        client_account_type = AccountType.objects.create(
            code='client',
            description='Client'
        )
        client = Client.objects.create(
            name="Adam",
            via_team_jobs_email="via-for-client@example.com",
            account_type=client_account_type,
        )
        self.project = Project.objects.create(
            name="The Encyclopedia",
            client=client,
            client_poc=client_user,
            current_user=client_user.id
        )
        self.delivery = Delivery.objects.create(
            vendor=self.vendor,
            project=self.project,
        )
        filename = get_project_delivery_path(self.delivery, "idc-10.pdf")
        self.delivery.file = filename
        self.delivery.save()

    def test_file_display_name(self):
        self.assertEqual("idc-10.pdf", self.delivery.file_display_name())


SIGIL = "hello"


@shared_task
def some_callback_func(*args, **kwargs):
    return SIGIL, args, kwargs


class TestBackgroundTask(TestCase):
    def test_errback(self):
        sig = some_callback_func.s(987)
        errback_str = json.dumps(sig)
        bg_task = BackgroundTask(errback_sig=errback_str)
        sigil, args, kwargs = bg_task.errback()

        self.assertEqual(SIGIL, sigil)

        # assert first arg is bg_task
        self.assertEqual((bg_task, 987), args)

        self.assertEqual({}, kwargs)

        self.assertIsNotNone(bg_task.completed)
