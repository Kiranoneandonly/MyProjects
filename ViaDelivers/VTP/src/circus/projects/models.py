from __future__ import unicode_literals
import json
import logging
import posixpath
from datetime import timedelta
from decimal import Decimal

from celery import shared_task
from celery.canvas import Signature
import celery.states
import celery.signals

from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import SUCCESS, ERROR, WARNING
from django.core.mail import mail_admins
from django.template import defaultfilters
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.db import models
from django.db.models import permalink, Q, Sum, Avg
from nullablecharfield.db.models.fields import CharNullField
from django.contrib.auth import get_user_model

from salesforce import models as sfmodels
from salesforce.backend.base import SalesforceError

from accounts.models import SalesforceUser, SalesforceContact, CircusUser
from clients.models import Client, ClientTeamRole, PM_ROLE, CLIENT_TEAM_ROLES, TSG_ENG_ROLE, AE_ROLE
from finance.models import InvoiceTemplate, ProjectPayment, CC_PAYMENT_CHOICE, CA_PAYMENT_CHOICE
from jams_api.engine import update_jams_job, create_jams_job_estimate
from localization_kits.make_kit_analysis import make_project_loc_kit_analysis
from localization_kits.make_locale_translation_kit import make_localetranslationkit, purge_old_localetranslationkit
from localization_kits.models import LocalizationKit
from notifications.notifications import notify_assigned_to_task_assigned, project_manual_quote_needed_via, \
    notify_new_job_ordered, notify_client_job_canceled, project_quote_ready
from people.models import Account, SalesforceAccount
from projects.assign_tasks import assign_project_tasks
from projects.duedates import add_delta_business_days
from projects.quote import ProjectQuote
from projects.set_prices import set_project_rates_and_prices, set_project_rates, set_project_prices
from projects.start_tasks import set_task_dates
from projects.managers import ProjectManager, BackgroundTaskManager, \
    SalesforceOpportunityManager, ProjectServicesGlobalManager, PriceQuoteManager, PriceQuoteDetailsManager, \
    ProjectJobOptionsManager
from services.managers import TARGET_BASIS, FINAL_APPROVAL_SERVICE_TYPE, POST_PROCESS_SERVICE_TYPE, \
    DISCOUNT_SERVICE_TYPE
from services.models import Locale, Industry, ServiceType, PricingBasis
from shared.fields import CurrencyField
from shared.models import CircusModel
from shared.state_machine import Machine
from projects.states import (PROJECT_STATES, PROJECT_STATUS_CHOICES, QUEUED_STATUS, CREATED_STATUS,
                             STARTED_STATUS, COMPLETED_STATUS, QUOTED_STATUS, TASK_COMPLETED_STATUS, CANCELED_STATUS, DELIVERED_STATUS,
                             TASK_CANCELED_STATUS, HOLD_STATUS)
from vendors.models import Vendor
from services.models import Country
from tinymce import HTMLField
from shared.group_permissions import PROTECTED_HEALTH_INFORMATION_GROUP


ENGLISH_LANG = 'English'

EXPRESS_SPEED = 'express'
STANDARD_SPEED = 'standard'

AUTO_ESTIMATE = 'auto'
MANUAL_ESTIMATE = 'manual'

logger = logging.getLogger('circus.' + __name__)


