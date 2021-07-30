from __future__ import unicode_literals

import io
import json
import logging
import re
import urllib
from collections import OrderedDict
from datetime import date, timedelta
from decimal import Decimal

import pytz
from celery import shared_task
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.messages import SUCCESS
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse, resolve
from django.db.models import Q
from django.http import HttpResponseRedirect, Http404, HttpResponse, HttpResponseNotAllowed, StreamingHttpResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, TemplateView, CreateView, ListView
from django.views.generic.base import ContextMixin
from django.views.generic.edit import UpdateView
from django.views.generic.list import BaseListView
from salesforce.backend.base import SalesforceError
from unicodecsv import DictWriter

from shared.group_permissions import DEPARTMENT_ADMINISTRATOR_GROUP, DEPARTMENT_USER_GROUP, CLIENT_NOTIFICATION_GROUP, \
    CLIENT_PROJECT_APPROVER_GROUP, CLIENT_MANAGER_GROUP, CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP
from shared.managers import get_delivered_projects_filter, get_overdue_projects_filter, get_completed_projects_filter

from finance import payflow
from finance.forms import CreditCardForm
from jams_api.engine import create_jams_job_number
from localization_kits.authorization import may_edit_project_loc_kit
from localization_kits.views import AJAXAnalysisStatusCheck, update_analysis_cookie
from projects.duedates import add_delta_business_days
from shared.mixins import HideSearchMixin, ProjectSearchMixin
from shared.viewmodels import ProjectTargetDeliveryViewModel
from client_portal.decorators import client_login_required, client_administrator_login_required
from accounts.forms import ClientProfileForm, CircusUserCreationForm, GroupCreationForm
from client_portal.forms import (ClientOrderForm, ClientApproveQuoteForm,
                                 ClientRegisterForm, ClientAccountForm, JoinClientForm,
                                 ClientManualQuoteForm)
from clients.models import Client, ClientTeamRole, PM_ROLE, ClientEmailDomain, ClientService, \
    ClientContact, ClientManifest
from django_comments.models import Comment
from finance import payflow
from finance.forms import CreditCardForm
from finance.models import CA_PAYMENT_CHOICE, CC_PAYMENT_CHOICE
from jams_api.engine import create_jams_job_number
from localization_kits.authorization import may_edit_project_loc_kit
from localization_kits.models import FileAsset
from localization_kits.views import AJAXAnalysisStatusCheck, update_analysis_cookie
from notifications.notifications import join_account_request, project_manual_quote_needed, \
    notify_via_new_client_user, notify_via_new_client_account, notify_account_welcome_email,\
    notify_client_job_access_provided, notify_client_job_access_rejected
from people.models import Account, JoinAccountRequest
from projects.duedates import add_delta_business_days, get_quote_due_date
from projects.models import Project, AUTO_ESTIMATE, MANUAL_ESTIMATE, BackgroundTask, SalesforceOpportunity , ProjectAccess, \
    ProjectServicesGlobal, ProjectJobOptions
from projects.states import (_normalize_project_status, _reverse_normalize_project_status, get_reversed_status,
                             CREATED_STATUS, QUOTED_STATUS, STARTED_STATUS, COMPLETED_STATUS, CLOSED_STATUS,
                             CANCELED_STATUS, QUEUED_STATUS, OVERDUE_STATUS, DELIVERED_STATUS, ACTIVE_STATUS,
                             CLIENT_STATUS_DETAIL, ALL_STATUS, INESTIMATE_STATUS, ESTIMATED_STATUS, HOLD_STATUS, MYJOBS_STATUS, INAPPROVAL_STATUS)
from projects.views import show_files, get_order_by_filed_name
from services.managers import DISCOUNT_SERVICE_TYPE
from services.models import Locale, ServiceType, Country
from shared.managers import get_delivered_projects_filter, get_overdue_projects_filter, get_completed_projects_filter
from shared.mixins import HideSearchMixin, ProjectSearchMixin
from shared.utils import comment_filters
from shared.viewmodels import ProjectTargetDeliveryViewModel, ProjectTargetSetViewModel, TargetAnalysisSetViewModel
from shared.views import DefaultContextMixin
from tasks.make_tasks import _verify_add_client_discount_task, _verify_client_discount_task
from tasks.models import TranslationTaskAnalysis, TaskLocalizedAsset
from shared.utils import format_datetime
from projects.views import show_files, get_order_by_filed_name
from django_comments.models import Comment
from collections import OrderedDict
from shared.viewmodels import ProjectTargetSetViewModel, TargetAnalysisSetViewModel
from accounts.models import CircusUser, ViaGroup, GroupOwner, GroupOwnerPermissions
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Group
from projects.models import SecureJobAccess
from dwh_reports.models import ClientReportAccess

logger = logging.getLogger('circus.' + __name__)


class ClientLoginRequiredMixin(object):
    @method_decorator(client_login_required)
    def dispatch(self, *args, **kwargs):
        #noinspection PyUnresolvedReferences
        return super(ClientLoginRequiredMixin, self).dispatch(*args, **kwargs)


class ClientAdministratorLoginRequired(object):
    @method_decorator(client_administrator_login_required)
    def dispatch(self, *args, **kwargs):
        #noinspection PyUnresolvedReferences
        return super(ClientAdministratorLoginRequired, self).dispatch(*args, **kwargs)


class ClientMenuContextMixin(ContextMixin):
    def get_context_data(self, **kwargs):
        context = super(ClientMenuContextMixin, self).get_context_data(**kwargs)
        context['user_timezone'] = self.request.user.user_timezone
        client = self.request.user.account.cast(Client)
        context['client_id'] = client.id
        context['show_client_messenger'] = client.manifest.show_client_messenger
        context['secure_hierarchy'] = client.manifest.enforce_customer_hierarchy
        context['secure_jobs'] = client.manifest.secure_jobs
        context['phi_warning'] = client.manifest.phi_warning() and not client.manifest.baa_agreement_for_phi
        context['can_access_users_groups_options'] = self.request.user.can_access_users_groups_options()
        context['can_manage_users'] = self.request.user.can_manage_users()
        return context


class DashboardView(ClientLoginRequiredMixin, ClientMenuContextMixin, DefaultContextMixin, TemplateView):
    template_name = 'clients/dashboard/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)

        # dashboard should only show for last +/- 6 months
        now = timezone.now()
        history_date = now - timedelta(days=settings.HISTORY_DATE_RANGE)
        future_date = now + timedelta(days=settings.FUTURE_DATE_RANGE)
        client_projects = Project.objects.select_related().filter(client_id=context['client_id'],
                                                 modified__range=[history_date, future_date],
                                                 internal_via_project=False)

        context['status'] = {
            'queued': client_projects.filter(status=QUEUED_STATUS).count(),
            'inestimate': client_projects.filter(status=CREATED_STATUS).count(),
            'estimated': client_projects.filter(status=QUOTED_STATUS).count(),
            'active': client_projects.filter(status=STARTED_STATUS, due__gte=now).count(),
            'overdue': client_projects.filter(status=STARTED_STATUS, due__lt=now).count(),
            'delivered': client_projects.filter(status=COMPLETED_STATUS).filter(delivered__isnull=False, completed__isnull=True).count(),
            'completed': client_projects.filter(Q(status=COMPLETED_STATUS) | Q(status=CLOSED_STATUS)).filter(completed__isnull=False).count(),
            'canceled': client_projects.filter(Q(status=CANCELED_STATUS)).count(),
            'inapproval': client_projects.filter(access_project__contact=self.request.user).count(),
        }
        context['calendar_events'] = []
        not_for_calendar = Q(status__in=[
            QUEUED_STATUS, CREATED_STATUS, HOLD_STATUS, QUOTED_STATUS, CANCELED_STATUS
        ])

        #calender data
        for project in client_projects.exclude(not_for_calendar):
            if project.started_timestamp and project.due:
                context['calendar_events'].append(
                    {
                        'title': project.job_number,
                        'start': unicode(project.started_timestamp),
                        'end': unicode(project.due),
                        'status': unicode(project.status),
                        'url': reverse('client_project_detail', args=(project.id,)),
                        'backgroundColor': project.calendar_status(),
                        'borderColor': '#757575',
                    }
                )
        context['is_phi_secure_client'] = self.request.user.account.is_phi_secure_client()
        return context


