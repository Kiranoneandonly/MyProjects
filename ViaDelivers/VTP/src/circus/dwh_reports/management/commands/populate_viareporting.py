#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from dwh_reports.models import ViaReporting, ViaUserReporting
from accounts.models import CircusUser
from people.models import AccountType
from via_staff.models import Via

logger = logging.getLogger('circus.' + __name__)


def populate_viareporting():
    try:
        logger.info(u'populate_viareporting started')

        # GET VIA Employees
        via_account_type = AccountType.objects.get(code=settings.VIA_USER_TYPE)
        via_companys = Via.objects.all().order_by('name')
        via_companys_count = via_companys.count()

        # for via_company in via_companys:
        for index, via_company in enumerate(via_companys, start=1):
            print(index, via_companys_count)

            via_reporting, created = ViaReporting.objects.get_or_create(
                client_id=via_company.id
            )
            via_reporting.name = via_company.name
            via_reporting.parent_id = via_company.parent_id
            via_reporting.account_type = via_company.account_type_id
            via_reporting.save()

            via_users = CircusUser.objects.filter(account=via_company).select_related()
            via_users_count = via_users.count()

            # for via_user in via_users:
            for indexvu, via_user in enumerate(via_users, start=1):
                print(indexvu, via_users_count)

                via_user_reporting, created = ViaUserReporting.objects.get_or_create(
                    id=via_user.id
                )
                via_user_reporting.department = via_user.department
                via_user_reporting.account_id = via_user.account.id
                via_user_reporting.user_type = via_user.user_type
                via_user_reporting.first_name = via_user.first_name
                via_user_reporting.last_name = via_user.last_name
                via_user_reporting.email = via_user.email
                via_user_reporting.reports_to_id = via_user.reports_to_id
                via_user_reporting.save()

        logger.info(u'populate_viareporting completed')

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
            logger.info("populate_viareporting started")
            populate_viareporting()
            logger.info("populate_viareporting All done!")
        except Exception:
            # unlike django request handling, management commands don't have
            # any top-level exception logger. add one here as this is run
            # unattended by heroku scheduler.
            logger.error("error in populate_viareporting", exc_info=True)
            raise
