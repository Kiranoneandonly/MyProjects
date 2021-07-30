"""Helpers to create instances in database for management scripts and tests.
"""
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.utils.timezone import now

from accounts.models import CircusUser
from localization_kits.models import FileAsset, SOURCEFILE_ASSET, FileAnalysis
from people.models import AccountType
from prices.models import ClientTranslationPrice, ClientNonTranslationPrice
from projects.models import Project
from clients.models import Client, ClientManifest, ClientDiscount
from services.managers import TARGET_BASIS, PRICING_SCHEMES_HEALTHCARE, PRICING_SCHEMES_STANDARD, \
    PM_SERVICE_TYPE, PERCENT_UNITS, SOURCE_BASIS, FINAL_APPROVAL_SERVICE_TYPE, HOURS_UNITS, \
    WORDS_UNITS, TRANSLATION_EDIT_PROOF_SERVICE_TYPE, THIRD_PARTY_REVIEW_SERVICE_TYPE, DTP_SERVICE_TYPE, \
    POST_PROCESS_SERVICE_TYPE, DISCOUNT_SERVICE_TYPE
from services.models import ScopeUnit, Locale, Service, ServiceType, PricingBasis, Vertical, PricingScheme, Industry
from tasks.models import NonTranslationTask, TranslationTask, TranslationTaskClientPrice
from projects.states import STARTED_STATUS, TASK_CREATED_STATUS, TASK_COMPLETED_STATUS
from vendors.models import Vendor
from django.utils import timezone


def create_client(name, vertical=None, via_team_jobs_email=None, pricing_scheme=None, pricing_basis=None):
    """Create a Client (with name, vertical and email).

    :type name: unicode
    :type vertical: Vertical or None
    :type via_team_jobs_email: unicode
    :type pricing_scheme: PricingScheme
    :rtype: Client
    """

    pbs, created = PricingBasis.objects.get_or_create(code=SOURCE_BASIS)
    if created:
        pass

    pbt, created = PricingBasis.objects.get_or_create(code=TARGET_BASIS)
    if created:
        pass

    client_account_type, created = AccountType.objects.get_or_create(
        code='client',
        description='Client'
    )

    if not pricing_scheme:
        pricing_scheme, created = PricingScheme.objects.get_or_create(code=PRICING_SCHEMES_STANDARD)

    if not pricing_basis:
        pricing_basis, created = PricingBasis.objects.get_or_create(code=TARGET_BASIS)
        if created:
            pass

    client = Client.objects.create(
        name=name,
        via_team_jobs_email=via_team_jobs_email,
        account_type=client_account_type,
    )
    client.account_number = "%dT%d" % (id(client), client.id)
    client.save()
    manifest = ClientManifest.objects.create(
        client=client,
        pricing_scheme=pricing_scheme,
        pricing_basis=pricing_basis,
        vertical=vertical,
        teamserver_client_subject_id=1,
        minimum_price=110,
        expansion_rate_floor_override=True,
    )
    manifest.save()

    cd = ClientDiscount.objects.create(client=client, start_date='2017-01-01', end_date='2017-02-01', discount=-0.2)
    cd.save()

    return client


def create_client_user(email, client=None, **kwargs):
    """Create a CircusUser (with email, account (client), .

    :type email: unicode
    :type client: Client
    :rtype: CircusUser
    """

    client_user = CircusUser.objects.create(
        user_type=settings.CLIENT_USER_TYPE,
        email=email,
        is_active=True,
        profile_complete=True,
        registration_complete=True,
        account=client,
        **kwargs
    )
    client_user.set_password("test")
    client_user.last_login = timezone.now()
    client_user.save()

    return client_user


def create_project(name, targets=None, source=None, status=STARTED_STATUS, client_poc=None, **project_kwargs):
    """Create a Project (with client, status, source and target).

    :type name: unicode
    :type targets: list of Locale
    :type source: Locale
    :rtype: Project
    """

    industry, created = Industry.objects.get_or_create(code='public', description='Public interest')
    if created:
        pass

    if targets is None:
        # russian
        targets = [Locale.objects.get(lcid=1049)]

    if source is None:
        # english
        source = Locale.objects.get(lcid=1033)

    if client_poc:
        client = client_poc.account
    else:
        client = create_client(
            name=u"Legion of Doom",
            via_team_jobs_email=u"legion-of-doom@example.com",
        )

        client_poc = create_client_user(
            email=u'client@test.com',
            client=client
        )

    if status == STARTED_STATUS:
        project_kwargs.setdefault('due', now() + timedelta(days=7))
        project_kwargs.setdefault('started_timestamp', now())

    project = Project.objects.create(
        name=name,
        status=status,
        client=client,
        client_poc=client_poc,
        current_user=client_poc.id,
        source_locale=source,
        industry=industry,
        **project_kwargs
    )

    project.target_locales.add(*targets)
    return project