class ProjectDeliveryView(ClientLoginRequiredMixin, ClientMenuContextMixin, DefaultContextMixin, DetailView):
    template_name = 'clients/projects/delivery.html'
    context_object_name = 'project'

    def get_queryset(self):
        self.lcid = self.kwargs.get('lcid')
        return Project.objects.select_related().filter(
            client=self.request.user.account.cast(Client), internal_via_project=False
        ).filter(
            Q(status=STARTED_STATUS) | Q(status=COMPLETED_STATUS) | Q(status=CLOSED_STATUS)
        )

    def get_context_data(self, **kwargs):
        context = super(ProjectDeliveryView, self).get_context_data(**kwargs)
        target = Locale.objects.get(lcid=self.lcid)
        context['delivery_vm'] = ProjectTargetDeliveryViewModel(self.object, target)
        context['can_access_job'] = self.object.can_access_job(self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        self.object = project = self.get_object()

        if 'client_notes' in request.POST:
            self.object = project
            tla_task_id = request.POST.get('tla_task_id')
            tla_id = request.POST.get('tla_id')
            post_delivery_notes = request.POST.get('client_notes')
            tla = TaskLocalizedAsset.objects.get(id=tla_id, task_id=tla_task_id)
            tla.post_delivery_notes = post_delivery_notes
            tla.save()

            return HttpResponseRedirect(reverse('client_project_delivery', args=(tla.task.project.id, tla.task.service.target.lcid)))

        if 'delete_post_delivery_edit_file' in request.POST:
            tla_id = request.POST['task_loc_asset_id']
            tla = TaskLocalizedAsset.objects.get(id=tla_id)
            tla.post_delivery_file = ''
            tla.post_delivery_notes = None
            tla.save()

            return HttpResponseRedirect(reverse('client_project_delivery', args=(tla.task.project.id, tla.task.service.target.lcid)))


class ProjectDetailView(ClientLoginRequiredMixin, ClientMenuContextMixin, DefaultContextMixin, DetailView):
    template_name = 'clients/projects/detail.html'
    context_object_name = 'project'
    active_tab = 'details'

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            #: :type: Project
            project = self.object

            _verify_add_client_discount_task(project)

        except Http404:
            messages.add_message(self.request, messages.INFO, _('That Job Number does not exist.'))
            return HttpResponseRedirect(reverse('client_dashboard'))
        return super(ProjectDetailView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        projects = Project.objects.select_related().filter(
            Q(client=self.request.user.account.cast(Client)) | Q(client__in=self.request.user.account.children.all()), internal_via_project=False
        )
        return projects

    def post(self, request, *args, **kwargs):
        if 'comment_id' in request.POST:
            instance = get_object_or_404(Comment, id=request.POST.get('comment_id', None))
            instance.comment_read_check = True
            instance.save()
            if instance:
                return HttpResponse(json.dumps({'message': 'Success'}), content_type="application/json")
            else:
                return HttpResponse(json.dumps({'message': 'Error'}), content_type="application/json")

        if 'request_user_id' in request.POST:
            comments = Comment.objects
            new_comments = comments.filter(object_pk=request.POST.get('comment_project_id'), comment_to=request.POST.get('request_user_id'), comment_read_check=False, is_removed=False, notification_type=settings.NOTIFICATION_TYPE_MESSAGE)
            new_comments.update(comment_read_check=True, filter_from_list=True, comment_read_on=timezone.now())
            if new_comments:
                return HttpResponse(json.dumps({'message': 'Success'}), content_type="application/json")
            else:
                return HttpResponse(json.dumps({'message': 'Error'}), content_type="application/json")

        if 'is_secure_job' in request.POST:
            if request.POST.get('option') == 'True':
                instance, created = SecureJobAccess.objects.get_or_create(user_id=request.POST.get('user_id'),
                                                             account_id=request.POST.get('account_id'),
                                                             project_id=request.POST.get('project_id'),
                                                             is_access_given=True)
            else:
                instance = SecureJobAccess.objects.get(user_id=request.POST.get('user_id'),
                                                       account_id=request.POST.get('account_id'),
                                                       project_id=request.POST.get('project_id')).delete()
            if instance:
                return HttpResponse(json.dumps({'message': 'Success'}), content_type="application/json")
            else:
                return HttpResponse(json.dumps({'message': 'Error'}), content_type="application/json")

    def get_context_data(self, **kwargs):
        context = super(ProjectDetailView, self).get_context_data(**kwargs)
        project = self.object
        project_targets = ProjectTargetSetViewModel(project, billable_only=True)
        context['project_target_locales'] = project_targets
        context['quote'] = project.quote_no_costs()
        reversed_status = OVERDUE_STATUS if project.is_overdue() else get_reversed_status(project.status)
        context['status'] = CLIENT_STATUS_DETAIL[reversed_status]
        context['is_sow_available'] = project.is_sow_available()
        context['show_files'] = show_files(self.request,project.id)
        comment_types = comment_filters(settings.CLIENT_USER_TYPE)
        context['client_comment_list_check'] = Comment.objects.filter(object_pk=project.id, is_removed=False).filter(*comment_types)
        context['client_message_unread_count'] = Comment.objects.filter(object_pk=self.object.id, comment_to=self.request.user.id,is_removed=False, comment_read_check=False, notification_type=settings.NOTIFICATION_TYPE_MESSAGE).count()
        context['active_tab'] = 'details'
        self.active_tab = 'details'

        if self.request.session.get('tab_session_name', False):
            context['active_tab'] = 'job_messages'
            self.active_tab = 'job_messages'

        target_analyses = OrderedDict()
        for target in project.target_locales.order_by("description"):
            target_analyses[target] = TargetAnalysisSetViewModel(target, project, include_placeholder=True)
        context['target_analyses'] = target_analyses

        client_discount_flag = _verify_client_discount_task(project)
        context['client_discount_flag'] = client_discount_flag

        if client_discount_flag:
            original_price_standard, original_price_express = project.project_original_price()
            context['original_price_standard'] = original_price_standard
            context['original_price_express'] = original_price_express

        context['secure_job_team'] = get_user_model().objects.filter(account=self.request.user.account).order_by('email')
        context['can_access_job'] = project.can_access_job(self.request.user)
        return context

    def get_success_url(self):
        params = urllib.urlencode({'active_tab': self.active_tab})
        success_url = HttpResponseRedirect(reverse('client_project_detail', args=(self.kwargs['pk'],)) + '?' + params)
        return success_url


class ProjectListMixin(ContextMixin):
    template_name = 'clients/projects/list.html'
    context_object_name = 'project_list'
    paginate_by = settings.PAGINATE_BY_STANDARD
    status = None

    def get_context_data(self, **kwargs):
        context = super(ProjectListMixin, self).get_context_data(**kwargs)
        projects = context['project_list']
        project = None

        for project in projects:
            # client_manifest = project.client.manifest
            reversed_status = OVERDUE_STATUS if project.is_overdue() else get_reversed_status(project.status)
            project.workflow = CLIENT_STATUS_DETAIL[reversed_status]

        for status, status_details in CLIENT_STATUS_DETAIL.items():
            url_status_parameter = status_details.get('url_status_parameter')
            if not url_status_parameter:
                status_details['url'] = reverse('client_project_list')
            else:
                status_details['url'] = reverse('client_project_status_list', kwargs={'status': url_status_parameter})

        context['CLIENT_STATUS_DETAIL'] = CLIENT_STATUS_DETAIL
        reversed_status = get_reversed_status(self.status)
        context['workflow_status'] = CLIENT_STATUS_DETAIL[reversed_status]
        context['workflow_status']['export_url'] = reverse('client_project_list_export', kwargs={'status': reversed_status})
        return context

    def get_queryset(self):
        self.status = _normalize_project_status(self.kwargs.get('status') or 'all')
        self.order_by = self.request.GET.get('order_by')
        self.first_char = ''
        self.order_by_field_name = None
        self.order_by_field_name_sort = None
        if self.order_by:
            if self.order_by[0] == '-':
                self.first_char = self.order_by[0]
                self.order_by = self.order_by[1:]
            self.order_by_field_name = get_order_by_filed_name(self.order_by)
            self.order_by_field_name_sort = str(self.first_char) + str(self.order_by_field_name)
        return _client_projects(self.request.user, self.status, self.order_by_field_name_sort)

    def post(self, request, *args, **kwargs):
        if 'request_access' in request.POST:
            project = int(request.POST['project_id'])
            project_with_access = Project.objects.filter(access_project__project_id=project, access_project__contact=self.request.user)
            if not project_with_access:
                project_access = ProjectAccess(project_id=project, contact=self.request.user)
                project_access.save()
                messages.add_message(self.request, messages.SUCCESS, _('Requested for access'))
            else:
                user_access = ProjectAccess.objects.get(project_id=project)
                if user_access.contact != self.request.user:
                    project_access = ProjectAccess(project_id=project, contact=self.request.user)
                    project_access.save()
                    messages.add_message(self.request, messages.SUCCESS, _('Requested for access'))
                else:
                    messages.add_message(self.request, messages.SUCCESS, _('Request is already logged'))
            return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


class ProjectSearchView(ClientLoginRequiredMixin, ClientMenuContextMixin, ProjectListMixin, ProjectSearchMixin, DefaultContextMixin, ListView):
    status = ALL_STATUS
    template_name = 'clients/projects/search.html'

    def get_context_data(self, **kwargs):
        context = super(ProjectSearchView, self).get_context_data(**kwargs)
        context['search_query'] = self.search_query
        return context

    def get_queryset(self):
        self.search_query = self.request.GET.get('q').strip()
        if not self.search_query:
            self.search_query = ""
            return []

        client_projects = super(ProjectSearchView, self).get_queryset().order_by('-job_number')
        matches = self.get_matches(client_projects, self.search_query)
        matches = matches.prefetch_related('client_poc', 'account_executive', 'project_manager', 'estimator')
        return matches


class ProjectStatusOverdueView(ClientLoginRequiredMixin, ClientMenuContextMixin, ProjectListMixin, DefaultContextMixin, ListView):

    def get_context_data(self, **kwargs):
        context = super(ProjectStatusOverdueView, self).get_context_data(**kwargs)
        projects = context['project_list']

        for project in projects:
            reversed_status = OVERDUE_STATUS if project.is_overdue() else get_reversed_status(project.status)
            project.workflow = CLIENT_STATUS_DETAIL[reversed_status]
        return context

    def get_queryset(self):
        client_projects = Project.objects.select_related().get_client_projects(self.request.user)
        client_projects = client_projects.get_overdue_projects()
        self.status = OVERDUE_STATUS
        return client_projects.order_by('-job_number')


def _client_projects(user, status, order_by_field):
    reversed_status = _reverse_normalize_project_status(status)

    client_projects_filter = []

    if reversed_status in [ALL_STATUS]:
        client_projects_filter = []
    elif reversed_status in [QUEUED_STATUS]:
        client_projects_filter = [Q(status=QUEUED_STATUS)]
    elif reversed_status in [CREATED_STATUS]:
        client_projects_filter = [Q(status=CREATED_STATUS)]
    elif reversed_status in [INESTIMATE_STATUS]:
        client_projects_filter = [Q(status=CREATED_STATUS)]
    elif reversed_status in [ESTIMATED_STATUS, QUOTED_STATUS]:
        client_projects_filter = [Q(status=QUOTED_STATUS)]
    elif reversed_status in [HOLD_STATUS]:
        client_projects_filter = [Q(status=HOLD_STATUS)]
    elif reversed_status in [ACTIVE_STATUS, STARTED_STATUS]:
        client_projects_filter = [Q(status=STARTED_STATUS)]
    elif reversed_status in [OVERDUE_STATUS]:
        client_projects_filter = get_overdue_projects_filter()
    elif reversed_status in [DELIVERED_STATUS]:
        client_projects_filter = get_delivered_projects_filter()
    elif reversed_status in [COMPLETED_STATUS]:
        client_projects_filter = get_completed_projects_filter()
    elif reversed_status in [CANCELED_STATUS]:
        client_projects_filter = [Q(status=CANCELED_STATUS)]
    elif reversed_status in [INAPPROVAL_STATUS]:
        client_projects_filter = [~Q(access_project__project =None)]

    project_obj = Project.objects

    if reversed_status in [MYJOBS_STATUS]:
        project_results = project_obj.select_related().filter(client_poc_id=user.id).distinct()
    else:
        project_results = project_obj.select_related().get_client_projects(user)\
            .filter(*client_projects_filter, internal_via_project=False)\
            .filter(Q(is_secure_job=False) | Q(client_poc_id=user.id))\
            .distinct()

    #Filtering the secure jobs for the current user and account.
    if user.is_client_administrator_group() or user.is_manager_group():
        secure_jobs_list = SecureJobAccess.objects.filter(account=user.account)
    else:
        secure_jobs_list = SecureJobAccess.objects.filter(user=user, account=user.account)

    secure_jobs = project_obj.filter(id__in=[project.project_id for project in secure_jobs_list])\
        .filter(*client_projects_filter, internal_via_project=False)\
        .distinct()
    project_results = project_results | secure_jobs

    if order_by_field:
        reverse_order = False
        if '-' in order_by_field:
            reverse_order = True

        if 'price' in order_by_field:
            client_projects = sorted(project_results, key=lambda t: t.price(), reverse=reverse_order)
        elif 'warnings' in order_by_field:
            client_projects = sorted(project_results, key=lambda t: t.client_warnings(), reverse=reverse_order)
        elif 'express' in order_by_field:
            client_projects = sorted(project_results, key=lambda t: t.is_express_speed(), reverse=reverse_order)
        else:
            client_projects = project_results.order_by(order_by_field)
    else:
        client_projects = project_results.order_by('-job_number')

    return client_projects


class ProjectListView(ClientLoginRequiredMixin, ClientMenuContextMixin, ProjectListMixin, DefaultContextMixin, ListView):

    def get_queryset(self):
        return super(ProjectListView, self).get_queryset()


class ProjectListViewExport(ClientLoginRequiredMixin, ClientMenuContextMixin, ProjectListMixin, DefaultContextMixin, BaseListView):
    paginate_by = settings.PAGINATE_BY_LARGE

    # get_matches doesn't use object state, so reduce our mixin count.
    _get_matches = ProjectSearchMixin().get_matches

    def get_queryset(self):
        self.status = _normalize_project_status(self.kwargs.get('status'))
        self.order_by_field_name_sort = None
        projects = _client_projects(self.request.user, self.status, self.order_by_field_name_sort)
        search_query = self.request.GET.get('q')
        if search_query:
            matches = self._get_matches(projects, search_query)
            matches = sorted(matches, key=lambda project: project.job_number,
                             reverse=True)
            return matches
        return projects

    def csv(self, projects):
        """
        :type projects: iterable of projects.models.Project
        """
        stream = io.BytesIO()
        stream.write(u'\ufeff'.encode('utf8'))

        headers = [
            'Job', 'Speed', 'Warnings', 'Approved', 'Workflow',
            'Purchase Order', 'Reference', 'Files', 'Source', 'Targets', 'Price',
            'Requester', 'Department', 'PM', 'AE', 'Estimate', 'Started', 'Due',
            'Delivered'
        ]
        csvwriter = DictWriter(stream, headers)
        csvwriter.writeheader()

        for project in projects:
            # assert isinstance(project, Project)
            targets = u', '.join(unicode(t) for t in project.target_locales.all())
            files = u', '.join(asset.short_name() for asset in
                               project.kit.source_files())

            record = {
                'Speed': project.project_speed,
                'Warnings': unicode(project.client_warnings() or ''),
                'Approved': project.approved,
                'Job': project.job_number,
                'Workflow': project.workflow.get('text'),
                'Purchase Order': project.payment_details.ca_invoice_number,
                'Reference': project.project_reference_name,
                'Files': files,
                'Source': project.source_locale,
                'Targets': targets,
                'Price': project.price(),
                'Requester': project.client_poc,
                'Department': project.client_poc.department,
                'PM': project.primary_pm(),
                'AE': project.account_executive,
                # Dates
                'Estimate': project.quote_due.date() if project.quote_due else '',
                'Started': project.started_timestamp.date() if project.started_timestamp else '',
                'Due': project.due.date() if project.due else '',
                'Delivered': project.delivered.date() if project.delivered else ''
            }

            csvwriter.writerow(record)

        return stream.getvalue()

    def render_to_response(self, context):
        search_query = self.request.GET.get('q')
        if search_query:
            query_slug = '_' + slugify(search_query)
        else:
            query_slug = ''

        filename = 'via-jobs-%s%s.csv' % (self.status, query_slug)
        content = self.csv(context['project_list'])
        response = StreamingHttpResponse(content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="%s"' % (filename,)
        return response


@client_login_required
def new_clone_job_redirect(request, id=None):
    client = request.user.account.cast(Client)
    if client.manifest.enforce_customer_hierarchy and not request.user.has_perm('projects.add_project'):
        messages.add_message(request, messages.ERROR, _(u"Not enough access to Start Estimate"))
        return HttpResponseRedirect(reverse('client_dashboard'))

    project = Project.objects.select_related().get(pk=id)

    clone_project = Project.objects.create(
        client_id=project.client_id,
        source_locale_id=project.source_locale_id,
        client_poc_id=project.client_poc_id,
        current_user=request.user.id,
        is_restricted_job=project.is_restricted_job,
        industry=project.industry,
    )
    clone_project.services = project.services.all()
    clone_project.target_locales = project.target_locales.all()
    clone_project.job_number = str(clone_project.id)
    clone_project.name = "{0} ({1}): {2}".format(request.user.account.name, request.user.get_full_name(), unicode(date.today()))
    if settings.VIA_JAMS_INTEGRATION:
        # get Job Number from JAMS API
        clone_project.name = "{0}: {1}".format(settings.APP_SLUG_INSTANCE, clone_project.name)
        created, job_number, job_id = create_jams_job_number(clone_project)
        if created:
            clone_project.job_number = job_number
            clone_project.jams_jobid = job_id
    clone_project.save()
    clone_project.assign_team()

    return HttpResponseRedirect(reverse('client_new_project', args=(clone_project.id,)))


@client_login_required
def new_project_redirect(request):
    client = request.user.account.cast(Client)
    if client.manifest.enforce_customer_hierarchy and not request.user.has_perm('projects.add_project'):
        messages.add_message(request, messages.ERROR, _(u"Not enough access to Start Estimate"))
        return HttpResponseRedirect(reverse('client_dashboard'))

    project = Project.objects.create(
        client=request.user.account.cast(Client),
        source_locale=Locale.objects.get(lcid=1033),
        client_poc=request.user,
        current_user=request.user.id
    )
    project.job_number = str(project.id)
    project.name = "{0} ({1}): {2}".format(request.user.account.name, request.user.get_full_name(), unicode(date.today()))
    if settings.VIA_JAMS_INTEGRATION:
        # get Job Number from JAMS API
        project.name = "{0}: {1}".format(settings.APP_SLUG_INSTANCE, project.name)
        try:
            created, job_number, job_id = create_jams_job_number(project)
            if created:
                project.job_number = job_number
                project.jams_jobid = job_id
        except:
            messages.add_message(request, messages.ERROR, _(u"ERROR in Start Estimate : {0}").format(project.job_name_display_name()))
            project.delete()
            return HttpResponseRedirect(reverse('client_dashboard'))

    current_url = resolve(request.path_info).url_name
    cs = ClientService.objects.filter(client=request.user.account.cast(Client), available=True, job_default=True)
    default_services = [ds.service for ds in cs.all()]
    project.services = default_services

    if current_url == "client_new_phi_project_start":
        project.is_phi_secure_job = True
        project.is_secure_job = True
    project.save()
    project.assign_team()

    return HttpResponseRedirect(reverse('client_new_project', args=(project.id,)))


class NewProjectView(ClientLoginRequiredMixin, ClientMenuContextMixin, DefaultContextMixin, UpdateView):
    template_name = 'clients/order/order_entry.html'
    form_class = ClientOrderForm

    def get_form_kwargs(self):
        kwargs = super(NewProjectView, self).get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(NewProjectView, self).get_context_data(**kwargs)
        cs = ClientService.objects.filter(client=self.request.user.account, available=True)
        avail_services_id = cs.values_list("service_id", flat=True)
        context['service_types'] = ServiceType.objects.filter(pk__in=avail_services_id).order_by('-description')
        context['can_access_job'] = True
        return context

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
        except Http404:
            messages.add_message(self.request, messages.INFO, _('That Job Number does not exist.'))
            return redirect('client_dashboard')

        if self.object.is_manual_estimate():
            return redirect('client_manual_quote_message', self.object.id)
        elif self.object.kit.analyzing():
            return redirect('client_waiting_for_quote', self.object.id)
        elif self.object.is_quoted_status():
            return redirect('client_quote', self.object.id)
        return super(NewProjectView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        return Project.objects.select_related().filter(Q(client=self.request.user.account.cast(Client)) | Q(client__in=self.request.user.account.children.all()), is_deleted=False, status__in=[QUEUED_STATUS, CREATED_STATUS, QUOTED_STATUS])

    def _make_name_for_project(self, project):
        """Make a name for the project from the source files."""
        max_files_in_name = 3
        source_names = [f.file_display_name() for f in
                        project.kit.source_files().order_by('created')]

        if source_names:
            project_name = '; '.join(source_names[:max_files_in_name])
            if len(source_names) > max_files_in_name:
                project_name = '%s; +%d more' % (
                    project_name, len(source_names) - max_files_in_name)
            project.name = "{0}: {1}".format(settings.APP_SLUG_INSTANCE, project_name)

    def form_valid(self, form):
        #: :type: Project
        project = form.save(commit=False)
        self.object = project
        project.estimate_type = AUTO_ESTIMATE

        try:
            country = Country.objects.get_or_none(country_code=self.request.user.country)
            if country:
                project.restricted_locations.add(country)
        except:
            pass

        self._make_name_for_project(project)
        project.current_user = self.request.user.id
        project.save()
        form.save_m2m()

        #Make the user assigned to Secure Job Team member is he selects Secure Job True
        is_secure_job = project.is_secure_job
        if is_secure_job:
            from shared.group_permissions import SECURE_JOB_PERMISSION
            permission = Permission.objects.get(codename=SECURE_JOB_PERMISSION)
            self.request.user.user_permissions.add(permission)

            #Saving into projects_securejobaccess table
            secure_job_access = SecureJobAccess.objects.create(
                project=project,
                user=self.request.user,
                is_access_given=True,
                account=self.request.user.account,
            )

        # figure out if we have a file or language combination that cannot be auto-quoted, if so send to manual
        if project.client.manifest.auto_estimate_jobs and \
                project.kit.can_auto_estimate_doctype() and \
                project.kit.can_auto_estimate_locale() and \
                not project.is_restricted_and_english_target() and \
                not project.is_phi_secure_job:

            project.kit.queue_analysis_tasks(
                callback=_analysis_complete_callback.si(project.id),
                errback=_analysis_complete_errback.s(project.id))
            response = HttpResponseRedirect(self.get_success_url())

            update_analysis_cookie(response, project)

            return response
        else:
            BackgroundTask.objects.revoke_analysis(project)
            project.kit.remove_analysis_code()
            project.estimate_type = MANUAL_ESTIMATE
            project.status = QUEUED_STATUS
            project.current_user = self.request.user.id
            project.save()
            return HttpResponseRedirect(reverse('client_manual_quote_message', args=(project.id,)))

    def get_success_url(self):
        return reverse('client_waiting_for_quote', args=(self.object.id,))


def quote_project(project):
    ProjectServicesGlobal.objects.filter(project=project).delete()
    quantity_dic = project.generate_default_service_global_quantity()
    project.save_service_global_quantity(quantity_dic)

    status, msg = project.generate_tasks()

    if status != SUCCESS:
        return False

    project.assign_tasks()

    if not project.has_price():
        project.quote()

    if QUOTED_STATUS in [t.target.name for t in project.valid_transitions()]:
        project.transition(QUOTED_STATUS)
        return True
    else:
        return False


@shared_task
def _analysis_complete_callback(project_id):
    project = Project.objects.select_related().get(id=project_id)

    quoted = quote_project(project)

    if not quoted:
        # Analysis completed successfully but quote failed to assign prices,
        # either we've failed to generate a quote for the client.
        return _analysis_complete_errback(None, project_id)
    else:
        if project.large_jobs_check():
            project.large_job_force_manual_estimate()


@shared_task
def _analysis_complete_errback(task_id, project_id, error=None):
    # celery error handlers get task_id as the first argument, even if we don't use it.
    project = Project.objects.select_related().get(id=project_id)
    project.estimate_type = MANUAL_ESTIMATE
    project.status = QUEUED_STATUS
    project.save()


class QuoteView(ClientLoginRequiredMixin, ClientMenuContextMixin, DefaultContextMixin, UpdateView):
    template_name = 'clients/order/order_approval.html'
    form_class = ClientApproveQuoteForm

    def get_context_data(self, **kwargs):
        context = super(QuoteView, self).get_context_data(**kwargs)
        project = self.object
        context['quote_summary_standard'] = project.quote_standard()
        context['quote_summary_express'] = project.quote_express()
        context['source_files'] = context['project'].kit.source_files()
        context['reference_files'] = context['project'].kit.reference_files()
        project_targets = ProjectTargetSetViewModel(project)
        context['project_targets'] = project_targets
        if project_targets:
            task_list = project_targets.targets[0].tasks
        context['task_list'] = sorted(task_list, key=lambda task: task.id)

        client_discount_flag = _verify_client_discount_task(project)
        context['client_discount_flag'] = client_discount_flag

        if client_discount_flag:
            original_price_standard, original_price_express = project.project_original_price()
            context['original_price_standard'] = original_price_standard
            context['original_price_express'] = original_price_express

        context['phi_contact'] = 'mailto:' + project.phi_contact()
        context['is_sow_available'] = project.is_sow_available()

        comment_types = comment_filters(settings.CLIENT_USER_TYPE)
        context['client_comment_list_check'] = Comment.objects.filter(object_pk=project.id, is_removed=False).filter(*comment_types)

        from localization_kits.models import FileAsset
        asset_docs = FileAsset.objects.filter(
            kit_id=project.kit_id,
        ).order_by('orig_name')
        context['project_asset_documents'] = asset_docs
        context['active_access_request'] = project.active_access_request()
        context['can_access_job'] = project.can_access_job(self.request.user)
        target_analyses = OrderedDict()
        for target in project.target_locales.order_by("description"):
            target_analyses[target] = TargetAnalysisSetViewModel(target, project, include_placeholder=True)
        context['target_analyses'] = target_analyses
        if target_analyses:
            context['project_memory_bank_discount_exists'] = target_analyses.items()[0][1].memory_bank_discount_exists
        return context

    def get(self, request, *args, **kwargs):
        try:
            self.object = self.get_object()
            #: :type: Project
            project = self.object

            _verify_add_client_discount_task(project)

        except Http404:
            messages.add_message(self.request, messages.INFO, _('That Job Number does not exist.'))
            return redirect('client_dashboard')
        if project.kit.analyzing():
            return redirect('client_waiting_for_quote', project.id)
        elif project.is_inestimate_status():
            return redirect('client_manual_quote_message', project.id)
        elif project.is_queued_status():
            if project.kit.analysis_completed:
                # analysis tried and failed
                return redirect('client_manual_quote_message', project.id)
            else:
                pass  # FIXME: at QuoteView but not project.is_quoted_status?

        return super(QuoteView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = project = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if 'request_access' in request.POST:
            # project_access = ProjectAccess.objects.get_or_none(project=project ,contact=self.request.user)
            project_with_access = Project.objects.filter(access_project__project=project,access_project__contact=self.request.user)
            if not project_with_access:
                project_access = ProjectAccess(project=project,contact=self.request.user)
                project_access.save()
                messages.add_message(self.request, messages.SUCCESS, _('Requested for access'))
            else:
                user_access = ProjectAccess.objects.get(project=project)
                if user_access.contact != self.request.user:
                    project_access = ProjectAccess(project=project,contact=self.request.user)
                    project_access.save()
                    messages.add_message(self.request, messages.SUCCESS, _('Requested for access'))
                else:
                    messages.add_message(self.request, messages.SUCCESS, _('Request is already logged'))
            return HttpResponseRedirect(reverse('client_new_project', args=(project.id,)))

        if 'provide_access' in request.POST:
            project_access = ProjectAccess.objects.filter(project=project)
            if project_access:
                for PA in project_access:
                    PA.is_access_given = True
                    PA.save()
                messages.add_message(self.request, messages.SUCCESS, _('Project access is given'))
            return HttpResponseRedirect(reverse('client_new_project', args=(project.id,)))

        if 'provide_access' in request.POST:
            project_access = ProjectAccess.objects.filter(project=project)
            if project_access:
                for PA in project_access:
                    PA.is_access_given = True
                    PA.save()
                messages.add_message(self.request, messages.SUCCESS, _('Project access is given'))
            return HttpResponseRedirect(reverse('client_new_project', args=(project.id,)))

        if 'remove_target_locales' in request.POST:
            self.object = project
            target_ids = request.POST.getlist('targid_rem')
            source_of_analysis_id = Project.objects.select_related().get(pk=project.id)
            kit_id = int(source_of_analysis_id.kit_id)

            #Removing the project_target_locales
            for target_id in target_ids:
                Project.target_locales.through.objects.get(project__id=project.id, locale__id=target_id).delete()
                TranslationTaskAnalysis.objects.get(source_of_analysis=kit_id, target=target_id).delete()

            # in case of target locale deletion, delete all obsolete LocaleTranslationKit and FileAnalysis
            # in case new language, need to generate base analysis and Clear Cache
            project.clean_target_locales()
            for target_id in target_ids:
                project.recalculate_target_price(target_id)

            return HttpResponseRedirect(reverse('client_quote', args=(project.id,)))
        
        if 'edit_job' in request.POST:
            project.reset_project_from_modify_scope()
            return HttpResponseRedirect(reverse('client_new_project', args=(project.id,)))

        if 'save_quote' in request.POST:
            if form.is_valid():
                self.object = project = form.save(commit=False)
                if not self.object.quote_due:
                    project.quote_due = timezone.now()
                    project.quoted = project.quote_due
                    project.save()
                data = form.cleaned_data
                project.instructions = data['instructions']
                project.current_user = self.request.user.id
                project.save()
                project.payment_details.payment_method = data['payment_method']
                project.payment_details.ca_invoice_number = data['ca_invoice_number']
                project.payment_details.save()

                # in case of target locale deletion, delete all obsolete LocaleTranslationKit and FileAnalysis
                # in case new language, need to generate base analysis and Clear Cache
                project.clean_target_locales()

                messages.add_message(self.request, messages.SUCCESS, _('Your Job has been saved for later.'))
                return HttpResponseRedirect(reverse('client_dashboard'))
            else:
                return self.form_invalid(form)

        if 'download_quote' in request.POST:
            # todo, need PDF quote (see PDF vendor PO example)
            return self.refresh_view(form)

        if 'place_order' in request.POST and form.is_valid():
            #: :type: Project
            project = form.save(commit=False)
            self.object = project
            data = form.cleaned_data

            project.current_user = self.request.user.id

            if not project.quote_due:
                project.quote_due = timezone.now()
                project.quoted = project.quote_due

            payment_method = data['payment_method']
            if payment_method == CA_PAYMENT_CHOICE:
                project.payment_details.payment_method = payment_method
                project.payment_details.ca_invoice_number = data['ca_invoice_number']
                project.payment_details.save()
                project.transition(STARTED_STATUS)
                messages.add_message(self.request, messages.SUCCESS, _('Your Job has been ordered.'))
                return HttpResponseRedirect(self.get_success_url())
            elif payment_method == CC_PAYMENT_CHOICE:
                project.payment_details.payment_method = payment_method
                project.payment_details.save()
                project.save()
                return redirect('client_pay', project.id)
            else:
                raise ValueError("Unhandled payment choice %r" %
                                 (payment_method,))
        else:
            return self.form_invalid(form)

        if 'comment_id' in request.POST:
            instance = get_object_or_404(Comment, id=request.POST.get('comment_id', None))
            instance.comment_read_check = True
            instance.save()
            if instance:
                return HttpResponse(json.dumps({'message': 'Success'}), content_type="application/json")
            else:
                return HttpResponse(json.dumps({'message': 'Error'}), content_type="application/json")

        if 'request_user_id' in request.POST:
            comments = Comment.objects
            new_comments = comments.filter(object_pk=request.POST.get('comment_project_id'), comment_to=request.POST.get('request_user_id'), comment_read_check=False, is_removed=False, notification_type=settings.NOTIFICATION_TYPE_MESSAGE)
            new_comments.update(comment_read_check=True, filter_from_list=True, comment_read_on=timezone.now())
            if new_comments:
                return HttpResponse(json.dumps({'message': 'Success'}), content_type="application/json")
            else:
                return HttpResponse(json.dumps({'message': 'Error'}), content_type="application/json")

    def refresh_view(self, form):
        return self.render(self.get_context_data(form=form))

    def get_queryset(self):
        return Project.objects.select_related().filter(Q(client=self.request.user.account.cast(Client)) | Q(client__in=self.request.user.account.children.all()), internal_via_project=False).filter(
            Q(status=QUEUED_STATUS) | Q(status=CREATED_STATUS) | Q(status=QUOTED_STATUS)
        )

    def get_success_url(self):
        return reverse('client_project_detail', args=(self.object.id,))

    # escalate to PM for manual assignment
    # email at 7PM pacific and 7AM pacific - go to assigned translator and everyone with a PM role, and people who have active task
    # general
    # there will be some kind of final check-off

    # customer has a team, distinct from the PM
    # team roles:
    # DTP lead, Loc engineer

    # customer invoicing
    # when the customer downloads the file,
    # ok to invoice

    # download link will be redirect to blob store


class WaitingQuoteView(ClientLoginRequiredMixin, ClientMenuContextMixin, DefaultContextMixin, DetailView):
    template_name = 'clients/order/waiting_quote.html'

    def get(self, request, *args, **kwargs):
        project = self.get_object()
        if not project.kit.analyzing():
            # Waiting is over already!
            return redirect('client_quote', project.id)
        return super(WaitingQuoteView, self).get(self, request, *args, **kwargs)

    def get_queryset(self):
        return Project.objects.select_related().filter(client=self.request.user.account.cast(Client))


class ManualQuoteUpdateView(ClientLoginRequiredMixin, ClientMenuContextMixin, DefaultContextMixin, UpdateView):
    template_name = 'clients/order/manual_quote_needed.html'
    form_class = ClientManualQuoteForm
    context_object_name = 'project'

    def get_initial(self):
        job_option_object = ProjectJobOptions.objects.get_or_none(project_id=self.object.id)
        if job_option_object:
            return {
                'editable_source': job_option_object.editable_source,
                'recreation_source': job_option_object.recreation_source,
                'translation_unformatted': job_option_object.translation_unformatted,
                'translation_billingual': job_option_object.translation_billingual
            }
    
    def get_form_kwargs(self):
        logger.debug(u'ManualQuoteUpdateView get_form_kwargs')
        kwargs = super( ManualQuoteUpdateView, self).get_form_kwargs()
        kwargs.update(self.kwargs)  
        return kwargs
    
    def get_context_data(self, **kwargs):
        logger.debug(u'ManualQuoteUpdateView get_context_data')
        context = super(ManualQuoteUpdateView, self).get_context_data(**kwargs)
        pms = list(ClientTeamRole.objects.filter(
            client=self.request.user.account.cast(Client),
            role=PM_ROLE
        ))
        if len(pms) == 1:
            context['pm'] = pms[0].contact
        if len(pms) > 1:
            context['pms'] = [pm.contact for pm in pms]
        project = self.object
        context['phi_contact'] = 'mailto:' + project.phi_contact()
        comment_types = comment_filters(settings.CLIENT_USER_TYPE)
        context['client_comment_list_check'] = Comment.objects.filter(object_pk=project.id, is_removed=False).filter(*comment_types)
        context['can_access_job'] = project.can_access_job(self.request.user)
        return context

    def get(self, request, *args, **kwargs):
        logger.debug(u'ManualQuoteUpdateView get')
        try:
            self.object = self.get_object()
        except Http404:
            logger.debug(u'ManualQuoteUpdateView get - That Job Number does not exist')
            messages.add_message(self.request, messages.INFO, _('That Job Number does not exist.'))
            return HttpResponseRedirect(reverse('client_dashboard'))
        return super(ManualQuoteUpdateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        logger.debug(u'ManualQuoteUpdateView post')
        self.object = project = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if 'edit_job' in request.POST:
            logger.debug(u'ManualQuoteUpdateView post edit_job')
            self.object.reset_project_from_modify_scope()
            return HttpResponseRedirect(reverse('client_new_project', args=(self.object.id,)))
        
        if 'save_quote' in request.POST:
            logger.debug(u'ManualQuoteUpdateView post save_quote')
            self.object = form.save(commit=False)
            #: :type: Project
            data = form.cleaned_data
            job_option, created = ProjectJobOptions.objects.get_or_create(project=self.object)
            if job_option:
                job_option.editable_source = data['editable_source']
                job_option.recreation_source = data['recreation_source']
                job_option.translation_unformatted = data['translation_unformatted']
                job_option.translation_billingual = data['translation_billingual']
            if job_option.editable_source or job_option.recreation_source or job_option.translation_unformatted or job_option.translation_billingual:
                job_option.save()
            self.object.approved = data['auto_approved']
            self.object.payment_details.ca_invoice_number = data['ca_invoice_number']
            self.object.payment_details.payment_method = CA_PAYMENT_CHOICE
            self.object.payment_details.save()
            self.object.estimate_type = MANUAL_ESTIMATE
            client_manifest_ignore_holiday_flag = self.object.client.manifest.ignore_holiday_flag
            self.object.ignore_holiday_flag = client_manifest_ignore_holiday_flag
            client_manifest_is_hourly_schedule = self.object.client.manifest.is_hourly_schedule
            client_poc_tz = pytz.timezone(self.object.client_poc.user_timezone)
            self.object.quote_due = get_quote_due_date(timezone.now(),
                                                       timedelta(days=1),
                                                       client_manifest_ignore_holiday_flag,
                                                       client_manifest_is_hourly_schedule,
                                                       client_poc_tz
                                                       )
            self.object.quoted = None
            self.object.save()
            self.object.payment_details.ca_invoice_number = data['ca_invoice_number']
            self.object.payment_details.save()
            messages.add_message(self.request, messages.SUCCESS, _('Your Job has been saved for later.'))
            return HttpResponseRedirect(reverse('client_dashboard'))

        if 'download_quote' in request.POST:
            logger.debug(u'ManualQuoteUpdateView post download_quote')
            # todo, need PDF quote (see PDF vendor PO example)
            return self.refresh_view(form)

        if 'comment_id' in request.POST:
            logger.debug(u'ManualQuoteUpdateView post comment_id')
            instance = get_object_or_404(Comment, id=request.POST.get('comment_id', None))
            instance.comment_read_check = True
            instance.save()
            if instance:
                return HttpResponse(json.dumps({'message': 'Success'}), content_type="application/json")
            else:
                return HttpResponse(json.dumps({'message': 'Error'}), content_type="application/json")

        if 'request_user_id' in request.POST:
            logger.debug(u'ManualQuoteUpdateView post request_user_id')

            comments = Comment.objects
            new_comments = comments.filter(object_pk=request.POST.get('comment_project_id'), comment_to=request.POST.get('request_user_id'), comment_read_check=False, is_removed=False, notification_type=settings.NOTIFICATION_TYPE_MESSAGE)
            new_comments.update(comment_read_check=True, filter_from_list=True, comment_read_on=timezone.now())
            if new_comments:
                return HttpResponse(json.dumps({'message': 'Success'}), content_type="application/json")
            else:
                return HttpResponse(json.dumps({'message': 'Error'}), content_type="application/json")

        if 'request_quote' in request.POST and form.is_valid():
            logger.debug(u'ManualQuoteUpdateView post request_quote')

            self.object = form.save(commit=False)
            #: :type: Project
            project = self.object
            data = form.cleaned_data

            # job_option, created = ProjectJobOptions.objects.get_or_create(project=self.object)
            # if job_option:
            #     job_option.editable_source = data['editable_source']
            #     job_option.recreation_source = data['recreation_source']
            #     job_option.translation_unformatted = data['translation_unformatted']
            #     job_option.translation_billingual = data['translation_billingual']
            # if job_option.editable_source or job_option.recreation_source or job_option.translation_unformatted or job_option.translation_billingual:
            #     job_option.save()

            project.approved = data['auto_approved']
            project.payment_details.ca_invoice_number = data['ca_invoice_number']
            project.payment_details.payment_method = CA_PAYMENT_CHOICE
            project.payment_details.save()
            project.estimate_type = MANUAL_ESTIMATE
            project.created = timezone.now()
            client_manifest_ignore_holiday_flag = project.client.manifest.ignore_holiday_flag
            project.ignore_holiday_flag = client_manifest_ignore_holiday_flag
            client_manifest_is_hourly_schedule = self.object.client.manifest.is_hourly_schedule
            client_poc_tz = pytz.timezone(self.object.client_poc.user_timezone)
            self.object.quote_due = get_quote_due_date(project.created,
                                                       timedelta(days=1),
                                                       client_manifest_ignore_holiday_flag,
                                                       client_manifest_is_hourly_schedule,
                                                       client_poc_tz
                                                       )

            project.quoted = None
            project.current_user = request.user.id
            project.save()
            # generate analysis placeholder for the uploaded files
            project.generate_loc_kit_analysis()
            project.generate_localetranslationkit()
            project.transition(CREATED_STATUS)
            # send email
            project_manual_quote_needed(project)

            # create JAMS estimate
            if project.can_create_jams_estimate():
                logger.debug(u'ManualQuoteUpdateView post request_quote project.create_jams_estimate()')
                project.create_jams_estimate()

            if not project.is_phi_secure_job and project.kit.can_auto_estimate(semiauto=True) :
                # start an analysis even though it'll need to be manually reviewed, but not for phi
                logger.debug(u'ManualQuoteUpdateView post request_quote project.queue_analysis_tasks()')
                project.kit.queue_analysis_tasks()

            if settings.SALESFORCE_ENABLED:
                try:
                    logger.debug(u'ManualQuoteUpdateView post request_quote SalesforceOpportunity.objects.create_for_project()')
                    SalesforceOpportunity.objects.create_for_project(project)
                except SalesforceError:
                    logger.error("request quote SalesforceError", exc_info=True,
                                 extra={'request': request})

            logger.debug(u'ManualQuoteUpdateView post messages.SUCCESS')
            messages.add_message(self.request, messages.SUCCESS, _('Your Job has been submitted for Manual Estimate.'))
            return HttpResponseRedirect(self.get_success_url())
        else:
            logger.debug(u'ManualQuoteUpdateView post self.form_invalid')
            return self.form_invalid(form)

    def refresh_view(self, form):
        logger.debug(u'ManualQuoteUpdateView refresh_view')

        return self.render(self.get_context_data(form=form))

    def get_queryset(self):
        logger.debug(u'ManualQuoteUpdateView get_queryset')
        return Project.objects.select_related().filter(Q(client=self.request.user.account.cast(Client)) | Q(client__in=self.request.user.account.children.all()), internal_via_project=False).filter(
            Q(status=QUEUED_STATUS) | Q(status=CREATED_STATUS) | Q(status=QUOTED_STATUS)
        )

    def get_success_url(self):
        logger.debug(u'ManualQuoteUpdateView get_success_url')
        return reverse('client_dashboard')


def _new_payment_view_render(request, project, cc_form, already_paid=False):
    context = {
        'already_paid': already_paid,
        'project': project,
        'price': project.price(),
        'cc_form': cc_form,
    }
    return render(request=request, template_name='clients/order/credit_card_payment_form.html', context=context)


@client_login_required
def new_payment_view(request, proj_id):
    account = request.user.account
    project = get_object_or_404(Project, client=account, id=proj_id)

    payment_details = project.payment_details
    already_paid = (payment_details.payment_method == CC_PAYMENT_CHOICE and
                    payment_details.cc_response_auth_code)

    if already_paid:
        return _new_payment_view_render(request, project,
                                        cc_form=None, already_paid=True)

    if request.method == 'GET':
        cc_form = CreditCardForm.for_account(account)
        return _new_payment_view_render(request, project, cc_form)

    elif request.method == 'POST':
        if 'cancel' in request.POST:
            return redirect('client_quote', proj_id)

        cc_form = CreditCardForm(request.POST)

        if cc_form.is_valid():
            price = project.price()

            if request.POST['price'] != str(price):
                cc_form.add_error("", u"The project price has changed.")
                return _new_payment_view_render(request, project, cc_form)

            payment_result = payflow.process_sale(price, cc_form.cleaned_data,
                                                  request.user, project)
            if payment_result.is_approved():
                payment_details.payment_method = CC_PAYMENT_CHOICE
                payment_details.cc_response_auth_code = payment_result.pnref
                # This should be structured data if people are going to be
                # reporting on this, but we haven't had that feature req yet.
                timestamp = timezone.localtime(timezone.now())
                timestamp = timestamp.strftime('%Y-%m-%d %H:%M(%Z)')
                note = (u"%s $%s paid online through VTP" %
                        (timestamp, price))
                if payment_details.note:
                    note = u"%s\n%s\n" % (payment_details.note, note)
                payment_details.note = note
                payment_details.save()

                project.transition(STARTED_STATUS)
                messages.success(request,
                                 _(u"Credit card payment complete."))
                return redirect('client_project_detail', proj_id)
            else:
                msg = _(u"The credit card payment did not go through. Please check the card details and try again. The error was: %s" % (payment_result.respmsg,))
                cc_form.add_error("", msg)
                return _new_payment_view_render(request, project, cc_form)

        else:
            # If the form didn't validate, re-render showing form errors.
            return _new_payment_view_render(request, project, cc_form)
    else:
        raise HttpResponseNotAllowed(['GET', 'POST'])


class ClientRegisterView(ClientLoginRequiredMixin, HideSearchMixin, DefaultContextMixin, UpdateView):
    template_name = 'clients/accounts/register.html'
    context_object_name = 'user'
    form_class = ClientRegisterForm

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_url(self):
        if not self.request.user.account or self.request.user.is_client_administrator_group():
            return reverse('account_setup')
        else:
            return reverse('client_dashboard')

    def get(self, request, *args, **kwargs):
        if self.request.user.profile_complete:
            return redirect(self.get_success_url())
        return super(ClientRegisterView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        response = super(ClientRegisterView, self).form_valid(form)
        return response


def clients_for_user(user):
    email_domain = user.email.split('@')[1]
    try:
        clients = Client.objects.filter(accountemaildomain__email_domain__iexact=email_domain)
        return clients
    except:
        return None


@client_login_required
def account_setup_view(request):
    if not request.user.account:
        # does user email domain connect to any existing clients?
        if clients_for_user(request.user):
            return redirect('join_client_organization')

        request.user.account = Client.objects.create_for_user(request.user)
        request.user.save()
        request.user.add_to_group(DEPARTMENT_ADMINISTRATOR_GROUP)

    return redirect('new_client_organization', request.user.account.id)


class UpdateClientAccountView(ClientAdministratorLoginRequired, ClientMenuContextMixin, HideSearchMixin, DefaultContextMixin, UpdateView):
    form_class = ClientAccountForm
    context_object_name = 'client'
    after = None

    def get_context_data(self, **kwargs):
        context = super(UpdateClientAccountView, self).get_context_data(**kwargs)
        context['support_email'] = settings.VIA_SUPPORT_EMAIL
        context['contactus_form'] = settings.VIA_SUPPORT_CONTACT_US_FORM
        context['current_user_id'] = self.request.user.pk
        context['hide_search'] = True

        return context

    def get_queryset(self):
        return Client.objects.filter(
            pk__in=[x.id for x in self.request.user.account.children.all()] + [self.request.user.account.id]
        )

    def get_success_url(self):
        messages.add_message(self.request, messages.SUCCESS, _('Your organization has been updated.'))
        return reverse(self.after) if self.after else reverse('update_client_organization', args=(self.object.id,))

    def form_valid(self, form):
        if not self.request.user.registration_complete:
            self.request.user.registration_complete = True
            self.request.user.save()

        account = self.get_object()
        # Assume this account is new if it didn't have a name _before_
        is_new = not account.name

        # if user email domain generic public account, then don't assign to this client
        if not self.request.user.is_public_email_domain():
            # assign domain if not exist and user is client admin
            if self.request.user.is_client_administrator_group() and not self.object.accountemaildomain_set.exists():
                client_email_domain = self.request.user.email.split("@")[1]
                ced, created = ClientEmailDomain.objects.get_or_create(account=self.object, email_domain=client_email_domain)
                self.request.user.add_to_group(CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP)

        response = super(UpdateClientAccountView, self).form_valid(form)
        # To update the is_top_organization field which is not included in the form
        if self.request.user.is_client_organization_administrator and self.request.user.account.parent_id is None:
            account_update = Account.objects.filter(id=account.id).update(is_top_organization=True)

        # Assign permissions to the users according to the groups.
        # This is for the new users first sign up for new organization and child departments
        user_groups = self.request.user.groups.all()
        for group in user_groups:
            # Getting the permisions of the Group.
            permissions = group.permissions.all()
            for prm in permissions:
                self.request.user.add_user_permission(permission=prm)

        if is_new:
            # reload user to be sure user.account is up-to-date
            user = ClientContact.objects.get_or_none(id=self.request.user.id)

            ### Updating the client team role based on the parent client
            ctr_obj = ClientTeamRole.objects
            ctr_obj_ids = ctr_obj.filter(client_id=user.account.parent_id)
            for ctr_obj_id in ctr_obj_ids:
                ctr, created = ctr_obj.get_or_create(client_id=user.account_id, contact_id=ctr_obj_id.contact_id, role=ctr_obj_id.role)

            ### Updating the client manifest based on the parent client
            cmf_obj = ClientManifest.objects
            pcmf_obj = cmf_obj.get_or_none(client_id=user.account.parent_id)
            dcmf_obj, created = cmf_obj.get_or_create(client_id=user.account_id)

            if pcmf_obj and dcmf_obj:
                dcmf_obj.express_factor = pcmf_obj.express_factor
                dcmf_obj.pricing_basis = pcmf_obj.pricing_basis
                dcmf_obj.auto_estimate_jobs = pcmf_obj.auto_estimate_jobs
                dcmf_obj.auto_start_workflow = pcmf_obj.auto_start_workflow
                dcmf_obj.secure_jobs = pcmf_obj.secure_jobs
                dcmf_obj.state_secrets_validation = pcmf_obj.state_secrets_validation
                dcmf_obj.restricted_pricing = pcmf_obj.restricted_pricing
                dcmf_obj.vertical = pcmf_obj.vertical
                dcmf_obj.pricing_scheme = pcmf_obj.pricing_scheme
                dcmf_obj.pricing_memory_bank_discount = pcmf_obj.pricing_memory_bank_discount
                dcmf_obj.teamserver_tm_enabled = pcmf_obj.teamserver_tm_enabled
                dcmf_obj.minimum_price = pcmf_obj.minimum_price
                dcmf_obj.is_sow_available = pcmf_obj.is_sow_available
                dcmf_obj.is_reports_menu_available = pcmf_obj.is_reports_menu_available
                dcmf_obj.update_tm = pcmf_obj.update_tm
                dcmf_obj.teamserver_client_code = pcmf_obj.teamserver_client_code
                dcmf_obj.teamserver_client_subject = pcmf_obj.teamserver_client_subject
                dcmf_obj.save()

            ### Updating the client services based on the parent client
            cs_obj = ClientService.objects
            cs_obj_ids = cs_obj.filter(client_id=user.account.parent_id)
            if cs_obj_ids:
                cs_obj.filter(client_id=user.account_id).delete()
                for cs_obj_id in cs_obj_ids:
                    cs, created = cs_obj.get_or_create(client_id=user.account_id,
                                                       service_id=cs_obj_id.service_id,
                                                       available=cs_obj_id.available,
                                                       job_default=cs_obj_id.job_default)

            ### Send Client Welcome Email
            notify_account_welcome_email(user)

            ### Notify VIA Team / Sales Management
            notify_via_new_client_user(user)
            notify_via_new_client_account(self.object)

        return response


class JoinClientAccountView(ClientLoginRequiredMixin, HideSearchMixin, DefaultContextMixin, CreateView):
    template_name = 'clients/accounts/join_account.html'
    form_class = JoinClientForm

    def set_clients(self):
        self.clients = clients_for_user(self.request.user)

    def get_form_kwargs(self):
        self.set_clients()
        kwargs = super(JoinClientAccountView, self).get_form_kwargs()
        kwargs.update({'clients': self.clients})
        return kwargs

    def get(self, request, *args, **kwargs):
        if request.user.registration_complete:
            return redirect('client_dashboard')

        # if user already has an account request, don't let them make another
        existing = list(JoinAccountRequest.objects.filter(user=self.request.user).order_by('-created'))
        if len(existing):
            return redirect('account_approval_needed', existing[0].id)

        # if user got here somehow but doesn't actually have a matching email to any clients, 404
        self.set_clients()
        if not self.clients or request.user.account:
            raise Http404

        return super(JoinClientAccountView, self).get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('account_approval_needed', args=(self.object.id,))

    def form_valid(self, form):
        self.request.user.add_to_group(DEPARTMENT_USER_GROUP)

        if 'new_department' in self.request.POST:
            # client hierarchy limited to 2 levels for now
            parent = self.clients.filter(parent__isnull=True).first()
            self.request.user.account = Client.objects.create_for_user(self.request.user, parent=parent)
            self.request.user.save()
            self.request.user.add_to_group(DEPARTMENT_ADMINISTRATOR_GROUP)
            return redirect('new_client_organization', self.request.user.account.id)

        # Assign permissions to the users according to the groups
        # This is for the users signs up and joined in child departments.
        user_groups = self.request.user.groups.all()
        for group in user_groups:
            # Getting the permisions of the Group.
            permissions = group.permissions.all()
            for prm in permissions:
                self.request.user.add_user_permission(permission=prm)

        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.save()
        self.request.user.account = self.object.account
        self.request.user.registration_complete = True
        self.request.user.save()

        ### Send Client Welcome Email
        notify_account_welcome_email(self.request.user)

        ### Send Org Manager Email
        join_account_request(self.object)

        ### Notify VIA Team / Sales Management
        notify_via_new_client_user(self.request.user)

        return HttpResponseRedirect(self.get_success_url())


class AccountApprovalNeededView(ClientLoginRequiredMixin, ClientMenuContextMixin, HideSearchMixin, DefaultContextMixin, DetailView):
    template_name = 'clients/accounts/approval_needed.html'
    model = JoinAccountRequest
    context_object_name = 'account_request'

    def get_queryset(self):
        return super(AccountApprovalNeededView, self).get_queryset().filter(user=self.request.user)


class GroupsListView(ClientAdministratorLoginRequired, ClientMenuContextMixin, DefaultContextMixin, ListView):
    template_name = 'clients/accounts/manage_groups.html'

    def get_group_list_dict(self):
        result = []
        for group in self.object_list:
            result.append({
                'id': group.id,
                'name': group.name,
                'has_permission': group.has_permissions(user=self.request.user),
                'has_users': group.has_users()
            })
        return result

    def get_context_data(self, **kwargs):
        context = super(GroupsListView, self).get_context_data(**kwargs)
        context['current_user_id'] = self.request.user.pk
        context['group_list'] = json.dumps(self.get_group_list_dict())
        context['hide_search'] = True

        # Fetching the project and client permissions.
        check_access_reports = ClientReportAccess.objects.filter(client=self.request.user.account_id, access=True).exists()
        content_type_app_labels = ['projects', 'clients']
        content_type_models = ['project', 'client']
        if self.request.user.account.manifest.is_reports_menu_available and check_access_reports:
            content_type_app_labels.append('dwh_reports')
            content_type_models.append('clientmanager')

        perm_models = ContentType.objects.filter(app_label__in=content_type_app_labels, model__in=content_type_models)
        permission_dict = [{'perm_id': x.id, 'perm_name': x.name, 'perm_codename': x.codename, 'perm_content_type': [c.app_label.title() for c in ContentType.objects.filter(id=x.content_type_id)]}
                           for x in Permission.objects.filter(content_type__in=perm_models).order_by('content_type', 'name')]
        context['permission_dict'] = json.dumps(permission_dict)

        return context

    def get_queryset(self):
        group_list = []
        current_user_groups = GroupOwner.objects.filter(Q(user_id=self.request.user.id) | Q(user_id=None))
        for group in current_user_groups:
            group_list.append(group.group_id)
        if self.request.user.is_client_organization_administrator:
            # return ViaGroup.objects.all().order_by('name')
            return ViaGroup.objects.filter(id__in=group_list).order_by('name')
        else:
            return ViaGroup.objects.filter(~Q(name=CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP), id__in=group_list).order_by('name')

    def post(self, request, *args, **kwargs):
        instance = get_object_or_404(Group, id=request.POST.get('group_id', None))
        # Get the list of users assigned to this group, Users from same organization or department
        group_user_list = get_user_model().objects.filter(account__id=request.user.account.id, groups__id=instance.id)

        if request.POST.get('group') == 'group_permissions':
            user_permission = request.POST.get('permission_id')
            permission = Permission.objects.get(id=user_permission)
            if request.POST['option'] == 'False':
                # instance.permissions.remove(permission)
                try:
                    #Removing permission from GroupOwnerPermission(User specific permission set by Client admin)
                    group_owner_permission = GroupOwnerPermissions.objects.get(group_id=instance.id,
                        permission_id=permission.id,
                        user_id=self.request.user.id,
                        parent_account_id=self.request.user.account.id)
                    group_owner_permission.delete()
                except:
                    #Removing permission from auth_group_permissions(Global permissions set by Via admin)
                    instance.permissions.remove(permission)

                # Remove the permission to all users assigned to this group
                for grp_user in group_user_list:
                    grp_user.remove_user_permission(permission=permission)
            else:
                # instance.permissions.add(permission)
                #add permissions to GroupOwnerPermissions
                group_owner_permission = GroupOwnerPermissions(
                    group_id=instance.id,
                    permission_id=permission.id,
                    user_id=self.request.user.id,
                    parent_account_id=self.request.user.account.id,
                )
                group_owner_permission.save()
                # Add the permission to all users assigned to this group
                for grp_user in group_user_list:
                    grp_user.add_user_permission(permission=permission)

        if instance:
            return HttpResponse(json.dumps({'message': 'Success'}), content_type="application/json")
        else:
            return HttpResponse(json.dumps({'message': 'Error'}), content_type="application/json")


class UserListView(ClientAdministratorLoginRequired, ClientMenuContextMixin, DefaultContextMixin, ListView):
    template_name = 'clients/accounts/manage_users.html'
    user_dept_object_list = None

    def get_user_list_dict(self):
        result = []
        for user in self.object_list:
            result.append({
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active,
                'is_active_icon': 'fa-check-square-o' if user.is_active else 'fa-square-o',
                'title': user.title,
                'department': user.account.name,
                'group': user.user_type,
                'last_login': unicode(user.last_login.strftime("%b-%d-%Y")),
                'id': user.id,
                'is_current_user': self.request.user.pk == user.id,
                'show_delete': 'true' if self.request.user.pk == user.id or not user.is_active else 'false',
                'has_group': user.has_group(),
                'is_top_organization': user.account.is_top_organization,
            })
        return result

    def get_context_data(self, **kwargs):
        context = super(UserListView, self).get_context_data(**kwargs)
        context['current_user_id'] = self.request.user.pk
        context['user_list'] = json.dumps(self.get_user_list_dict())
        context['hide_search'] = True

        #Fetching all the Groups.
        group_list = []
        current_user_groups = GroupOwner.objects.filter(Q(user_id=self.request.user.id) | Q(user_id=None))
        for group in current_user_groups:
            group_list.append(group.group_id)

        group_dict = [{'grp_id': grp.id, 'grp_name': grp.name} for grp in ViaGroup.objects.filter(id__in=group_list).order_by('name')
                      if not grp.name == CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP or self.request.user.is_client_organization_administrator]
        context['group_dict'] = json.dumps(group_dict)

        #getting permissions
        perm_models = ContentType.objects.filter(app_label__in=['projects', 'clients'], model__in=['project', 'client'])
        context['permission_filter_list'] = [{'perm_id': x.id, 'perm_name': x.name, 'perm_codename': x.codename}
                                             for x in Permission.objects.filter(content_type__in=perm_models).order_by('name')]
        context['group_filter_list'] = group_dict

        departments_list = []
        for u in self.user_dept_object_list:
            departments_list.append(u.account.id)

        departments = Account.objects.filter(id__in=departments_list)
        context['department_filter_list'] = departments

        context['group_select_option'] = int(self.request.GET['group_filter']) if self.request.GET.get('group_filter') else 0
        context['permission_select_option'] = int(self.request.GET['permission_filter']) if self.request.GET.get('permission_filter') else 0
        context['department_select_option'] = int(self.request.GET['department_filter']) if self.request.GET.get('department_filter') else 0
        context['organization_administrator_group'] = CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP
        return context

    def get_queryset(self):
        permission_id = self.request.GET.get('permission_filter')
        group_id = self.request.GET.get('group_filter')
        department_id = self.request.GET.get('department_filter')
        status_filter = self.request.GET.get('status_filter')
        user_filter = self.request.GET.get('user_filter')

        client = get_object_or_404(Client, id=self.request.user.account.id)

        if client.manifest.enforce_customer_hierarchy and self.request.user.has_perm('clients.client_admin_access_child_departments'):
            user_list = get_user_model().objects.filter(Q(account=self.request.user.account) | Q(account__in=self.request.user.account.children.all()))\
                .order_by('-account__is_top_organization', 'account__parent', 'account', '-is_client_organization_administrator', '-is_active', 'email')
        else:
            user_list = get_user_model().objects.filter(account=self.request.user.account).order_by('-is_active', 'email')

        self.user_dept_object_list = user_list

        if user_filter:
            user_list = user_list.filter(Q(first_name__icontains=user_filter) | Q(last_name__icontains=user_filter))
        if group_id:
            user_list = user_list.filter(groups__id=group_id)
        if permission_id:
            user_list = user_list.filter(user_permissions__id=permission_id)
        if department_id:
            user_list = user_list.filter(account__id=department_id)
        if status_filter:
            status = True if status_filter == 'True' else False
            user_list = user_list.filter(is_active=status)

        return user_list

    def post(self, request, *args, **kwargs):
        instance = get_object_or_404(get_user_model(), id=request.POST.get('user_id', None))

        client_group = request.POST.get('group')
        group_id = request.POST.get('group_id')

        if request.POST['option'] == 'False':
            instance.remove_from_group(client_group)
            instance.remove_user_permission(group_id, user_id=self.request.user.id)
        else:
            instance.add_to_group(client_group)
            instance.add_user_permission(group_id, user_id=self.request.user.id)
        if instance:
            return HttpResponse(json.dumps({'message': 'Success'}), content_type="application/json")
        else:
            return HttpResponse(json.dumps({'message': 'Error'}), content_type="application/json")


def send_new_user_password_reset(new_user):
    """Send a message welcoming the new user and directing them to set
    a password.

    :param new_user: The new user to send the password reset link to.
    :type new_user: CircusUser
    :rtype: None
    """
    # Password reset only works on active users.
    assert new_user.is_active, "New user not active: %r" % (new_user,)

    # It is a little weird to build a Form to send an email, but the existing
    # password-reset-link generation is in PasswordResetForm.save().
    form = PasswordResetForm({'email': new_user.email})

    # is_valid has side-effects that need to run before form.save.
    if not form.is_valid():
        raise ValueError(form.errors)

    form.save(
        email_template_name='notifications/new_user_password_reset_email.txt',
        subject_template_name='notifications/new_user_password_reset_subject.txt',
        from_email=settings.FROM_EMAIL_ADDRESS,
        use_https=settings.LINKS_USE_HTTPS)


class CreateGroupView(ClientAdministratorLoginRequired, ClientMenuContextMixin, DefaultContextMixin, CreateView):
    template_name = 'clients/accounts/create_group.html'
    context_object_name = 'group'
    form_class = GroupCreationForm

    def get_context_data(self, **kwargs):
        context = super(CreateGroupView, self).get_context_data(**kwargs)
        context['current_user_id'] = self.request.user.pk
        context['hide_search'] = True
        return context

    def get_success_url(self):
        messages.add_message(self.request, messages.SUCCESS, _('{0} has been created.').format(self.object.name))
        return reverse('client_manage_groups')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.name = self.request.POST['name']
        self.object.save()
        group_owner = GroupOwner(
            group_id=self.object.id,
            user_id=self.request.user.id
        )
        group_owner.save()

        return HttpResponseRedirect(self.get_success_url())


class CreateUserView(ClientAdministratorLoginRequired, ClientMenuContextMixin, DefaultContextMixin, CreateView):
    template_name = 'clients/accounts/create_user.html'
    context_object_name = 'user'
    form_class = CircusUserCreationForm

    def get_form_kwargs(self):
        kwargs = super(CreateUserView, self).get_form_kwargs()
        kwargs.update({'current_user': self.request.user})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(DefaultContextMixin, self).get_context_data(**kwargs)
        context = super(CreateUserView, self).get_context_data(**kwargs)
        context['current_user_id'] = self.request.user.pk
        context['hide_search'] = True
        return context

    def get_success_url(self):
        messages.add_message(self.request, messages.SUCCESS, _('{0} has been created.').format(self.object.get_full_name()))
        return reverse('client_edit_user', args=(self.object.id,))

    def form_valid(self, form):
        #noinspection PyAttributeOutsideInit
        account = self.request.POST.get('account')
        self.object = form.save(commit=False)
        self.object.account_id = account if account else self.request.user.account.id
        self.object.registration_complete = True
        self.object.is_active = True
        self.object.user_type = settings.CLIENT_USER_TYPE
        self.object.save()
        self.object.add_to_group(DEPARTMENT_USER_GROUP)

        send_new_user_password_reset(self.object)
        return HttpResponseRedirect(self.get_success_url())


class EditUserView(ClientAdministratorLoginRequired, ClientMenuContextMixin, DefaultContextMixin, UpdateView):
    template_name = 'clients/accounts/edit_user.html'
    context_object_name = 'user'
    form_class = ClientProfileForm

    def get_context_data(self, **kwargs):
        context = super(DefaultContextMixin, self).get_context_data(**kwargs)
        context['hide_search'] = True
        context['can_access_users_groups_options'] = self.request.user.can_access_users_groups_options()
        context['can_manage_users'] = self.request.user.can_manage_users()
        return context

    def get_queryset(self):
        # return get_user_model().objects.filter(account=self.request.user.account)
        if 'pk' in self.kwargs:
            return get_user_model().objects.filter(id=self.kwargs['pk'])
        return get_user_model().objects.filter(account=self.request.user.account)

    def get_success_url(self):
        messages.add_message(self.request, messages.SUCCESS, _('{0} has been updated.').format(self.object.get_full_name()))
        return reverse('client_manage_users')

    def form_valid(self, form):
        self.object = form.save(commit=False)
        if not self.object.user_type:
            self.object.user_type = settings.CLIENT_USER_TYPE
        self.object.save()

        return HttpResponseRedirect(self.get_success_url())


@client_administrator_login_required
def disable_user(request, pk=None):
    try:
        u = get_user_model().objects.get(pk=pk)
    except:
        raise Http404

    u.is_active = False
    u.save()
    return redirect('client_manage_users')


@client_administrator_login_required
def edit_delete_group(request, pk=None, action=None):
    try:
        grp = Group.objects.get(id=pk)
    except:
        raise Http404
    if action == 'rename':
        grp.name = request.POST.get('rename_group')
        grp.save()
    else:
        # Check whether any user is added before deleting this group.
        check_user = grp.user_set.all().exists()
        if not check_user:
            grp.delete()
            messages.add_message(request, messages.SUCCESS, _('{0} group has been deleted.').format(grp.name))
        else:
            messages.add_message(request, messages.ERROR, _(u"You can not delete this group as user(s) are already assigned to this group"))

    return redirect('client_manage_groups')


@csrf_exempt
@login_required
@require_POST
def delete_asset_ajax(request, pk=None):
    asset = get_object_or_404(FileAsset, id=pk)
    project = asset.kit.project
    if not may_edit_project_loc_kit(project, request.user):
        raise PermissionDenied()
    asset.delete()
    return HttpResponse('OK')


def _filter_projects_for_client(request, projects):
    account_id = request.user.account_id
    return projects.filter(client_id=account_id)


check_analysis_status = AJAXAnalysisStatusCheck(
    project_filter=_filter_projects_for_client,
    project_ready_url=lambda project: reverse('client_quote', args=(project.id,))
)


def client_post_delivery_replace_redirect(request, pk=None):
    try:
        la = TaskLocalizedAsset.objects.get(pk=pk)
    except:
        raise Http404
    key = request.GET.get('key')
    la.post_delivery_file = re.sub('^media/', '', key)
    la.save()

    return HttpResponseRedirect(reverse('client_project_delivery', args=(la.task.project.id, la.task.service.target.lcid)))


class ProjectCommentsView(ClientLoginRequiredMixin, ClientMenuContextMixin, ListView):
    template_name = 'clients/projects/client_project_comments.html'
    model = Project

    def get_context_data(self, **kwargs):
        context = super(ProjectCommentsView, self).get_context_data(**kwargs)
        project_id = self.kwargs['project_id']
        comment_types = comment_filters(settings.CLIENT_USER_TYPE)
        context['client_comment_list_check'] = Comment.objects.filter(object_pk=project_id, is_removed=False).filter(*comment_types)
        return context


class ClientProjectCommentsListView(ClientLoginRequiredMixin, ClientMenuContextMixin, ListView):
    template_name = 'clients/projects/client_project_comments_list.html'
    context_object_name = 'messages_list'
    model = Comment
    paginate_by = settings.PAGINATE_BY_STANDARD

    def get_queryset(self):
        comments = super(ClientProjectCommentsListView, self).get_queryset()
        comments = comments.filter(comment_to=self.request.user.id, is_removed=False, filter_from_list=False, comment_read_check=False, notification_type=settings.NOTIFICATION_TYPE_MESSAGE).order_by('-id')
        return comments

    def get_context_data(self, **kwargs):
        context = super(ClientProjectCommentsListView, self).get_context_data(**kwargs)

        comments = context['messages_list']
        context['message_type'] = True
        comments_obj = Comment.objects
        i = 0
        for cmnt in comments:
            context['messages_list'][i].comments = comments_obj.filter(id=cmnt.id).order_by('-submit_date')
            cmt = comments_obj.get(id=cmnt.id)
            i += 1
        return context

    def post(self, request, *args, **kwargs):
        filter_comment = self.request.POST.get('message_list_filter')
        comment = Comment.objects.get(pk=filter_comment)
        comment.filter_from_list = True
        comment.comment_read_check = True
        comment.comment_read_on = timezone.now()
        comment.save()
        return HttpResponseRedirect(reverse('job_messages_list_page_client'))


class ClientProjectNotificationsListView(ClientLoginRequiredMixin, ListView):
    template_name = 'clients/projects/client_project_comments_list.html'
    context_object_name = 'messages_list'
    model = Comment
    paginate_by = settings.PAGINATE_BY_STANDARD

    def get_queryset(self):
        comments = super(ClientProjectNotificationsListView, self).get_queryset()
        comments = comments.filter(comment_to=self.request.user.id,is_removed=False, filter_from_list=False, comment_read_check=False, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION).order_by('-id')
        return comments

    def get_context_data(self, **kwargs):
        context = super(ClientProjectNotificationsListView, self).get_context_data(**kwargs)

        client = self.request.user.account.cast(Client)
        context['show_client_messenger'] = client.manifest.show_client_messenger
        comments = context['messages_list']
        context['message_type'] = False
        comments_obj = Comment.objects
        i = 0
        for cmnt in comments:
            context['messages_list'][i].comments = comments_obj.filter(id=cmnt.id).order_by('-submit_date')
            cmt = comments_obj.get(id=cmnt.id)
            i += 1
        return context

    def post(self, request, *args, **kwargs):
        if 'message_list_filter' in self.request.POST:
            filter_comment = self.request.POST.get('message_list_filter')
            comment = Comment.objects.get(pk=filter_comment)
            comment.filter_from_list = True
            comment.comment_read_check = True
            comment.comment_read_on = timezone.now()
            comment.save()
            return HttpResponseRedirect(reverse('job_notification_list_page_client'))
        if 'clear_all' in self.request.POST:
            comment = Comment.objects.filter(comment_to=self.request.user.id, comment_read_check=False, is_removed=False, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
            comment.update(comment_read_check=True, filter_from_list=True, comment_read_on=timezone.now())
            return HttpResponseRedirect(reverse('job_notification_list_page_client'))


class RequestedJobsView(ClientMenuContextMixin, ListView):
    template_name = 'clients/projects/request.html'
    model = Project

    def get_queryset(self):
        current_user = self.request.user.id
        manager_user_ids = [current_user]
        if self.request.user.has_perm('clients.approve_access_requested_jobs'):
            managers_list = CircusUser.objects.filter(reports_to_id=current_user)
            for mgr in managers_list:
                manager_user_ids.append(mgr.id)

        return ProjectAccess.objects.filter(project__client_poc_id__in=manager_user_ids, is_access_given=False)

    def get_context_data(self, **kwargs):
        context = super(RequestedJobsView, self).get_context_data(**kwargs)
        context['project_access_list'] = self.get_queryset()
        context['workflow_stat'] = "Requested Jobs"
        return context

    def post(self, request, *args, **kwargs):
        if 'provide_access' in request.POST:
            project_id = request.POST.getlist('provide_access')[0]
            project = Project.objects.get(pk=project_id)
            requester_id = request.POST.getlist('provide_access')[1]
            project_access = ProjectAccess.objects.filter(project_id=project_id)
            requester_obj = CircusUser.objects.get(pk=requester_id)
            if project_access:
                for PA in project_access:
                    if PA.contact.id == int(requester_id):
                        PA.is_access_given = True
                        PA.save()
                    else:
                        pass
                messages.add_message(self.request, messages.SUCCESS, _('Project access is given'))

            notify_client_job_access_provided(project, requester_obj)
            return redirect('requested_job_access')

        if 'reject_access' in request.POST:
            project_id = request.POST.getlist('reject_access')[0]
            project = Project.objects.get(pk=project_id)
            requester_id = request.POST.getlist('reject_access')[1]
            project_access = ProjectAccess.objects.filter(project_id=project_id)
            requester_obj = CircusUser.objects.get(pk=requester_id)
            if project_access:
                for PA in project_access:
                    if PA.contact.id == int(requester_id):
                        PA.is_access_given = False
                        PA.save()
                    else:
                        pass
                messages.add_message(self.request, messages.SUCCESS, _('Access for the job is rejected'))

            notify_client_job_access_rejected(project, requester_obj)
            return redirect('requested_job_access')


def no_access_job_redirect(request):
        messages.add_message(request, messages.ERROR, _(u"You don't have enough permissions to access this job. Please request the access from job owner or manager"))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
