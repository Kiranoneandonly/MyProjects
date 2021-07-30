import logging
import math
from decimal import Decimal, ROUND_CEILING
from django.conf import settings
from django.utils.timezone import localtime, get_default_timezone
import pytz
import datetime
from datetime import timedelta, time
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from holidays.models import Holiday
from services.managers import FEEDBACK_MANAGEMENT_SERVICE_TYPE, \
    FILE_PREP_SERVICE_TYPE, RECREATE_SOURCE_FROM_PDF_SERVICE_TYPE, PM_HOUR_SERVICE_TYPE

logger = logging.getLogger('circus.' + __name__)

(MON, TUE, WED, THU, FRI, SAT, SUN) = range(7)

working_days = (MON, TUE, WED, THU, FRI)
weekend_days = (SAT, SUN)

def get_holidays():
    return Holiday.objects.filter(holiday_date__isnull=False, is_deleted=False)


def get_number_holidays(start_date, end_date):
    return Holiday.objects.filter(holiday_date__range=[start_date, end_date])


def is_in_workday(timestamp, ignore_holiday=False, is_hourly_schedule=False):
    # convert to pst for my sanity
    try:
        if timestamp:
            pst_timestamp = timestamp.astimezone(pytz.timezone(settings.PST_TIME_ZONE))
            holiday_dates = [d.holiday_date for d in get_holidays()] if not ignore_holiday else []
            if pst_timestamp.weekday() in working_days and not pst_timestamp.date() in holiday_dates:
                if not is_hourly_schedule:
                    if time(settings.JOB_UPLOAD_TIME_FIRST_RECEIVED_TIME) <= pst_timestamp.time() <= time(settings.JOB_UPLOAD_TIME_LAST_RECEIVED_TIME):
                        return True
                else:
                    return True
            return False
        return False
    except:
        return False


def get_quote_due_date(start, delta, ignore_holiday_flag=False, is_hourly_schedule=False, tz=None):
    tz = get_default_timezone() if not tz else tz
    quote_due_date = add_delta_business_days(start, delta, ignore_holiday_flag, is_hourly_schedule)
    quote_due_date = quote_due_date.replace(hour=settings.QUOTE_DUE_HOUR, minute=0, second=0, microsecond=0, tzinfo=tz)
    return quote_due_date


def get_due_date(start, delta, ignore_holiday_flag=False, is_hourly_schedule=False):
    due_date = add_delta_business_days(start, delta, ignore_holiday_flag, is_hourly_schedule)
    via_tz = get_default_timezone()
    # "due on this day" means "due by close of business in the U.S." which means "due by 5pm Eastern" which means "due by 2pm VIA Time (Pacific)".
    if not is_hourly_schedule and due_date.time() < time(settings.QUOTE_DUE_HOUR, tzinfo=via_tz):
        due_date = due_date.replace(hour=settings.QUOTE_DUE_HOUR, minute=7, second=0, tzinfo=via_tz)
    return due_date


def get_late_response_timestamp():
    """ unaccepted tasks that were created before what time are now overdue? """
    now = timezone.now()
    return now - timedelta(hours=settings.RESPOND_BY_TIMEDELTA)


def next_business_hour(timestamp, ignore_holiday=False, is_hourly_schedule=False):
    if not timestamp:
        return None
    if is_in_workday(timestamp, ignore_holiday, is_hourly_schedule):
        return timestamp
    pst_timestamp = timestamp.astimezone(pytz.timezone(settings.PST_TIME_ZONE))
    # set time to the start of business hours if not already
    if not is_hourly_schedule:
        if pst_timestamp.time() < time(settings.JOB_UPLOAD_TIME_FIRST_RECEIVED_TIME):
            pst_timestamp = pst_timestamp.replace(hour=settings.JOB_UPLOAD_TIME_FIRST_RECEIVED_TIME_PUSH_HOUR, minute=settings.JOB_UPLOAD_TIME_FIRST_RECEIVED_TIME_PUSH_MINUTE)
        elif pst_timestamp.time() > time(settings.JOB_UPLOAD_TIME_LAST_RECEIVED_TIME):
            pst_timestamp = pst_timestamp.replace(hour=settings.JOB_UPLOAD_TIME_FIRST_RECEIVED_TIME_PUSH_HOUR, minute=settings.JOB_UPLOAD_TIME_FIRST_RECEIVED_TIME_PUSH_MINUTE)
            pst_timestamp += timedelta(days=1)
    while not is_in_workday(pst_timestamp, ignore_holiday, is_hourly_schedule):
        pst_timestamp += timedelta(days=1)
    return pst_timestamp


