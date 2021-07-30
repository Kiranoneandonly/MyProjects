from django.db import models
from django.conf import settings
from services.models import Vertical
from clients.models import Client
from tasks.models import Task
from vendors.models import Vendor
from projects.models import Project
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

QD = (
    ('no', 'No'),
    ('eqd', 'EQD'),
    ('iqd', 'IQD'),
)

RC = (
    ('PM', 'PM'),
    ('SM', 'SM'),
    ('DTP', 'DTP'),
    ('Linguistic', 'Linguistic'),
    ('Billing', 'Billing'),
    ('Technical', 'Technical'),
    ('client_source', 'Client Source'),
    ('Sales', 'Sales'),
    ('Other', 'Other'),
)
ClientConsulted = (
    ('satisfied', 'Satisfied'),
    ('not_satisfied', 'Not Satisfied')
)


class QualityDefect(models.Model):
    quality_defect = models.CharField(choices=QD, max_length=10, blank=True, null=True)
    title = models.CharField(max_length=300, blank=True, null=True, verbose_name='title')
    due_date = models.DateTimeField(_('Due Date'), blank=True, null=True)
    due_created = models.DateTimeField(_('Date Created'), default=timezone.now)
    due_modified = models.DateTimeField(_('Date Created'), blank=True, null=True)
    status = models.CharField(max_length=50, choices=[('open', 'Open'), ('closed', 'Closed')],  blank=True, null=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='+')
    priority = models.CharField(max_length=20,blank=True, null=True, choices=[('1', '(1) High'), ('2', '(2) Normal'),('3','(3) Low')])
    vertical = models.ForeignKey(Vertical, null=True, blank=True)
    client = models.ForeignKey(Client, null=True, blank=True, related_name='client')
    project = models.ForeignKey(Project, null=True, blank=True)
    task = models.ForeignKey(Task, null=True, blank=True, default=False)
    vendor = models.ForeignKey(Vendor, null=True, blank=True, related_name='vendor')
    closed_date = models.DateTimeField(_('Closed Date'), blank=True, null=True)
    root_cause = models.CharField(max_length=50, choices=RC, blank=True, null=True )
    root_cause_analysis = models.TextField(_('Root Cause Analysis'), blank=True, null=True )
    resolution = models.TextField(_('Resolution'), blank=True, null=True )
    client_consulted = models.CharField(choices=ClientConsulted, max_length=10, blank=True, null=True)
    client_consulted_notes = models.TextField(_('Client consulted notes'), blank=True, null=True )
    related_qd = models.ForeignKey('self', blank=True, null=True)
    client_informed = models.BooleanField(_('client informed'), default=False)


class QualityDefectComment(models.Model):
    comment = models.TextField(_('Comment'), blank=True, null=True )
    comment_by = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True)
    quality_defect = models.ForeignKey(QualityDefect)
    date_created = models.DateTimeField(_('Date Created'), default=timezone.now)
    date_modified = models.DateTimeField(_('Date Created'), blank=True, null=True)
