import csv
import inspect
import os
from django.conf import settings
from django.core.management import BaseCommand
from accounts.models import CircusUser
from people.models import AccountType, VendorType
from vendors.models import Vendor, VendorContact


def make_vendors_etl():

    path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

    vendor_account_type = AccountType.objects.get(code=settings.VENDOR_USER_TYPE)

    with open(os.path.join(path, 'vendors_etl.csv'), 'rb') as csv_file:
        for row in csv.reader(csv_file, delimiter=','):

            # row[0] = SupplierID
            # row[1] = SupplierFirstName
            # row[2] = SupplierLastName
            # row[3] = Supplier
            # row[4] = SupplierEmails
            # row[5] = SupplierType
            # row[6] = Name
            # row[7] = UserName
            # row[8] = Password

            print 'Create vendors {0}: {1}: {2}'.format(row[0], row[3], row[5])

            try:

                vendor_type = VendorType.objects.get(description=row[5])

                jams_supplier_id = row[0]
                vendor, created = Vendor.objects.get_or_create(account_number=jams_supplier_id, account_type=vendor_account_type)
                if created:
                    vendor.name = row[3]
                    vendor.jobs_email = row[4]
                    vendor.vendor_type = vendor_type
                    vendor.save()

                if vendor:
                    # create vendor contact

                    vendor_user, created = CircusUser.objects.get_or_create(email=row[7], user_type=settings.VENDOR_USER_TYPE)
                    if created:
                        vendor_user.account = vendor
                        vendor_user.email = row[7]
                        vendor_user.first_name = row[1]
                        vendor_user.last_name = row[2]
                        vendor_user.is_active = True
                        vendor_user.profile_complete = True
                        vendor_user.registration_complete = True
                        vendor_user.set_password(row[8])
                        vendor_user.save()

                else:
                    print 'No Vendor created'

            except:
                import traceback
                tb = traceback.format_exc()  # NOQA
                print 'ERROR: No Vendor created'
                print tb


class Command(BaseCommand):
    args = ''
    help = 'Populate default Vendors ETL'

    def handle(self, *args, **options):
        make_vendors_etl()