def add_delta_business_days(start_date, delta, ignore_holiday=False, is_hourly_schedule=False):
    # adjust start_date to next business day
    start_date = next_business_hour(start_date, ignore_holiday, is_hourly_schedule)

    # Calculate Due Date
    new_date = duedate_by_adding_business_seconds(start_date, delta.total_seconds())

    if not ignore_holiday:
        # count holidays between start_date and new_date
        holiday_dates = [d.holiday_date for d in get_holidays()]
        new_date += timedelta(days=len([d for d in holiday_dates if start_date.date() < d <= new_date.date()]))

    # Check to make sure we are not on a weekend
    new_date = get_next_business_day_after_weekend(new_date)

    if not ignore_holiday:
        # Check to make sure we are not on a holiday
        new_date = get_next_business_day_if_holiday(new_date)

    return new_date


def duedate_by_adding_business_seconds(from_date, add_seconds):
    seconds_per_day = 86400
    business_seconds_to_add = add_seconds
    current_date = from_date
    while business_seconds_to_add > 0:
        current_date_calculator = seconds_per_day if business_seconds_to_add > seconds_per_day else business_seconds_to_add
        current_date += datetime.timedelta(seconds=current_date_calculator)
        weekday = current_date.weekday()
        if weekday >= 5:  # sunday = 6
            continue
        business_seconds_to_add -= current_date_calculator
    return current_date


def workdays_between_dates(start_date, end_date, whichdays=(MON, TUE, WED, THU, FRI)):
    '''
    Calculate the number of working days between two dates inclusive (start_date <= end_date).
    The actual working days can be set with the optional whichdays parameter (default is MON-FRI)
    '''
    # delta_days = (end_date - start_date).days + 1
    days_bet = (parse_datetime(str(start_date)) - parse_datetime(str(end_date)))
    delta_days = days_bet.days
    full_weeks, extra_days = divmod(delta_days, 7)
    # num_workdays = how many days/week you work * total # of weeks
    num_workdays = (full_weeks + 1) * len(whichdays)
    # subtract out any working days that fall in the 'shortened week'
    for d in range(1, 8 - extra_days):
                if (end_date + timedelta(d)).weekday() in whichdays:
                                num_workdays -= 1
    return num_workdays


def get_next_business_day_if_holiday(due_date):

    holiday_dates = [d.holiday_date for d in get_holidays()]

    while due_date.date() in holiday_dates:
        due_date += timedelta(days=1)
        due_date = get_next_business_day_after_weekend(due_date)

    return due_date


def get_next_business_day_after_weekend(due_date):

    while due_date.weekday() not in working_days:
        due_date += timedelta(days=1)

    return due_date


def get_job_standard_duration(wordcount, translation_words_per_day=None, mbd=0.0):
    """ translation duration in business days """
    networds = wordcount * (1.00 + (settings.MBD_TAT_FACTOR * float(mbd)))
    minimum_translation_words = translation_words_per_day if translation_words_per_day else settings.MINIMUM_TRANSLATION_WORDS_STANDARD
    translation_words_per_day_calc = float(translation_words_per_day) if translation_words_per_day else settings.BASIC_TRANSLATION_WORDS_PER_DAY_STANDARD
    calculated_job_duration = calculate_job_duration(settings.TAT_DAYS_STANDARD, networds, minimum_translation_words, translation_words_per_day_calc)
    logger.info('duedates get_job_standard_duration wordcount %s, networds %s, minimum_translation_words %s, translation_words_per_day_calc %s, calculated_job_duration %s', wordcount, networds, minimum_translation_words, translation_words_per_day_calc, calculated_job_duration)
    return calculated_job_duration


