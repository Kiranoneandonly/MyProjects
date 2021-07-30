import csv
import inspect
import os
from django.core.management import BaseCommand
from prices.models import ClientNonTranslationPrice
from services.managers import TRANSLATION_EDIT_PROOF_SERVICE_TYPE

from services.models import ServiceType, Service, ScopeUnit, PricingScheme


def make_pricing_default_non_translation():

    path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

    # base the Language Pairs off of Translation and Proof (tep) services available
    tep = ServiceType.objects.get(code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE)
    language_pairs = [(s.source, s.target) for s in Service.objects.filter(service_type=tep)]
    pricing_schemes = PricingScheme.objects.all()

    with open(os.path.join(path, 'pricing_default_non_translation.csv'), 'rb') as csv_file:
        for row in csv.reader(csv_file, delimiter=','):

            # -----------------------------------------------------
            # third_party_review,Third Party Review,Hours,65.00
            # -----------------------------------------------------
            # row[0] = service_type.code,
            # row[1] = service_type.description,
            # row[2] = Scope Unit
            # row[3] = Unit Price

            for slcid, tlcid in language_pairs:

                print u'Create Default Pricing Non Translation - {0}: {1}: {2}: {3}'.format(row[0], slcid, tlcid, row[3])

                service = None
                created = None

                service_type, created = ServiceType.objects.get_or_create(code=row[0])
                if created:
                    service_type.description = row[1]
                    service_type.save()

                unit_of_measure = ScopeUnit.objects.get(code=row[2])

                if slcid and tlcid:
                    service, created = Service.objects.get_or_create(
                        service_type=service_type,
                        unit_of_measure=unit_of_measure,
                        source=slcid,
                        target=tlcid
                    )
                    print 'Service: ' + service.__unicode__()
                else:
                    print 'Not valid LCIDs'

                if service:

                    unit_price = row[3]

                    if unit_price:
                        cntp, created = ClientNonTranslationPrice.objects.get_or_create(
                            client=None,
                            pricing_scheme=None,
                            service=service
                        )

                        cntp.unit_price = unit_price
                        cntp.save()

                    print 'Created Service'

                else:
                    print 'No Service created'

            # for pricing_scheme in pricing_schemes:
            #
            #     for slcid, tlcid in language_pairs:
            #
            #         print u'Create Default Pricing Non Translation - {0}: {1}: {2}: {3}: {4}'.format(pricing_scheme, row[0], slcid, tlcid, row[3])
            #
            #         service = None
            #         created = None
            #
            #         service_type, created = ServiceType.objects.get_or_create(code=row[0])
            #         if created:
            #             service_type.description = row[1]
            #             service_type.save()
            #
            #         unit_of_measure = ScopeUnit.objects.get(code=row[2])
            #
            #         if slcid and tlcid:
            #             service, created = Service.objects.get_or_create(
            #                 service_type=service_type,
            #                 unit_of_measure=unit_of_measure,
            #                 source=slcid,
            #                 target=tlcid
            #             )
            #             print 'Service: ' + service.__unicode__()
            #         else:
            #             print 'Not valid LCIDs'
            #
            #         if service:
            #
            #             unit_price = row[3]
            #
            #             if unit_price and pricing_scheme:
            #                 cntp, created = ClientNonTranslationPrice.objects.get_or_create(
            #                     client=None,
            #                     pricing_scheme=pricing_scheme,
            #                     service=service
            #                 )
            #
            #                 cntp.unit_price = unit_price
            #                 cntp.save()
            #
            #             print 'Created Service'
            #
            #         else:
            #             print 'No Service created'


class Command(BaseCommand):
    args = ''
    help = 'Populate default Non Translation Pricing - Creates Services'

    def handle(self, *args, **options):
        make_pricing_default_non_translation()
