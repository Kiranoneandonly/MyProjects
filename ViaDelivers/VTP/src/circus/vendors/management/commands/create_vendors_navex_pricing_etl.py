# -*- coding: utf-8 -*-
import re
from decimal import Decimal
from django.core.management import BaseCommand
import unicodecsv
from clients.models import Client
from prices.models import VendorTranslationRate
from services.managers import SOURCE_BASIS, TRANSLATION_EDIT_PROOF_SERVICE_TYPE, \
    WORDS_UNITS
from services.models import Locale, PricingBasis, ServiceType, ScopeUnit, \
    Service
from shared.utils import sibpath
from vendors.models import Vendor

INPUT_FILENAME = 'vendors_navex_pricing_etl.csv'

COL_MINIMUM = 'Minimum'
COL_SERVICE = 'Service'
COL_TARGET_LCID = 'Target LCID'
COL_VENDOR = 'Vendor'
COL_WORD_RATE = 'Word rate'

COL_PRFECT = 'Prfect'  # sic
COL_EXACT = 'Exact'
COL_REPS = 'Reps'
COL_9599 = '95-99'
COL_8594 = '85-94'
COL_7584 = '75-84'
COL_5074 = '50-74'
COL_NO_MATCH = 'NoMch'

expansion_re = re.compile(r'\((\d\.\d+)\)$')

VERBOSE = False


def make_vendor_rates_for_navex(input_file, dry_run=False):
    reader = unicodecsv.DictReader(input_file)

    print """\
Assumptions:
    All sources are English.
    All rates are based on source words.
    Vendors already exist.
"""

    source = Locale.objects.get(lcid=1033)
    source_basis = PricingBasis.objects.get(code=SOURCE_BASIS)
    tep = ServiceType.objects.get(code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE)
    unit_of_measure = ScopeUnit.objects.get(code=WORDS_UNITS)

    navex = Client.objects.get(account_number='1880', parent=None)

    print 'new\tid\tvendor_id\tvendor\ttarget_lcid\tword_rate\tminimum'

    for record in reader:
        if VERBOSE:
            print record

        vendor = Vendor.objects.get(name=record[COL_VENDOR])

        target = Locale.objects.get(lcid=record[COL_TARGET_LCID])

        expansion_rate = expansion_re.search(record[COL_SERVICE]).group(1)
        expansion_rate = float(expansion_rate)

        # not using get_or_create because of expansion_rate discrepancies
        try:
            service = Service.objects.get(
                service_type=tep,
                unit_of_measure=unit_of_measure,
                source=source,
                target=target,
            )
        except Service.DoesNotExist:
            service = Service.objects.create(
                service_type=tep,
                unit_of_measure=unit_of_measure,
                source=source,
                target=target,
                expansion_rate=expansion_rate
            )
        else:
            if service.expansion_rate != expansion_rate:
                print u"updating expansion rate for %s (%s) from %s to %s" % (
                    target, target.lcid, service.expansion_rate, expansion_rate
                )
                service.expansion_rate = expansion_rate
                service.save()


        existing_rate = VendorTranslationRate.objects.filter(
            client=navex,
            vendor=vendor,
            service=service,
            vertical=None,
            basis=source_basis,
        )

        try:
            rate = existing_rate.get()
        except VendorTranslationRate.DoesNotExist:
            rate = VendorTranslationRate(
                client=navex,
                vendor=vendor,
                service=service,
                vertical=None,
                basis=source_basis,
            )

        rate.minimum = Decimal(record[COL_MINIMUM])
        rate.word_rate = Decimal(record[COL_WORD_RATE])

        rate.guaranteed = Decimal(record[COL_PRFECT])
        rate.exact = Decimal(record[COL_EXACT])
        rate.duplicate = Decimal(record[COL_REPS])
        rate.fuzzy5074 = Decimal(record[COL_5074])
        rate.fuzzy7584 = Decimal(record[COL_7584])
        rate.fuzzy8594 = Decimal(record[COL_8594])
        rate.fuzzy9599 = Decimal(record[COL_9599])
        rate.no_match = Decimal(record[COL_NO_MATCH])

        is_new = rate.id is None

        if not dry_run:
            rate.save()

        print u'\t'.join(str(s) for s in (
            is_new, rate.id, vendor.id, vendor,
            target.lcid, rate.word_rate, rate.minimum))


    if dry_run:
        print "dry run mode: rates not saved"


class Command(BaseCommand):
    help = 'Load NAVEX-specific rates for vendors'

    def handle(self, *args, **options):
        with file(sibpath(__file__, INPUT_FILENAME), 'rb') as input_file:
            make_vendor_rates_for_navex(input_file)