class Project(CircusModel):
    PROJECT_SPEED_CHOICES = [
        (STANDARD_SPEED, _(u'Standard')),
        (EXPRESS_SPEED, _(u'Express')),
        ]

    PROJECT_ESTIMATE_CHOICES = [
        (AUTO_ESTIMATE, _(u'Automatic')),
        (MANUAL_ESTIMATE, _(u'Manual')),
        ]

    RESTRICTED_CHOICES = (
        (True, _(u'Restricted Access')),
        (False, _(u'Unrestricted Access')),
    )

    DELAY_JOB_CHOICES = (
        (False, _(u'Estimate Hours')),
        (True, _(u'Actual Hours')),
    )
    li = []

    def __init__(self, *args, **kwargs):
        super(Project, self).__init__(*args, **kwargs)
        self.machine = Machine(self, PROJECT_STATES, 'status')

    job_number = models.CharField(max_length=50, db_index=True)
    name = models.CharField(max_length=1000, blank=True, null=True, db_index=True)
    status = models.CharField(choices=PROJECT_STATUS_CHOICES, max_length=40, default=QUEUED_STATUS, db_index=True)
    is_secure_job = models.NullBooleanField(default=False, blank=True, null=True)
    is_phi_secure_job = models.NullBooleanField(default=False, blank=True, null=True)
    is_restricted_job = models.NullBooleanField(default=False, blank=True, null=True)
    delay_job_po = models.BooleanField(choices=DELAY_JOB_CHOICES, default=False)
    estimate_type = models.CharField(choices=PROJECT_ESTIMATE_CHOICES, max_length=10, default=AUTO_ESTIMATE)
    revenue_recognition_month = models.DateTimeField(_(u'Revenue Recognition Month'), blank=True, null=True)
    original_invoice_count = models.IntegerField(_(u'Original Invoice Count'), blank=True, null=True)

    salesforce_opportunity_id = CharNullField(max_length=18, null=True, blank=True, db_index=True)

    # people
    industry = models.ForeignKey(Industry, null=True)
    client = models.ForeignKey(Client)
    client_poc = models.ForeignKey(settings.AUTH_USER_MODEL)
    # todo - populate default people on start
    account_executive = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='+')
    project_manager = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='+')
    estimator = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='+')

    # assets
    kit = models.OneToOneField(LocalizationKit, related_name='project', blank=True, null=True)

    # languages
    source_locale = models.ForeignKey(Locale, blank=True, null=True, related_name='+')
    target_locales = models.ManyToManyField(Locale, blank=True, related_name='+')
    assigned_to = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='+')
    access_request = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='access_project', through='ProjectAccess')
    restricted_locations = models.ManyToManyField(Country, blank=True, related_name='+')

    approved = models.BooleanField(default=False)

    # service options
    instructions = HTMLField(_('Client Instructions'), blank=True, null=True)
    instructions_via = HTMLField(_('VIA Instructions'), blank=True, null=True)
    instructions_vendor = HTMLField(_('Supplier Instructions'), blank=True, null=True)

    services = models.ManyToManyField(ServiceType, blank=True, related_name='+')
    services_global = models.ManyToManyField(ServiceType, blank=True, related_name='service_global', through='ProjectServicesGlobal')

    # dates
    project_speed = models.CharField(choices=PROJECT_SPEED_CHOICES, max_length=10, default=STANDARD_SPEED)

    quote_due = models.DateTimeField(_(u'Quote Due Date'), blank=True, null=True)
    quoted = models.DateTimeField(_(u'Quote Delivered Date'), blank=True, null=True)
    started_timestamp = models.DateTimeField(_(u'Started Date'), blank=True, null=True)
    due = models.DateTimeField(_(u'Due Date'), blank=True, null=True)
    delivered = models.DateTimeField(_(u'Delivered Date'), blank=True, null=True)
    completed = models.DateTimeField(_(u'Complete Date'), blank=True, null=True)
    canceled = models.DateTimeField(_(u'Canceled Date'), blank=True, null=True)

    # copied from client at quote time
    express_factor = models.DecimalField(max_digits=15, decimal_places=4, default=1.5)
    pricing_basis = models.ForeignKey(PricingBasis, blank=True, null=True, related_name='+')

    # Project Accounting
    payment_details = models.OneToOneField(ProjectPayment, related_name='payment_detail', blank=True, null=True)
    invoice_template = models.ForeignKey(InvoiceTemplate, related_name='invoice_template', null=True)

    # JAMS API
    jams_jobid = models.IntegerField(_(u'JAMS JobID'), blank=True, null=True)
    jams_estimateid = models.IntegerField(_(u'JAMS EstimateID'), blank=True, null=True)

    project_reference_name = models.CharField(max_length=1000, blank=True, null=True)

    current_user = models.IntegerField(blank=True, null=True)
    internal_via_project = models.BooleanField(default=False)
    no_express_option = models.BooleanField(default=False)

    project_manager_approver = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='+')
    ops_management_approver = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='+')
    sales_management_approver = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, related_name='+')

    large_job_approval_timestamp = models.DateTimeField(_(u'Large Jobs Approval Date'), blank=True, null=True)
    large_job_approval_notes = models.TextField(_(u'Large Jobs Approval Instructions'), blank=True, null=True)

    ignore_holiday_flag = models.BooleanField(default=False)
    price_per_document = models.BooleanField(default=True)

    objects = ProjectManager()

    def quote(self):
        return ProjectQuote(self)

    def sub_task_quote(self):
        return ProjectQuote(self, sub_tasks=True)

    def quote_no_costs(self):
        return ProjectQuote(self, include_costs=False)

    def quote_standard(self):
        return ProjectQuote(self, speed=STANDARD_SPEED)

    def quote_express(self):
        return ProjectQuote(self, speed=EXPRESS_SPEED)

    def quote_standard_no_costs(self):
        return ProjectQuote(self, speed=STANDARD_SPEED, include_costs=False)

    def quote_express_no_costs(self):
        return ProjectQuote(self, speed=EXPRESS_SPEED, include_costs=False)

    def quote_standard_no_price_no_costs(self):
        return ProjectQuote(self, speed=STANDARD_SPEED, include_price=False, include_costs=False)

    def quote_express_no_price_no_costs(self):
        return ProjectQuote(self, speed=EXPRESS_SPEED, include_price=False, include_costs=False)

    def quote_summary(self):
        return ProjectQuote(self, quote_summary=True)

    def quote_summary_recalculate(self, task, tat_custom):
        return ProjectQuote(self, quote_summary=True, task=task, tat_custom=tat_custom)

    def quote_summary_recalculate_all(self):
        return ProjectQuote(self, quote_summary=True, recalculate_flag=True)

    def recalculate_target_price(self, target):
        price_quote = PriceQuote.objects.get(project=self)
        price_quote_details = PriceQuoteDetails.objects.get(pricequote=price_quote, target_id=target)

        price_quote.price -= price_quote_details.target_price
        price_quote.cost -= price_quote_details.target_cost
        price_quote.gm = ((price_quote.price - price_quote.cost) / price_quote.price)

        price_quote.express_price -= price_quote_details.target_express_price
        price_quote.express_cost -= price_quote_details.target_express_cost
        price_quote.express_gm = ((price_quote.express_price - price_quote.express_cost) / price_quote.express_price)
        price_quote.standard_tat -= price_quote_details.target_standard_tat
        price_quote.express_tat -= price_quote_details.target_express_tat
        price_quote.save()

    def quote_summary_no_costs(self):
        return ProjectQuote(self, include_costs=False, quote_summary=True)

    def quote_summary_standard(self):
        return ProjectQuote(self, speed=STANDARD_SPEED, quote_summary=True)

    def quote_summary_express(self):
        return ProjectQuote(self, speed=EXPRESS_SPEED, quote_summary=True)

    def quote_summary_standard_no_costs(self):
        return ProjectQuote(self, speed=STANDARD_SPEED, include_costs=False, quote_summary=True)

    def quote_summary_express_no_costs(self):
        return ProjectQuote(self, speed=EXPRESS_SPEED, include_costs=False, quote_summary=True)

    def target_price_details(self):
        price_quote = PriceQuote.objects.get_or_none(project=self, active=True)

        target_dict = {}
        for target in self.target_locales.all():
            price_quote_details = PriceQuoteDetails.objects.get_or_none(pricequote=price_quote, target=target)
            if price_quote_details:
                target_dict[target.id] = price_quote_details
        return target_dict

    def project_pricequote(self):
        return PriceQuote.objects.get_or_none(project=self, active=True)

    def project_original_price(self):
        client_discount_standard = client_discount_express = Decimal(0.00)
        project_price_standard = project_price_express = Decimal(0.00)
        original_price_standard = original_price_express = Decimal(0.00)

        pq = self.project_pricequote()
        if pq:
            project_price_standard += pq.price if pq.price else 0
            project_price_express += pq.express_price if pq.express_price else 0

        cd_tq = self.taskquote_set.filter(task__service__service_type__code=DISCOUNT_SERVICE_TYPE).aggregate(Sum('net_price'), Sum('express_net_price'))
        if cd_tq:
            client_discount_standard += cd_tq['net_price__sum'] if cd_tq['net_price__sum'] else 0
            client_discount_express += cd_tq['express_net_price__sum'] if cd_tq['express_net_price__sum'] else 0

        original_price_standard += project_price_standard + (-client_discount_standard)
        original_price_express += project_price_express + (-client_discount_express)

        return original_price_standard, original_price_express

    def job_name_display_name(self):
        length = 90
        job_name = ''
        if self.name:
            job_name = self.name
            if job_name.__len__() > length:
                job_name = self.name[:length] + '...'
        return job_name

    def get_estimate_team_full(self):
        return self.get_ae_team() + self.get_estimates_team()

    def get_team_full(self):
        return self.get_ae_pm_team() + self.get_tsg_team()

    def get_ae_pm_team(self):
        return self.get_pm_team() + list(set(self.get_ae_team()) - set(self.get_pm_team()))

    def get_pm_tsg_team(self):
        return self.get_pm_team() + list(set(self.get_tsg_team()) - set(self.get_pm_team()))

    def get_pm_team(self):
        if self.project_manager:
            return [self.project_manager.email]

        team_members = self.team.filter(role=PM_ROLE)

        if team_members:
            team = [member.contact.email for member in team_members]
        else:
            # Default via contact email for this client
            # FIXME: What should the result be if that value is not set?
            # (via_team_jobs_email is not a required field)
            team = [self.client.via_team_jobs_email]

        return team

    def get_tsg_team(self):
        team_members = self.team.filter(role=TSG_ENG_ROLE)

        if team_members:
            team = [member.contact.email for member in team_members]
        else:
            team = [settings.VIA_TSG_GROUP_EMAIL_ALIAS]

        return team

    def get_estimates_team(self):
        team = [settings.VIA_ESTIMATES_EMAIL_ALIAS]
        return team

    def get_ae_team(self):
        if self.account_executive:
            team_members = self.team.filter(contact=self.account_executive)
        else:
            team_members = self.team.filter(role=AE_ROLE)

        if team_members:
            team = [member.contact.email for member in team_members]
        else:
            team = [self.client.via_team_jobs_email]

        return team

    def project_managers(self):
        if self.project_manager:
            return self.project_manager.mail_link()
        else:
            return u', '.join(p.mail_link() for p in self.team.filter(role=PM_ROLE))

    def primary_pm(self):
        return self.project_manager

    def phi_contact(self):
        if self.account_executive:
            return self.account_executive.email
        else:
            return settings.HEALTHCARE_CONTACT

    def create_team(self):
        # ProjectTeamRole.objects.filter(project=self).delete()

        if self.project_manager:
            ProjectTeamRole.objects.get_or_create(project=self, contact=self.project_manager, role=PM_ROLE)
        if self.account_executive:
            ProjectTeamRole.objects.get_or_create(project=self, contact=self.account_executive, role=AE_ROLE)
        if self.estimator:
            ProjectTeamRole.objects.get_or_create(project=self, contact=self.estimator, role=TSG_ENG_ROLE)

    def assign_primary_pm(self):
        if not self.project_manager:
            r = list(self.team.filter(role=PM_ROLE)[:1])
            if len(r) == 1:
                self.project_manager = r[0].contact
                self.save()
        return True

    def assign_primary_estimator(self):
        if not self.estimator:
            r = list(self.team.filter(role=TSG_ENG_ROLE)[:1])
            if len(r) == 1:
                self.estimator = r[0].contact
                self.save()
        return True

    def assign_primary_account_executive(self):
        if not self.account_executive:
            r = list(self.team.filter(role=AE_ROLE)[:1])
            if len(r) == 1:
                self.account_executive = r[0].contact
                self.save()
        return True

    def get_client_notification_team(self):
        client_id = self.client_id
        rel_clients = CircusUser.objects.filter(account=client_id).order_by('email')
        client_emails = [member.email for member in rel_clients if member.is_active and member.is_client_notification_group()]
        return client_emails

    def get_client_approvers_team(self):
        client_id = self.client_id
        rel_clients = CircusUser.objects.filter(account_id=client_id).order_by('email')
        client_emails = [member.email for member in rel_clients if member.is_active and member.is_approver_group()]
        return client_emails

    def active_access_request(self):
        access_project = self.access_project.all()
        if access_project:
            return [ request.contact for request in access_project ]
                # contact = request.contact.name
            # return access_project
        return False

    def is_credit_card_payment(self):
        return self.payment_details.payment_method == CC_PAYMENT_CHOICE

    def is_corp_account_payment(self):
        return self.payment_details.payment_method == CA_PAYMENT_CHOICE

    def is_manual_estimate(self):
        return self.estimate_type == MANUAL_ESTIMATE

    def is_auto_estimate(self):
        return self.estimate_type == AUTO_ESTIMATE

    def is_queued_status(self):
        return self.status == QUEUED_STATUS

    def is_created_status(self):
        return self.status == CREATED_STATUS

    def is_inestimate_status(self):
        return self.is_queued_status() or self.is_created_status()

    def is_quoted_status(self):
        return self.status == QUOTED_STATUS

    def is_started_status(self):
        return self.status == STARTED_STATUS

    def is_hold_status(self):
        return self.status == HOLD_STATUS

    def is_completed_status(self):
        return self.status == COMPLETED_STATUS

    def is_not_completed_status(self):
        return self.status != COMPLETED_STATUS

    def is_approved_job_status(self):
        return self.is_started_status() or self.is_completed_status()

    def is_canceled_status(self):
        return self.status == CANCELED_STATUS

    def is_normal_display_status(self):
        return self.is_queued_status() or self.is_created_status() or self.is_quoted_status()

    def is_client_quote_status(self):
        return self.is_created_status() or self.is_quoted_status()

    def is_completed_status_tm_update_not_updated(self):
        return self.is_completed_status() and self.kit.has_analysis_code() and self.kit.is_tm_not_updated()

    def show_transitions_header_task(self):
        return self.is_started_status() or self.is_completed_status()

    def show_transitions_header_estimate(self):
        return self.is_inestimate_status() or self.is_quoted_status() or self.is_hold_status() or self.is_canceled_status()

    def can_access_secure_job(self, user):
        try:
            can_access = True
            if self.is_secure_job and not self.client_poc == user:
                can_access = self.secure_job.filter(user=user, account=user.account).count()
            return can_access
        except:
            logger.error("project.can_access_secure_job %s failed for %s.", self.job_number, user, exc_info=True)
            return False

    def can_access_locked_job(self, user):
        try:
            return self.access_project.filter(contact=user, is_access_given=True).count()
        except:
            logger.error("project.can_access_locked_job %s failed for %s.", self.job_number, user, exc_info=True)
            return False

    def can_access_job(self, user):
        try:
            can_access = False
            if user == self.client_poc:
                can_access = True
            elif self.client.manifest.enforce_customer_hierarchy:
                if self.is_secure_job and self.can_access_secure_job(user):
                        can_access = True
                elif self.can_access_locked_job(user):
                    can_access = True
                elif user.can_access_client_job_order():
                    can_access = True
            else:
                # clients without enforce customer hierarchy do not need permissions
                can_access = True
            return can_access
        except:
            logger.error("project.can_access_job %s failed for %s.", self.job_number, user, exc_info=True)
            return False

    def is_phi_secure_client_job(self):
        if self.is_phi_secure_job and self.client.manifest.phi_warning() and self.client.manifest.baa_agreement_for_phi:
            return True
        return False

    def is_via_user_phi_group_enabled(self, user):
        phi_via_user = CircusUser.objects.get_or_none(id=user.id,
                                                      user_type=settings.VIA_USER_TYPE,
                                                      groups__name=PROTECTED_HEALTH_INFORMATION_GROUP)
        if phi_via_user:
            return True
        else:
            return False

    def can_via_user_access_secure_job(self, user):
        can_access = True

        if user.is_superuser:
            return True

        if self.is_phi_secure_client_job():
            # For PHI secure job
            project_access = False
            try:
                project_access = ProjectTeamRole.objects.filter(project_id=self.id,
                                                                contact_id=user.id,
                                                                contact__groups__name=PROTECTED_HEALTH_INFORMATION_GROUP)
            except:
                logger.error("project.can_via_user_access_secure_job %s failed for %s.", self.job_number, user, exc_info=True)
                pass
            if not project_access and not user.is_superuser:
                can_access = False
        elif self.is_secure_job:
            # For Secure jobs
            # Getting the project Team Roles members
            team_member_ids = [team.contact_id for team in self.team.all()]
            if not user.id in team_member_ids and not user.is_superuser:
                can_access = False
        return can_access

    # def calendar_status(self, user):
    def calendar_status(self):
        now = timezone.now()
        if self.is_queued_status():
            return '#4555DB'
        elif self.is_created_status():
            return '#3498DB'
        elif self.is_quoted_status():
            return '#34495E'
        elif self.is_hold_status():
            return '#8B4513'
        elif self.is_started_status() and now > self.due:
            return '#C0392B'
        elif self.is_started_status() and now < self.due:
            return '#27AE60'
        elif self.is_completed_status() and self.delivered and not self.completed:
            return '#706E9B'
        elif self.is_completed_status() and self.completed:
            return '#7F8C8D'
        elif self.is_canceled_status():
            return '#8D807F'
        return '#7F8C8D'

    def job_status_color(self):
        now = timezone.now()
        if self.is_queued_status():
            return 'queued'
        elif self.is_created_status():
            return 'inestimate'
        elif self.is_quoted_status():
            return 'estimated'
        elif self.is_hold_status():
            return 'hold'
        elif self.is_started_status() and now < self.due:
            return 'active'
        elif self.is_started_status() and now > self.due:
            return 'overdue'
        elif self.is_completed_status() and self.delivered and not self.completed:
            return 'delivered'
        elif self.is_completed_status() and self.completed:
            return 'completed'
        elif self.is_canceled_status():
            return 'canceled'
        return 'completed'

    def large_jobs_check(self):
        return self.price(speed=STANDARD_SPEED) >= settings.LARGE_JOB_PRICE

    def get_approvers_list(self):
        return [self.project_manager_approver_id, self.ops_management_approver_id, self.sales_management_approver_id]

    def check_approvers_exists(self):
        return any(self.get_approvers_list())

    def check_approvers_all_set(self):
        return all(self.get_approvers_list())

    def remove_approvals_on_small_job(self):
        self.project_manager_approver_id = None
        self.ops_management_approver_id = None
        self.sales_management_approver_id = None
        self.large_job_approval_timestamp = None
        self.save()

    def large_job_force_manual_estimate(self):
        self.estimate_type = MANUAL_ESTIMATE
        self.status = QUEUED_STATUS
        self.save()

    #######################
    # validations and state checks

    def can_be_quote_completed(self):
        return self.is_inestimate_status() and self.tasks_are_priced() and self.can_be_large_quote_completed()

    def can_be_large_quote_completed(self):
        return not self.large_jobs_check() or (self.large_jobs_check() and self.check_approvers_all_set() and self.is_large_job_approval_timestamp())

    def is_large_job_approval_timestamp(self):
        return self.large_job_approval_timestamp is not None

    def is_sow_available(self):
        return self.client.manifest.is_sow_available and self.tasks_are_priced()

    def tasks_exist_for_target_locale(self, target):
        return self.all_tasks().filter(service__source=self.source_locale, service__target=target)

    def tasks_are_priced(self):
        """Project has at least one task and billable tasks have prices."""
        if not self.kit.is_valid_for_quote():
            return False

        all_tasks_are_priced = False
        for target in self.target_locales.all():
            tasks = self.tasks_exist_for_target_locale(target)
            if len(tasks) and all(task.is_valid() for task in tasks):
                all_tasks_are_priced = True
            else:
                all_tasks_are_priced = False
                break
        return all_tasks_are_priced

    def tasks_service(self):
        """Project has at least one task and billable tasks have prices."""
        li = ""
        for service in self.services.all():
            li = " ".join((li, service.abbreviation + ","))
        li = li.strip(",")
        return li

    def manual_estimate_too_long(self):
        if self.kit.analysis_started and timezone.now() > self.kit.analysis_started + timedelta(seconds=settings.VIA_API_CALL_TIMEOUT_SECONDS):
            return True
        else:
            if not self.kit.analysis_started:
                self.kit.analysis_started = timezone.now()
                self.kit.save()
            return False

    def can_edit_analysis(self):
        # Changing the analysis after the quote is complete would change the
        # price.
        return self.is_created_status()

    def project_restricted_locations(self):
        return self.restricted_locations.all()

    def project_restricted_locations_list(self):
        return self.project_restricted_locations().values_list('country_code', flat=True)

    def can_edit_job(self, user_country):
        # non-secure jobs : can edit all
        # secure jobs : only edit if restricted location has been set and you are in that country/region
        can_edit_job_answer = True
        project_restricted_locations = self.project_restricted_locations_list()
        if self.is_restricted_job and project_restricted_locations.exists() and (user_country not in project_restricted_locations):
            can_edit_job_answer = False
        return can_edit_job_answer

    def can_edit_kit(self):
        if self.is_not_completed_status():
            return True
        return False

    def can_edit_source_files(self):
        if self.is_inestimate_status() or self.is_queued_status():
            return True
        return False

    def can_edit_tasks(self):
        if self.is_inestimate_status():
            return True
        return False

    def can_edit_locales(self):
        return self.can_edit_analysis() or self.can_edit_tasks()

    def can_be_canceled(self):
        return True

    def can_be_hold(self):
        return True

    def can_be_estimated(self):
        return True

    def can_be_manual_estimated(self):
        return True

    def target_locales_count(self):
        return self.target_locales.count()

    def billable_tasks(self, also_related=None):
        tasks = self.all_billable_tasks()
        # Because you generally ask about billable tasks when you're interested in their price,
        # also fetch the necessary fields for price calculation.
        # noinspection PyUnresolvedReferences
        tasks = tasks.select_for_pricing(*(also_related or ()))
        return tasks

    def billable_tasks_per_locale_count(self):
        locale_count = self.target_locales_count() or 1
        billable_tasks_count = self.billable_tasks().count() or 1
        return billable_tasks_count / locale_count

    def all_tasks(self):
        return self.task_set.all()

    def all_root_tasks(self):
        return self.all_tasks().filter(predecessor=None)

    def all_root_tasks_target(self, target):
        return self.all_root_tasks().filter(service__target=target)

    def all_root_tasks_billable(self):
        return self.all_root_tasks().filter(billable=True)

    def all_billable_tasks(self):
        return self.all_tasks().filter(billable=True)

    def all_billable_translation_tasks(self):
        return self.all_billable_tasks().filter(service__service_type__translation_task=True)

    def all_billable_nontranslation_tasks(self):
        return self.all_billable_tasks().filter(service__service_type__translation_task=False)

    def all_billable_translation_tasks_not_min_job_surcharge(self):
        return self.all_billable_translation_tasks().filter('')

    def all_workflow_tasks(self):
        return self.all_tasks().filter(service__service_type__workflow=True)

    def all_workflow_translation_tasks(self):
        return self.all_workflow_tasks().filter(service__service_type__translation_task=True)

    def all_workflow_translation_tasks_target(self, target):
        return self.all_workflow_translation_tasks().filter(service__target_id=target)

    def all_workflow_target_tasks(self, target_locale):
        return self.task_set.filter(service__service_type__workflow=True, service__target=target_locale)

    def all_workflow_billable_tasks(self):
        return self.all_workflow_tasks().filter(billable=True)

    def all_workflow_billable_translation_tasks(self):
        return self.all_workflow_billable_tasks().filter(service__service_type__translation_task=True)

    def all_workflow_billable_nontranslation_tasks(self):
        return self.all_workflow_billable_tasks().filter(service__service_type__translation_task=False)

    def check_po_approved(self):
        return all(task.check_po_approved() for task in self.all_workflow_billable_nontranslation_tasks())

    def all_tasks_complete(self):
        return all(task.is_complete() for task in self.all_workflow_tasks())

    def all_tasks_none_active(self):
        return all(task.is_active_status() is False for task in self.all_workflow_tasks())

    def all_billable_tasks_rated(self):
        return all(task.is_rated() for task in self.all_workflow_billable_tasks())

    def workflow_root_tasks(self):
        return self.all_workflow_tasks().filter(predecessor=None, parent=None)

    def workflow_root_sub_tasks(self):
        return self.all_workflow_tasks().filter(~Q(parent=None), ~Q(predecessor=None)).order_by('id')

    def workflow_root_tasks_billable(self):
        return self.all_workflow_billable_tasks().filter(predecessor=None)

    def workflow_root_tasks_target(self, target=None):
        return self.workflow_root_tasks().filter(service__target=target)

    def workflow_root_tasks_billable_target(self, target=None):
        return self.workflow_root_tasks_billable().filter(service__target=target)

    def workflow_root_and_sub_tasks(self):
        return self.all_workflow_tasks().filter(predecessor=None)

    def workflow_root_tasks_all_have_input_file(self):
        root_tasks_list = self.workflow_root_tasks()
        have_input_files = all(task.has_input_file() for task in root_tasks_list)
        return have_input_files

    def show_copy_loc_kit(self):
        return self.kit.is_valid_for_start() and not self.workflow_root_tasks_all_have_input_file()

    def has_workflow_sub_tasks(self):
        return any(self.workflow_root_sub_tasks())

    def workflow_root_tasks_target_locale(self, target_locale):
        return self.workflow_root_tasks().filter(service__target=target_locale)

    def workflow_root_and_sub_tasks_target_locale(self, target_locale):
        return self.workflow_root_and_sub_tasks().filter(service__target=target_locale)

    def workflow_root_tasks_target_locale_copy_lockit(self, target_locale):
        try:
            action_completed = True
            root_tasks_list = self.workflow_root_and_sub_tasks_target_locale(target_locale)
            for task in root_tasks_list:
                if task.is_translation():
                    action_completed = task.copy_trans_kit_assets_from_lockit()
                else:
                    action_completed = task.copy_task_localized_assets_setup()
            return action_completed
        except:
            return ERROR, _(u'Error occurred during Loc Kit copy process')

    def workflow_root_tasks_target_locale_remove_assets(self, target_locale):
        try:
            root_tasks_list = self.workflow_root_and_sub_tasks_target_locale(target_locale)
            for task in root_tasks_list:
                if task.is_translation():
                    task.remove_trans_kit_assets()
                else:
                    task.remove_task_localized_assets()

            return True
        except:
            return ERROR, _(u'Error occurred during Task Loc Kit removal process')

    def workflow_root_tasks_target_locale_remove_reference_file(self, target_locale):
        try:
            for task in self.workflow_root_tasks_target_locale(target_locale):
                if task.is_translation():
                    task.reference_file = None
                    task.save()
            return True
        except:
            return ERROR, _(u'Error occurred during Task Loc Kit removal process')

    def manual_tm_file_imported(self):
        if self.is_completed_status_tm_update_not_updated():
            return True
        if self.is_completed_status() and self.kit.has_analysis_code():
            for task in self.all_workflow_tasks():
                if task.is_translation() \
                        and task.trans_kit.tm_file_updated_at is not None \
                        and self.kit.tm_update_completed < task.trans_kit.tm_file_updated_at:
                    return False
        return True

    def can_be_reactivated(self):
        return True

    def is_status_delivered(self):
        # self.delivered is the delivery date
        # self.completed is the completion date
        return self.status == COMPLETED_STATUS and self.delivered and not self.completed

    def get_status(self):
        if self.is_status_delivered():
            return DELIVERED_STATUS
        return self.status

    def is_invoiced(self):
        return False

    def is_overdue(self):
        return self.is_overdue_job() or self.is_overdue_estimate()

    def is_overdue_job(self):
        return self.is_started_status() and not self.delivered and self.due and self.due < timezone.now()

    def is_overdue_estimate(self):
        return self.is_created_status() and not self.quoted and self.quote_due and self.quote_due < timezone.now()

    def has_overdue_tasks(self):
        return any(task.is_overdue() for task in self.all_tasks())

    def has_unassigned_tasks(self):
        # only care if Billable Workflow task is not assigned.  PM sometimes leave non-billable tasks unassigned
        return self.is_started_status() and not all(task.assigned_to for task in self.all_workflow_billable_tasks())

    def has_tasks(self):
        return self.all_tasks().exists()

    def is_restricted_and_english_target(self):
        if self.is_restricted_job and ENGLISH_LANG in self.get_target_locale_name_list() :
            return True
        return False

    def warnings(self):
        if self.is_overdue_job():
            return _(u'Job Overdue!')
        elif self.is_overdue_estimate():
            return _(u'Estimate Overdue!')
        elif self.has_overdue_tasks():
            return _(u'Tasks overdue!')
        elif self.has_unassigned_tasks():
            return _(u'Tasks need assignment!')
        elif self.show_start_workflow():
            return _(u'Workflow is not started!')
        elif self.is_completed_status_tm_update_not_updated():
            return _(u'Job Completed, but TM update needed!')
        # todo other issues?
        else:
            return None

    def warnings_icon(self):
        if self.is_overdue_job():
            return _(u'fa fa-exclamation-circle')
        elif self.is_overdue_estimate():
            return _(u'fa fa-bell-o')
        elif self.has_overdue_tasks():
            return _(u'fa fa-frown-o')
        elif self.has_unassigned_tasks():
            return _(u'fa fa-meh-o')
        elif self.show_start_workflow():
            return _(u'fa fa-magic')
        elif self.is_completed_status_tm_update_not_updated():
            return _(u'fa fa-language')
        else:
            return None

    def client_warnings(self):
        if self.is_started_status() and not self.delivered and self.due and self.due < timezone.now():
            return _(u'Job Overdue!')
        elif self.is_created_status() and not self.quoted and self.quote_due and self.quote_due < timezone.now():
            return _(u'Estimate Overdue!')
        else:
            return None

    def get_overdue_tasks(self, assigned_to):
        return self.all_tasks().filter(assignee_content_type=ContentType.objects.get_for_model(Account),
                                    assignee_object_id=assigned_to.id,
                                    due__lt=timezone.now())\
            .exclude(status=TASK_COMPLETED_STATUS)

    #######################
    # calculations
    def get_target_locale_name_list(self):
        return ", ".join(sorted(set([target.description for target in self.target_locales.all()])))

    def language_count(self):
        return self.target_locales.all().count()

    def is_target_pricing_basis(self):
        if self.pricing_basis == PricingBasis.objects.get(code=TARGET_BASIS):
            return True
        else:
            return False

    def is_standard_speed(self):
        return self.project_speed == STANDARD_SPEED

    def is_express_speed(self):
        return self.project_speed == EXPRESS_SPEED

    def price(self, speed=None):
        # todo don't do this calc every time, just keep a total and update when something changes
        price = None
        price_object = self.project_pricequote()
        if price_object:
            if speed == EXPRESS_SPEED:
                price = price_object.express_price
            elif speed == STANDARD_SPEED:
                price = price_object.price
            else:
                price = price_object.price if self.is_standard_speed() else price_object.express_price
        return price

    def has_price(self):
        project_price = self.price()
        logger.info(u'Project.has_price : {0} : Price: {1}!'.format(self.job_number, project_price))
        if project_price is None or project_price <= 0:
            return False
        else:
            return True

    def standard_duration(self):
        return self.duration(STANDARD_SPEED)

    def express_duration(self):
        return self.duration(EXPRESS_SPEED)

    def duration(self, speed=None):
        """ Calculate project duration for speed (express or standard). If not specified, use project's default """
        if not speed:
            speed = self.project_speed
        longest_found = 0
        for task in self.workflow_root_tasks():
            task_duration = task.duration_with_children(speed)
            if task_duration > longest_found:
                longest_found = task_duration
        return longest_found

    def percent_complete(self):
        return 0

    def show_start_workflow(self):
        return (
            self.is_started_status() and
            any(task.is_created() for task in self.workflow_root_tasks()))

    def start_workflow(self, user=None):
        if not self.kit.is_valid_for_start():
            return ERROR, _(u'Cannot Start Workflow! Please add Files > Loc Kits in order to continue.')

        auto_start_workflow = True
        jams_update = False

        if self.start_project(auto_start_workflow, jams_update):
            return SUCCESS, _(u'Workflow has been started')
        else:
            return ERROR, _(u'Error occurred during workflow start')

    def show_pickup_post_process_tasks(self):
        return self.is_started_status() and any(task.is_unassigned() for task in self.all_tasks().filter(service__service_type=ServiceType.objects.get(code=POST_PROCESS_SERVICE_TYPE)))

    def pickup_post_process_tasks(self, user=None):
        try:
            new_assignments = 0
            # post process tasks
            for post_process_task in self.all_tasks().filter(service__service_type=ServiceType.objects.get(code=POST_PROCESS_SERVICE_TYPE)):
                new_assignments += 1
                post_process_task.assigned_to = user
                post_process_task.nontranslationtask.unit_cost = None
                post_process_task.nontranslationtask.vendor_minimum = None
                post_process_task.nontranslationtask.save()
                post_process_task.save()

            message = _(u'{0} tasks assigned.').format(new_assignments)

            if new_assignments:
                return SUCCESS, message
            return WARNING, message
        except:
            return ERROR, _(u'Errors occurred during pickup post process')

    def show_pickup_final_approval_tasks(self):
        return self.is_started_status() and any(task.is_unassigned() for task in self.all_tasks().filter(service__service_type=ServiceType.objects.get(code=FINAL_APPROVAL_SERVICE_TYPE)))

    def pickup_final_approval_tasks(self, user=None):
        try:
            new_assignments = 0
            # final approval tasks
            for approval_task in self.all_tasks().filter(service__service_type=ServiceType.objects.get(code=FINAL_APPROVAL_SERVICE_TYPE)):
                new_assignments += 1
                approval_task.assigned_to = user
                approval_task.nontranslationtask.unit_cost = None
                approval_task.nontranslationtask.vendor_minimum = None
                approval_task.nontranslationtask.save()

                if user:
                    approval_task.accepted_timestamp = timezone.now()
                else:
                    approval_task.accepted_timestamp = None
                approval_task.save()

            message = _(u'{0} tasks assigned.').format(new_assignments)

            if new_assignments:
                return SUCCESS, message
            return WARNING, message
        except:
            return ERROR, _(u'Errors occurred during pickup post process')

    def reset_project_timestamps(self):
        client_manifest_ignore_holiday_flag = self.client.manifest.ignore_holiday_flag
        self.ignore_holiday_flag = client_manifest_ignore_holiday_flag
        self.quote_due = add_delta_business_days(timezone.now(), timedelta(days=1), client_manifest_ignore_holiday_flag)
        self.quoted = None
        self.started_timestamp = None
        self.due = None
        self.delivered = None
        self.completed = None
        return self.save()

    def delete_project_tasks(self):
        try:
            for task in self.all_tasks().order_by('predecessor', '-id'):
                try:
                    task.delete_task()
                except:
                    task.delete()
            return True
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            print tb
            mail_admins('[project.delete_project_tasks]: failed',
                        'project = {0}.\n{1}'.format(self, tb))
            return False

    def reset_project_from_modify_scope(self):
        try:
            self.kit.delete_analysis_files()
            self.kit.delete_localetranslationkits()
            self.kit.remove_analysis_code()
            self.delete_project_tasks()
            self.estimate_type = AUTO_ESTIMATE
            self.status = QUEUED_STATUS
            self.save()
            self.clean_target_locales()
            return True
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            print tb
            mail_admins('[reset_project_from_modify_scope]: failed',
                        'project = {0}.\n{1}'.format(self, tb))
            return False

    ########################
    # callbacks
    def start_project(self, auto_start_workflow=False, jams_update_needed=True):
        # set start and end for project and tasks
        is_hourly_schedule = self.client.manifest.is_hourly_schedule

        if not self.started_timestamp:
            self.started_timestamp = timezone.now()
            self.due = max(set_task_dates(task, self.started_timestamp, self.ignore_holiday_flag, is_hourly_schedule) for task in self.workflow_root_tasks())
            self.save()
        else:
            if any(not task.scheduled_start_timestamp for task in self.all_workflow_billable_tasks()):
                self.due = max(set_task_dates(task, self.started_timestamp, self.ignore_holiday_flag, is_hourly_schedule) for task in self.workflow_root_tasks())
                self.save()

        # update JAMS Job data
        if jams_update_needed and settings.VIA_JAMS_INTEGRATION and self.client.account_number:
            try:
                if not update_jams_job(self):
                    # todo send email to PM about Job not updated in JAMS
                    logger.error("project.start_project.update_jams_job() %s failed.", self.job_number, exc_info=True)
                    pass
            except:
                logger.error("project.start_project.update_jams_job() %s errored.", self.job_number, exc_info=True)
                pass

        # :type: LocalizationKit
        kit = self.kit

        # Do we have a loc kit?
        if kit.is_valid_for_start():
            return self._callback_got_loc_kit(auto_start_workflow)
        elif self.is_phi_secure_job:
            logger.info("PHI Secure Job Project %s#%s loc kit #%s does not kick off Deja Vu automatically.", self.job_number, self.id, kit.id)
            return False
        elif kit.can_auto_prep_kit():
            callback = _cb_project_got_loc_kit.si(self.id, auto_start_workflow)
            result = kit.queue_pre_translation(call_prep_kit=True, callback=callback)
            return result
        else:
            # TODO: email PM we don't have loc kit
            logger.error("Project %s#%s loc kit #%s is not valid and we cant use automatic prep_kit.", self.job_number, self.id, kit.id)
            return False

    def _callback_got_loc_kit(self, auto_start_workflow):
        action_completed = True
        for task in self.workflow_root_tasks():
            if task.is_translation():
                action_completed = task.copy_trans_kit_assets_from_lockit()
            else:
                action_completed = task.copy_task_localized_assets_setup()

        if not auto_start_workflow:
            # if any task is not ready, bail out. Unless someone hit the
            # Start Workflow button, which overrides auto_start_workflow to True.
            if not all(task.is_workflow_ready() for task in self.all_tasks()):
                logger.info("Project %s#%s start_project _callback_got_loc_kit does not have all tasks ready.", self.job_number, self.id)
                # todo send email to PM about Job workflow not starting
                return False

        for task in self.all_workflow_billable_tasks():
            if not task.predecessor_id:
                if auto_start_workflow:
                    task.activate()
            else:
                if task.assignee_content_type == ContentType.objects.get_for_model(Account):
                    notify_assigned_to_task_assigned(task)

        return True

    ########################
    # actions
    def can_create_jams_estimate(self):
        return settings.VIA_JAMS_INTEGRATION and \
            not self.jams_estimateid and \
            self.client.account_number

    def create_jams_estimate(self, rush_estimate=False, user=None):
        from tasks.make_tasks import convert_project_to_manual_tasks

        if self.is_auto_estimate():
            self.estimate_type = MANUAL_ESTIMATE
            self.save()
            convert_project_to_manual_tasks(self)
        created, jams_estimateid = create_jams_job_estimate(self, rush_estimate)
        if created:
            self.jams_estimateid = jams_estimateid
            self.save()
            project_manual_quote_needed_via(self)
            return SUCCESS, _(u'JAMS Estimate # {0} created.').format(jams_estimateid)
        else:
            # todo send email to PM about Estimate not updated in JAMS
            return ERROR, _(u'JAMS Estimate creation failure.')

    def assign_team(self, user=None):
        client_team = ClientTeamRole.objects.filter(client=self.client)
        if not client_team:
            client_team = ClientTeamRole.objects.filter(client=self.client.parent)

        for member in client_team:
            ProjectTeamRole.objects.get_or_create(project=self, contact=member.contact, role=member.role)

        self.create_team()
        self.assign_primary_pm()
        self.assign_primary_estimator()
        self.assign_primary_account_executive()

        return SUCCESS, _(u'Project team assigned')

    def get_assigned_team(self):
        return ProjectTeamRole.objects.filter(project_id=self.id)

    def get_phi_assigned_team(self, user_type):
        user_model = get_user_model().objects
        if user_type == settings.CLIENT_USER_TYPE:
            client_id = self.client_id
            children_list = []
            children_list.append(client_id)

            for child in Account.objects.filter(parent=client_id):
                        children_list.append(child.id)

            phi_secure_job_users = user_model.filter(Q(id=self.client_poc_id) | Q(groups__name=PROTECTED_HEALTH_INFORMATION_GROUP),
                                                     user_type=user_type, account_id__in=children_list).distinct()
        else:
            # team_list = []
            phi_secure_job_users = ProjectTeamRole.objects.filter(project_id=self.id,
                                                                  contact__user_type=settings.VIA_USER_TYPE,
                                                                  contact__groups__name=PROTECTED_HEALTH_INFORMATION_GROUP)
            # for users in project_access:
            #     team_list.append(users.contact_id)
            # phi_secure_job_users = user_model.filter(Q(id__in=team_list) | Q(is_superuser=True, groups__name=PROTECTED_HEALTH_INFORMATION_GROUP))
        return phi_secure_job_users

    def get_assigned_team_comments(self):
        return self.get_assigned_team().filter(Q(role=PM_ROLE) | Q(role=AE_ROLE))

    def generate_loc_kit_analysis(self, user=None):
        return make_project_loc_kit_analysis(self)

    def clean_loc_kit_analysis(self, user=None):
        # delete FileAnalysis for all removed Source and Target Locales
        self.kit.analysis_files().filter(
            (~Q(source_locale=self.source_locale)) |
            (~Q(target_locale__in=self.target_locales.all()))
        ).delete()

    def set_rates_and_prices(self, user=None):
        return set_project_rates_and_prices(self)

    def set_create_po_needed(self, check):
        try:
            for task in self.all_workflow_billable_nontranslation_tasks():
                task.create_po_needed = check
                task.save()

            return SUCCESS, _(u'Set the Delay PO creation for Non-translation tasks')
        except:
            return ERROR, _(u'Problem setting Delay PO creation for Non-translation tasks')

    def is_delay_job_po(self):
        return self.delay_job_po

    def set_rates(self, user=None):
        return set_project_rates(self)

    def set_prices(self, user=None):
        return set_project_prices(self)

    def assign_tasks(self, user=None):
        return assign_project_tasks(self)

    def generate_tasks(self, user=None, use_globals=True):
        import tasks.make_tasks
        self.clean_pricing()
        return tasks.make_tasks.make_project_tasks(self, use_globals)

    def generate_default_service_global_quantity(self, user=None):
        import tasks.make_tasks
        return tasks.make_tasks.default_global_service_quantity(self)

    def add_fa_service(self, services):
        fa_service = ServiceType.objects.get_or_none(code=FINAL_APPROVAL_SERVICE_TYPE)
        services.append(fa_service)
        return services

    def calc_project_tat(self, price_quote=None):
        standard_tat = settings.TAT_DAYS_STANDARD
        express_tat = settings.TAT_DAYS_EXPRESS

        if not price_quote:
            price_quote = self.project_pricequote()

        for target in self.target_locales.all():
            price_quote_details = PriceQuoteDetails.objects.get_or_none(pricequote=price_quote, target=target)
            if price_quote_details:
                if price_quote_details.target_standard_tat > standard_tat:
                    standard_tat = price_quote_details.target_standard_tat
                if price_quote_details.target_express_tat > express_tat:
                    express_tat = price_quote_details.target_express_tat
        return standard_tat, express_tat

    def get_project_tat(self, price_quote=None):
        if not price_quote:
            price_quote = self.project_pricequote()
        return price_quote.standard_tat, price_quote.express_tat

    def save_service_global_quantity(self, quantity_dic):
        psg = ProjectServicesGlobal.objects.filter(project=self)

        service_list = [service for service in self.services.all() if service.translation_task is False]
        services = self.add_fa_service(service_list)
        for service in services:

            service_global_object, created = psg.get_or_create(project=self, servicetype=service)
            if service_global_object and str(service.code) in quantity_dic:
                if quantity_dic[str(service.code)][0]:
                    service_global_object.quantity = quantity_dic[str(service.code)][0]
                if quantity_dic[str(service.code)][1]:
                    service_global_object.standard_days = quantity_dic[str(service.code)][1]
                if quantity_dic[str(service.code)][2]:
                    service_global_object.express_days = quantity_dic[str(service.code)][2]
                if service_global_object.quantity or service_global_object.standard_days or service_global_object.express_days:
                    service_global_object.save()

    def clean_pricing(self):
        from tasks.models import TaskAssetQuote

        PriceQuoteDetails.objects.filter(pricequote__project=self).delete()
        self.pricequote_set.all().delete()
        self.taskquote_set.all().delete()
        TaskAssetQuote.objects.filter(task__project=self).delete()

    def clean_tasks(self):
        """Remove any tasks which don't match the current source and targets."""
        self.all_tasks().exclude(service__source=self.source_locale).delete()
        self.all_tasks().exclude(service__target__in=self.target_locales.all()).delete()

    def delete_all_tasks(self):
        self.all_tasks().delete()

    def is_due_date_changed(self, pro_id, date_changed=None):
        result = False
        if date_changed is not None:
            self.li.append(pro_id)
        else:
            if pro_id in self.li:
                result = True
        return result

    def set_job_status_completed_offline(self, user=None):
        try:
            for task in self.all_tasks():
                task.accepted_timestamp = timezone.now()
                task.started_timestamp = timezone.now()
                task.completed_timestamp = timezone.now()
                task.status = TASK_COMPLETED_STATUS
                task.save()

            if self.all_tasks_complete():
                self.transition(COMPLETED_STATUS)

            self.completed = timezone.now()
            self.save()
            return SUCCESS, _(u'Project was Completed Offline')

        except Exception, error:
            logger.error("project.set_job_status_completed_offline() failed.", exc_info=True)
            return WARNING, _(u'Project was not set to Completed Status')

    def show_set_job_status_completed_offline(self):
        return self.is_started_status() and not self.all_tasks_complete()

    def reschedule_due_dates(self, user=None, task_start=None, date_changed=None):
        """Reset the due date for this project after rescheduling tasks.
        Task start and end dates will be reset based on the project start date and the tasks' current duration.
        """
        is_hourly_schedule = self.client.manifest.is_hourly_schedule
        tasks_due_date = None

        if task_start:
            start_time = task_start.scheduled_start_timestamp
        else:
            start_time = self.started_timestamp

        if start_time:
            head_tasks = self.workflow_root_tasks()
            if not head_tasks:
                return ERROR, _(u'No tasks defined.')

            if date_changed == "Due":
                tasks_due_date = set_task_dates(task_start, start_time, self.ignore_holiday_flag, is_hourly_schedule, task_start.due)
            elif date_changed == "Scheduled_start":
                tasks_due_date = set_task_dates(task_start, start_time, self.ignore_holiday_flag, is_hourly_schedule)
                if task_start.predecessor is None:
                    self.started_timestamp = task_start.scheduled_start_timestamp
            else:
                tasks_due_date = max(set_task_dates(task, start_time, self.ignore_holiday_flag, is_hourly_schedule) for task in head_tasks)

            if self.due is None and tasks_due_date:
                self.due = max(set_task_dates(task, start_time,
                                self.ignore_holiday_flag, is_hourly_schedule)for task in head_tasks)

            self.save()

            if self.has_workflow_sub_tasks():
                self.reschedule_due_dates_sub_tasks(self)

            due_msg = defaultfilters.date(self.due)
            tasks_due_date_msg = defaultfilters.date(tasks_due_date)

            if tasks_due_date > self.due:
                return ERROR, _(u'Original Project Due Date: {0} - Latest Tasks Workflow Due Date: {1}'.format(due_msg, tasks_due_date_msg))

            if due_msg:
                return SUCCESS, _(u'Project Due Date: {0}'.format(due_msg))
        return WARNING, _(u'Project not Active yet.')

    def show_reschedule_due_dates(self):
        return self.is_started_status() and not self.all_tasks_complete()

    def reschedule_due_dates_sub_tasks(self, project):
        # Sub-tasks should be scheduled hourly every time
        is_hourly_schedule = True
        head_sub_tasks = project.workflow_root_sub_tasks()
        for task in head_sub_tasks:
            set_task_dates(task, task.parent.scheduled_start_timestamp, project.ignore_holiday_flag, is_hourly_schedule)
        return True

    def generate_localetranslationkit(self, user=None):
        return make_localetranslationkit(self)

    def clean_localetranslationkit(self):
        return purge_old_localetranslationkit(self)

    def clean_target_locales(self):
        try:
            # in case of target locale deletion, delete all obsolete LocaleTranslationKit and FileAnalysis
            self.clean_localetranslationkit()
            self.clean_loc_kit_analysis()
            self.clean_tasks()

            # in case new language, need to generate base analysis
            self.generate_localetranslationkit()
            self.generate_loc_kit_analysis()

            # Clear Cache
            from shared.utils import clear_cache
            clear_cache()

            return True
        except Exception, error:
            logger.error("project.clean_target_locales() failed.", exc_info=True)
            return False

    def pre_translate_and_prep_kit(self, user=None, remove_current_files=True, target=None):
        if remove_current_files:
                translation_task_remove_current_files(self.id)
        callback = ltk_to_tasks.si(self.id)
        self.kit.queue_pre_translation(call_prep_kit=True, callback=callback, target=target)
        return SUCCESS, _(u'Sent kit for pretranslate and prep, may take a minute or two.')

    # def pre_translate_kit(self, user=None, remove_current_files=True):
    #     if remove_current_files:
    #             translation_task_remove_current_files(self.id)
    #     self.kit.queue_pre_translation(call_prep_kit=False, callback=None)
    #     return SUCCESS, _(u'Sent kit for pretranslate, may take a minute or two.')

    # def prep_localization_kit(self, user=None, target=None, remove_current_files=True):
    #     if remove_current_files:
    #             translation_task_remove_current_files(self.id)
    #     callback = ltk_to_tasks.si(self.id)
    #     self.kit.queue_prep_kit(self.kit, lk_id=self.kit.id, callback=callback, target=target)
    #     return SUCCESS, _(u'Sent kit for prep, may take a minute or two.')

    def add_to_tm_kit(self, user=None):
        self.kit.queue_add_to_tm()
        return SUCCESS, _(u'Sent kit for Add to Translation Memory update, may take a minute or two.')

    def copy_localization_translation_kit_to_tasks(self, user=None):
        ltk_copied = ltk_to_tasks(self.id)

        if ltk_copied and not self.show_copy_loc_kit():
            return SUCCESS, _(u'Loc Kit(s) copied to root tasks.')
        else:
            return WARNING, _(u'Loc Kit(s) not copied to root tasks.')

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):

        if not self.kit:
            kit = LocalizationKit.objects.create()
            self.kit = kit

        if not self.payment_details:
            payment_detail = ProjectPayment.objects.create()
            self.payment_details = payment_detail

        obj = super(Project, self).save(force_insert, force_update, using, update_fields)

        if not self.job_number and self.id:
            # todo get Job Number from JAMS API
            # self.job_number = "{0}T{1}".format(str(50000 + self.id), date.today().year % 1000)
            self.job_number = str(self.id)
            obj = super(Project, self).save()
        return obj

    #####################
    # state machine features

    def always_show_action(self):
        return True

    def valid_actions(self):
        return self.machine.get_valid_actions()

    def invalid_actions(self):
        return self.machine.get_invalid_actions()

    def actions(self):
        # return self.machine.get_actions()
        return self.machine.get_valid_actions()

    def valid_transitions(self):
        return self.machine.get_valid_transitions()

    def invalid_transitions(self):
        return self.machine.get_invalid_transitions()

    def transition(self, target_state_name):
        state = self.machine.transition_to(target_state_name)
        callback = getattr(self, '_transition_' + state.name)
        return callback()

    # _transition_* are triggered following Project.transition()
    def _transition_queued(self):
        pass

    def _transition_created(self):
        pass

    def _transition_hold(self):
        pass

    def _transition_quoted(self):
        self.quoted = timezone.now()
        if not self.quote_due:
            self.quote_due = timezone.now()
        self.save()
        if self.approved:
            # if pre-approved by client need to get started
            self.transition(STARTED_STATUS)
        else:
            project_quote_ready(self)
            if settings.SALESFORCE_ENABLED and self.salesforce_opportunity_id:
                # update the Opportunity with the new quote
                # Warning: this will clobber any SalesforceOpportunity fields
                #    we use, including Description.
                try:
                    SalesforceOpportunity.objects.create_for_project(self)
                except SalesforceError:
                    logger.error("transition_quoted SalesforceError", exc_info=True)

    def _transition_started(self):
        self.delivered = None
        self.completed = None
        self.approved = True
        self.save()
        notify_new_job_ordered(self)
        if settings.SALESFORCE_ENABLED:
            try:
                SalesforceOpportunity.objects.create_for_project(self)
            except SalesforceError:
                logger.error("transition_started SalesforceError", exc_info=True)

    def _transition_completed(self):
        # The state with COMPLETED_STATUS is labeled "Delivered"
        self.delivered = timezone.now()
        # This doesn't currently have the notify call here. Of the things that
        # do transition(COMPLETED_STATUS),
        #     TaskUpdateView does notify,
        #     VendorTaskDetailView doesn't,
        #     ApproveTask does, and also notifies for cases where there is
        #         no transition (re-delivery).
        self.save()

    def _transition_closed(self):
        pass

    def _transition_canceled(self):
        self.all_tasks().update(status=TASK_CANCELED_STATUS)
        self.approved = False
        self.save()
        notify_client_job_canceled(self)

    ##############
    # deliveries

    def has_deliveries(self):
        from tasks.models import TaskLocalizedAsset
        return TaskLocalizedAsset.objects.filter(
            task__project_id=self.id,
            task__service__service_type__code=FINAL_APPROVAL_SERVICE_TYPE,
            task__status=TASK_COMPLETED_STATUS
        ).count() > 0

    def deliveries(self):
        from tasks.models import TaskLocalizedAsset
        target_locales = self.target_locales.all()
        source_files = self.kit.source_files()
        completed_review_assets = TaskLocalizedAsset.objects.filter(
            task__project_id=self.id,
            task__service__service_type__code=FINAL_APPROVAL_SERVICE_TYPE,
            task__status=TASK_COMPLETED_STATUS
        )
        deliveries = []
        for f in source_files:
            row = {
                'source': f,
                'task_assets': []
            }
            for locale in target_locales:
                try:
                    delivery = next(t for t in completed_review_assets if t.task.service.target_id == locale.id and t.source_asset_id == f.id)
                except:
                    delivery = None
                row['task_assets'].append(delivery)
            deliveries.append(row)
        return deliveries

    def all_deliveries_complete(self):
        from tasks.models import TaskLocalizedAsset
        deliveries = TaskLocalizedAsset.objects.filter(
            task__project_id=self.id,
            task__service__service_type__code=FINAL_APPROVAL_SERVICE_TYPE,
            task__status=TASK_COMPLETED_STATUS
        ).count()
        delivered = TaskLocalizedAsset.objects.filter(
            task__project_id=self.id,
            task__service__service_type__code=FINAL_APPROVAL_SERVICE_TYPE,
            task__status=TASK_COMPLETED_STATUS,
            downloaded__isnull=False
        ).count()
        return delivered == deliveries

    @permalink
    def get_absolute_url(self):
        return 'via_job_detail_overview', [self.id]

    def __unicode__(self):
        return u'{0}: {1}'.format(self.job_number, self.name)

    #################
    # accounting
    def orders(self):
        invoices = self.invoice_set
        return invoices.filter(order_amount__gt=0)

    def original_order_amount(self):
        orders = self.orders()
        if orders:
            original = orders.order_by('id')[0]
            return original.order_amount
        return 0

    def sum_orders(self):
        orders = self.orders()
        total = 0
        for order in orders:
            total += order.order_amount
        return total

    def via_invoices(self):
        # return all invoices with invoice_amount, not order_amount
        return self.invoice_set.filter(invoice_amount__gt=0)

    def paid_via_invoices(self):
        via_invoices = self.via_invoices()
        return via_invoices.filter(billing_paid=True)

    def sum_via_invoices_all(self):
        invoices = self.via_invoices()
        total = 0
        for invoice in invoices or []:
            total += invoice.invoice_amount
        return total

    def sum_via_invoices_billed(self):
        invoices = self.via_invoices()
        invoices = invoices.filter(ok_to_invoice=True)
        total = 0
        for invoice in invoices or []:
            total += invoice.invoice_amount
        return total


