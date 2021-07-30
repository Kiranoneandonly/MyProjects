# -*- coding: utf-8 -*-
"""Reports exported to other data formats (i.e. spreadsheet)."""
import time
from Queue import Queue
from cStringIO import StringIO
from datetime import timedelta
from threading import Thread

from django.conf import settings
from django.db.models import Q
from django.utils.timezone import now
from unicodecsv import DictWriter

from dwh_reports.models import TasksReporting, ClientManager, TaskRating
from dwh_reports.states import CLIENT_REPORT_VIA_STATUS_DETAIL_CLIENT_PORTAL, client_report_via_normalize_status
from projects.states import ALL_STATUS, QUOTED_STATUS, STARTED_STATUS, COMPLETED_STATUS, CLOSED_STATUS
from shared.utils import format_datetime, remove_html_tags

COL_JOB_NUMBER = u'Number'
COL_PROJECT_STATUS = u'Status'
COL_CLIENT_NAME = u'Client'
COL_DEPARTMENT = u'Department'
COL_USER_FULL_NAME = u'Owner'
COL_CLIENT_MANAGER = u'Manager'
COL_PROJECT_REFERENCE_NAME = u'Project Reference Name'
COL_USER_EMAIL = u'Email'
COL_PROJECT_MANAGER = u'PM'
COL_SOURCE = u'Source'
COL_TARGET = u'Target'
COL_FILENAME = u'File'
COL_TASK_TYPE = u'Task'
COL_PRICE = u'Price'
COL_WORD_COUNT = u'WordCount'
COL_MBD = u'MBD'
COL_PAYMENT_METHOD = u'Payment'
COL_PAYMENT_PO = u'PO'
COL_INDUSTRY = u'Industry'
COL_PRIORITY = u'Priority'
COL_ESTIMATE_TYPE = u'Type'
COL_CLIENT_INSTRUCTIONS = u'Instructions'
COL_START_DATE = u'Started'
COL_QUOTED_DATE = u'Quoted'
COL_DUE_DATE = u'Due'
COL_DELIVERED_DATE = u'Delivered'

q = Queue()


def client_activity_csv(client, status, from_days, to_days):
    fields = [
        COL_JOB_NUMBER,
        COL_PROJECT_STATUS,
        COL_CLIENT_NAME,
        COL_DEPARTMENT,
        COL_USER_FULL_NAME,
        COL_CLIENT_MANAGER,
        COL_PROJECT_REFERENCE_NAME,
        COL_USER_EMAIL,
        COL_PROJECT_MANAGER,
        COL_SOURCE,
        COL_TARGET,
        COL_TASK_TYPE,
        COL_FILENAME,
        COL_PRICE,
        COL_WORD_COUNT,
        COL_MBD,
        COL_PAYMENT_METHOD,
        COL_PAYMENT_PO,
        COL_INDUSTRY,
        COL_PRIORITY,
        COL_ESTIMATE_TYPE,
        COL_CLIENT_INSTRUCTIONS,
        COL_START_DATE,
        COL_QUOTED_DATE,
        COL_DUE_DATE,
        COL_DELIVERED_DATE,
    ]

    t = Thread(target=get_client_activity_records, args=(client, status, from_days, to_days))
    t.start()

    while t.is_alive():
        time.sleep(1)
        t.join(.1)
        yield (" ")

    records = q.get(False)

    outfile = StringIO()
    csv_writer = DictWriter(outfile, fields)

    csv_writer.writeheader()
    csv_writer.writerows(records)

    yield outfile.getvalue()
    return


