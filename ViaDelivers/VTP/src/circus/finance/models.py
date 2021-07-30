from __future__ import unicode_literals
from django.db import models
from shared.models import CircusLookup, CircusModel
from django.utils.translation import ugettext_lazy as _

# TODO: make sure any changes in invoice types are reflected here
# TODO: explore options for auto-updating
INVOICE_TEMPLATES = (
    ('standard ', 'Standard'),
    ('semi-complex', 'Semi-complex'),
    ('complex', 'Complex'),
    ('mp_services', 'MobilePaks Services'),
    ('mp_subscriptions', 'MobilePaks Subscriptions'),
    ('vle', 'VLE'),
)

CA_PAYMENT_CHOICE = "ca"
CC_PAYMENT_CHOICE = "cc"

PAYMENT_CHOICES = [
    (CA_PAYMENT_CHOICE, _('Corporate/Invoice')),
    (CC_PAYMENT_CHOICE, _('Credit Card')),
]


class InvoiceTemplate(CircusLookup):
    class Meta:
        verbose_name = 'attribute: Invoice Template'

    def __unicode__(self):
        return unicode(self.description)


class ProjectPayment(CircusModel):
    payment_method = models.CharField(choices=PAYMENT_CHOICES, max_length=10, default=CA_PAYMENT_CHOICE)
    cc_response_auth_code = models.CharField(max_length=255, blank=True, null=True, verbose_name='Credit Card Authorization Code')
    ca_invoice_number = models.CharField(max_length=100, blank=True, null=True, help_text='Corporate Account Reference Number. 100 characters max.', verbose_name='Purchase Order')
    note = models.TextField(blank=True, null=True)

    def __init__(self, *args, **kwargs):
        super(ProjectPayment, self).__init__(*args, **kwargs)


    def __repr__(self):
        if self.payment_method == CC_PAYMENT_CHOICE:
            code = self.cc_response_auth_code
        elif self.payment_method == CA_PAYMENT_CHOICE:
            code = self.ca_invoice_number
        else:
            code = ''

        s = '<%s.%s#%s %s %s>' % (__name__, self.__class__.__name__, self.id,
            self.payment_method, code)
        return s