class ProjectAccess(models.Model):

    ACCESS_CHOICES = (
        (True, u'Access given'),
        (False, u'No Access'),
    )
    project = models.ForeignKey(Project, related_name='access_project')
    contact = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='access_team')
    is_access_given = models.BooleanField(choices=ACCESS_CHOICES, default=False)

    def __unicode__(self):
        return u'{0}'.format(self.project)


class SecureJobAccess(models.Model):

    ACCESS_CHOICES = (
        (True, u'Access given'),
        (False, u'No Access'),
    )
    project = models.ForeignKey(Project, related_name='secure_job')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='secure_job_team')
    account = models.ForeignKey(Account, related_name='member_account')
    is_access_given = models.BooleanField(choices=ACCESS_CHOICES, default=False)

    def mail_link(self):
        return self.user.mail_link()

    def __unicode__(self):
        return u'{0}'.format(self.project)


class ProjectServicesGlobal(models.Model):
    project = models.ForeignKey(Project, related_name='service_global')
    servicetype = models.ForeignKey(ServiceType, related_name='service_globaltype')
    quantity = models.DecimalField(max_digits=19, decimal_places=2, blank=True, null=True)
    standard_days = models.DecimalField(decimal_places=2, default=0, max_digits=6)
    express_days = models.DecimalField(decimal_places=2, default=0, max_digits=6)

    objects = ProjectServicesGlobalManager()


