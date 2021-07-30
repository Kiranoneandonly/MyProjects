from django.core.management.base import BaseCommand
from services.managers import PRICING_SCHEMES
from services.models import PricingScheme


class Command(BaseCommand):
    args = ''
    help = 'Populate Pricing Scheme lookup tables'

    def handle(self, *args, **options):

        for code, desc in PRICING_SCHEMES:
            PricingScheme.objects.get_or_create(code=code, description=desc)
            print 'Created Pricing Scheme template {0}: {1}'.format(code, desc)
