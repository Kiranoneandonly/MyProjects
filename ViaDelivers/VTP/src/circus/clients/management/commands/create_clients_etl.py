import unicodecsv
import inspect
import os
from django.conf import settings
from django.core.management import BaseCommand
from clients.models import Client, ClientService, ClientTeamRole, AE_ROLE
from people.models import AccountType
from services.managers import TARGET_BASIS, TRANSLATION_EDIT_PROOF_SERVICE_TYPE, THIRD_PARTY_REVIEW_SERVICE_TYPE
from services.models import Vertical, PricingScheme, PricingBasis, ServiceType
from via_staff.models import ViaContact


def make_clients_etl():

    path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

    client_account_type = AccountType.objects.get(code=settings.CLIENT_USER_TYPE)
    target_basis = PricingBasis.objects.get(code=TARGET_BASIS)
    tep = ServiceType.objects.get(code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE)
    tpr = ServiceType.objects.get(code=THIRD_PARTY_REVIEW_SERVICE_TYPE)

    with open(os.path.join(path, 'clients_etl.csv'), 'rb') as csv_file:
        for row in unicodecsv.reader(csv_file, delimiter=','):

            # row[0] = Parent
            # row[1] = JAMSCustomerID
            # row[2] = JAMSCompanyName
            # row[3] = ID
            # row[4] = CompanyName
            # row[5] = DepartmentName
            # row[6] = Vertical
            # row[7] = Pricing
            # row[8] = AE FullName
            # row[9] = IndustryID
            # row[10] = URL
            # row[11] = BillingMode
            # row[12] = Address1
            # row[13] = Address2
            # row[14] = City
            # row[15] = State
            # row[16] = Zip
            # row[17] = Phone
            # row[18] = Email
            # row[19] = CountryCode
            # row[20] = CountryName
            # row[21] = CustomerAddress1
            # row[22] = CustomerAddress2
            # row[23] = CustomerCity
            # row[24] = CustomerState
            # row[25] = CustomerZip
            # row[26] = CountryName
            # row[27] = CustomerPhone

            print 'Create clients {0}: {1}: {2}'.format(row[1], row[2], row[5])

            try:

                is_parent = row[0]
                jams_customer_id = row[1]
                client_name = row[2]
                department_name = row[5]
                department_name = department_name if department_name else row[4]
                client_name += (' : ' + department_name if department_name else '')

                vertical = Vertical.objects.get(code=row[6].strip())
                pricing_scheme = PricingScheme.objects.get(code=row[7].lower().strip())

                client_parent = None
                if not is_parent:
                    try:
                        client_parent = Client.objects.get(account_number=jams_customer_id, parent=None, account_type=client_account_type)
                    except:
                        # do nothing as probably just single client
                        pass

                client, created = Client.objects.get_or_create(name=client_name, account_number=jams_customer_id, account_type=client_account_type)
                if created:
                    client.vertical = vertical
                    client.description = row[3]
                    client.website = row[10]
                    client.site = row[5]
                    client.parent = client_parent
                    client.owner = None
                    client.pricing_scheme = pricing_scheme
                    client.pricing_basis = target_basis
                    client.pricing_memory_bank_discount = False
                    client.express_factor = 1.5
                    client.jobs_email = row[18]
                    client.via_team_jobs_email = settings.VIA_PM_GROUP_EMAIL_ALIAS
                    client.teamserver_tm_enabled = False
                    client.auto_start_workflow = False
                    client.auto_estimate_jobs = True
                    client.phone = row[27]

                    CustomerAddress1 = row[21]
                    CustomerPhone = row[27]

                    billing_street = None
                    billing_city = None
                    billing_state = None
                    billing_postal_code = None
                    billing_country = None

                    if CustomerAddress1:
                        billing_street = row[21]
                        billing_city = row[23]
                        billing_state = row[24]
                        billing_postal_code = row[25]
                        billing_country = row[26]
                    else:
                        billing_street = row[12]
                        billing_city = row[14]
                        billing_state = row[15]
                        billing_postal_code = row[16]
                        billing_country = row[20]

                    client.billing_street = billing_street
                    client.billing_city = billing_city
                    client.billing_state = billing_state
                    client.billing_postal_code = billing_postal_code
                    client.billing_country = billing_country

                    client.save()

                elif client:
                    print 'Client already exists'
                else:
                    print 'No Client created'

                if client:
                    # create client default services
                    cs_tep, created = ClientService.objects.get_or_create(client=client, service=tep, available=True, job_default=True)
                    if created:
                        print 'Client TEP services added'
                    else:
                        print 'Client TEP services exists'

                    cs_tpr, created = ClientService.objects.get_or_create(client=client, service=tpr, available=True, job_default=False)
                    if created:
                        print 'Client TPR services added'
                    else:
                        print 'Client TPR services exists'

                    ae_first, ae_last = row[8].lower().split()
                    ae_email = ae_first[0] + ae_last + '@viadelivers.com'

                    try:
                        ae_user = ViaContact.objects.get(email=ae_email)
                    except ViaContact.DoesNotExist:
                        print "No account for AE %r" % (ae_email,)
                    else:
                        ClientTeamRole.objects.get_or_create(
                            client=client, role=AE_ROLE, contact=ae_user)
                        print 'AE added to client'

            except:
                import traceback
                tb = traceback.format_exc()  # NOQA
                print tb
                print 'ERROR: No Client created'


class Command(BaseCommand):
    args = ''
    help = 'Populate default Vendors ETL'

    def handle(self, *args, **options):
        make_clients_etl()