class ProjectJobOptions(models.Model):
    project = models.OneToOneField(Project, related_name='project', blank=True, null=True)
    editable_source = models.NullBooleanField(default=False, blank=True, null=True)
    recreation_source = models.NullBooleanField(default=False, blank=True, null=True)
    translation_unformatted = models.NullBooleanField(default=False, blank=True, null=True)
    translation_billingual = models.NullBooleanField(default=False, blank=True, null=True)

    objects = ProjectJobOptionsManager()


@shared_task
def _cb_project_got_loc_kit(project_id, auto_start_workflow):
    project = Project.objects.select_related().get(id=project_id)
    # noinspection PyProtectedMember
    return project._callback_got_loc_kit(auto_start_workflow)


@shared_task
def ltk_to_tasks(project_id):
    try:
        action_completed = True
        project = Project.objects.select_related().get(id=project_id)
        root_tasks_list = project.workflow_root_tasks()
        if root_tasks_list:
            for task in root_tasks_list:
                if task.is_translation():
                    action_completed = task.copy_trans_kit_assets_from_lockit()
                else:
                    action_completed = task.copy_task_localized_assets_setup()
                logger.info(u'Task %s ltk_to_tasks. action_completed %s.', task, str(action_completed))
        return action_completed
    except Exception:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        logger.error("ltk_to_tasks error", exc_info=True)
        return False


