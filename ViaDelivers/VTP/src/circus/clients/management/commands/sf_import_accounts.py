# -*- coding: utf-8 -*-
import os.path
import sys

from django.core.management import BaseCommand
import unicodecsv
from clients.models import Client

DATA_FILENAME = 'salesforce_account_ids.csv'

SALESFORCE_ID_LENGTH = 15


def error(msg, *args):
    sys.stderr.write((msg % args).encode('utf-8') + '\n')


def import_contact_ids(infile, dry_run=True):
    reader = unicodecsv.DictReader(infile)
    count = 0
    error_count = 0
    for record in reader:

        # VTP Account ID,JAMS Account ID,VTP Account Name,SF Account Name,SF Account ID

        count += 1
        vtp_id = record['VTP Account ID']
        sf_id = record['SF Account ID']

        if len(sf_id) != SALESFORCE_ID_LENGTH:
            error(u"%r has bad SF ID", record)
            error_count += 1
            continue

        account = Client.objects.filter(id=vtp_id)
        if dry_run:
            written = account.exists()
        else:
            written = bool(account.update(salesforce_account_id=sf_id))

        if not written:
            error(u"No VTP account ID %r for record %r", vtp_id, record)
            error_count += 1

    if dry_run:
        print "DRY RUN complete."

    print "%s records processed, %s errors." % (count, error_count)


class Command(BaseCommand):
    help = 'salesforce Account ID import from salesforce_account_ids.csv'

    def handle(self, *args, **kwargs):
        filename = os.path.join(os.path.dirname(__file__), DATA_FILENAME)
        with file(filename, 'rb') as csv_file:
            import_contact_ids(csv_file, False)
