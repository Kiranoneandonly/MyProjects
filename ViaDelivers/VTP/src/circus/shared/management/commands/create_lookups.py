import csv
import os
from decimal import Decimal
from django.conf import settings
from django.core.management.base import BaseCommand
from finance.models import InvoiceTemplate, INVOICE_TEMPLATES
from people.models import AccountType, Salutation, ContactRole, VendorType, GenericEmailDomain
from services.managers import SERVICE_TYPES, UNITS, INDUSTRIES, DOCUMENT_TYPES, PRICING_BASIS, VERTICALS, PRICING_SCHEMES
from services.models import ServiceType, Locale, PricingFormula, ScopeUnit, Industry, DocumentType, PricingBasis, Vertical, PricingScheme


SALUTATIONS = (
    ('mr', 'Mr.'),
    ('ms', 'Ms.'),
    ('mrs', 'Mrs.'),
    ('dr', 'Dr.'),
    ('prof', 'Prof.'),
)

ACCOUNT_TYPES = (
    (settings.VIA_USER_TYPE, 'VIA'),
    (settings.CLIENT_USER_TYPE, 'Client'),
    (settings.COMPETITOR_USER_TYPE, 'Competitor'),
    (settings.PARTNER_USER_TYPE, 'Partner'),
    (settings.VENDOR_USER_TYPE, 'Vendor')
)

CONTACT_ROLES = (
    ('user', 'Business User'),
    ('decision_maker', 'Decision Maker'),
    ('economic_buyer', 'Economic Buyer'),
    ('economic_decision_maker', 'Economic Decision Maker'),
    ('evaluator', 'Evaluator'),
    ('exec_sponsor', 'Executive Sponsor'),
    ('influencer', 'Influencer'),
    ('technical_buyer', 'Technical Buyer'),
    ('other', 'Other'),
)

PRICING_FORMULAE = (
    ('five_percent_total', '5% of project total', '0.05'),
    ('ten_percent_total', '10% of project total', '0.10'),
    ('fifteen_percent_total', '15% of project total', '0.15'),
    ('ten_percent_total_discount', '10% discount off project total', '-0.10'),
    ('five_percent_total_discount', '5% discount off project total', '-0.05'),
)


VENDOR_TYPE_INDIVIDUAL = 'individual'
VENDOR_TYPE_AGENCY = 'agency'
VENDOR_TYPE_PAIR = 'pair'

VENDOR_TYPES = (
    (VENDOR_TYPE_INDIVIDUAL, 'Individual'),
    (VENDOR_TYPE_AGENCY, 'Agency'),
    (VENDOR_TYPE_PAIR, 'Pair'),
)

GENERIC_EMAIL_DOMAINS = (
    'aol.com',
    'bellsouth.net',
    'btinternet.com',
    'charter.net',
    'comcast.net',
    'cox.net',
    'earthlink.net',
    'gmail.com',
    'hotmail.co.uk',
    'hotmail.com',
    'live.com',
    'me.com',
    'msn.com',
    'ntlworld.com',
    'outlook.com',
    'rediffmail.com',
    'sbcglobal.net',
    'shaw.ca',
    'verizon.net',
    'yahoo.ca',
    'yahoo.co.in',
    'yahoo.co.uk',
    'yahoo.com',
)

class Command(BaseCommand):
    args = ''
    help = 'Populate lookup tables'

    def handle(self, *args, **options):
        for code, desc in SALUTATIONS:
            Salutation.objects.get_or_create(code=code, description=desc)
        print 'Created salutations from {0}'.format(SALUTATIONS)

        for code, desc in ACCOUNT_TYPES:
            AccountType.objects.get_or_create(code=code, description=desc)
        print 'Created account types from {0}'.format(ACCOUNT_TYPES)

        for code, desc in CONTACT_ROLES:
            ContactRole.objects.get_or_create(code=code, description=desc)
        print 'Created contact roles from {0}'.format(CONTACT_ROLES)

        for code, desc, translation_task, billable, jams_jobtaskid in SERVICE_TYPES:
            ServiceType.objects.get_or_create(code=code, description=desc, translation_task=translation_task, billable=billable, jams_jobtaskid=jams_jobtaskid)
            print 'Created service type {0}: {1}: {2}: {3}: {4}'.format(code, desc, translation_task, billable, jams_jobtaskid)

        for code, desc in PRICING_BASIS:
            PricingBasis.objects.get_or_create(code=code, description=desc)
            print 'Created pricing basis template {0}: {1}'.format(code, desc)

        for code, desc, percent_calc in PRICING_FORMULAE:
            percent_calc = Decimal(percent_calc)
            PricingFormula.objects.get_or_create(code=code, description=desc, percent_calculation=percent_calc)
            print 'Created pricing formula {0}: {1}: {2}'.format(code, desc, percent_calc)

        for code, desc in INVOICE_TEMPLATES:
            InvoiceTemplate.objects.get_or_create(code=code, description=desc)
            print 'Created invoice template {0}: {1}'.format(code, desc)

        for code, desc in DOCUMENT_TYPES:
            DocumentType.objects.get_or_create(code=code, description=desc)
            print 'Created document types template {0}: {1}'.format(code, desc)

        for code, desc in VENDOR_TYPES:
            VendorType.objects.get_or_create(code=code, description=desc)
            print 'Created vendor types template {0}: {1}'.format(code, desc)

        for code, desc in VERTICALS:
            Vertical.objects.get_or_create(code=code, description=desc)
            print 'Created vertical template {0}: {1}'.format(code, desc)

        for code, desc in PRICING_SCHEMES:
            PricingScheme.objects.get_or_create(code=code, description=desc)
            print 'Created pricing schemes template {0}: {1}'.format(code, desc)

        path = os.path.dirname(os.path.abspath(__file__))

        with open(os.path.join(path, 'langs.csv'), 'rb') as csv_file:
            for row in csv.reader(csv_file, delimiter=','):
                lcid, unused, description, available, dvx_log_name = row[:5]
                try:
                    loc = Locale.objects.get(lcid=int(lcid))
                except Locale.DoesNotExist:
                    loc = Locale(lcid=int(lcid))
                loc.code = lcid
                loc.jams_lcid = lcid
                loc.dvx_lcid = lcid
                loc.description = description
                loc.available = (available == "Yes")
                loc.dvx_log_name = dvx_log_name
                loc.save()
                print 'Created language {0}: {1}: {2}'.format(row[0], row[1], row[2])

        for code, desc, jams_basisid in UNITS:
            ScopeUnit.objects.get_or_create(code=code, description=desc, jams_basisid=jams_basisid)
            print 'Created scope unit {0}: {1}'.format(code, desc)

        for code, desc in INDUSTRIES:
            Industry.objects.get_or_create(code=code, description=desc)
            print 'Created industry: {0}: {1}'.format(code, desc)

        for email_domain in GENERIC_EMAIL_DOMAINS:
            GenericEmailDomain.objects.get_or_create(email_domain=email_domain)
            print 'Created GenericEmailDomain: {0}'.format(email_domain)
