from datetime import datetime, timedelta
from django.test import TestCase
import pytz
from django.conf import settings
from django.utils.timezone import localtime, get_default_timezone
from projects.models import MANUAL_ESTIMATE, AUTO_ESTIMATE, BackgroundTask
from projects.start_tasks import set_task_dates, activate_non_translation_task, _activate_and_notify_by_id, _generate_files_from_translation_v2
from projects.states import TASK_CREATED_STATUS, TASK_COMPLETED_STATUS
from projects.test_duedates import reset_holidays
from shared.datafactory import create_project, TaskFactory
from mock import patch, sentinel
from tasks.models import TaskLocaleTranslationKit, Task

UTC = pytz.utc
PST = pytz.timezone(settings.PST_TIME_ZONE)  # "America/Los_Angeles"
via_tz = get_default_timezone()

class TestSetTaskDates(TestCase):

    def setUp(self):
        self.project = create_project(self.id())
        self.task_factory = TaskFactory(self.project)

        reset_holidays()

    def test_start_tasks_childless(self):
        task = self.task_factory.create_tep_task(
            TASK_CREATED_STATUS, standard_days=1)

        start = datetime(2012, 11, 5, 9, tzinfo=via_tz)
        expected_due = datetime(2012, 11, 6, 14, 7, tzinfo=via_tz)

        result = set_task_dates(task, start, False, False)

        self.assertEqual(task.due, expected_due)
        self.assertEqual(result, expected_due)


    def test_start_tasks_child_with_duration(self):
        # create a task_1 with a >= 1 day duration
        # add child task_2 with a >= 1 day duration
        task_1 = self.task_factory.create_tep_task(
            TASK_CREATED_STATUS, standard_days=1)

        task_2 = self.task_factory.create_tep_task(
            TASK_CREATED_STATUS, standard_days=2, predecessor=task_1)

        # sanity check
        self.assertEqual(task_1.children.count(), 1)

        # http://stackoverflow.com/questions/24856643/unexpected-results-converting-timezones-in-python
        # http://pytz.sourceforge.net/#localized-times-and-date-arithmetic

        start = datetime(2012, 11, 5, 9, tzinfo=via_tz)

        expected_1 = datetime(2012, 11, 6, 14, 7, tzinfo=via_tz)

        expected_due = datetime(2012, 11, 8, 14, 7, tzinfo=via_tz)

        result = set_task_dates(task_1, start,  False, False)
        task_2 = task_2.__class__.objects.get(id=task_2.id)

        self.assertEqual(task_1.due, expected_1)
        self.assertEqual(task_2.due, expected_due)
        self.assertEqual(result, expected_due)


    def test_start_tasks_child_with_hourly_estimate(self):
        # create a task_1 with a >= 1 day duration
        # add child task_2 with 0 standard_days, but
        #    service.unit_of_measure is hourly and
        #    task.quantity > 0
        est_hours = 0

        task_1 = self.task_factory.create_tep_task(
            TASK_CREATED_STATUS, standard_days=1)

        task_2 = self.task_factory.create_fa_task(
            TASK_CREATED_STATUS, standard_days=0, predecessor=task_1,
            quantity=est_hours)

        start = datetime(2012, 11, 5, 9, tzinfo=via_tz)

        expected_due = datetime(2012, 11, 6, 14 + est_hours, 7, tzinfo=via_tz)

        # sanity check
        self.assertEqual(task_1.children.count(), 1)

        result = set_task_dates(task_1, start,  False, False)
        task_2 = task_2.__class__.objects.get(id=task_2.id)

        allocated_time = task_2.due - task_1.due
        self.assertEqual(allocated_time, timedelta(hours=est_hours))

        self.assertEqual(task_2.due, expected_due)
        self.assertEqual(task_2.due, result)


    def test_start_tasks_children_with_hourly_estimates(self):
        est_hours_pp = 2
        est_hours_fa = 1

        task_1 = self.task_factory.create_tep_task(
            TASK_CREATED_STATUS, standard_days=1)

        task_pp = self.task_factory.create_fa_task(
            TASK_CREATED_STATUS, standard_days=0, predecessor=task_1,
            quantity=est_hours_pp)

        task_fa = self.task_factory.create_fa_task(
            TASK_CREATED_STATUS, standard_days=0, predecessor=task_pp,
            quantity=est_hours_fa)

        start = datetime(2012, 11, 5, 19, tzinfo=UTC)
        expected_due = datetime(2012, 11, 6, 14, 7, tzinfo=PST)

        result = set_task_dates(task_1, start,  False, True)
        task_pp = task_pp.__class__.objects.get(id=task_pp.id)
        task_fa = task_fa.__class__.objects.get(id=task_fa.id)

        self.assertEqual(task_fa.due, expected_due.astimezone(UTC))
        self.assertEqual(result, expected_due.astimezone(UTC))


    #def test_start_tasks_with_mixed_children(self):
    #    # TEP - 1 day
    #    # PP - 1 hour
    #    # DTP - 1 day
    #    # Review - 1 day
    #    # FA - 1 hour
    #    self.fail()

    # Scope units of Minutes exist, do we need to handle those too?
    # (no such services exist in translation-dev)