def create_project_details(project, add_pm_task=False):
        russian = Locale.objects.get(lcid=1049)
        targets = [russian]

        project.payment_details.ca_invoice_number = "Diamond-2035"
        project.payment_details.save()

        filename = 'Charter.rtf'
        source_file = FileAsset.objects.create(
            kit=project.kit,
            asset_type=SOURCEFILE_ASSET,
            orig_name=filename,
        )
        analysis = FileAnalysis.objects.create(
            asset=source_file,
            no_match=100,
            source_locale=project.source_locale,
            target_locale=targets[0]
        )

        task_factory = TaskFactory(project)

        pbt, created = PricingBasis.objects.get_or_create(code=TARGET_BASIS)
        ttcp = task_factory.create_ttcp(
            source_of_client_prices=-1,
            word_rate=Decimal('0.230'),
            expansion_rate=1.25,
            minimum_price=110,
            basis=pbt
        )

        task = task_factory.create_tep_task(
            TASK_COMPLETED_STATUS,
            client_price=ttcp)

        if add_pm_task:
            pm_task = task_factory.create_pm_task()

            pm_price = ClientNonTranslationPrice.objects.create(
                service=pm_task.service,
                unit_price=Decimal('0.10')
            )
            pm_task.set_from_client_price(pm_price)


def create_vendor_user(email='vendor@howl.example.com', vendor=None):
    """Create a Vendor.

    Also returns the credentials they may use to login.

    :return: (User, credentials)
    :rtype: (CircusUser, dict)
    """

    if vendor is None:
        vendor_account_type = AccountType.objects.get_or_create(
            code='vendor',
            description='Vendor'
        )[0]
        vendor = Vendor.objects.create(
            name="Howl's Translation Services",
            account_type=vendor_account_type,
        )

    password = "test"

    vendor_user = CircusUser.objects.create(
        user_type=settings.VENDOR_USER_TYPE,
        email=email,
        is_active=True,
        profile_complete=True,
        registration_complete=True,
        account=vendor
    )
    vendor_user.set_password(password)
    vendor_user.save()
    return vendor_user, {'email': email,
                         'password': password}


def create_via_user(email='pm@via.example.com', **user_kwargs):
    """Create a VIA User.

    Also returns the credentials they may use to login.

    :return: (User, credentials)
    :rtype: (CircusUser, dict)
    """
    password = "test"

    via_user = CircusUser.objects.create(
        user_type=settings.VIA_USER_TYPE,
        is_staff=True,
        email=email,
        is_active=True,
        profile_complete=True,
        registration_complete=True,
        **user_kwargs
    )
    via_user.set_password(password)
    via_user.save()
    return via_user, {'email': email,
                      'password': password}


