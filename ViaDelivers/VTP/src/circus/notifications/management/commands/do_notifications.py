from __future__ import unicode_literals
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.timezone import now
from notifications.notifications import vendor_did_not_respond_to_project, vendor_delivery_overdue
from projects.duedates import get_late_response_timestamp
from tasks.models import Task
import datetime


def get_unique_pairs(tasks):
    to_notify = set()
    for task in tasks:
        # to_notify.add((task.assigned_to, task.project))
        if task.overdue_email_last_sent is not None:
            if now()-task.overdue_email_last_sent > datetime.timedelta(days=1):
                to_notify.add((task.assigned_to, task.project))
                task_object = Task.objects.get(id=task.id)
                task_object.overdue_email_last_sent = now()
                task_object.save()
        else:
            to_notify.add((task.assigned_to, task.project))
            task_object = Task.objects.get(id=task.id)
            task_object.overdue_email_last_sent = now()
            task_object.save()
    return to_notify


def check_overdue_task_responses():
    """ Any tasks that haven't been accepted or rejected by the assigned vendor in time """
    for vendor, project in get_unique_pairs(Task.objects.pending_acceptance().filter(started_timestamp__lt=get_late_response_timestamp())):
        print "Task has not been accepted: {0}, {1}".format(vendor, project.job_number)
        vendor_did_not_respond_to_project(vendor, project)


def check_overdue_deliveries():
    """ Tasks that haven't been delivered by the vendor """
    for vendor, project in get_unique_pairs(Task.objects.pending_completion().filter(due__lt=timezone.now())):
        print "Task has not been delivered: {0}, {1}".format(vendor, project.job_number)
        vendor_delivery_overdue(vendor, project)


class Command(BaseCommand):
    args = ''
    help = 'check for notices that need to go out'

    def handle(self, *args, **options):
        check_overdue_task_responses()
        check_overdue_deliveries()