from __future__ import unicode_literals

import django
from django.db import models
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext as _
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timesince import timesince as djtimesince
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
# from django.contrib.contenttypes import generic


try:
    from django.utils import timezone
    now = timezone.now
except ImportError:
    from datetime import datetime
    now = datetime.now

@python_2_unicode_compatible
class Actions(models.Model):
    action_content_type = models.ForeignKey(ContentType, related_name='action', db_index=True)
    action_object_id = models.PositiveIntegerField()
    action_object_name = models.CharField(max_length=500, db_index=True)
    content_object = GenericForeignKey('action_content_type', 'action_object_id')

    verb = models.CharField(max_length=255)
    actor = models.CharField(max_length=500)
    timestamp = models.DateTimeField(default=now, db_index=True)

    trans_file_name = models.CharField(max_length=500, default='', blank=True, null=True)
    support_file_name = models.CharField(max_length=500, default='', blank=True, null=True)
    supplier_reference_file = models.CharField(max_length=500, default='', blank=True, null=True)

    ntt_input_file_name = models.CharField(max_length=500, default='', blank=True, null=True)
    ntt_output_file_name = models.CharField(max_length=500, default='', blank=True, null=True)
    ntt_support_file_name = models.CharField(max_length=500, default='', blank=True, null=True)
    task_service_type = models.CharField(max_length=500, default='', blank=True, null=True)

    file_type = models.CharField(max_length=500, default='', blank=True, null=True)

    job_id = models.IntegerField(default=0, blank=True, null=True)
    task_id = models.IntegerField(default=0, blank=True, null=True)
    user = models.CharField(max_length=500, default='', blank=True, null=True)
    status = models.CharField(max_length=500, default='', blank=True, null=True)

    description = models.TextField(blank=True, null=True)
    data = models.CharField(max_length=500, default='', blank=True, null=True)

    project_manager_approver = models.IntegerField(default=0, blank=True, null=True)
    ops_management_approver = models.IntegerField(default=0, blank=True, null=True)
    sales_management_approver = models.IntegerField(default=0, blank=True, null=True)
    task_price = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, blank=True, null=True)
    task_hours = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, blank=True, null=True)
    po_number = models.CharField(max_length=500, default='', blank=True, null=True)
    po_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, blank=True, null=True)

    class Meta:
        ordering = ('-timestamp', )

    def __str__(self):
        return '{0} {1} by {2} on {3}'.format(self.action_content_type.name, self.verb, self.actor, self.timesince())

    def timesince(self, now=None):
        """
        Shortcut for the ``django.utils.timesince.timesince`` function of the
        current timestamp.
        """
        return djtimesince(self.timestamp, now).encode('utf8').replace(b'\xc2\xa0', b' ').decode('utf8')



### NOTE: This is for including the signals file to connect signals. Don't remove this.
from activity_log import signals
