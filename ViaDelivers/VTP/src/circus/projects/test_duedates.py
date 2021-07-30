# coding=utf-8
"""Test project.duedates."""
import pytz
from datetime import datetime, timedelta, date
from django.test import TestCase
from django.conf import settings
from django.utils.timezone import localtime, get_default_timezone
from holidays.models import Holiday
from projects.duedates import add_delta_business_days, get_due_date, get_approval_task_duration, \
    get_post_process_task_duration, get_quote_due_date, get_job_standard_duration, get_job_express_duration

GMT = pytz.timezone('GMT')
PST = pytz.timezone(settings.TIME_ZONE)  # "America/Los_Angeles"
via_tz = get_default_timezone()

def reset_holidays():
        Holiday.objects.all().delete()

        holidays = [
            date(2013, 5, 27),
            date(2013, 7, 4),
            date(2013, 9, 2),
            date(2013, 11, 11),
            date(2013, 11, 28),
            date(2013, 12, 25),
            date(2013, 12, 31),
            date(2014, 1, 1),
            date(2014, 3, 17),
            date(2014, 5, 26),
            date(2014, 7, 4),
            date(2014, 9, 1),
            date(2014, 11, 10),
            date(2014, 11, 28),
            date(2014, 12, 25),
            date(2014, 12, 31)
        ]

        for holiday_date in holidays:
            holiday, created = Holiday.objects.get_or_create(holiday_date=holiday_date)
            pass


def setup_locales(self):
    from services.models import Locale
    self.en_US = Locale.objects.get(lcid=1033)
    self.ru = Locale.objects.get(lcid=1049)
    self.af = Locale.objects.get(lcid=1078)
    self.al = Locale.objects.get(lcid=1052)
    self.am = Locale.objects.get(lcid=1118)
    self.als = Locale.objects.get(lcid=1156)
    self.cht = Locale.objects.get(lcid=1028)
    self.chs = Locale.objects.get(lcid=2052)