@shared_task
def translation_task_remove_current_files(project_id):
    project = Project.objects.select_related().get(id=project_id)
    project.kit.remove_localetranslationkits__translation_file()
    for task in project.workflow_root_tasks():
        if task.is_translation():
            task.remove_trans_kit_assets()
        else:
            task.remove_task_localized_assets()


class ProjectTeamRole(models.Model):
    project = models.ForeignKey(Project, related_name='team')
    contact = models.ForeignKey(settings.AUTH_USER_MODEL)
    role = models.CharField(choices=CLIENT_TEAM_ROLES, max_length=10, blank=True, null=True, db_index=True)

    unique_together = ("project", "contact", "role")

    def mail_link(self):
        return self.contact.mail_link()

    def __unicode__(self):
        return unicode(self.contact.get_full_name())


def get_project_delivery_path(instance, filename):
    return posixpath.join('projects', str(instance.project_id), 'deliveries', filename)


class Delivery(CircusModel):
    vendor = models.ForeignKey(Vendor)
    project = models.ForeignKey(Project)
    file = models.FileField(max_length=settings.FULL_FILEPATH_LENGTH, upload_to=get_project_delivery_path)
    notes = models.TextField(blank=True, null=True)
    tasks = models.ManyToManyField('tasks.Task')

    def file_display_name(self):
        full = unicode(self.file)
        return posixpath.basename(full)