def get_client_activity_records(client, status=ALL_STATUS, from_days=settings.REPORT_DEFAULT_DAYS_FROM, to_days=None):
    records = []
    #: :type: django.db.models.query.QuerySet[Project]

    taskreports_filter = Q(project__project_status__in=[QUOTED_STATUS, STARTED_STATUS, COMPLETED_STATUS, CLOSED_STATUS])

    if client:
        taskreports_filter &= (Q(project__customer=client.client_id) | Q(project__customer__parent_id=client.client_id))

    if status and status != ALL_STATUS:
        taskreports_filter &= Q(project__project_status=status)

    if from_days:
        if to_days is None:
            from_date = (now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=from_days))
            taskreports_filter &= (Q(project__quoted__gte=from_date) | Q(project__start_date__gte=from_date))
        else:
            to_date = (now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=int(to_days)))
            from_date = (to_date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=int(from_days)))
            taskreports_filter &= (Q(project__quoted__gte=from_date) | Q(project__start_date__gte=from_date)) & \
                                  (Q(project__quoted__lt=to_date) | Q(project__start_date__lt=to_date))

    tasks = TasksReporting.objects.filter(taskreports_filter).select_related().\
        order_by('project__job_number', 'target', 'source_file', 'service_type')

    for task in tasks:
        manager_name = None
        manager_id = ClientManager.objects.filter(id=task.project.client_poc.reports_to_id)
        for manager in manager_id:
            manager_name = manager.first_name + ' ' + manager.last_name

        task.project.project_status = client_report_via_normalize_status(task.project.project_status)
        task_project_workflow = CLIENT_REPORT_VIA_STATUS_DETAIL_CLIENT_PORTAL[task.project.project_status]['text']

        record = {
            COL_JOB_NUMBER: task.project.job_number,
            COL_PROJECT_STATUS: task_project_workflow,
            COL_CLIENT_NAME: client.name,
            COL_DEPARTMENT: task.project.client_poc.department,
            COL_USER_FULL_NAME: task.project.client_poc.first_name + ' ' + task.project.client_poc.last_name,
            COL_CLIENT_MANAGER: manager_name,
            COL_PROJECT_REFERENCE_NAME: task.project.project_reference_name,
            COL_USER_EMAIL: task.project.client_poc.email,
            COL_PROJECT_MANAGER: task.project.project_manager,
            COL_SOURCE: task.project.source_locale,
            COL_PRIORITY: task.project.priority,
            COL_ESTIMATE_TYPE: task.project.estimate_type,
            COL_PAYMENT_METHOD: task.project.payment_method,
            COL_PAYMENT_PO: task.project.client_po,
            COL_INDUSTRY: task.project.industry,
            COL_CLIENT_INSTRUCTIONS: remove_html_tags(task.project.instructions),
            COL_START_DATE: format_datetime(task.project.start_date),
            COL_QUOTED_DATE: format_datetime(task.project.quoted),
            COL_DUE_DATE: format_datetime(task.project.due_date),
            COL_DELIVERED_DATE: format_datetime(task.project.delivered_date),
            COL_TASK_TYPE: task.service_type,
            COL_TARGET: task.target,
            COL_PRICE: task.price,
            COL_FILENAME: task.source_file,
            COL_MBD: u'%f%s' % (task.memory_bank_discount, '%'),
            COL_WORD_COUNT: task.word_count,
        }
        records.append(record)

    q.put(records)
    return records


# For the Supplier Task Rating Export

COL_SUPPLIER_NAME = u'Supplier Name'
COL_RATING = u'Rating'
COL_SERVICE = u'Service'
COL_NOTES = u'Instructions'
COL_VENDOR_NOTES = u'Supplier Notes'
COL_VIA_NOTES = u'Delivery Notes'
COL_TASK = u'Task'
COL_PROJECT = u'Job'
COL_STARTED = u'Started'
COL_COMPLETED = u'Completed'


def supplier_ratings_by_task_csv(assignee_id, days):
    fields = [
        COL_SUPPLIER_NAME,
        COL_RATING,
        COL_SERVICE,
        COL_NOTES,
        COL_VENDOR_NOTES,
        COL_VIA_NOTES,
        COL_TASK,
        COL_PROJECT,
        COL_STARTED,
        COL_COMPLETED,
    ]

    t = Thread(target=get_supplier_ratings_by_task_records, args=(assignee_id, days))
    t.start()

    while t.is_alive():
        time.sleep(1)
        t.join(.1)
        yield (" ")

    records = q.get(False)

    outfile = StringIO()
    csv_writer = DictWriter(outfile, fields)

    csv_writer.writeheader()
    csv_writer.writerows(records)

    yield outfile.getvalue()
    return


def get_supplier_ratings_by_task_records(assignee_id, days=settings.REPORT_DEFAULT_DAYS_FROM):
    records = []
    taskrating_filter = Q(project_id__isnull=False)

    if assignee_id and not assignee_id == '0':
        taskrating_filter &= (Q(assignee_object_id=assignee_id))

    if days:
        from_date = (now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days))
        taskrating_filter &= (Q(started__gte=from_date))

    task_ratings = TaskRating.objects.filter(taskrating_filter).order_by('started')

    for rating in task_ratings:
        record = {
            COL_SUPPLIER_NAME: rating.assignee_name,
            COL_RATING: rating.rating,
            COL_SERVICE: rating.service_type,
            COL_NOTES: rating.notes,
            COL_VENDOR_NOTES: rating.vendor_notes,
            COL_VIA_NOTES: rating.via_notes,
            COL_TASK: rating.task_name,
            COL_PROJECT: rating.job_number,
            COL_STARTED: rating.started,
            COL_COMPLETED: rating.completed,
        }
        records.append(record)

    q.put(records)
    return records
