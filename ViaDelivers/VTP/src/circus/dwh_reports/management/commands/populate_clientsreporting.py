#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging
from django.conf import settings
from django.core.management.base import BaseCommand
from clients.models import Client
from dwh_reports.models import ClientsReporting, ClientManager
from accounts.models import CircusUser
from people.models import AccountType

logger = logging.getLogger('circus.' + __name__)


def populate_clientreporting():
    try:
        logger.info(u'populate_clientreporting started')

        # GET CLIENTS
        client_account_type = AccountType.objects.get(code=settings.CLIENT_USER_TYPE)
        clients = Client.objects.filter(account_type=client_account_type.id).order_by('name')
        clients_count = clients.count()

        # for client in clients:
        for index, client in enumerate(clients, start=1):
            print(index, clients_count)

            clients_reporting, created = ClientsReporting.objects.get_or_create(
                client_id=client.id
            )
            clients_reporting.name = client.name
            clients_reporting.parent_id = client.parent_id
            clients_reporting.account_type = client.account_type_id
            clients_reporting.save()

            client_users = CircusUser.objects.filter(account=client).select_related()
            client_users_count = client_users.count()

            # for client_user in client_users:
            for indexcu, client_user in enumerate(client_users, start=1):
                print(indexcu, client_users_count)

                client_mgr_user, created = ClientManager.objects.get_or_create(
                    id=client_user.id
                )
                client_mgr_user.department = client_user.department
                client_mgr_user.account_id = client_user.account.id
                client_mgr_user.user_type = client_user.user_type
                client_mgr_user.first_name = client_user.first_name
                client_mgr_user.last_name = client_user.last_name
                client_mgr_user.email = client_user.email
                client_mgr_user.reports_to_id = client_user.reports_to_id
                client_mgr_user.save()

        logger.info(u'populate_clientreporting completed')

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
            logger.info("populate_clientreporting started")
            populate_clientreporting()
            logger.info("populate_clientreporting All done!")
        except Exception:
            # unlike django request handling, management commands don't have
            # any top-level exception logger. add one here as this is run
            # unattended by heroku scheduler.
            logger.error("error in populate_clientreporting", exc_info=True)
            raise
