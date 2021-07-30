import os.path

from django.core.management import BaseCommand
import unicodecsv
from clients.models import Client, ClientEmailDomain


def import_emaildomains(csv_file):
    reader = unicodecsv.reader(csv_file)

    created = 0
    row_count = 0

    for row in reader:
        row_count += 1
        jams_id = row[1]
        domain = row[2]

        if not jams_id or not domain:
            print("row missing elements: %s" % (row,))
            continue

        accounts = Client.objects.filter(account_number=jams_id)
        assert accounts.count(), "no accounts for %s" % (jams_id,)
        for account in accounts:
            email_domain, new = ClientEmailDomain.objects.get_or_create(
                account=account,
                email_domain=domain
            )
            if new:
                created += 1
            print('\t'.join(map(unicode, (domain, new, account.id, account.name))))

    print("Done. %d rows imported, %d new email domains set." % (
        row_count, created))


class Command(BaseCommand):
    help = 'Import from clients_emaildomains CSV'

    def handle(self, *args, **kwargs):
        filename = os.path.join(os.path.dirname(__file__),
                                'clients_emaildomains_etl.csv')
        with file(filename, 'rb') as csv_file:
            import_emaildomains(csv_file)
