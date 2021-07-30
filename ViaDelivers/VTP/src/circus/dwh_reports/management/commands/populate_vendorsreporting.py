#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from dwh_reports.models import VendorsReporting, VendorUserReporting
from accounts.models import CircusUser
from people.models import AccountType
from vendors.models import Vendor

logger = logging.getLogger('circus.' + __name__)


def populate_vendorreporting():
    try:
        logger.info(u'populate_vendorreporting started')

        # GET VENDORS
        vendor_account_type = AccountType.objects.get(code=settings.VENDOR_USER_TYPE)
        vendors = Vendor.objects.filter(account_type=vendor_account_type.id).order_by('name')
        vendors_count = vendors.count()

        # for vendor in vendors:
        for index, vendor in enumerate(vendors, start=1):
            print(index, vendors_count)

            vendor_reporting, created = VendorsReporting.objects.get_or_create(
                client_id=vendor.id
            )
            vendor_reporting.name = vendor.name
            vendor_reporting.parent_id = vendor.parent_id
            vendor_reporting.account_type=vendor.account_type_id
            vendor_reporting.save()

            vendor_users = CircusUser.objects.filter(account=vendor).select_related()
            vendor_users_count = vendor_users.count()

            # for vendor_user in vendor_users:
            for indexvu, vendor_user in enumerate(vendor_users, start=1):
                print(indexvu, vendors_count)


                vendor_user_reporting, created = VendorUserReporting.objects.get_or_create(
                    id=vendor_user.id
                )
                vendor_user_reporting.department = vendor_user.department
                vendor_user_reporting.account_id = vendor_user.account.id
                vendor_user_reporting.user_type = vendor_user.user_type
                vendor_user_reporting.first_name = vendor_user.first_name
                vendor_user_reporting.last_name = vendor_user.last_name
                vendor_user_reporting.email = vendor_user.email
                vendor_user_reporting.reports_to_id = vendor_user.reports_to_id
                vendor_user_reporting.save()

        logger.info(u'populate_vendorreporting completed')

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
            logger.info("populate_vendorreporting started")
            populate_vendorreporting()
            logger.info("All done!")
        except Exception:
            # unlike django request handling, management commands don't have
            # any top-level exception logger. add one here as this is run
            # unattended by heroku scheduler.
            logger.error("error in populate_vendorreporting", exc_info=True)
            raise
