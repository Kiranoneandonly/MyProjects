from django.core.management.base import BaseCommand
from services.managers import VERTICALS
from services.models import Vertical


class Command(BaseCommand):
    args = ''
    help = 'Populate Vertical lookup tables'

    def handle(self, *args, **options):

        for code, desc in VERTICALS:
            Vertical.objects.get_or_create(code=code, description=desc)
            print 'Created vertical template {0}: {1}: {2}'.format(code, desc)
