#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from dwh_reports.models import ClientsReporting, ClientReportAccess, ClientReport
from people.models import AccountType

logger = logging.getLogger('circus.' + __name__)


def populate_clientreportaccess():
    try:
        logger.info(u'populate_clientreportaccess started')

        # GET CLIENTS
        clients = ClientsReporting.objects.order_by('name')
        clients_count = clients.count()
        reports = ClientReport.objects.all()
        reports_count = reports.count()

        # for client in clients:
        for index, client in enumerate(clients, start=1):
            print(index, clients_count)

            # for report in reports:
            for indexr, report in enumerate(reports, start=1):
                print(indexr, reports_count)

                clients_reporting, created = ClientReportAccess.objects.get_or_create(
                    client_id=client.client_id,
                    client_report_id=report.id
                )
                clients_reporting.save()

        logger.info(u'populate_clientreportaccess completed')

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
            logger.info("populate_clientreportaccess started")
            populate_clientreportaccess()
            logger.info("populate_clientreportaccess All done!")
        except Exception:
            # unlike django request handling, management commands don't have
            # any top-level exception logger. add one here as this is run
            # unattended by heroku scheduler.
            logger.error("error in populate_clientreportaccess", exc_info=True)
            raise
