from django.db import models
from django.db.models import Q

from services.managers import ServiceTypeManager, LocaleManager, ScopeUnitManager, IndustryManager, \
    DocumentTypeManager, PricingBasisManager, VerticalManager, HOURS_UNITS, PricingSchemeManager, CountryManager, \
    SOURCE_BASIS, TARGET_BASIS, PERCENT_UNITS
from shared.models import CircusLookup, CircusModel
from pygeoip.const import COUNTRY_CODES , COUNTRY_NAMES


class ServiceCategory(CircusLookup):
    """Service Types are grouped into Categories.

    i.e. Translation and Proofreading are Linguistic Tasks, DTP is a
    Post-Translation Task.
    """

    rank = models.FloatField("Display Order")
    verbose_description = models.TextField(default='', blank=True)

    class Meta:
        verbose_name = 'attribute: Service Type Category'
        verbose_name_plural = 'attribute: Service Type Categories'
        ordering = ['rank']


class ServiceType(CircusLookup):
    objects = ServiceTypeManager()

    available = models.BooleanField(default=False)
    verbose_description = models.TextField(blank=True, null=True)
    translation_task = models.BooleanField(default=False)
    billable = models.BooleanField(default=True)
    jams_jobtaskid = models.PositiveIntegerField(blank=True, null=True)
    # Tasks for non-workflow services may be billed but will not appear
    # in the workflow with predecessors.
    workflow = models.BooleanField(default=True)
    category = models.ForeignKey(ServiceCategory, blank=True, null=True)
    abbreviation = models.CharField(max_length=20, default='', blank=True)
    icon = models.CharField(max_length=20, default='', blank=True)

    class Meta:
        verbose_name = 'attribute: Service Type'
        ordering = ['category', 'description']

    def is_translation(self):
        return self.translation_task


class Locale(CircusLookup):
    objects = LocaleManager()

    lcid = models.IntegerField(null=False, unique=True)
    # JAMS has data with some remapped LCIDs.
    jams_lcid = models.IntegerField(null=False, unique=True)
    dvx_lcid = models.IntegerField(null=False, unique=True)

    available = models.BooleanField(default=False)
    dvx_log_name = models.CharField(max_length=100, null=True, blank=True, unique=True)
    if_source_no_auto_estimate = models.BooleanField(default=False)
    if_target_no_auto_estimate = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'attribute: Locale'
        ordering = ['description']

    def normalize_english(self):
        if self.lcid in [loc.lcid for loc in self.english_locales()]:
            return self.english_us_locale()
        else:
            return self

    def english_locales(self):
        return list(Locale.objects.filter(Q(available=True) & Q(description__icontains="english")))

    def english_us_locale(self):
        return Locale.objects.get(lcid=1033)


class Country(models.Model):
    country_code = models.CharField(choices=zip(COUNTRY_CODES, COUNTRY_CODES), max_length=3, default=False, blank=True)
    country_name = models.CharField(choices=zip(COUNTRY_NAMES, COUNTRY_NAMES), max_length=70, default=False, blank=True)

    objects = CountryManager()

    def __unicode__(self):
        return u'%s' % self.country_name

    class Meta:
        verbose_name = 'attribute: Country'
        verbose_name_plural = 'attribute: Countries'


class PricingBasis(CircusLookup):
    objects = PricingBasisManager()

    class Meta:
        verbose_name = 'attribute: Pricing Basis'
        verbose_name_plural = 'attribute: Pricing Bases'
        ordering = ['description']

    def is_basis_source(self):
        return self.code == SOURCE_BASIS

    def is_basis_target(self):
        return self.code == TARGET_BASIS


class PricingFormula(CircusLookup):

    percent_calculation = models.DecimalField(max_digits=10, decimal_places=3, default=0.000)

    class Meta:
        verbose_name = 'attribute: Pricing Formula'
        ordering = ['description']

    def get_price(self):
        raise NotImplementedError('No logic exists for this formula')


class ScopeUnit(CircusLookup):
    objects = ScopeUnitManager()

    jams_basisid = models.IntegerField(null=True, unique=False)

    class Meta:
        verbose_name = 'attribute: Scope Unit'
        ordering = ['description']


class Industry(CircusLookup):
    objects = IndustryManager()

    class Meta:
        verbose_name = 'attribute: Industry'
        verbose_name_plural = 'attribute: Industries'
        ordering = ['description']


class Vertical(CircusLookup):
    objects = VerticalManager()

    class Meta:
        verbose_name = 'attribute: Vertical'
        ordering = ['description']


class PricingScheme(CircusLookup):
    objects = PricingSchemeManager()

    # use ClientManifest.teamserver_client_subject instead.
    # TODO: remove this after migration is deployed.
    obsolete_dvx_subject_code = models.IntegerField(
        default=0, db_column='dvx_subject_code')

    class Meta:
        verbose_name = 'attribute: Pricing Scheme'
        ordering = ['description']


class DocumentType(CircusLookup):
    objects = DocumentTypeManager()

    can_auto_estimate = models.BooleanField(default=True)

    # This is for formats we don't trust a client-provided document to provide
    # an accurate estimate, but an engineer may choose to send it to DVX.
    can_semiauto_estimate = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'attribute: Document Type'
        ordering = ['description']


class Service(CircusModel):
    service_type = models.ForeignKey(ServiceType)
    unit_of_measure = models.ForeignKey(ScopeUnit, max_length=10)
    formula = models.ForeignKey(PricingFormula, blank=True, null=True)
    source = models.ForeignKey(Locale, blank=True, null=True, related_name='services_as_source')
    target = models.ForeignKey(Locale, blank=True, null=True, related_name='services_as_target')
    expansion_rate = models.FloatField(default=1.0)

    class Meta:
        unique_together = ('service_type', 'unit_of_measure', 'source', 'target')
        ordering = ['source', 'target', 'service_type', 'unit_of_measure']

    def is_hourly(self):
        return (self.unit_of_measure and
                self.unit_of_measure.code == HOURS_UNITS)

    def is_percent(self):
        return (self.unit_of_measure and
                self.unit_of_measure.code == PERCENT_UNITS)

    def __unicode__(self):
        return u'{0} ({1}) {2} to {3} ({4})'.format(self.service_type, self.unit_of_measure, self.source, self.target, self.expansion_rate)


def get_translation_task_service_types():
    return [s.id for s in ServiceType.objects.filter(translation_task=True)]


def get_translation_task_service_types_code():
    return [s.code for s in ServiceType.objects.filter(translation_task=True)]