import csv
import inspect
import os
from django.core.management import BaseCommand
from prices.models import ClientTranslationPrice, ClientNonTranslationPrice
from services.managers import TRANSLATION_EDIT_PROOF_SERVICE_TYPE, WORDS_UNITS, SOURCE_BASIS, TARGET_BASIS, \
    PRICING_SCHEMES_STANDARD, PRICING_SCHEMES_HEALTHCARE, PRICING_SCHEMES_HEALTHCARE_PHI, PRICING_SCHEMES_HEALTHCARE_STRATEGIC, PRICING_SCHEMES_EDUCATION, PRICING_SCHEMES_GOVERNMENT, PRICING_SCHEMES_LEGAL, PRICING_SCHEMES_LEGAL_IP, HOURS_UNITS, ATTORNEY_REVIEW_SERVICE_TYPE
from services.models import ServiceType, Service, ScopeUnit, Locale, PricingBasis, PricingScheme


def make_pricing_default_tep():

    path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

    source_basis = PricingBasis.objects.get(code=SOURCE_BASIS)
    target_basis = PricingBasis.objects.get(code=TARGET_BASIS)

    tep = ServiceType.objects.get(code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE)
    unit_of_measure = ScopeUnit.objects.get(code=WORDS_UNITS)

    attorney_review = ServiceType.objects.get(code=ATTORNEY_REVIEW_SERVICE_TYPE)
    hours = ScopeUnit.objects.get(code=HOURS_UNITS)

    with open(os.path.join(path, 'pricing_default_tep.csv'), 'rb') as csv_file:
        for row in csv.reader(csv_file, delimiter=','):

            # row[0] = Language pairs,
            # row[1] = Source Name,
            # row[2] = sLCID,
            # row[3] = Target Name,
            # row[4] = tLCID,
            # row[5] = Word expansion,
            # row[6] = Corporate(Target),
            # row[7] = Government,
            # row[8] = Healthcare,
            # row[9] = Healthcare PHI,
            # row[10] = Healthcare Strategic,
            # row[11] = K12,
            # row[12] = via-Hansa,
            # row[13] = viaLegal,
            # row[14] = viaLegal IP,
            # row[15] = Legal review

            print 'Create TEP Default Pricing {0}: {1}: {2}'.format(row[0], row[2], row[4])

            expansion_rate = 1 if row[5] < 1 else row[5]

            slcid = None
            tlcid = None

            try:
                if row[2]:
                    slcid = Locale.objects.get(lcid=int(row[2]))

                if row[4]:
                    tlcid = Locale.objects.get(lcid=int(row[4]))
            except:
                pass

            service = None

            if slcid and tlcid:
                service, created = Service.objects.get_or_create(
                    service_type=tep,
                    unit_of_measure=unit_of_measure,
                    source=slcid,
                    target=tlcid
                )
                service.expansion_rate = expansion_rate
                service.save()

                print 'Service: ' + service.__unicode__()
            else:
                print 'No valid LCIDs'

            if service:

                # Unassigned - Default Standard Pricing
                word_rate = row[6]

                pricing_scheme = PricingScheme.objects.get(code=PRICING_SCHEMES_STANDARD)

                if word_rate and pricing_scheme:
                    ctp, created = ClientTranslationPrice.objects.get_or_create(
                        client=None,
                        pricing_scheme=pricing_scheme,
                        service=service,
                        basis=target_basis
                    )
                    ctp.word_rate = word_rate
                    ctp.guaranteed = 0.0
                    ctp.exact = 0.5
                    ctp.duplicate = 0.5
                    ctp.fuzzy9599 = 1
                    ctp.fuzzy8594 = 1
                    ctp.fuzzy7584 = 1
                    ctp.fuzzy5074 = 1
                    ctp.no_match = 1
                    ctp.minimum_price = 110
                    ctp.notes = ''
                    ctp.save()

                print 'Created Unassigned'

                # Corporate(Source)
                word_rate = row[6]

                pricing_scheme = PricingScheme.objects.get(code=PRICING_SCHEMES_STANDARD)

                if word_rate and pricing_scheme:
                    ctp, created = ClientTranslationPrice.objects.get_or_create(
                        client=None,
                        pricing_scheme=pricing_scheme,
                        service=service,
                        basis=source_basis
                    )
                    ctp.word_rate = word_rate
                    ctp.guaranteed = 0.0
                    ctp.exact = 0.4
                    ctp.duplicate = 0.4
                    ctp.fuzzy9599 = 0.5
                    ctp.fuzzy8594 = 0.6
                    ctp.fuzzy7584 = 0.75
                    ctp.fuzzy5074 = 1
                    ctp.no_match = 1
                    ctp.minimum_price = 110
                    ctp.notes = ''
                    ctp.save()

                print 'Created Corporate(Source)'

                # Corporate(Target)
                word_rate = row[6]

                pricing_scheme = PricingScheme.objects.get(code=PRICING_SCHEMES_STANDARD)

                if word_rate and pricing_scheme:
                    ctp, created = ClientTranslationPrice.objects.get_or_create(
                        client=None,
                        pricing_scheme=pricing_scheme,
                        service=service,
                        basis=target_basis
                    )
                    ctp.word_rate = word_rate
                    ctp.guaranteed = 0.0
                    ctp.exact = 0.5
                    ctp.duplicate = 0.5
                    ctp.fuzzy9599 = 1
                    ctp.fuzzy8594 = 1
                    ctp.fuzzy7584 = 1
                    ctp.fuzzy5074 = 1
                    ctp.no_match = 1
                    ctp.minimum_price = 110
                    ctp.notes = ''
                    ctp.save()

                print 'Created Corporate(Target)'

                # Healthcare
                word_rate = row[8]

                pricing_scheme = PricingScheme.objects.get(code=PRICING_SCHEMES_HEALTHCARE)

                if word_rate and pricing_scheme:
                    ctp, created = ClientTranslationPrice.objects.get_or_create(
                        client=None,
                        pricing_scheme=pricing_scheme,
                        service=service,
                        basis=target_basis
                    )
                    ctp.word_rate = word_rate
                    ctp.guaranteed = 0.0
                    ctp.exact = 0.5
                    ctp.duplicate = 0.5
                    ctp.fuzzy9599 = 1
                    ctp.fuzzy8594 = 1
                    ctp.fuzzy7584 = 1
                    ctp.fuzzy5074 = 1
                    ctp.no_match = 1
                    ctp.minimum_price = 110
                    ctp.notes = ''
                    ctp.save()

                print 'Created Healthcare'

                # Healthcare PHI
                word_rate = row[9]

                if word_rate == 0:
                    # Healthcare
                    word_rate = row[8]

                pricing_scheme = PricingScheme.objects.get(code=PRICING_SCHEMES_HEALTHCARE_PHI)

                if word_rate and pricing_scheme:
                    ctp, created = ClientTranslationPrice.objects.get_or_create(
                        client=None,
                        pricing_scheme=pricing_scheme,
                        service=service,
                        basis=target_basis
                    )
                    ctp.word_rate = word_rate
                    ctp.guaranteed = 0.0
                    ctp.exact = 0.5
                    ctp.duplicate = 0.5
                    ctp.fuzzy9599 = 1
                    ctp.fuzzy8594 = 1
                    ctp.fuzzy7584 = 1
                    ctp.fuzzy5074 = 1
                    ctp.no_match = 1
                    ctp.minimum_price = 110
                    ctp.notes = ''
                    ctp.save()

                print 'Created Healthcare PHI'

               # Healthcare Strategic
                word_rate = row[10]
                if word_rate == 0:
                    # Healthcare
                    word_rate = row[8]

                pricing_scheme = PricingScheme.objects.get(code=PRICING_SCHEMES_HEALTHCARE_STRATEGIC)


                if word_rate and pricing_scheme:
                    ctp, created = ClientTranslationPrice.objects.get_or_create(
                        client=None,
                        pricing_scheme=pricing_scheme,
                        service=service,
                        basis=target_basis
                    )
                    ctp.guaranteed = 0.0
                    ctp.exact = 0.5
                    ctp.duplicate = 0.5
                    ctp.fuzzy9599 = 1
                    ctp.fuzzy8594 = 1
                    ctp.fuzzy7584 = 1
                    ctp.fuzzy5074 = 1
                    ctp.no_match = 1
                    ctp.minimum_price = 110
                    ctp.notes = ''
                    ctp.save()

                print 'Created Healthcare Strategic'

                # K12 Education
                word_rate = row[11]

                pricing_scheme = PricingScheme.objects.get(code=PRICING_SCHEMES_EDUCATION)

                if word_rate and pricing_scheme:
                    ctp, created = ClientTranslationPrice.objects.get_or_create(
                        client=None,
                        pricing_scheme=pricing_scheme,
                        service=service,
                        basis=target_basis
                    )
                    ctp.word_rate = word_rate
                    ctp.guaranteed = 0.0
                    ctp.exact = 1
                    ctp.duplicate = 1
                    ctp.fuzzy9599 = 1
                    ctp.fuzzy8594 = 1
                    ctp.fuzzy7584 = 1
                    ctp.fuzzy5074 = 1
                    ctp.no_match = 1
                    ctp.minimum_price = 75
                    ctp.notes = ''
                    ctp.save()

                print 'Created k12'

                # Government
                word_rate = row[7]

                pricing_scheme = PricingScheme.objects.get(code=PRICING_SCHEMES_GOVERNMENT)

                if word_rate and pricing_scheme:
                    ctp, created = ClientTranslationPrice.objects.get_or_create(
                        client=None,
                        pricing_scheme=pricing_scheme,
                        service=service,
                        basis=target_basis
                    )
                    ctp.word_rate = word_rate
                    ctp.guaranteed = 0.0
                    ctp.exact = 0.5
                    ctp.duplicate = 0.5
                    ctp.fuzzy9599 = 1
                    ctp.fuzzy8594 = 1
                    ctp.fuzzy7584 = 1
                    ctp.fuzzy5074 = 1
                    ctp.no_match = 1
                    ctp.minimum_price = 110
                    ctp.notes = ''
                    ctp.save()

                print 'Government'

               # Legal
                word_rate = row[13]

                pricing_scheme = PricingScheme.objects.get(code=PRICING_SCHEMES_LEGAL)

                if word_rate and pricing_scheme:
                    ctp, created = ClientTranslationPrice.objects.get_or_create(
                        client=None,
                        pricing_scheme=pricing_scheme,
                        service=service,
                        basis=target_basis
                    )
                    ctp.word_rate = word_rate
                    ctp.guaranteed = 0.0
                    ctp.exact = 0.5
                    ctp.duplicate = 0.5
                    ctp.fuzzy9599 = 1
                    ctp.fuzzy8594 = 1
                    ctp.fuzzy7584 = 1
                    ctp.fuzzy5074 = 1
                    ctp.no_match = 1
                    ctp.minimum_price = 110
                    ctp.notes = ''
                    ctp.save()

                print 'Created Legal'

               # Legal IP
                word_rate = row[14]

                if word_rate == 0:
                   # Legal
                    word_rate = row[13]

                pricing_scheme = PricingScheme.objects.get(code=PRICING_SCHEMES_LEGAL_IP)

                if word_rate and pricing_scheme:
                    ctp, created = ClientTranslationPrice.objects.get_or_create(
                        client=None,
                        pricing_scheme=pricing_scheme,
                        service=service,
                        basis=target_basis
                    )
                    ctp.word_rate = word_rate
                    ctp.guaranteed = 0.0
                    ctp.exact = 0.5
                    ctp.duplicate = 0.5
                    ctp.fuzzy9599 = 1
                    ctp.fuzzy8594 = 1
                    ctp.fuzzy7584 = 1
                    ctp.fuzzy5074 = 1
                    ctp.no_match = 1
                    ctp.minimum_price = 110
                    ctp.notes = ''
                    ctp.save()

                print 'Created Legal IP'

            else:
                print 'No Service created'


            # =============================================================
            # ClientNonTranslationPrice - Legal Review if exists
            # =============================================================

           # Legal Review
            rate = row[15]

            if rate:
                attorney_review_service = None

                if slcid and tlcid:
                    attorney_review_service, created = Service.objects.get_or_create(
                        service_type=attorney_review,
                        unit_of_measure=hours,
                        source=slcid,
                        target=tlcid
                    )

                    print 'Service: ' + attorney_review_service.__unicode__()
                else:
                    print 'No valid LCIDs'

                if attorney_review_service:

                   # Legal Review
                    rate = row[15]

                    pricing_scheme = PricingScheme.objects.get(code=PRICING_SCHEMES_LEGAL)

                    if rate and pricing_scheme:
                        cntp, created = ClientNonTranslationPrice.objects.get_or_create(
                            client=None,
                            pricing_scheme=pricing_scheme,
                            service=attorney_review_service
                        )

                        cntp.unit_price = rate
                        cntp.save()

                    print 'Created Legal Review'


                   # Legal IP Review
                    rate = row[15]

                    pricing_scheme = PricingScheme.objects.get(code=PRICING_SCHEMES_LEGAL_IP)

                    if rate and pricing_scheme:
                        cntp, created = ClientNonTranslationPrice.objects.get_or_create(
                            client=None,
                            pricing_scheme=pricing_scheme,
                            service=attorney_review_service
                        )

                        cntp.unit_price = rate
                        cntp.save()

                    print 'Created Legal IP Review'

                else:
                    print 'No Service created'


class Command(BaseCommand):
    args = ''
    help = 'Populate default TEP Pricing - Creates Services'

    def handle(self, *args, **options):
        make_pricing_default_tep()