class SalesforceOpportunity(sfmodels.SalesforceModel):
    STAGE_Prospect = "Prospect"
    STAGE_P1 = "P1"
    STAGE_P1_Wildcard = "P1 - Wildcard"
    STAGE_P1_Commit = "P1 - Commit"
    STAGE_P2 = "P2"
    STAGE_P2_Wildcard = "P2 - Wildcard"
    STAGE_P2_Commit = "P2 - Commit"
    STAGE_Closed_Won = "Closed Won"
    STAGE_Closed_Lost = "Closed Lost"

    STAGE_CHOICES = [
        (STAGE_Prospect, "Prospect"),
        (STAGE_P1, "P1"),
        (STAGE_P1_Wildcard, "P1 - Wildcard"),
        (STAGE_P1_Commit, "P1 - Commit"),
        (STAGE_P2, "P2"),
        (STAGE_P2_Wildcard, "P2 - Wildcard"),
        (STAGE_P2_Commit, "P2 - Commit"),
        (STAGE_Closed_Won, "Closed Won"),
        (STAGE_Closed_Lost, "Closed Lost"),
    ]

    name = models.CharField(db_column='Name', max_length=120)
    account = models.ForeignKey(SalesforceAccount, db_column='AccountId',
                                on_delete=models.DO_NOTHING,
                                related_name='opportunities',
                                blank=True, null=True)
    owner = models.ForeignKey(SalesforceUser, db_column='OwnerId',
                              on_delete=models.DO_NOTHING,
                              related_name='opportunities')
    amount = CurrencyField(db_column='Amount', max_digits=16, decimal_places=2,
                           blank=True, null=True)
    close_date = models.DateField(db_column='CloseDate', blank=True,
                                  null=True)
    description = models.TextField(db_column='Description', blank=True,
                                   max_length=32000)

    # ManyToMany on OpportunityContactRole doesn't actually work. :(
    # https://github.com/freelancersunion/django-salesforce/issues/55
    contacts = models.ManyToManyField(
        SalesforceContact,
        through='projects.SalesforceOpportunityContactRole',
        related_name='opportunities')

    # semicolon-separated multi-select field
    opportunity_type = models.CharField(db_column='Opportunity_Type__c',
                                        max_length=2048)

    stage = models.CharField(db_column='StageName', max_length=40,
                             choices=STAGE_CHOICES)

    # FORECAST_Omitted = "Omitted"
    # FORECAST_Pipeline = "Pipeline"
    # FORECAST_Best_Case = "Best Case"
    # FORECAST_Commit = "Commit"
    # FORECAST_Closed = "Closed"
    #
    # FORECAST_CHOICES = [
    #     (FORECAST_Omitted, "Omitted"),
    #     (FORECAST_Pipeline, "Pipeline"),
    #     (FORECAST_Best_Case, "Best Case"),
    #     (FORECAST_Commit, "Commit"),
    #     (FORECAST_Closed, "Closed"),
    # ]

    # forecast_category = models.CharField(db_column='ForecastCategoryName',
    #                                      max_length=40,
    #                                      choices=FORECAST_CHOICES,
    #                                      blank=True, null=True)

    # Need to be read-only fields?
    # created_date = models.DateTimeField(db_column='CreatedDate', blank=True,
    #                                     null=True)
    # is_closed = models.BooleanField(db_column='IsClosed')
    # is_deleted = models.BooleanField(db_column='IsDeleted')
    # is_won = models.BooleanField(db_column='IsWon')

    objects = SalesforceOpportunityManager()

    class Meta:
        db_table = 'Opportunity'
        managed = False

    def __repr__(self):
        return '<%s %s %r>' % (self.__class__.__name__, self.pk, self.name)


