#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from dwh_reports.models import TaskRating
from tasks.models import Task
from people.models import AccountType

logger = logging.getLogger('circus.' + __name__)


def populate_taskrating(last_modified=None):
    try:
        logger.info(u'populate_taskrating started')

        task_ratings = Task.objects.extra(where=["LENGTH(notes) > 0 or LENGTH(via_notes) > 0 or LENGTH(vendor_notes) > 0 or rating > 0"])

        logger.info(u'populate_taskrating task_ratings count: %s' % task_ratings.count())

        if last_modified:
            rating_report_filter = Q(modified__gte=last_modified)
            task_ratings = task_ratings.filter(rating_report_filter)

        tr_count = task_ratings.count()

        # for rating in task_ratings:
        for index, rating in enumerate(task_ratings, start=1):
            print(index, tr_count)
            assignee_type = None
            if rating.assignee_object_id:
                if hasattr(rating.assigned_to, 'name'):
                    assignee_name = rating.assigned_to.name
                    assignee_type = rating.assigned_to.account_type_id
                elif rating.assigned_to:
                    assignee_name = rating.assigned_to.get_full_name()
                    assignee_type = rating.assigned_to.user_type
                else:
                    assignee_name = None
                    assignee_type = None

            account_type = AccountType.objects.get(code=settings.VENDOR_USER_TYPE)
            if assignee_type == settings.VENDOR_USER_TYPE or assignee_type == account_type.id:
                rating_reporting, created = TaskRating.objects.get_or_create(
                    pk=rating.pk
                )
                rating_reporting.task_id = rating.id
                rating_reporting.project_id = rating.project_id
                rating_reporting.job_number = rating.project.job_number
                ### Here calling __unicode__() method as without that, not getting the object/task name.
                rating_reporting.task_name = rating.__unicode__()
                rating_reporting.assignee_object_id = rating.assignee_object_id
                rating_reporting.assignee_name = assignee_name
                rating_reporting.rating = rating.rating
                rating_reporting.service_id = rating.service.service_type.id
                rating_reporting.service_type = rating.service.service_type.description
                rating_reporting.notes = rating.notes
                rating_reporting.via_notes = rating.via_notes
                rating_reporting.vendor_notes = rating.vendor_notes
                rating_reporting.due_date = rating.due
                rating_reporting.started = rating.started_timestamp
                rating_reporting.completed = rating.completed_timestamp
                rating_reporting.save()

            else:
                logger.info(u'populate_taskrating : No assignee_type == settings.VENDOR_USER_TYPE!!!')
        else:
            logger.info(u'populate_taskrating : No task_ratings!!!')

        logger.info(u'populate_taskrating completed')

    except Exception, exc:
        import pprint
        msg = [
            u'Exception:',
            pprint.pformat(exc),
        ]
        logger.error(msg)
        raise


class Command(BaseCommand):
    args = ''
    help = 'Scheduler to sync VTP Reporting Data Warehouse.'

    def handle(self, *args, **options):

        try:
            logger.info("populate_taskrating started")
            populate_taskrating()
            logger.info("populate_taskrating All done!")
        except Exception:
            # unlike django request handling, management commands don't have
            # any top-level exception logger. add one here as this is run
            # unattended by heroku scheduler.
            logger.error("error in populate_taskrating", exc_info=True)
            raise