def get_job_express_duration(wordcount, translation_words_per_day=None, mbd=0.0):
    """ translation duration in business days """
    networds = wordcount * (1.00 + (settings.MBD_TAT_FACTOR * float(mbd)))
    minimum_translation_words = translation_words_per_day if translation_words_per_day else settings.MINIMUM_TRANSLATION_WORDS_EXPRESS
    translation_words_per_day_calc = float(translation_words_per_day) if translation_words_per_day else settings.BASIC_TRANSLATION_WORDS_PER_DAY_EXPRESS
    return calculate_job_duration(settings.TAT_DAYS_EXPRESS, networds, minimum_translation_words, translation_words_per_day_calc)


def calculate_job_duration(base_day, wordcount, minimum_translation_words, translation_words_per_day_calc):
    return base_day + (int(math.ceil((wordcount - minimum_translation_words) / translation_words_per_day_calc)) if wordcount > minimum_translation_words else 0)


def get_task_standard_duration(hours):
    """
    :type hours: Decimal
    """
    return (hours / settings.HOURS_PER_DAY_STANDARD).to_integral_value(ROUND_CEILING)


def get_task_express_duration(hours):
    """
    :type hours: Decimal
    """
    return (hours / settings.HOURS_PER_DAY_EXPRESS).to_integral_value(ROUND_CEILING)


def get_hour_increment(wordcount, per_hour_count, increment_value, minimum_value=settings.ONE_HOUR_MIN_HOURS):
    increment_hours = (Decimal(increment_value) * wordcount / Decimal(per_hour_count))
    increment_hours = increment_hours.to_integral_value(ROUND_CEILING)
    if increment_hours <= increment_value:
        return Decimal(minimum_value)
    else:
        hours = increment_hours / increment_value
        hours = minimum_value if hours < minimum_value else hours
        return hours


def get_approval_task_duration(project):
    duration = 0.0
    if project.language_count() >= settings.LANGUAGE_COUNT_NUMBER_OF_LANGUAGES:
        # Excel Formula: =ROUNDUP((Language_Count-5)/5,0)
        if project.is_auto_estimate():
            duration = 1.0
        duration += math.ceil((project.language_count() - settings.LANGUAGE_COUNT_NUMBER_OF_LANGUAGES) / settings.LANGUAGE_COUNT_NUMBER_OF_LANGUAGES)
    return duration


def get_post_process_task_duration(project):
    duration = 0
    if project.language_count() >= settings.LANGUAGE_COUNT_NUMBER_OF_LANGUAGES:
        duration += 1
    return duration


def get_image_localization_hours():
    return 1


def get_image_localization_task_duration(hours):
    return get_task_standard_duration(hours)


def get_dtp_hours(wordcount):
    # one-hour minimum, half-hour increments after that.
    return get_hour_increment(wordcount, Decimal(settings.DTP_WORDS_PER_HOUR), settings.HALF_HOUR_INCREMENT_VALUE, settings.ONE_HOUR_MIN_HOURS)


def get_dtp_standard_duration(hours):
    return get_task_standard_duration(hours)


def get_dtp_express_duration(hours):
    return get_task_express_duration(hours)


def get_proofreading_hours(wordcount):
    # one-hour minimum, half-hour increments after that.
    return get_hour_increment(wordcount, Decimal(settings.PROOFREADING_WORDS_PER_HOUR), settings.HALF_HOUR_INCREMENT_VALUE, settings.ONE_HOUR_MIN_HOURS)


def get_proofreading_standard_duration(hours):
    return get_task_standard_duration(hours)