class TaskFactory(object):
    def __init__(self, project, target=None):
        """
        @type project: Project
        @type target: Locale
        """
        self.project = project
        self.source = project.source_locale
        if target is None:
            target = project.target_locales.first()
        self.target = target

    def create_ttcp(self, source_of_client_prices=None, word_rate=0.0, expansion_rate=1.0, minimum_price=0.0, basis=None, **task_args):
        """Create a Translation/Edit/Proof task.

        :rtype : TranslationTask
        """

        if not basis:
            basis, created = PricingBasis.objects.get_or_create(code=TARGET_BASIS)

        ttcp = TranslationTaskClientPrice.objects.create(
            source_of_client_prices=source_of_client_prices,
            word_rate=word_rate,
            expansion_rate=expansion_rate,
            minimum_price=minimum_price,
            basis=basis,
            **task_args
        )
        return ttcp

    def create_tep_task(self, status, target=None, **task_args):
        """Create a Translation/Edit/Proof task.

        :rtype : TranslationTask
        """
        words = ScopeUnit.objects.get_or_create(code=WORDS_UNITS, description="Words")[0]
        translation_edit_proof = ServiceType.objects.get_or_create(code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE, description="Translation and Proofreading")[0]

        if target is None:
            target = self.target

        service = Service.objects.get_or_create(
            source=self.source, target=target,
            service_type=translation_edit_proof,
            unit_of_measure=words)[0]

        task_args.setdefault('billable', True)

        tep = TranslationTask.objects.create(
            status=status,
            project=self.project,
            service=service,
            **task_args
        )

        if tep.client_price:
            prices = tep.client_price.itemized_price_details()

        return tep

    def create_fa_task(self, status, **task_args):
        """Create a Final Approval task.

        :rtype : NonTranslationTask
        """
        final_approval = ServiceType.objects.get_or_create(code=FINAL_APPROVAL_SERVICE_TYPE, description="Final Approval")[0]
        hours = ScopeUnit.objects.get_or_create(code=HOURS_UNITS,description="Hours")[0]

        service = Service.objects.get_or_create(
            source=self.source, target=self.target,
            service_type=final_approval,
            unit_of_measure=hours)[0]

        return NonTranslationTask.objects.create(
            status=status,
            project=self.project,
            service=service,
            **task_args
        )

    def create_pp_task(self, status, **task_args):
        """Create a Final Approval task.

        :rtype : NonTranslationTask
        """
        post_process = ServiceType.objects.get_or_create(code=POST_PROCESS_SERVICE_TYPE, description="Post Process")[0]
        hours = ScopeUnit.objects.get_or_create(code=HOURS_UNITS,description="Hours")[0]

        service = Service.objects.get_or_create(
            source=self.source, target=self.target,
            service_type=post_process,
            unit_of_measure=hours)[0]

        return NonTranslationTask.objects.create(
            status=status,
            project=self.project,
            service=service,
            **task_args
        )

    def create_dtp_task(self, status, target=None, **task_args):
        """Create a Desktop Publishing task.

        :rtype : NonTranslationTask
        """
        dtp = ServiceType.objects.get_or_create(code=DTP_SERVICE_TYPE, description="Desktop Publishing")[0]
        hours = ScopeUnit.objects.get_or_create(code=HOURS_UNITS, description="Hours")[0]

        if target is None:
            target = self.target

        service = Service.objects.get_or_create(
            source=self.source, target=target,
            service_type=dtp,
            unit_of_measure=hours)[0]

        task_args.setdefault('billable', True)

        return NonTranslationTask.objects.create(
            status=status,
            project=self.project,
            service=service,
            **task_args
        )

    def create_review_task(self, status, target=None, **task_args):
        """Create a Third Party Review task.

        :rtype : NonTranslationTask
        """
        third_party_review = ServiceType.objects.get_or_create(code=THIRD_PARTY_REVIEW_SERVICE_TYPE, description="Third Party Review")[0]
        hours = ScopeUnit.objects.get_or_create(code=HOURS_UNITS, description="Hours")[0]

        if target is None:
            target = self.target

        service = Service.objects.get_or_create(
            source=self.source, target=target,
            service_type=third_party_review,
            unit_of_measure=hours)[0]

        task_args.setdefault('billable', True)

        return NonTranslationTask.objects.create(
            status=status,
            project=self.project,
            service=service,
            **task_args
        )

    def create_pm_task(self, status=TASK_CREATED_STATUS, target=None, **task_args):
        if target is None:
            target = self.target

        pm_service_type = ServiceType.objects.get(code=PM_SERVICE_TYPE)
        percent = ScopeUnit.objects.get(code=PERCENT_UNITS)

        service = Service.objects.get_or_create(
            source=self.source, target=target,
            service_type=pm_service_type,
            unit_of_measure=percent)[0]

        task_args.setdefault('billable', True)

        return NonTranslationTask.objects.create(
            status=status,
            project=self.project,
            service=service,
            price_is_percentage=True,
            **task_args
        )

    def create_client_discount_task(self, status=TASK_CREATED_STATUS, target=None, **task_args):
        if target is None:
            target = self.target

        cd_service_type = ServiceType.objects.get_or_none(code=DISCOUNT_SERVICE_TYPE)
        percent = ScopeUnit.objects.get(code=PERCENT_UNITS)

        service = Service.objects.get_or_create(
            source=self.source, target=target,
            service_type=cd_service_type,
            unit_of_measure=percent)[0]

        task_args.setdefault('billable', True)

        return NonTranslationTask.objects.create(
            status=status,
            project=self.project,
            service=service,
            price_is_percentage=True,
            **task_args
        )


