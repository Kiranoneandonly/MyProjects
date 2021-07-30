# -*- coding: utf-8 -*-
"""I just need anyone with a value in Column T (19) to be put in for Third
Party Review and anyone with a value in column W (22) to be put in for DTP.
Both should be on a per language basis (Identified in columns D, E, F (3–5))
and please add everybody on an “Hourly” basis since per page could be
confusing."""
from decimal import Decimal

import os.path
import re
from django.core.management import BaseCommand
import unicodecsv

from clients.models import Client
from prices.models import VendorNonTranslationRate
from services.managers import HOURS_UNITS, THIRD_PARTY_REVIEW_SERVICE_TYPE, \
    DTP_SERVICE_TYPE
from services.models import ScopeUnit, ServiceType, Locale, Service
from vendors.models import Vendor

COL_JAMS_SUPPLIER_ID = 0  # Vendor.account_number
COL_JAMS_CLIENT_ID = 7
COL_CLIENT_NAME = 8
COL_LANGS_DESC = 3
COL_SOURCE_LCID = 4
COL_TARGET_LCID = 5
COL_REVIEW_RATE = 19
COL_DTP_RATE = 22


def success(*args):
    print(u'\t'.join(unicode(a) for a in args))


shorten = re.compile(r'^(.+?)\(?')


class LocaleChecker(object):

    def __init__(self):
        self.missing = set()
        self.mismatch = set()

    def check_record(self, record):
        problems = []
        langs = record[COL_LANGS_DESC]
        source_desc, target_desc = langs.split(' to ')

        lcid_descs = [
            (record[COL_SOURCE_LCID], source_desc),
            (record[COL_TARGET_LCID], target_desc)
        ]

        for lcid, desc in lcid_descs:
            lcid = int(lcid)
            try:
                locale = Locale.objects.get(dvx_lcid=lcid)
            except Locale.DoesNotExist:
                self.missing.add((lcid, desc))
                problems.append(lcid)
                continue

            short_desc = shorten.match(desc).group(1)
            if not short_desc in locale.description:
                self.mismatch.add((lcid, desc, locale.description, locale.id))
                problems.append(lcid)

        return problems


    def report(self):
        print("Locales which did not match any dvx_lcid:")
        for lcid, desc in self.missing:
            print((u"%d\t%s" % (lcid, desc)).encode('utf-8'))

        print("Locales with name mismatches")
        print("import LCID\timport description\tVTP description\tVTP ID")
        for row in self.mismatch:
            print(u"\t".join(unicode(f) for f in row).encode('utf-8'))



def create_vendor_dtp_and_review_rates(records, dry_run=True):
    hourly = ScopeUnit.objects.get(code=HOURS_UNITS)
    review = ServiceType.objects.get(code=THIRD_PARTY_REVIEW_SERVICE_TYPE)
    dtp = ServiceType.objects.get(code=DTP_SERVICE_TYPE)

    checker = LocaleChecker()

    row_number = 0
    review_count = 0
    dtp_count = 0
    errors = []

    for row_number, record in enumerate(records):
        try:
            review_rate = Decimal(record[COL_REVIEW_RATE])
            dtp_rate = Decimal(record[COL_DTP_RATE])

            if not review_rate or not dtp_rate:
                continue

            locale_problems = checker.check_record(record)
            if locale_problems:
                errors.append(
                    u"row %d: skipped %s for locale %r, see locale report" %
                    (row_number, record[COL_LANGS_DESC], locale_problems))
                continue

            vendor = Vendor.objects.get(account_number=record[COL_JAMS_SUPPLIER_ID])

            client_id = int(record[COL_JAMS_CLIENT_ID])

            if client_id:
                try:
                    client = Client.objects.get(account_number=client_id)
                except Client.DoesNotExist:
                    client_name = record[COL_CLIENT_NAME]
                    errors.append(
                        "row %d: Cannot find client with account_number %d (%s)" % (
                            row_number + 1, client_id, client_name
                        ))
                    continue
            else:
                client = None

            source = Locale.objects.get(dvx_lcid=record[COL_SOURCE_LCID])
            target = Locale.objects.get(dvx_lcid=record[COL_TARGET_LCID])

            if review_rate:
                if dry_run:
                    success(row_number + 1, '3PR', vendor.name, client and client.name,
                            source.description, target.description,
                            review_rate, '')
                else:
                    review_service = Service.objects.get_or_create(
                        service_type=review,
                        unit_of_measure=hourly,
                        source=source,
                        target=target
                    )[0]

                    new_review_rate = VendorNonTranslationRate.objects.create(
                        vendor=vendor,
                        service=review_service,
                        client=client,
                        unit_cost=review_rate
                    )
                    review_count += 1
                    success(row_number + 1, '3PR', vendor.name, client and client.name,
                            source.description, target.description,
                            new_review_rate.unit_cost, new_review_rate.id)


            if dtp_rate:
                if dry_run:
                    success(row_number + 1, 'DTP', vendor.name, client and client.name,
                            source.description, target.description,
                            dtp_rate, '')
                else:
                    dtp_service = Service.objects.get_or_create(
                        service_type=dtp,
                        unit_of_measure=hourly,
                        source=source,
                        target=target
                    )[0]

                    new_dtp_rate = VendorNonTranslationRate.objects.create(
                        vendor=vendor,
                        service=dtp_service,
                        client=client,
                        unit_cost=dtp_rate
                    )
                    dtp_count += 1
                    success(row_number + 1, 'DTP', vendor.name, client and client.name,
                            source.description, target.description,
                            new_dtp_rate.unit_cost, new_dtp_rate.id)
        except Exception:
            print("Error on row %d\n%s" % (row_number + 1, record))
            raise

    print("%d rows processed, %d review rates created, %d DTP rates created" %
          (row_number + 1, review_count, dtp_count))

    if errors:
        print("%d errors:" % (len(errors),))
        print(('\n'.join(errors)).encode('utf8'))
    else:
        print("No errors. :-)")

    checker.report()


class Command(BaseCommand):
    help = 'Import third party review and DTP rates from vendors_pricing_etl CSV'

    def handle(self, *args, **kwargs):
        filename = os.path.join(os.path.dirname(__file__),
                                'vendors_pricing_etl.csv')
        with file(filename, 'rb') as csv_file:
            reader = unicodecsv.reader(csv_file)
            create_vendor_dtp_and_review_rates(reader, dry_run=False)
