#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
from django.core.management.base import BaseCommand
from dwh_reports.models import TasksReporting, ClientsReporting, ProjectsReporting, RefreshTracking, ClientManager,\
    EqdReporting, VendorUserReporting, VendorsReporting, ViaUserReporting, ViaReporting, ClientReportAccess, TaskRating

logger = logging.getLogger('circus.' + __name__)


def cleanout_dwh_reports_data():
    try:
        logger.info(u'cleanout_dwh_reports_data started')

        TaskRating.objects.all().delete()
        EqdReporting.objects.all().delete()
        TasksReporting.objects.all().delete()
        ProjectsReporting.objects.all().delete()
        ClientManager.objects.all().delete()
        ClientReportAccess.objects.all().delete()
        ClientsReporting.objects.all().delete()
        VendorUserReporting.objects.all().delete()
        VendorsReporting.objects.all().delete()
        ViaUserReporting.objects.all().delete()
        ViaReporting.objects.all().delete()
        RefreshTracking.objects.all().delete()

        logger.info(u'cleanout_dwh_reports_data completed')

    except Exception, exc:
        import pprint
        msg = [
            u'cleanout_dwh_reports_data Exception:',
            pprint.pformat(exc),
        ]
        logger.error(msg)
        raise


class Command(BaseCommand):
    args = ''
    help = 'Clean the VTP Reporting Data Warehouse.'

    def handle(self, *args, **options):

        try:
            logger.info("clean_dwh_reports_data : Started")
            cleanout_dwh_reports_data()
            logger.info("clean_dwh_reports_data : All done!")
        except Exception:
            # Unlike django request handling, management commands don't have any top-level exception logger.
            # Add one here as this is run unattended by heroku scheduler.
            logger.error("clean_dwh_reports_data : Error!", exc_info=True)
            raise