class NonTranslationPriceFactory(object):
    def __init__(self, default_price=0, default_client_price=0,
                 healthcare_price=0, all_langs_price=0, client=None):

        pb, created = PricingBasis.objects.get_or_create(code=SOURCE_BASIS)
        if created:
            pass

        pb, created = PricingBasis.objects.get_or_create(code=TARGET_BASIS)
        if created:
            pass

        # english
        source = Locale.objects.get(lcid=1033)
        # russian
        target = Locale.objects.get(lcid=1049)

        unit_of_measure = ScopeUnit.objects.get_or_create(code=HOURS_UNITS, description="Hours")[0]
        target_basis = PricingBasis.objects.get(code=TARGET_BASIS)

        third_party_review = ServiceType.objects.get_or_create(code=THIRD_PARTY_REVIEW_SERVICE_TYPE, description="Third Party Review")[0]

        all_languages_service = Service.objects.create(
            service_type=third_party_review,
            unit_of_measure=unit_of_measure,
            source=None,
            target=None
        )

        service = Service.objects.get(
            service_type=third_party_review,
            unit_of_measure=unit_of_measure,
            source=source,
            target=target
        )

        ClientNonTranslationPrice.objects.create(
            client=None,
            pricing_scheme=None,
            service=all_languages_service,
            unit_price=all_langs_price,
        )

        # Unassigned - Default Pricing
        ctp, created = ClientNonTranslationPrice.objects.get_or_create(
            client=None,
            pricing_scheme=None,
            service=service
        )
        ctp.unit_price = default_price
        ctp.save()

        # Client - Default Pricing
        ctp, created = ClientNonTranslationPrice.objects.get_or_create(
            client=client,
            pricing_scheme=None,
            service=service
        )
        ctp.unit_price = default_client_price
        ctp.save()

        # Healthcare
        pricing_scheme = PricingScheme.objects.get(code=PRICING_SCHEMES_HEALTHCARE)

        ctp, created = ClientNonTranslationPrice.objects.get_or_create(
            client=client,
            pricing_scheme=pricing_scheme,
            service=service
        )
        ctp.unit_price = healthcare_price
        ctp.save()


class TranslationPriceFactory(object):
    def __init__(self, default_price=0, default_client_price=0, healthcare_price=0, client=None):

        pb, created = PricingBasis.objects.get_or_create(code=SOURCE_BASIS)
        if created:
            pass

        pb, created = PricingBasis.objects.get_or_create(code=TARGET_BASIS)
        if created:
            pass

        # english
        source = Locale.objects.get(lcid=1033)
        # russian
        target = Locale.objects.get(lcid=1049)

        translation_edit_proof = ServiceType.objects.get_or_create(code=TRANSLATION_EDIT_PROOF_SERVICE_TYPE, description="Translation and Proofreading")[0]
        unit_of_measure = ScopeUnit.objects.get_or_create(code=WORDS_UNITS, description="Words")[0]

        service = Service.objects.get(
                    service_type=translation_edit_proof,
                    unit_of_measure=unit_of_measure,
                    source=source,
                    target=target
                )

        service.expansion_rate = 1.1
        service.save()

        # Unassigned - Default Pricing
        word_rate = default_price

        target_basis = PricingBasis.objects.get(code=TARGET_BASIS)

        ctp, created = ClientTranslationPrice.objects.get_or_create(
            client=None,
            pricing_scheme=None,
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

        # Client - Default Pricing
        word_rate = default_client_price

        ctp, created = ClientTranslationPrice.objects.get_or_create(
            client=client,
            pricing_scheme=None,
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

        # Healthcare
        word_rate = healthcare_price
        pricing_scheme = PricingScheme.objects.get(code=PRICING_SCHEMES_HEALTHCARE)

        ctp, created = ClientTranslationPrice.objects.get_or_create(
            client=client,
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