class TestDueDates(TestCase):
    def setUp(self):
        reset_holidays()
        setup_locales(self)

    def test_get_quote_due_date(self):
        expected_due_date = datetime(2014, 3, 19, 14, tzinfo=PST)
        start_date = datetime(2014, 3, 18, 9, tzinfo=PST)
        due_date = get_quote_due_date(start_date, timedelta(days=1), False, False, PST)
        self.assertEqual(expected_due_date, due_date)

    def test_get_quote_due_date_gmt(self):
        expected_due_date = datetime(2014, 3, 19, 14, tzinfo=GMT)
        start_date = datetime(2014, 3, 18, 9, tzinfo=GMT)
        due_date = get_quote_due_date(start_date, timedelta(days=1), False, False, GMT)
        self.assertEqual(expected_due_date, due_date)

    def test_get_quote_due_date_gmt_pst(self):
        expected_due_date = datetime(2014, 3, 19, 14, tzinfo=PST)
        start_date = datetime(2014, 3, 18, 9, tzinfo=GMT)
        due_date = get_quote_due_date(start_date, timedelta(days=1), False, False, PST)
        self.assertEqual(expected_due_date, due_date)

    def test_add_delta_business_days(self):
        expected_due_date = datetime(2014, 3, 19, 9, tzinfo=PST)
        start_date = datetime(2014, 3, 18, 9, tzinfo=PST)
        due_date = add_delta_business_days(start_date, timedelta(days=1), False, False)
        self.assertEqual(expected_due_date, due_date)

    def test_add_delta_business_days_holiday(self):
        expected_due_date = datetime(2014, 3, 19, 9, tzinfo=PST)
        start_date = datetime(2014, 3, 17, 9, tzinfo=PST)
        due_date = add_delta_business_days(start_date, timedelta(days=1), False, False)
        self.assertEqual(expected_due_date, due_date)

    def test_add_delta_business_days_holiday_ignore(self):
        expected_due_date = datetime(2014, 3, 18, 9, tzinfo=PST)
        start_date = datetime(2014, 3, 17, 9, tzinfo=PST)
        due_date = add_delta_business_days(start_date, timedelta(days=1), True, False)
        self.assertEqual(expected_due_date, due_date)

    def test_add_delta_business_days_holiday_before_8am(self):
        expected_due_date = datetime(2014, 3, 19, 9, 30, tzinfo=PST)
        start_date = datetime(2014, 3, 17, 7, tzinfo=PST)
        due_date = add_delta_business_days(start_date, timedelta(days=1), False, False)
        self.assertEqual(expected_due_date, due_date)

    def test_add_delta_business_days_holiday_ignore_before_8am(self):
        expected_due_date = datetime(2014, 3, 18, 9, 30, tzinfo=PST)
        start_date = datetime(2014, 3, 17, 7, tzinfo=PST)
        due_date = add_delta_business_days(start_date, timedelta(days=1), True, False)
        self.assertEqual(expected_due_date, due_date)

    def test_add_delta_business_days_holiday_after_5pm(self):
        expected_due_date = datetime(2014, 3, 19, 9, 30, tzinfo=PST)
        start_date = datetime(2014, 3, 17, 18, tzinfo=PST)
        due_date = add_delta_business_days(start_date, timedelta(days=1), False, False)
        self.assertEqual(expected_due_date, due_date)

    def test_add_delta_business_days_holiday_ignore_after_5pm(self):
        expected_due_date = datetime(2014, 3, 19, 9, 30, tzinfo=PST)
        start_date = datetime(2014, 3, 17, 18, tzinfo=PST)
        due_date = add_delta_business_days(start_date, timedelta(days=1), True, False)
        self.assertEqual(expected_due_date, due_date)

    def test_add_delta_business_days_weekend_plus_holiday(self):
        expected_due_date = datetime(2014, 3, 18, 9, tzinfo=PST)
        start_date = datetime(2014, 3, 14, 9, tzinfo=PST)
        due_date = add_delta_business_days(start_date, timedelta(days=1), False, False)
        self.assertEqual(expected_due_date, due_date)

    def test_add_delta_business_days_weekend_plus_holiday_ignore(self):
        expected_due_date = datetime(2014, 3, 17, 9, tzinfo=PST)
        start_date = datetime(2014, 3, 14, 9, tzinfo=PST)
        due_date = add_delta_business_days(start_date, timedelta(days=1), True, False)
        self.assertEqual(expected_due_date, due_date)

    def test_add_delta_business_days_weekend_9am(self):
        expected_due_date = datetime(2014, 3, 24, 9, tzinfo=PST)
        start_date = datetime(2014, 3, 21, 9, tzinfo=PST)
        due_date = add_delta_business_days(start_date, timedelta(days=1), False, False)
        self.assertEqual(expected_due_date, due_date)

    def test_add_delta_business_days_weekend_4pm(self):
        expected_due_date = datetime(2014, 3, 24, 16, tzinfo=PST)
        start_date = datetime(2014, 3, 21, 16, tzinfo=PST)
        due_date = add_delta_business_days(start_date, timedelta(days=1), False, False)
        self.assertEqual(expected_due_date, due_date)

    def test_add_delta_business_days_weekend_6pm(self):
        expected_due_date = datetime(2014, 3, 25, 9, 30, tzinfo=PST)
        start_date = datetime(2014, 3, 21, 18, tzinfo=PST)
        due_date = add_delta_business_days(start_date, timedelta(days=1), False, False)
        self.assertEqual(expected_due_date, due_date)

    def test_add_delta_business_days_after_6pm(self):
        expected_due_date = datetime(2014, 3, 27, 9, 30, tzinfo=PST)
        start_date = datetime(2014, 3, 25, 18, tzinfo=PST)
        due_date = add_delta_business_days(start_date, timedelta(days=1), False, False)
        self.assertEqual(expected_due_date, due_date)

    def test_add_delta_business_days_start_friday_hourly(self):
        expected_due_date = localtime(datetime(2016, 1, 12, 12, 30, tzinfo=PST), via_tz)
        start_date = datetime(2016, 1, 8, 12, 30, tzinfo=PST)
        due_date = get_due_date(start_date, timedelta(minutes=round(24*60*2)), False, True)
        self.assertEqual(expected_due_date, due_date)

    def test_add_delta_business_days_start_friday_hourly_decimal(self):
        expected_due_date = localtime(datetime(2016, 1, 12, 18, 30, tzinfo=PST), via_tz)
        start_date = datetime(2016, 1, 8, 12, 30, tzinfo=PST)
        due_date = get_due_date(start_date, timedelta(minutes=round(24*60*2.25)), False, True)
        self.assertEqual(expected_due_date, due_date)

    def test_add_delta_business_days_start_friday_standard(self):
        expected_due_date = datetime(2016, 1, 12, 14, 07, tzinfo=via_tz)
        start_date = datetime(2016, 1, 8, 12, 30, tzinfo=via_tz)
        due_date = get_due_date(start_date, timedelta(minutes=round(24*60*2)), False, False)
        self.assertEqual(expected_due_date, due_date)

    def test_get_post_process_task_duration_manual(self, estimate_type='manual'):
        started_timestamp = datetime(2013, 11, 12, 9, tzinfo=PST)
        from shared.datafactory import create_project
        project = create_project(self.id(),
                                 started_timestamp=started_timestamp,
                                 source=self.en_US,
                                 targets=[self.ru, self.af, self.al, self.als, self.am, self.chs, self.cht],
                                 estimate_type=estimate_type,
                                 )
        tat_expected = 1.0
        tat_duration = get_post_process_task_duration(project)
        self.assertEqual(tat_expected, tat_duration)

    def test_get_approval_task_duration_manual(self, estimate_type='manual'):
        started_timestamp = datetime(2013, 11, 12, 9, tzinfo=PST)
        from shared.datafactory import create_project
        project = create_project(self.id(),
                                 started_timestamp=started_timestamp,
                                 source=self.en_US,
                                 targets=[self.ru, self.af, self.al, self.als, self.am, self.chs, self.cht],
                                 estimate_type=estimate_type,
                                 )
        tat_expected = 0.0
        tat_duration = get_approval_task_duration(project)
        self.assertEqual(tat_expected, tat_duration)

    def test_get_approval_task_duration_auto(self, estimate_type='auto'):
        started_timestamp = datetime(2013, 11, 12, 9, tzinfo=PST)
        from shared.datafactory import create_project
        project = create_project(self.id(),
                                 started_timestamp=started_timestamp,
                                 source=self.en_US,
                                 targets=[self.ru, self.af, self.al, self.als, self.am, self.chs, self.cht],
                                 estimate_type=estimate_type,
                                 )
        tat_expected = 1.0
        tat_duration = get_approval_task_duration(project)
        self.assertEqual(tat_expected, tat_duration)

    def test_get_job_standard_duration(self):
        wordcount = 10000
        tat_expected = 6
        tat_duration = get_job_standard_duration(wordcount)
        self.assertEqual(tat_expected, tat_duration)

    def test_get_job_standard_duration_mbd(self):
        wordcount = 10000
        mbd = -0.5
        tat_expected = 5
        tat_duration = get_job_standard_duration(wordcount=wordcount, mbd=mbd)
        self.assertEqual(tat_expected, tat_duration)

    def test_get_job_standard_duration_custom_wpd(self):
        wordcount = 10000
        translation_words_per_day = 5000
        tat_expected = 3
        tat_duration = get_job_standard_duration(wordcount, translation_words_per_day)
        self.assertEqual(tat_expected, tat_duration)

    def test_get_job_express_duration(self):
        wordcount = 10000
        tat_expected = 5
        tat_duration = get_job_express_duration(wordcount)
        self.assertEqual(tat_expected, tat_duration)

    def test_get_job_express_duration_mbd(self):
        wordcount = 10000
        mbd = -0.5
        tat_expected = 4
        tat_duration = get_job_express_duration(wordcount=wordcount, mbd=mbd)
        self.assertEqual(tat_expected, tat_duration)

    def test_get_job_express_duration_custom_wpd(self):
        wordcount = 10000
        translation_words_per_day = 6000
        tat_expected = 2
        tat_duration = get_job_express_duration(wordcount, translation_words_per_day)
        self.assertEqual(tat_expected, tat_duration)
