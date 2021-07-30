import csv
import inspect
import os
from django.conf import settings
from django.core.management import BaseCommand
from clients.models import Client, ClientManifest
from people.models import AccountType
from prices.models import VendorTranslationRate
from services.managers import SOURCE_BASIS, TARGET_BASIS, TRANSLATION_EDIT_PROOF_SERVICE_TYPE, WORDS_UNITS, \
    VERTICAL_UNASSIGNED, PRICING_SCHEMES_STANDARD
from services.models import Locale, Service, PricingBasis, ServiceType, ScopeUnit, \
    Vertical, PricingScheme
from vendors.models import Vendor

# webjams placeholder
LEGAL_RATES = 1943


def create_client(account_number, name):
    client = Client.objects.create(
        account_type=AccountType.objects.get(code=settings.CLIENT_USER_TYPE),
        account_number=account_number,
        name=name,
        via_team_jobs_email=settings.VIA_PM_GROUP_EMAIL_ALIAS,
    )
    manifest = ClientManifest.objects.create(
        client=client,
        auto_estimate_jobs=True,
        auto_start_workflow=False,
        pricing_basis=PricingBasis.objects.get(code=TARGET_BASIS),
        vertical=Vertical.objects.get(code=VERTICAL_UNASSIGNED),
        pricing_scheme=PricingScheme.objects.get(code=PRICING_SCHEMES_STANDARD),
        teamserver_client_code=client.account_number,
    )
    return client


def make_vendors_pricing_etl():

    path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

    vendor_account_type = AccountType.objects.get(code=settings.VENDOR_USER_TYPE)

    source_basis = PricingBasis.objects.get(code=SOURCE_BASIS)
    target_basis = PricingBasis.objects.get(code=TARGET_BASIS)

    tep = ServiceType.objects.get(code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE)
    unit_of_measure = ScopeUnit.objects.get(code=WORDS_UNITS)

    missing_clients = []

    with open(os.path.join(path, 'vendors_pricing_etl.csv'), 'rb') as csv_file:
        for row in csv.reader(csv_file, delimiter=','):

            # row[0] = SupplierID
            # row[1] = Supplier
            # row[2] = ProductID
            # row[3] = Language pairs
            # row[4] = Source_LCID
            # row[5] = Target_LCID
            # row[6] = LanguageID
            # row[7] = CustomerID
            # row[8] = Customer
            # row[9] = PSLangPairID
            # row[10] = PSPriceBasis
            # row[11] = PSLanguageStatus
            # row[12] = SupplierStatus
            # row[13] = PSTrxPrf
            # row[14] = PSNoMatch
            # row[15] = PSFuzzy
            # row[16] = PS100Match_Rep
            # row[17] = PSTrxOnly
            # row[18] = PSPrfOnly
            # row[19] = PSLinquisticHourlyRate
            # row[20] = PSMinFlatCharge
            # row[21] = PSDTPType
            # row[22] = PSDTPRate
            # row[23] = PS_FZ50
            # row[24] = PS_FZ75
            # row[25] = PS_FZ85
            # row[26] = PS_FZ95
            # row[27] = PS_FZ100
            # row[28] = PS_FZREPS
            # row[29] = PSPerfectMatch

            print 'Create vendor pricing {0}: {1}: {2}'.format(row[0], row[1], row[3])

            try:
                jams_supplier_id = row[0]
                vendor = Vendor.objects.get(account_number=jams_supplier_id, account_type=vendor_account_type)

                jams_customer_id = int(row[7])
                if jams_customer_id > 0:
                    if jams_customer_id == LEGAL_RATES:
                        print "Skipping LEGAL RATES"
                        continue

                    try:
                        client = Client.objects.get(
                            account_number=jams_customer_id, parent=None)
                    except Client.DoesNotExist:
                        client_name = row[8]
                        client = create_client(jams_customer_id, client_name)
                        missing_clients.append((client.id, jams_customer_id,
                                                client_name))
                else:
                    client = None

                slcid = None
                tlcid = None

                try:
                    if row[4]:
                        slcid = Locale.objects.get(lcid=int(row[4]))

                    if row[5]:
                        tlcid = Locale.objects.get(lcid=int(row[5]))
                except Locale.DoesNotExist:
                    pass

                if slcid and tlcid and vendor:
                    service, created = Service.objects.get_or_create(
                        service_type=tep,
                        unit_of_measure=unit_of_measure,
                        source=slcid,
                        target=tlcid
                    )

                    print 'Service: ' + service.__unicode__()
                else:
                    print 'Not enough info for Service, no rate created.'
                    continue


                vertical = None

                PSTrxPrf = float(row[13]) if row[13] else None
                if PSTrxPrf:

                    vtr, created = VendorTranslationRate.objects.get_or_create(
                        vendor=vendor,
                        service=service,
                        vertical=vertical,
                        client=client,
                        basis=source_basis
                    )

                    PSMinFlatCharge = float(row[20]) if row[20] else 0.0
                    PS_FZ50 = float(row[23]) if row[23] else PSTrxPrf
                    PS_FZ75 = float(row[24]) if row[24] else PSTrxPrf
                    PS_FZ85 = float(row[25]) if row[25] else PSTrxPrf
                    PS_FZ95 = float(row[26]) if row[26] else PSTrxPrf
                    PS_FZ100 = float(row[27]) if row[27] else PSTrxPrf
                    PS_FZREPS = float(row[28]) if row[28] else PSTrxPrf
                    PSPerfectMatch = float(row[29]) if row[29] else 0.0

                    # PSNoMatch = row[14]
                    # PS100Match_Rep = row[16]
                    # PSFuzzy = row[15]
                    # PSTrxOnly = row[17]
                    # PSPrfOnly = row[18]
                    # PSLinquisticHourlyRate = row[19]
                    # PSDTPType = row[21]
                    # PSDTPRate = row[22]

                    vtr.word_rate = PSTrxPrf
                    vtr.guaranteed = vendor_translation_bucket_percentage(PSPerfectMatch, PSTrxPrf)
                    vtr.exact = vendor_translation_bucket_percentage(PS_FZ100, PSTrxPrf)
                    vtr.duplicate = vendor_translation_bucket_percentage(PS_FZREPS, PSTrxPrf)
                    vtr.fuzzy9599 = vendor_translation_bucket_percentage(PS_FZ95, PSTrxPrf)
                    vtr.fuzzy8594 = vendor_translation_bucket_percentage(PS_FZ85, PSTrxPrf)
                    vtr.fuzzy7584 = vendor_translation_bucket_percentage(PS_FZ75, PSTrxPrf)
                    vtr.fuzzy5074 = vendor_translation_bucket_percentage(PS_FZ50, PSTrxPrf)
                    vtr.no_match = vendor_translation_bucket_percentage(PSTrxPrf, PSTrxPrf)
                    vtr.minimum = PSMinFlatCharge
                    vtr.notes = 'Converted from OLS'
                    vtr.save()

                print 'Created vendor pricing {0}: {1}: {2}'.format(row[0], row[1], row[3])

            except Exception:
                import traceback
                tb = traceback.format_exc()
                print 'ERROR: No Vendor Pricing created'
                print tb


    if missing_clients:
        print "VTP Client records created:"
        for client_record in missing_clients:
            print '\t'.join(str(field) for field in client_record)


def vendor_translation_bucket_percentage(bucket_cost, word_rate):
    return bucket_cost / word_rate


class Command(BaseCommand):
    args = ''
    help = 'Populate default Vendors ETL'

    def handle(self, *args, **options):
        make_vendors_pricing_etl()
