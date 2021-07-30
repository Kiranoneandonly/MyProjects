from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.utils import timezone

from shared.models import CircusModel
from accounts.models import CircusUser
from projects.models import Project
from shared.fields import CurrencyField


class Invoice(CircusModel):
    project = models.ForeignKey(Project)
    due_date = models.DateTimeField(_('Due Date'), blank=True, null=True, default=timezone.now)
    order_amount = CurrencyField(default=0.00)
    invoice_amount = CurrencyField(default=0.00)
    ok_to_invoice = models.BooleanField(default=False)
    internal_notes = models.TextField(blank=True, null=True)
    external_notes = models.TextField(blank=True, null=True)
    billing_refnumber = models.CharField(_('RefNumber'), max_length=50, blank=True, null=True)
    billing_txnnumber = models.CharField(_('TxnNumber'), max_length=50, blank=True, null=True)
    billing_sync_date = models.DateTimeField(_('Sync Date'), blank=True, null=True)
    billing_sent_date = models.DateTimeField(_('Sent Date'), blank=True, null=True)
    billing_paid = models.BooleanField(_('Paid'), default=False)
    billing_paid_date = models.DateTimeField(_('Paid Date'), blank=True, null=True)

    def __unicode__(self):
        return unicode(self.project) + ', Invoice ' + unicode(self.pk)


class InvoiceNotes(CircusModel):
    invoice = models.ForeignKey(Invoice)
    note = models.TextField(blank=True, null=True)
    user = models.ForeignKey(CircusUser)

    class Meta:
        verbose_name_plural = 'invoice notes'
