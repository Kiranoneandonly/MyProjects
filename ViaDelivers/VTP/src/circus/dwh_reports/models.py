# coding=utf-8
from __future__ import unicode_literals
from django.db import models
from django.utils import timezone
from projects.models import EXPRESS_SPEED
from projects.states import (COMPLETED_STATUS, QUEUED_STATUS, STARTED_STATUS, CREATED_STATUS)
from django.utils.translation import ugettext_lazy as _
from shared.models import CircusModel, CircusLookup


#Model for reporting framework
class ClientsReporting(CircusModel):
    client_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=1000, blank=True, null=True)
    parent_id = models.IntegerField(blank=True, null=True)
    account_type = models.IntegerField(blank=True, null=True)

    def __unicode__(self):
        return u"%s" % (self.name)


class ClientManager(CircusModel):
    id = models.IntegerField(primary_key=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    account = models.ForeignKey(ClientsReporting, blank=True, null=True)
    user_type = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=1000, blank=True, null=True)
    last_name = models.CharField(max_length=1000, blank=True, null=True)
    email = models.EmailField(max_length=254, null=True)
    reports_to_id = models.IntegerField(blank=True, null=True)

    def __unicode__(self):
        return u"%s %s (%s)" % (self.first_name, self.last_name, self.email)


class VendorsReporting(CircusModel):
    client_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=1000, blank=True, null=True)
    parent_id = models.IntegerField(blank=True, null=True)
    account_type = models.IntegerField(blank=True, null=True)

    def __unicode__(self):
        return u"%s" % (self.name)


class VendorUserReporting(CircusModel):
    id = models.IntegerField(primary_key=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    account = models.ForeignKey(VendorsReporting, blank=True, null=True)
    user_type = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=1000, blank=True, null=True)
    last_name = models.CharField(max_length=1000, blank=True, null=True)
    email = models.EmailField(max_length=254, null=True)
    reports_to_id = models.IntegerField(blank=True, null=True)

    def __unicode__(self):
        return u"%s %s (%s)" % (self.first_name, self.last_name, self.email)


class ViaReporting(CircusModel):
    client_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=1000, blank=True, null=True)
    parent_id = models.IntegerField(blank=True, null=True)
    account_type = models.IntegerField(blank=True, null=True)

    def __unicode__(self):
        return u"%s" % (self.name)


class ViaUserReporting(CircusModel):
    id = models.IntegerField(primary_key=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    account = models.ForeignKey(ViaReporting, blank=True, null=True)
    user_type = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=1000, blank=True, null=True)
    last_name = models.CharField(max_length=1000, blank=True, null=True)
    email = models.EmailField(max_length=254, null=True)
    reports_to_id = models.IntegerField(blank=True, null=True)

    def __unicode__(self):
        return u"%s %s (%s)" % (self.first_name, self.last_name, self.email)


class ProjectsReporting(CircusModel):
    project_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=1000, blank=True, null=True)
    customer = models.ForeignKey(ClientsReporting)           #should be related with client_id  #related with people_account
    price = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, blank=True, null=True)
    payment_method = models.CharField(max_length=1000, blank=True, null=True)
    gross_margin = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, blank=True, null=True)
    on_time_delivery = models.CharField(max_length=10, blank=True, null=True)
    project_status = models.CharField(max_length=50, blank=True, null=True)
    approved = models.BooleanField(default=False)
    source_locale = models.CharField(max_length=1000, blank=True, null=True)
    client_po = models.CharField(max_length=1000, blank=True, null=True)
    job_number = models.CharField(max_length=1000, blank=True, null=True)
    client_poc = models.ForeignKey(ClientManager, blank=True, null=True)        #should be related with client_poc_id #related with accounts_circususer
    account_executive = models.CharField(max_length=1000, blank=True, null=True)
    project_manager_id = models.IntegerField(blank=True, null=True)
    project_manager = models.CharField(max_length=1000, blank=True, null=True)
    estimator_id = models.IntegerField(blank=True, null=True)
    estimator = models.CharField(max_length=1000, blank=True, null=True)
    industry = models.CharField(max_length=1000, blank=True, null=True)
    start_date = models.DateTimeField(blank=True, null=True)
    due_date = models.DateTimeField(blank=True, null=True)
    completed = models.DateTimeField(blank=True, null=True)
    delivered_date = models.DateTimeField(blank=True, null=True)
    quoted = models.DateTimeField(blank=True, null=True)
    priority = models.CharField(max_length=1000, blank=True, null=True)
    estimate_type = models.CharField(max_length=1000, blank=True, null=True)
    instructions = models.TextField(_('Client Instructions'), blank=True, null=True)
    instructions_via = models.TextField(_('VIA Instructions'), blank=True, null=True)
    instructions_vendor = models.TextField(_('Supplier Instructions'), blank=True, null=True)
    project_reference_name = models.CharField(max_length=1000, blank=True, null=True)
    is_secure_job = models.NullBooleanField(default=False, blank=True, null=True)

    def is_completed_status(self):
        return self.project_status == COMPLETED_STATUS

    def is_canceled_status(self):
        return self.project_status == COMPLETED_STATUS

    def is_created_status(self):
        return self.project_status == CREATED_STATUS

    def is_started_status(self):
        return self.project_status == STARTED_STATUS

    def is_queued_status(self):
        return self.project_status == QUEUED_STATUS

    def is_quoted_status(self):
        return self.project_status == QUEUED_STATUS

    def is_express_speed(self):
        return self.priority == EXPRESS_SPEED

    def is_overdue_job(self):
        return self.is_started_status() and not self.delivered_date and self.due_date and self.due_date < timezone.now()

    def warnings(self):
        if self.is_overdue_job():
            return _('Job Overdue!')
        # todo other warnings
        else:
            return None

    def warnings_icon(self):
        if self.is_overdue_job():
            return _('fa fa-exclamation-circle')
        # todo other warnings
        else:
            return None
    
    def __unicode__(self):
        return u"%s — %s" % (self.job_number, self.customer)


