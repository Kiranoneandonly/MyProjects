from __future__ import unicode_literals

from django.db import models

from clients.models import Client
from matches.models import AnalysisCategoryCurrencyFields
from prices.managers import VendorRateManager, ClientPriceManager
from services.models import Service, PricingBasis, Vertical, PricingScheme
from shared.fields import CurrencyField
from shared.models import CircusModel
from vendors.models import Vendor


class PricingBasisMixin(models.Model):
    pricing_scheme = models.ForeignKey(PricingScheme, related_name='+', blank=True, null=True)
    client = models.ForeignKey(Client, blank=True, null=True)

    class Meta:
        abstract = True


class ClientPrice(CircusModel, PricingBasisMixin):
    service = models.ForeignKey(Service, related_name='+')

    class Meta:
        abstract = True
        unique_together = ('client', 'service', 'pricing_scheme')

    def __unicode__(self):
        return "{0} {1} {2} {3}".format(self.client, self.pricing_scheme, self.service, self.unit_price)


class ClientTranslationPrice(ClientPrice, AnalysisCategoryCurrencyFields):
    objects = ClientPriceManager()

    minimum_price = CurrencyField(default=0.0)
    word_rate = CurrencyField(default=0.0)
    basis = models.ForeignKey(PricingBasis, blank=True, null=True, related_name='+')
    notes = models.TextField(blank=True, null=True)

    def __unicode__(self):
        return "Translation pricing for {0} ({1}) ({2}) ".format(self.client, self.pricing_scheme, self.basis)


class ClientNonTranslationPrice(ClientPrice):
    objects = ClientPriceManager()

    unit_price = CurrencyField(default=0.0)

    def __unicode__(self):
        return "{0} {1} {2} {3}".format(self.client, self.pricing_scheme, self.service, self.unit_price)


class VendorRate(CircusModel):
    vendor = models.ForeignKey(Vendor, blank=True, null=True)
    service = models.ForeignKey(Service, related_name='+')
    vertical = models.ForeignKey(Vertical, related_name='+', blank=True, null=True)
    client = models.ForeignKey(Client, related_name='+', blank=True, null=True)
    minimum = CurrencyField(default=0.0)

    class Meta:
        abstract = True
        unique_together = ('vendor', 'service', 'vertical', 'client')


class VendorTranslationRate(VendorRate, AnalysisCategoryCurrencyFields):
    objects = VendorRateManager()

    word_rate = CurrencyField(default=0.0)
    basis = models.ForeignKey(PricingBasis, blank=True, null=True, related_name='+')

    def __unicode__(self):
        return "Translation pricing for {0} ({1}) ({2}) ".format(self.vendor, self.vertical, self.basis)


class VendorNonTranslationRate(VendorRate):
    objects = VendorRateManager()

    unit_cost = CurrencyField(default=0.0)

    def __unicode__(self):
        return "{0} {1} {2} {3}".format(self.vendor, self.vertical, self.service, self.unit_cost)
