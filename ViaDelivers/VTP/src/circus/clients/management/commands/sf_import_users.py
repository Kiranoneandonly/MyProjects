# -*- coding: utf-8 -*-
import sys

from django.core.management import BaseCommand
from accounts.models import CircusUser

SALESFORCE_ID_LENGTH = 15

COL_SF_ID = 1
COL_VTP_EMAIL = 2

DATA = [
    ('abatman', '00540000001U5l6', u'abatman@viadelivers.com'),
    ('bkennedy', '00540000000ogml', u'bkennedy@viadelivers.com'),
    ('developer', '00540000002JBc5', u'developer@viadelivers.com'),
    ('dmegarry', '00540000000ldlj', u'dmegarry@viadelivers.com'),
    ('dpenney', '00540000001S9Jq', None),
    ('dwittwer', '00540000001Slwq', u'dwittwer@viadelivers.com'),
    ('kdonovan', '00540000001SqTA', u'kdonovan@viadelivers.com'),
    ('liburg', '00540000001SgvR', u'liburg@viadelivers.com'),
    ('lwhite', '00540000000yUsD', u'lwhite@viadelivers.com'),
    ('rchacon', '00540000001TKGd', None),
    ('rgrimmer', '00540000001RfQN', u'rgrimmer@viadelivers.com'),
    ('sherber', '00540000000yf6t', None),
    ('thoward', '00540000001Sb2W', u'thoward@viadelivers.com')
]


def error(msg, *args):
    sys.stderr.write((msg % args).encode('utf-8') + '\n')


def import_user_ids(dry_run=True):
    count = 0
    error_count = 0
    for record in DATA:
        count += 1
        vtp_id = record[COL_VTP_EMAIL]
        sf_id = record[COL_SF_ID]

        if len(sf_id) != SALESFORCE_ID_LENGTH:
            error(u"%r has bad SF ID", record)
            error_count += 1
            continue

        if vtp_id is None:
            print u"No VTP account, skipping %s" % (record,)
            continue

        try:
            user = CircusUser.objects.get_by_natural_key(vtp_id)
        except CircusUser.DoesNotExist:
            error(u"VTP user not found: %r", vtp_id)
            error_count += 1
            continue
        else:
            print "Found %s <= %s" % (user, sf_id)

        user.salesforce_user_id = sf_id

        if not dry_run:
            user.save()

    if dry_run:
        print "DRY RUN complete."

    print "%s records processed, %s errors." % (count, error_count)


class Command(BaseCommand):
    help = 'salesforce User ID import (VIA accounts only)'

    def handle(self, *args, **kwargs):
        import_user_ids(False)