def get_proofreading_express_duration(hours):
    return get_task_express_duration(hours)


def get_review_hours(wordcount):
    # one-hour minimum, quarter-hour increments after that.
    return get_hour_increment(wordcount, Decimal(settings.POST_DTP_REVIEW_WORDS_PER_HOUR), settings.HALF_HOUR_INCREMENT_VALUE, settings.ONE_HOUR_MIN_HOURS)


def get_review_standard_duration(hours):
    return get_task_standard_duration(hours)


def get_review_express_duration(hours):
    return get_task_express_duration(hours)


def get_proof_third_party_review_hours(wordcount):
    # one-hour minimum, half-hour increments after that.
    return get_hour_increment(wordcount, Decimal(settings.PROOFREADING_THIRD_PARTY_REVIEW_WORDS_PER_HOUR), settings.HALF_HOUR_INCREMENT_VALUE, settings.ONE_HOUR_MIN_HOURS)


def get_proof_third_party_review_standard_duration(hours):
    return get_task_standard_duration(hours)


def get_proof_third_party_review_express_duration(hours):
    return get_task_express_duration(hours)


def get_lso_hours(wordcount):
    # one-hour minimum, half-hour increments after that.
    return get_hour_increment(wordcount, Decimal(settings.DTP_LSO_WORDS_PER_HOUR), settings.HALF_HOUR_INCREMENT_VALUE, settings.HALF_HOUR_MIN_HOURS)


def get_lso_standard_duration(hours):
    return get_task_standard_duration(hours)


def get_lso_express_duration(hours):
    return get_task_express_duration(hours)


def get_attorney_review_hours(wordcount):
    # one-hour minimum, quarter-hour increments after that.
    return get_hour_increment(wordcount, Decimal(settings.ATTORNEY_REVIEW_WORDS_PER_HOUR), settings.QUARTER_HOUR_INCREMENT_VALUE, settings.ONE_HOUR_MIN_HOURS)


def get_attorney_review_standard_duration(hours):
    return get_task_standard_duration(hours)


def get_attorney_review_express_duration(hours):
    return get_task_express_duration(hours)


def get_feedback_management_hours(wordcount):
    # half-hour minimum, quarter-hour increments after that.
    return get_hour_increment(wordcount, Decimal(settings.FEEDBACK_MANAGEMENT_WORDS_PER_HOUR), settings.QUARTER_HOUR_INCREMENT_VALUE, settings.FEEDBACK_MANAGEMENT_MIN_HOURS)


def get_file_prep_hours(wordcount):
    # half-hour minimum, quarter-hour increments after that.
    return get_hour_increment(wordcount, Decimal(settings.FILE_PREP_WORDS_PER_HOUR), settings.QUARTER_HOUR_INCREMENT_VALUE, settings.FILE_PREP_MIN_HOURS)


def get_recreate_source_from_pdf_hours(wordcount):
    # One-hour minimum, quarter-hour increments after that.
    return get_hour_increment(wordcount, Decimal(settings.RECREATE_SOURCE_FROM_PDF_WORDS_PER_HOUR), settings.QUARTER_HOUR_INCREMENT_VALUE, settings.HALF_HOUR_MIN_HOURS)


def get_pm_hour_hours(wordcount):
    # One-hour minimum.
    return Decimal(settings.PM_HOURS_MIN_HOURS)


_non_workflow_quantity = {
    FILE_PREP_SERVICE_TYPE: get_file_prep_hours,
    FEEDBACK_MANAGEMENT_SERVICE_TYPE: get_feedback_management_hours,
    RECREATE_SOURCE_FROM_PDF_SERVICE_TYPE: get_recreate_source_from_pdf_hours,
    PM_HOUR_SERVICE_TYPE: get_pm_hour_hours,
}


def get_non_workflow_hours(service_type, wordcount):
    if service_type.code in _non_workflow_quantity:
        func = _non_workflow_quantity[service_type.code]
        return func(wordcount)
    else:
        return 0