class SalesforceOpportunityContactRole(sfmodels.SalesforceModel):
    class Meta:
        db_table = 'OpportunityContactRole'
        managed = False

    # on_delete=CASCADE would be appropriate here, but django-salesforce doesn't
    # support it.
    opportunity = models.ForeignKey(SalesforceOpportunity,
                                    db_column='OpportunityId',
                                    on_delete=models.DO_NOTHING,
                                    related_name='contact_roles')
    contact = models.ForeignKey(SalesforceContact,
                                db_column='ContactId',
                                on_delete=models.DO_NOTHING,
                                related_name='opportunity_roles')

    role = models.CharField(db_column='Role', max_length=40,
                            blank=True, null=True)

    def __repr__(self):
        return '<%s %s %r>' % (self.__class__.__name__, self.pk, self.role)


class BackgroundTask(CircusModel):

    ANALYSIS = 'ANALYSIS'
    PRE_TRANSLATE = 'PRE_TRANSLATE'
    PSEUDO_TRANSLATE = 'PSEUDO_TRANSLATE'
    MACHINE_TRANSLATE = 'MACHINE_TRANSLATE'
    PREP_KIT = 'PREP_KIT'
    IMPORT_TRANSLATION = 'IMPORT_TRANSLATION'
    GENERATE_DELIVERY = 'GENERATE_DELIVERY'
    MEMORY_DB_TM = 'MEMORY_DB_TM'
    TERMINOLOGY_DB = 'TERMINOLOGY_DB'

    NAME_CHOICES = [
        (ANALYSIS, _(u'Analysis')),
        (PRE_TRANSLATE, _(u'Pretranslate')),
        (PSEUDO_TRANSLATE, _(u'Pseudotranslate')),
        (MACHINE_TRANSLATE, _(u'Machine Translate (MT)')),
        (PREP_KIT, _(u'Prepare Loc. Kit')),
        (IMPORT_TRANSLATION, _(u'Import Translation')),
        (GENERATE_DELIVERY, _(u'Generate Delivery Files')),
        (MEMORY_DB_TM, _(u'Add to Translation Memory')),
        (TERMINOLOGY_DB, _(u'Add to Terminology Database')),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE,
                                db_index=True, null=True)

    # if this action applies to a particular VTP Task (not to be confused with a BackgroundTask or a Celery task).
    task = models.ForeignKey("tasks.Task", on_delete=models.CASCADE, null=True)

    celery_task_id = models.CharField(max_length=36, unique=True,
                                      blank=True, null=True)

    # if not using celery
    callback_sig = models.TextField(blank=True, null=True)
    errback_sig = models.TextField(blank=True, null=True)
    remote_id = models.CharField(max_length=36, unique=True,
                                 blank=True, null=True)

    name = models.CharField(max_length=200, db_index=True,
                            choices=NAME_CHOICES)

    completed = models.DateTimeField(null=True, blank=True)

    objects = BackgroundTaskManager()

    @property
    def celery_result(self):
        """
        :rtype: celery.result.AsyncResult
        """
        if self.celery_task_id:
            # AsyncResult doesn't pull from the backend on creation, so we can make
            # this a property without anything blocking.
            import celery.app
            result = celery.app.current_app().AsyncResult(self.celery_task_id)
            return result
        else:
            return None

    def revoke(self):
        """Revoke this task from the queue.

        This doesn't cancel a task if it's currently in progress, but if it's
        still pending it will make sure it won't be started.
        """
        result = self.celery_result
        if result is None:
            # TODO: task cancellation in DVX API v2
            logger.warning("Cannot cancel %r, not a Celery task.")

        while result:
            result.revoke()
            # we probably want to revoke the whole chain, not just the tail.
            result = result.parent

    def complete(self):
        self.completed = timezone.now()
        self.save()

    def callback(self, *args, **kwargs):
        try:
            if self.callback_sig is None:
                return None
            try:
                sig_dict = json.loads(self.callback_sig)
                sig = Signature.from_dict(sig_dict)
                result = sig(*args, **kwargs)
            except Exception, error:
                logger.error("Error in %r.callback", self, exc_info=True)
                self.errback(error=error)
            else:
                return result
        finally:
            self.complete()

    def errback(self, *args, **kwargs):
        try:
            if self.errback_sig is None:
                return None
            sig_dict = json.loads(self.errback_sig)
            sig = Signature.from_dict(sig_dict)
            # invoke errback with BackgroundTask as first arg, for rough signature compatibility with
            # Celery error handlers which expect a celery task ID as the first arg.
            result = sig(self)
            return result
        finally:
            self.complete()

    def __repr__(self):
        complete = "complete" if (self.completed is not None) else "incomplete"
        return "<%s %s proj#%s (%s)>" % (
            self.__class__.__name__,
            self.name, self.project_id, complete)


