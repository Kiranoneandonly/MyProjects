import unicodecsv
import inspect
import os
from django.conf import settings
from django.core.management import BaseCommand
from people.models import AccountType
from preferred_vendors.models import PreferredVendor
from services.managers import TRANSLATION_EDIT_PROOF_SERVICE_TYPE
from services.models import Locale, ServiceType
from vendors.models import Vendor


def make_vendors_preferred_order_etl():

    path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

    vendor_account_type = AccountType.objects.get(code=settings.VENDOR_USER_TYPE)

    tep = ServiceType.objects.get(code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE)

    with open(os.path.join(path, 'vendors_preferred_order_etl.csv'), 'rb') as csv_file:
        for row in unicodecsv.reader(csv_file, delimiter=','):

            # row[0] = Language pairs
            # row[1] = Source LCID
            # row[2] = Target LCID
            # row[3] = SupplierID
            # row[4] = Supplier	Name
            # row[5] = CustomerID
            # row[6] = CustomerName
            # row[7] = Preferred Vendor Order

            print u'Create vendor preferred order {0}: {1}: {2}: {3}: {4}'.format(row[0], row[3], row[4], row[1], row[2])

            try:
                vendor = None
                jams_supplier_id = row[3]
                vendor = Vendor.objects.get(account_number=jams_supplier_id, account_type=vendor_account_type)

                slcid = None
                tlcid = None

                try:
                    if row[1]:
                        slcid = Locale.objects.get(lcid=int(row[1]))

                    if row[2]:
                        tlcid = Locale.objects.get(lcid=int(row[2]))
                except:
                    pass

                if slcid and tlcid and vendor:
                    service = None

                    preferred_vendor_order = int(row[7]) or 1

                    customer_id = int(row[5])

                    if customer_id is 0:
                        pv, created = PreferredVendor.objects.get_or_create(
                            service_type=tep,
                            source=slcid,
                            target=tlcid,
                            vertical=None,
                            client=None,
                            vendor=vendor,
                            priority=preferred_vendor_order
                        )
                        if created:
                            print u'PV: ' + pv.__unicode__()
                        else:
                            print u'PV exists already'
                    else:
                        print u'Not adding customer preferred vendors'
                else:
                    print u'No valid LCIDs'

            except:
                import traceback
                tb = traceback.format_exc()  # NOQA
                print 'ERROR: No Preferred Vendor Order created'
                print tb


class Command(BaseCommand):
    args = ''
    help = 'Populate default Vendors Preferred Order ETL'

    def handle(self, *args, **options):
        make_vendors_preferred_order_etl()
