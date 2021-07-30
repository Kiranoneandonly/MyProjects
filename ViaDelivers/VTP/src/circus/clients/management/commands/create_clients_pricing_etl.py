import unicodecsv
import inspect
import os
from django.conf import settings
from django.core.management import BaseCommand
from clients.models import Client
from people.models import AccountType
from prices.models import ClientTranslationPrice
from services.managers import SOURCE_BASIS, TARGET_BASIS, TRANSLATION_EDIT_PROOF_SERVICE_TYPE, WORDS_UNITS
from services.models import Locale, Service, PricingBasis, ServiceType, ScopeUnit, PricingScheme


def make_clients_pricing_etl():

    path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

    client_account_type = AccountType.objects.get(code=settings.CLIENT_USER_TYPE)
    source_basis = PricingBasis.objects.get(code=SOURCE_BASIS)
    target_basis = PricingBasis.objects.get(code=TARGET_BASIS)
    tep = ServiceType.objects.get(code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE)
    unit_of_measure = ScopeUnit.objects.get(code=WORDS_UNITS)

    with open(os.path.join(path, 'clients_pricing_etl.csv'), 'rb') as csv_file:
        for row in unicodecsv.reader(csv_file, delimiter=','):

            # row[0] = JAMSCustomerID
            # row[1] = CompanyName
            # row[2] = Pricing
            # row[3] = Price
            # row[4] = FromLCID
            # row[5] = LanguageName
            # row[6] = ToLCID
            # row[7] = LanguageName
            # row[8] = Minimum-Standard
            # row[9] = Minimum-Express

            print 'Create client pricing {0}: {1}: {2}: {3}: {4}'.format(row[0], row[1], row[2], row[5], row[7])

            try:
                client = None
                jams_customer_id = int(row[0])
                client = Client.objects.get(account_number=jams_customer_id, parent=None, account_type=client_account_type)

                slcid = None
                tlcid = None

                try:
                    if row[4]:
                        slcid = Locale.objects.get(lcid=int(row[4]))

                    if row[6]:
                        tlcid = Locale.objects.get(lcid=int(row[6]))
                except:
                    pass

                service = None
                if slcid and tlcid and client:

                    service, created = Service.objects.get_or_create(
                        service_type=tep,
                        unit_of_measure=unit_of_measure,
                        source=slcid,
                        target=tlcid
                    )

                    if created:
                        print 'Created Service: ' + service.__unicode__()
                    else:
                        print 'Found Service: ' + service.__unicode__()
                else:
                    print 'No valid LCIDs'

                if service:

                    pricing_scheme = None
                    pricing_scheme = PricingScheme.objects.get(code=row[2].lower().strip())

                    word_rate = float(row[3]) if row[3] else None
                    if word_rate:

                        ctp, created = ClientTranslationPrice.objects.get_or_create(
                            client=client,
                            pricing_scheme=pricing_scheme,
                            service=service,
                            basis=target_basis
                        )

                        if created:
                             print 'Created client pricing {0}: {1}: {2}'.format(row[0], row[1], row[3])
                        else:
                             print 'Found client pricing {0}: {1}: {2}'.format(row[0], row[1], row[3])

                        minimum_price_standard = row[8] or 0.0
                        minimum_price_express = row[9] or 0.0

                        if minimum_price_standard == 0 and jams_customer_id is not 1880:
                            print 'No minimum found, get default for pricing scheme'
                            ctp_default, created = ClientTranslationPrice.objects.get_or_create(
                                client=None,
                                pricing_scheme=pricing_scheme,
                                service=service,
                                basis=target_basis
                            )
                            minimum_price_standard = ctp_default.minimum_price

                        ctp.word_rate = word_rate
                        ctp.minimum_price = minimum_price_standard
                        ctp.notes = 'Converted from OLS'
                        ctp.guaranteed = 0.0
                        ctp.exact = 0.5
                        ctp.duplicate = 0.5
                        ctp.fuzzy9599 = 1
                        ctp.fuzzy8594 = 1
                        ctp.fuzzy7584 = 1
                        ctp.fuzzy5074 = 1
                        ctp.no_match = 1
                        ctp.save()

                        if minimum_price_standard and minimum_price_express:
                            print 'Different minimum found, so need to get express_factor'

                            # need to reset the Express Factor for this client if they have special pricing
                            express_factor = express_factor_calc(minimum_price_express, minimum_price_standard)
                            client.express_factor = express_factor
                            client.save()

                        print 'Finished client pricing {0}: {1}: {2}'.format(row[0], row[1], row[3])

                else:
                    print 'No Client Pricing created'

            except:
                import traceback
                tb = traceback.format_exc()  # NOQA
                print tb
                print 'ERROR: No Client Pricing created'


def express_factor_calc(minimum_price_express, minimum_price_standard):
    return float(minimum_price_express) / float(minimum_price_standard)


class Command(BaseCommand):
    args = ''
    help = 'Populate default Client pricing ETL'

    def handle(self, *args, **options):
        make_clients_pricing_etl()
