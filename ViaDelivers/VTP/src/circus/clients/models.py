# coding=utf-8
import posixpath
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import Group

from accounts.models import CircusUser
from clients.managers import ClientsManager, ClientManifestManager, ClientTeamRoleManager, \
    ClientEmailDomainManager, ClientServiceManager, ClientReferenceFilesManager, TEAMServerSubjectManager, \
    ClientDiscountManager
from people.models import Account, AccountEmailDomain
from services.managers import PRICING_SCHEMES_HEALTHCARE, PRICING_SCHEMES_HEALTHCARE_STRATEGIC, PRICING_SCHEMES_HEALTHCARE_PHI
from services.models import Locale, ServiceType, PricingBasis, Vertical, PricingScheme
from shared.fields import CurrencyField
from shared.models import CircusModel, CircusLookup

PM_ROLE = 'pm'
AE_ROLE = 'ae'
TSG_ENG_ROLE = 'tsg_eng'
VLE_ENG_ROLE = 'vle_eng'
QA_ENG_ROLE = 'qa_eng'
SECURE_JOB_TEAM_ROLE = 'sjt_member'
PHI_SECURE_JOB_TEAM_ROLE = 'psj_team'

CLIENT_TEAM_ROLES = (
    (PM_ROLE, 'Project Manager'),
    (AE_ROLE, 'Account Executive'),
    (TSG_ENG_ROLE, 'TSG Engineer'),
    (VLE_ENG_ROLE, 'VLE Engineer'),
    (QA_ENG_ROLE, 'QA Engineer'),
    (SECURE_JOB_TEAM_ROLE, 'Secure Job Team Member'),
    (PHI_SECURE_JOB_TEAM_ROLE, 'PHI Secure Job Team Member'),
)


class Client(Account):
    objects = ClientsManager()

    class Meta:
        proxy = True

    # manifest is the related_name for ClientManifest

    def is_phi_secure_client(self):
        return self.manifest.baa_agreement_for_phi and self.manifest.phi_warning()

    @models.permalink
    def get_absolute_url(self):
        return 'clients_detail', (self.id,), {}


class ClientContact(CircusUser):
    USER_TYPE = settings.CLIENT_USER_TYPE

    class Meta:
        proxy = True


class ClientTeamRole(models.Model):
    client = models.ForeignKey(Client)
    contact = models.ForeignKey(settings.AUTH_USER_MODEL)
    role = models.CharField(choices=CLIENT_TEAM_ROLES, max_length=10, blank=True, null=True)

    unique_together = ("client", "contact", "role")

    objects = ClientTeamRoleManager()


class ClientEmailDomain(AccountEmailDomain):
    objects = ClientEmailDomainManager()

    class Meta:
        proxy = True


class TEAMServerSubject(CircusLookup):
    dvx_subject_code = models.CharField(
        _('TEAMServer Subject Code'), max_length=40, null=False)

    objects = TEAMServerSubjectManager()

    def __unicode__(self):
        return u"%s — %s" % (self.description, self.dvx_subject_code)


def default_subject():
    if TEAMServerSubject.objects.all():
        return TEAMServerSubject.objects.get(code=settings.DEFAULT_TEAMSERVER_SUBJECT)
    else:
        return None