class TestActivateNonTranslationTask(TestCase):

    def setUp(self):
        self.project = create_project(self.id())
        task_factory = TaskFactory(self.project)
        # translation task first
        self.translation_task = task_factory.create_tep_task(TASK_COMPLETED_STATUS)
        # followed by two non-translation tasks
        self.review_task = task_factory.create_review_task(
            TASK_CREATED_STATUS, predecessor=self.translation_task)
        self.fa_task = task_factory.create_fa_task(
            TASK_CREATED_STATUS, predecessor=self.review_task)

        self.tltk = TaskLocaleTranslationKit.objects.create(
            task=self.translation_task)

        activate_patcher = patch(
            'projects.start_tasks._activate_and_notify', autospec=True)
        self.activate_and_notify = activate_patcher.start()
        self.addCleanup(activate_patcher.stop)


    def test_predecessor_is_nontranslation(self):
        self.review_task.status = TASK_COMPLETED_STATUS
        self.review_task.save()

        task = self.fa_task

        # noinspection PyUnresolvedReferences
        with patch.object(task, 'copy_localized_assets_from_predecessor',
                          autospec=True) as copy_lafp:
            copy_to_output = sentinel.copy_to_output
            notify_assigned_to = sentinel.notify_assigned_to
            activate_non_translation_task(task, task.service.service_type,
                                          notify_assigned_to, copy_to_output)

            copy_lafp.assert_called_once_with(copy_to_output)

        self.activate_and_notify.assert_called_once_with(
            task, notify_assigned_to, '')


    def test_predecessor_is_translation_manual_estimate(self):
        self.project.estimate_type = MANUAL_ESTIMATE
        self.project.save()

        task = self.review_task

        with patch('projects.start_tasks.generate_task_files_manual',
                   autospec=True) as generate_delivery, \
                patch('tasks.models.TaskLocaleTranslationKit.can_dvx_import',
                      autospec=True) as can_dvx_import:
            can_dvx_import.return_value = False
            copy_to_output = sentinel.copy_to_output
            notify_assigned_to = sentinel.notify_assigned_to
            activate_non_translation_task(task, task.service.service_type,
                                          notify_assigned_to, copy_to_output)

            generate_delivery.assert_called_once_with(
                self.translation_task.trans_kit, task)

        args = self.activate_and_notify.call_args[0]

        self.assertEqual(task, args[0])
        self.assertEqual(notify_assigned_to, args[1])
        self.assertIn('Manual Estimate', args[2])


    def test_predecessor_is_translation_auto_estimate(self):
        self.project.estimate_type = AUTO_ESTIMATE
        self.project.save()

        task = self.review_task

        copy_to_output = False
        notify_assigned_to = False

        with patch('tasks.models.TaskLocaleTranslationKit.can_dvx_import', autospec=True) as can_dvx_import:
            can_dvx_import.return_value = True
            result = activate_non_translation_task(
                task, task.service.service_type,
                notify_assigned_to, copy_to_output)

        self.assertTrue("projects.start_tasks._generate_after_import" in result.callback_sig)

        # TODO: how to inspect the args passed to the async calls?
        # also, we didn't mock _generate_files, did it actually get queued?
        result.revoke()


    def test_generate_files_from_translation_v2(self):
        # tests the multi-part callback chain used by
        # generate_files_from_translation, making sure the callback initially
        # passed in is run after the completion of the generate action.

        activate_args = self.review_task.id, False, u"hello \N{SNOWMAN}"
        callback = _activate_and_notify_by_id.si(*activate_args)

        with patch('projects.start_tasks.import_translation_v2',
                   autospec=True) as import_translation_v2, \
            patch('projects.start_tasks.generate_delivery_files_v2',
                   autospec=True) as generate_delivery_files_v2:

            import_translation_v2.return_value = None
            generate_delivery_files_v2.return_value = None

            bg_task = _generate_files_from_translation_v2(
                self.tltk, self.review_task, callback)
            import_translation_v2.assert_called_once_with(
                self.tltk, bg_task=bg_task)

            # reload to make sure we have results of serialization
            bg_task = BackgroundTask.objects.get(id=bg_task.id)

            # complete import, start generate
            gen_bg_task = bg_task.callback()
            generate_delivery_files_v2.assert_called_once_with(
                self.tltk, bg_task=gen_bg_task)

            # notification should not have happened yet
            self.assertFalse(self.activate_and_notify.called)

            # complete generate
            gen_bg_task.callback()

        # now the notification callback should have been triggered
        self.activate_and_notify.assert_called_once_with(
            Task.objects.get(id=activate_args[0]),
            activate_args[1],
            activate_args[2])