class PriceQuote(CircusModel):
    project = models.ForeignKey(Project, null=True, blank=True)
    price = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, blank=True, null=True)
    cost = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, blank=True, null=True)
    gm = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    express_price = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, blank=True, null=True)
    express_cost = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, blank=True, null=True)
    express_gm = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    standard_tat = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, blank=True, null=True)
    express_tat = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, blank=True, null=True)
    wordcount = models.IntegerField(blank=True, null=True)
    version = models.IntegerField(blank=True, null=True)
    active = models.BooleanField(default=False)

    objects = PriceQuoteManager()

    def sum_details(self):
        pqds_aggregate = self.pricequotedetails_set.aggregate(Sum('target_price'), Sum('target_cost'), Avg("target_gross_margin"), Sum('target_express_price'), Sum('target_express_cost'), Avg("target_express_gross_margin"))
        return pqds_aggregate

    def sum_details_by_target(self, target):
        pqds_aggregate = self.pricequotedetails_set.filter(target=target).aggregate(Sum('target_price'), Sum('target_cost'), Avg("target_gross_margin"), Sum('target_express_price'), Sum('target_express_cost'), Avg("target_express_gross_margin"))
        return pqds_aggregate

    def __unicode__(self):
        return u'{0}: v {1}'.format(self.project, self.version)


class PriceQuoteDetails(CircusModel):
    pricequote = models.ForeignKey(PriceQuote, null=True, blank=True)
    target = models.ForeignKey(Locale, blank=True, null=True)
    target_price = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    target_cost = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    target_gross_margin = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    target_standard_tat = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, blank=True, null=True)
    target_express_tat = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, blank=True, null=True)
    target_express_price = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    target_express_cost = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    target_express_gross_margin = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)

    objects = PriceQuoteDetailsManager()

    def sum_details_taskquote(self):
        from tasks.models import TaskQuote
        tq_aggregate = TaskQuote.objects.filter(project=self.pricequote.project, task__service__target=self.target)\
                           .aggregate(Sum('total_cost'),
                                      Sum('raw_price'),
                                      Avg("mbd"),
                                      Sum('net_price'),
                                      Avg("gm"),
                                      Sum('total_express_cost'),
                                      Sum('express_raw_price'),
                                      Avg("express_mbd"),
                                      Sum('express_net_price'),
                                      Avg("express_gm"),
                                      Sum('wordcount'),
                                      Sum('standard_tat'),
                                      Sum('express_tat')
                                      )
        return tq_aggregate

    def __unicode__(self):
        return u'{0}'.format(self.pricequote)


def celery_task_completed(task_id, state, **kwargs):
    if state in celery.states.READY_STATES:
        BackgroundTask.objects.filter(celery_task_id=task_id).update(
            completed=timezone.now())

celery.signals.task_postrun.connect(celery_task_completed)


def celery_task_revoked(request, **kwargs):
    celery_task_completed(
        task_id=request.id,
        state=celery.states.REVOKED)

celery.signals.task_revoked.connect(celery_task_revoked)