class TasksReporting(CircusModel):
    task_id = models.IntegerField(blank=True, null=True)
    project = models.ForeignKey(ProjectsReporting)
    status = models.CharField(max_length=50, blank=True, null=True)
    assignee_object_id = models.PositiveIntegerField(blank=True, null=True)
    memory_bank_discount = models.DecimalField(max_digits=15, decimal_places=1, default=0.0, blank=True, null=True)
    gross_margin = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, blank=True, null=True)
    price = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, blank=True, null=True)
    service_id = models.IntegerField(blank=True, null=True)
    service_code = models.CharField(max_length=50, blank=True, null=True)
    service_type = models.CharField(max_length=50, blank=True, null=True)
    target_id = models.IntegerField(blank=True, null=True)
    target = models.CharField(max_length=1000, blank=True, null=True)
    source_file = models.CharField(max_length=1000, blank=True, null=True)
    word_count = models.IntegerField(blank=True, null=True)
    due = models.DateTimeField(blank=True, null=True)
    started = models.DateTimeField(blank=True, null=True)
    completed = models.DateTimeField(blank=True, null=True)
    accepted = models.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        return u"%s — %s — %s" % (self.target, self.service_type, self.project)


class EqdReporting(CircusModel):
    quality_defect = models.CharField(max_length=10, blank=True, null=True)
    title = models.CharField(max_length=300, blank=True, null=True, verbose_name='title')
    client_id = models.IntegerField(blank=True, null=True)
    project_id = models.IntegerField(blank=True, null=True)
    task_id = models.IntegerField(blank=True, null=True)
    project_manager_id = models.IntegerField(blank=True, null=True)
    due_date = models.DateTimeField(_('Due Date'), blank=True, null=True)
    due_created = models.DateTimeField(_('Date Created'), default=timezone.now)
    due_modified = models.DateTimeField(_('Date Modified'), blank=True, null=True)

    def __unicode__(self):
        return u"%s — %s" % (self.quality_defect, self.title)


class ClientReport(CircusLookup):
    report_name = models.CharField(max_length=200, blank=True, null=True)
    report_url_reverse = models.CharField(max_length=500, blank=True, null=True)

    def __unicode__(self):
        return u"%s" % (self.report_name)


class ClientReportAccess(CircusModel):
    client = models.ForeignKey(ClientsReporting)
    client_report = models.ForeignKey(ClientReport)
    access = models.BooleanField(default=False)

    unique_together = ("client", "client_report")

    def __unicode__(self):
        return u"%s" % (self.client)


class TaskRating(CircusModel):
    task_id = models.IntegerField(blank=True, null=True)
    project_id = models.IntegerField(blank=True, null=True)
    job_number = models.CharField(max_length=100, blank=True, null=True)
    task_name = models.TextField(blank=True, null=True)
    assignee_object_id = models.IntegerField(blank=True, null=True)
    assignee_name = models.CharField(max_length=500, blank=True, null=True)
    rating = models.IntegerField(default=0, blank=True, null=True)
    service_id = models.IntegerField(blank=True, null=True)
    service_type = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(_('Notes'), blank=True, null=True)
    via_notes = models.TextField(_('Via Notes'), blank=True, null=True)
    vendor_notes = models.TextField(_('Vendor Notes'), blank=True, null=True)
    started = models.DateTimeField(blank=True, null=True)
    completed = models.DateTimeField(blank=True, null=True)

    def __unicode__(self):
        return u"%s — %s" % (self.task_id, self.rating)


class RefreshTracking(models.Model):
    last_refreshed_timestamp = models.DateTimeField(auto_now_add=True)
