from django.conf import settings

from people.models import AccountManager, AccountType, AccountContactRole, ContactRole
from services.managers import TRANSLATION_EDIT_PROOF_SERVICE_TYPE, THIRD_PARTY_REVIEW_SERVICE_TYPE, TARGET_BASIS, VERTICAL_UNASSIGNED, PRICING_SCHEMES_STANDARD, \
    DTP_SERVICE_TYPE
from services.models import ServiceType, PricingBasis, Vertical, PricingScheme
from shared.managers import CircusManager, CircusLookupManager, get_default_kwargs

# code, description, dvx_subject_code
DVX_SUBJECT_CODES = (
    ('corporate', 'Corporate', '1'),
    ('healthcare', 'Healthcare', '2'),
    ('legal', 'Legal', '3'),
    ('education', 'K-12 (Education)', '4'),
    ('healthcare_strategic', 'Healthcare Strategic', '5'),
    ('government', 'Government', '6'),
)


class ClientsManager(AccountManager):
    def for_filter(self, filters):
        try:
            return self.get(id=filters[settings.CLIENT_USER_TYPE])
        except:
            return None

    def create_for_user(self, user, **kwargs):
        from clients.models import ClientEmailDomain, ClientManifest, ClientService

        #: :type: clients.models.Client
        client = self.create(
            account_type=AccountType.objects.get(code=settings.CLIENT_USER_TYPE),
            phone=user.phone,
            billing_street=user.mailing_street,
            billing_city=user.mailing_city,
            billing_state=user.mailing_state,
            billing_postal_code=user.mailing_postal_code,
            billing_country=user.mailing_country,
            via_team_jobs_email=settings.VIA_PM_GROUP_EMAIL_ALIAS,
            **kwargs
        )

        parent = kwargs['parent'] if kwargs else None
        if parent:            
            manifest = ClientManifest.objects.create(
                client=client,
                express_factor=parent.manifest.express_factor,
                pricing_basis=parent.manifest.pricing_basis,
                auto_estimate_jobs=parent.manifest.auto_estimate_jobs,
                auto_start_workflow=parent.manifest.auto_start_workflow,
                vertical=parent.manifest.vertical,
                pricing_scheme=parent.manifest.pricing_scheme,
                pricing_memory_bank_discount=parent.manifest.pricing_memory_bank_discount,
                teamserver_tm_enabled=parent.manifest.teamserver_tm_enabled,
                minimum_price=parent.manifest.minimum_price,
                teamserver_client_code=parent.manifest.teamserver_client_code,
                teamserver_client_subject=parent.manifest.teamserver_client_subject,
            )

            client.salesforce_account_id = parent.salesforce_account_id
            client.via_team_jobs_email = parent.via_team_jobs_email
            client.jobs_email = parent.jobs_email
            client.account_number = parent.account_number
            client.save()

            for emaildomain in parent.accountemaildomain_set.all():
                ClientEmailDomain.objects.create(
                    account=client,
                    email_domain=emaildomain.email_domain
                )
        else:
            from clients.models import default_subject
            manifest = ClientManifest.objects.create(
                client=client,
                auto_estimate_jobs=True,
                auto_start_workflow=False,
                pricing_basis=PricingBasis.objects.get(code=TARGET_BASIS),
                vertical=Vertical.objects.get(code=VERTICAL_UNASSIGNED),
                pricing_scheme=PricingScheme.objects.get(code=PRICING_SCHEMES_STANDARD),
                teamserver_client_code=client.account_number,
                teamserver_client_subject=default_subject(),
            )

        ClientService.objects.create(
            client=client,
            service=ServiceType.objects.get(code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE),
            available=True,
            job_default=True
        )

        available_service_types = [
            THIRD_PARTY_REVIEW_SERVICE_TYPE,
            DTP_SERVICE_TYPE,
        ]
        for service_type_code in available_service_types:
            ClientService.objects.create(
                client=client,
                service=ServiceType.objects.get(code=service_type_code),
                available=True,
                job_default=False
            )

        AccountContactRole.objects.create(
            account=client,
            contact=user,
            is_primary=True,
            role=ContactRole.objects.get(code='economic_decision_maker')
        )
        return client


class ClientManifestManager(CircusManager):
    def default(self):
        return None


class ClientEmailDomainManager(CircusManager):
    def default(self):
        return None


class ClientContactManager(CircusManager):
    def default(self):
        return None


class ClientTeamRoleManager(CircusManager):
    def default(self):
        return None


class ClientServiceManager(CircusManager):
    def default(self):
        return None


class ClientDiscountManager(CircusManager):
    def default(self):
        return None


class ClientReferenceFilesManager(CircusManager):
    def default(self):
        return None


class TEAMServerSubjectManager(CircusLookupManager):
    def default(self):
        obj, created = self.get_or_create(**get_default_kwargs(DVX_SUBJECT_CODES))
        return obj

    def default_id(self):
        from clients.models import default_subject
        return default_subject().id

    def for_filter(self, filters):
        try:
            return self.get(id=filters['dvx_subject_code'])
        except:
            return self.get_empty_query_set()