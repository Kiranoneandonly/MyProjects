import os.path
import pprint
import random
import string
from django.conf import settings
from django.core.management import BaseCommand
import unicodecsv

from clients.models import ClientContact, Client
from people.models import Salutation
from shared.group_permissions import DEPARTMENT_USER_GROUP, DEPARTMENT_ADMINISTRATOR_GROUP


def random_password():
    return ''.join([random.choice(string.ascii_letters) for i in range(24)])


def create_user(row, dry_run):
    email = row['email']
    #: :type: Client
    department = Client.objects.get(description=row['department_id'])
    user = ClientContact(
        user_type=settings.CLIENT_USER_TYPE,
        is_active=True,
        email=email,
        first_name=row['first_name'],
        last_name=row['last_name'],
        account=department,
        title=row['job_title'],
        phone=row['phone'],
        department=row['department_name']
    )
    if row['name_title']:
        user.salutation = Salutation.objects.get(description=row['name_title'])

    password = random_password()
    user.set_password(password)

    user.mailing_street = department.billing_street
    user.mailing_city = department.billing_city
    user.mailing_state = department.billing_state
    user.mailing_postal_code = department.billing_postal_code
    user.mailing_country = department.billing_country

    user.registration_complete = True
    user.profile_complete = False

    if not dry_run:
        user.save()
        user.add_to_group(DEPARTMENT_USER_GROUP)
        if row['role'] == 'BAM':
            user.add_to_group(DEPARTMENT_ADMINISTRATOR_GROUP)

    return user, password


def import_contacts(csv_file, dry_run=True):
    reader = unicodecsv.DictReader(csv_file, fieldnames=[
        'department_id',
        'client_id',
        'jams_company_name',
        'AE',
        'company_name',
        'department_name',
        'email',
        'name_title',
        'first_name',
        'last_name',
        'job_title',
        'alt_email',
        'phone',
        'jams_id',
        'role'
    ])

    created = 0
    row_count = 0
    errors = []

    for row in reader:
        row_count += 1

        email = row['email']
        assert '@' in email, "Doesn't look like an email address %r" % (email,)

        if ClientContact.objects.filter(email=email).exists():
            print("%s\tskipped" % (email,))
            continue

        try:
            user, password = create_user(row, dry_run)
        except Exception, exc:
            print("Failed on row %r" % (row_count,))
            print(exc)
            pprint.pprint(row)
            errors.append(row)
            continue  # raise

        created += 1
        print("%s\tadded\t%s" % (email, password))


    if errors:
        print("Errors:")
        pprint.pprint(errors)
    else:
        print "No errors. :)"

    print("Done. %d rows imported, %d new client accounts created." % (
        row_count, created))


class Command(BaseCommand):
    help = 'Import from clients_emaildomains CSV'

    def handle(self, *args, **kwargs):
        filename = os.path.join(os.path.dirname(__file__),
                                'clients_contacts_etl.csv')
        with file(filename, 'rb') as csv_file:
            import_contacts(csv_file, False)
