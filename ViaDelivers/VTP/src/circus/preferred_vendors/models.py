from django.db import models
from clients.models import Client
from preferred_vendors.managers import PreferredVendorManager
from services.models import Locale, ServiceType, Vertical
from shared.models import CircusModel
from vendors.models import Vendor


class PreferredVendor(CircusModel):
    objects = PreferredVendorManager()

    vertical = models.ForeignKey(Vertical, related_name='preferred_vendors', blank=True, null=True)
    client = models.ForeignKey(Client, related_name='preferred_vendors', blank=True, null=True)
    service_type = models.ForeignKey(ServiceType, blank=True, null=True)

    # switch this to an instance of service?
    source = models.ForeignKey(Locale, blank=True, null=True, related_name='preferred_vendors_as_source')
    target = models.ForeignKey(Locale, blank=True, null=True, related_name='preferred_vendors_as_target')

    priority = models.IntegerField(default=1)

    vendor = models.ForeignKey(Vendor)

    class Meta:
        ordering = ['priority']

    def __unicode__(self):
        return u'{0}: {1} ({2}) ({3}): {4} to {5}'.format(self.vendor, self.service_type, self.vertical, self.client, self.source, self.target)
