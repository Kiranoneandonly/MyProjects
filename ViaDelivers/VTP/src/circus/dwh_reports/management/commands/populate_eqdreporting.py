#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
from django.core.management.base import BaseCommand
from django.db.models import Q
from dwh_reports.models import EqdReporting
from projects.models import Project
from quality_defects.models import QualityDefect

logger = logging.getLogger('circus.' + __name__)


def populate_eqdreporting(last_modified=None):
    try:
        logger.info(u'populate_eqdreporting started')

        eqd_report_filter = Q(project_id__isnull=False)
        if last_modified:
            eqd_report_filter = eqd_report_filter & Q(due_modified__gte=last_modified)

        quality_defects = QualityDefect.objects.filter(eqd_report_filter)
        quality_defects_count = quality_defects.count()

        # for eqd in quality_defects:
        for index, eqd in enumerate(quality_defects, start=1):
            print(index, quality_defects_count)

            project_manager_id = None
            mgr_id = Project.objects.select_related().filter(pk=eqd.project_id)
            for mgr in mgr_id:
                project_manager_id = mgr.project_manager_id

            eqd_reporting, created = EqdReporting.objects.get_or_create(
                pk=eqd.pk
            )
            eqd_reporting.quality_defect = eqd.quality_defect
            eqd_reporting.title = eqd.title
            eqd_reporting.client_id = eqd.client_id
            eqd_reporting.project_id = eqd.project_id
            eqd_reporting.task_id = eqd.task_id
            eqd_reporting.project_manager_id = project_manager_id
            eqd_reporting.due_date = eqd.due_date
            eqd_reporting.due_created = eqd.due_created
            eqd_reporting.due_modified = eqd.due_modified
            eqd_reporting.save()

        logger.info(u'populate_eqdreporting completed')

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
            logger.info("populate_eqdreporting started")
            populate_eqdreporting()
            logger.info("populate_eqdreporting All done!")
        except Exception:
            # unlike django request handling, management commands don't have
            # any top-level exception logger. add one here as this is run
            # unattended by heroku scheduler.
            logger.error("error in populate_viareporting", exc_info=True)
            raise