class ClientManifest(CircusModel):
    client = models.OneToOneField(Client, related_name='manifest')
    express_factor = models.DecimalField(max_digits=15, decimal_places=4, default=Decimal('1.5'))
    pricing_basis = models.ForeignKey(PricingBasis, null=True, related_name='+')
    auto_estimate_jobs = models.BooleanField(default=True)
    auto_start_workflow = models.BooleanField(default=False)
    is_hourly_schedule = models.BooleanField(default=False)
    secure_jobs = models.BooleanField("Restricted Jobs", default=False)
    state_secrets_validation = models.BooleanField(default=False)
    restricted_pricing = models.DecimalField(_('Restricted Pricing %'), null=True, blank=True,
                                     max_digits=6, decimal_places=4,default=Decimal('16'))
    vertical = models.ForeignKey(Vertical, null=True)
    pricing_scheme = models.ForeignKey(PricingScheme, null=True)
    pricing_memory_bank_discount = models.BooleanField(_('Memory Bank Discount'), default=False)
    teamserver_tm_enabled = models.BooleanField(_('TEAMServer TM Enabled'), default=False)
    note = models.TextField(blank=True)

    # Default pricing modifiers. Not inheriting AnalysisCategoryCurrencyFields because these need to be nullable
    # (in which case the value in the ClientTranslationPrice will be used).
    guaranteed = models.DecimalField(_('Prfect'), null=True, blank=True, max_digits=6, decimal_places=4)
    exact = models.DecimalField(_('Exact'), null=True, blank=True, max_digits=6, decimal_places=4)
    duplicate = models.DecimalField(_('Reps'), null=True, blank=True, max_digits=6, decimal_places=4)
    fuzzy9599 = models.DecimalField(_('95-99'), null=True, blank=True, max_digits=6, decimal_places=4)
    fuzzy8594 = models.DecimalField(_('85-94'), null=True, blank=True, max_digits=6, decimal_places=4)
    fuzzy7584 = models.DecimalField(_('75-84'), null=True, blank=True, max_digits=6, decimal_places=4)
    fuzzy5074 = models.DecimalField(_('50-74'), null=True, blank=True, max_digits=6, decimal_places=4)
    no_match = models.DecimalField(_('NoMch'), null=True, blank=True, max_digits=6, decimal_places=4)

    minimum_price = CurrencyField(null=True, blank=True)
    default_client_user_level = models.ManyToManyField(Group, blank=True, related_name='+')

    # client code shouldn't be null, but new clients won't have one yet
    teamserver_client_code = models.CharField(_('TEAMServer Client Code'), max_length=40, null=True)

    teamserver_client_subject = models.ForeignKey(
        TEAMServerSubject, on_delete=models.PROTECT, null=False,
        verbose_name=_('TEAMServer Subject Code'),
        default=default_subject)

    is_sow_available = models.BooleanField(default=False)
    is_reports_menu_available = models.BooleanField(default=False, null=False)
    update_tm = models.CharField(max_length=256, choices=[('immediately', 'immediately'), ('weekly', 'weekly'), ('monthly', 'monthly')], default='immediately')
    show_client_messenger = models.BooleanField(default=False)
    ignore_holiday_flag = models.BooleanField(default=False)
    client_notification_group = models.BooleanField(default=True)
    word_count_breakdown_flag = models.BooleanField(default=False)
    expansion_rate_floor_override = models.NullBooleanField(default=False)
    standard_translation_words_per_day = models.IntegerField(blank=True, null=True)
    enforce_customer_hierarchy = models.NullBooleanField(default=False, blank=True, null=True)
    baa_agreement_for_phi = models.NullBooleanField(_('BAA Agreement in place for PHI'), default=False, blank=True, null=True)

    objects = ClientManifestManager()

    def phi_warning(self):
        return self.pricing_scheme.code == PRICING_SCHEMES_HEALTHCARE \
               or self.pricing_scheme.code == PRICING_SCHEMES_HEALTHCARE_STRATEGIC \
               or self.pricing_scheme.code == PRICING_SCHEMES_HEALTHCARE_PHI


class ClientService(models.Model):
    client = models.ForeignKey(Client)
    service = models.ForeignKey(ServiceType)
    available = models.BooleanField(default=False)
    job_default = models.BooleanField(default=False)

    unique_together = ("client", "service")

    objects = ClientServiceManager()

    def __unicode__(self):
        return u'{0} ({1})'.format(self.client.name, self.service.description)


class ClientDiscount(models.Model):
    client = models.ForeignKey(Client)
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    discount = models.DecimalField(max_digits=15, decimal_places=1, blank=True, null=True)

    objects = ClientDiscountManager()

    def __unicode__(self):
        return u'{0} ({1})'.format(self.client.name, self.discount)


CLIENT_REFERENCE_FILE_TYPES = (
    ('glossary', 'Glossary'),
    ('style_guide', 'StyleGuide'),
)


def get_reference_file_path(crf, filename):
    return posixpath.join('projects', str(crf.client.id), str(crf.source.id), str(crf.target.id), 'ref', filename)


class ClientReferenceFiles(CircusModel):
    client = models.ForeignKey(Client)
    orig_name = models.CharField(max_length=255, verbose_name="Original Name")
    orig_file = models.FileField(max_length=settings.FULL_FILEPATH_LENGTH, upload_to=get_reference_file_path, null=True, blank=True)
    reference_file_type = models.CharField(choices=CLIENT_REFERENCE_FILE_TYPES,  max_length=50, blank=True, null=True)
    source = models.ForeignKey(Locale, blank=True, null=True, related_name='+')
    target = models.ForeignKey(Locale, blank=True, null=True, related_name='+')

    objects = ClientReferenceFilesManager()

    def file_exists(self):
        if self.orig_file:
            return True
        else:
            return False

    def file_display_name(self):
        full = unicode(self.orig_file)
        prefix = unicode(get_reference_file_path(self, ''))
        return full.replace(prefix, '')

    def __unicode__(self):
        return unicode(self.orig_name)
