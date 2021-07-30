from django.conf import settings
from django.db import models
from django.db.models import permalink
from django.utils.translation import ugettext_lazy as _
from accounts.models import CircusUser
from people.models import Account
from services.models import Locale
from shared.models import CircusModel
from vendors.managers import VendorManager

import logging

logger = logging.getLogger('circus.' + __name__)


class Vendor(Account):
    USER_TYPE = settings.VENDOR_USER_TYPE
    objects = VendorManager()

    class Meta:
        proxy = True

    def get_job_contacts(self):
        # todo how to do this: use Contact role? ask vendors to provide a single email for this value?
        return [self.jobs_email] if self.jobs_email else []

    def can_access_phi_secure_job(self):
        try:
            if self.vendor_manifest:
                return self.vendor_manifest.is_phi_approved
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            print tb
            logger.error(u'ERROR: No Vendor vendor_manifest: {0} - {1}'.format(self.id, self), exc_info=True)
            vm, created = VendorManifest.objects.get_or_create(vendor = self)
            if created:
                logger.info(u'Vendor vendor_manifest created: {0} - {1}'.format(self.id, self))
            return False

    @permalink
    def get_absolute_url(self):
        return 'vendors_detail', (self.id,), {}


class VendorContact(CircusUser):
    USER_TYPE = settings.VENDOR_USER_TYPE

    class Meta:
        proxy = True


class VendorLanguagePair(CircusModel):
    vendor = models.ForeignKey(Vendor)
    source = models.ForeignKey(Locale, related_name='source_vendors')
    target = models.ForeignKey(Locale, related_name='target_vendors')


class VendorTranslationTaskFileType(CircusModel):
    code = models.CharField(max_length=40, unique=True)
    description = models.CharField(max_length=400, unique=True)
    extension = models.CharField(max_length=40, unique=False)
    
    def __unicode__(self):
        return u'{0} ({1})'.format(unicode(self.description), self.code)

class VendorManifest(CircusModel):
    vendor = models.OneToOneField(Vendor, related_name='vendor_manifest')
    vendortranslationtaskfiletype = models.ForeignKey(VendorTranslationTaskFileType, null=True, blank=True, verbose_name='Assign Filetypes')
    is_phi_approved = models.NullBooleanField('Is PHI approved', default=False, blank=True, null=True)
    baa_agreement_for_phi_signed = models.DateField('BAA Agreement for PHI Signed', blank=True, null=True)
    can_supplier_manage_freelancers = models.NullBooleanField('Supplier Manages Freelancers', default=False, blank=True, null=True)

    def __unicode__(self):
        return u'{0} ({1})'.format(self.vendor.name, unicode(self.vendortranslationtaskfiletype))
