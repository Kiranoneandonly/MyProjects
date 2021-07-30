from __future__ import unicode_literals

import codecs
import io
import json
import logging
import re
import urllib
from collections import OrderedDict
from datetime import timedelta, datetime, date
from functools import partial
from os.path import splitext
from urlparse import urljoin

import pytz
from celery import shared_task
from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.http import StreamingHttpResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.utils import html, timezone
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, TemplateView, ListView, DetailView, UpdateView
from unicodecsv import DictWriter

from accounts.models import CircusUser
from activity_log.models import Actions
from clients.models import Client, ClientManifest, ClientService, ClientReferenceFiles, TSG_ENG_ROLE, \
    SECURE_JOB_TEAM_ROLE, PHI_SECURE_JOB_TEAM_ROLE
from django_comments.models import Comment
from jams_api.engine import create_jams_job_number
from lib.filetransfers.api import serve_file
from localization_kits.engine import analysis_from_json, import_translation_v2_for_tm
from localization_kits.import_analysis import process_log_file
from localization_kits.models import LocaleTranslationKit, FileAsset, SOURCEFILE_ASSET, REFERENCEFILE_ASSET, \
    LocalizationKit
from localization_kits.viewmodels import LocalizationKitForAnalysis
from localization_kits.views import update_analysis_cookie
from prices.constants import MINIMUM_JOB_SURCHARGE
from notifications.notifications import via_rejected_task, notify_client_job_ready, notify_via_analysis_complete, \
    notify_no_task_active
from projects.duedates import add_delta_business_days, get_due_date, get_holidays, workdays_between_dates, get_number_holidays, \
    get_quote_due_date
from projects.forms import ProjectForm, ProjectNewAutoJobForm, ProjectAutoJobContinueForm, ViaInstructionsForm, \
    ViaWorkflowForm, ProjectJobOptionsForm
from projects.models import Project, BackgroundTask, ProjectTeamRole, PriceQuote, \
    MANUAL_ESTIMATE, AUTO_ESTIMATE, translation_task_remove_current_files, ProjectAccess
from projects.states import (_normalize_project_status, get_reversed_status, COMPLETED_STATUS,
                             QUEUED_STATUS, STARTED_STATUS, QUOTED_STATUS, CREATED_STATUS, CANCELED_STATUS,
                             CLOSED_STATUS, ALL_STATUS, MYJOBS_STATUS, UPDATE_TM_STATUS, UNASSIGNED_STATUS,
                             WARNING_STATUS,
                             OVERDUE_STATUS, VIA_STATUS_DETAIL, DELIVERED_STATUS, INESTIMATE_STATUS,
                             ESTIMATED_STATUS, ACTIVE_STATUS, HOLD_STATUS, UNASSIGNED_ESTIMATES_STATUS,
                             MY_ESTIMATES_STATUS, HOTLIST_STATUS, UNAPPROVED_PO)
from projects.views import get_order_by_filed_name
from quality_defects.forms import QualityDefectForm, QualityDefectCommentForm
from quality_defects.models import QualityDefect, QualityDefectComment
from services.managers import FINAL_APPROVAL_SERVICE_TYPE, DISCOUNT_SERVICE_TYPE
from services.models import Locale, ServiceType, Service
from shared import utils
from shared.managers import get_overdue_projects_filter, get_delivered_projects_filter, get_completed_projects_filter
from shared.mixins import ProjectSearchMixin
from shared.templatetags.get_item import asset_target_price
from shared.utils import delete_file_asset, comment_filters, remove_html_tags
from shared.viewmodels import ProjectTargetSetViewModel, TargetAnalysisSetViewModel, ViaMyTasksViewModel
from shared.views import DefaultContextMixin, set_filefield_from_s3_redirect
from tasks.forms import RatingForm
from tasks.make_tasks import _verify_add_client_discount_task
from tasks.models import Task, TaskLocalizedAsset, TaskLocaleTranslationKit, TranslationTaskClientPrice, \
    TranslationTask, \
    VendorPurchaseOrder
from via_portal.decorators import via_login_required
from via_portal.forms import EstimateForm, DashboardFilterForm
from projects.models import ProjectServicesGlobal, ProjectJobOptions, SecureJobAccess
import pytz
from accounts.models import CircusUser
from shared.group_permissions import PROTECTED_HEALTH_INFORMATION_GROUP
from activity_log.models import Actions
from projects.forms import ViaInstructionsForm
from django_comments.models import Comment
from projects.duedates import get_holidays
from collections import Counter
from prices.constants import MINIMUM_JOB_SURCHARGE
from decimal import Decimal
from services.models import ServiceType, Service
from services.managers import TRANSLATION_ONLY_SERVICE_TYPE, PROOFREADING_SERVICE_TYPE
from tasks.models import TranslationTaskAnalysis
from projects.set_prices import set_price, set_rate
from prices.models import ClientTranslationPrice

logger = logging.getLogger('circus.' + __name__)

# dashboard views
VIEW_DASHBOARD_ALL = 'all'
VIEW_DASHBOARD_MY = 'my'
VIEW_DASHBOARD_TEAM = 'team'

# Background Tasks
ANALYSIS = 'ANALYSIS'
PRE_TRANSLATE = 'PRE_TRANSLATE'
PSEUDO_TRANSLATE = 'PSEUDO_TRANSLATE'
MACHINE_TRANSLATE = 'MACHINE_TRANSLATE'
PREP_KIT = 'PREP_KIT'
IMPORT_TRANSLATION = 'IMPORT_TRANSLATION'
GENERATE_DELIVERY = 'GENERATE_DELIVERY'
MEMORY_DB_TM = 'MEMORY_DB_TM'
TERMINOLOGY_DB = 'TERMINOLOGY_DB'


def get_item(a_dict, key):
    return a_dict[key]


def get_holidays_during_job(project):
    if project.started_timestamp and project.due:
        start_date = project.started_timestamp
        end_date = project.due
        holiday_dates = [d.holiday_date for d in get_holidays()]
        return any([d for d in holiday_dates if start_date.date() < d <= end_date.date()])


class ViaLoginRequiredMixin(object):
    @method_decorator(via_login_required)
    def dispatch(self, *args, **kwargs):
        return super(ViaLoginRequiredMixin, self).dispatch(*args, **kwargs)


class ViaPortalFiltersMixin(object):

    def get_is_user_type(self):
        is_user_type = VIEW_DASHBOARD_ALL
        if self.kwargs:
            is_user_type = self.kwargs['is_user_type']
        return is_user_type

    def is_my(self, is_user_type):
        if is_user_type == VIEW_DASHBOARD_MY:
            return True
        else:
            return False

    def is_team(self, is_user_type):
        if is_user_type == VIEW_DASHBOARD_TEAM:
            return True
        else:
            return False

    def is_user_or_team(self, is_user_type):
        if self.is_my(is_user_type) or self.is_team(is_user_type):
            return True
        else:
            return False

    def is_all(self, is_user_type):
        if is_user_type == VIEW_DASHBOARD_ALL:
            return True
        else:
            return False


class ViaDashboardView(ViaPortalFiltersMixin, DefaultContextMixin, TemplateView):
    template_name = 'via/dashboard.html'

    def get_projects(self, is_user_type, client=None):

        user_id = self.request.user.id
        via_projects_filters = []

        if self.is_user_or_team(is_user_type):
            via_projects_filters = [Q(team__contact_id=user_id)]

        if self.is_all(is_user_type) and client is not None:
            via_projects_filters = [Q(client=client) | Q(client__parent=client)]

        self.status = _normalize_project_status(self.kwargs.get('status') or 'all')

        # dashboard should only show for last +/- 6 months
        time_now = timezone.now()
        history_date = time_now - timedelta(days=settings.HISTORY_DATE_RANGE)
        future_date = time_now + timedelta(days=settings.FUTURE_DATE_RANGE)

        order_by_field_name_sort=None
        projects = _via_projects(self, self.status, via_projects_filters, order_by_field_name_sort, history_date, future_date).distinct()
        return projects

    def get_status_counts(self, projects, link_querystr):
        time_now = timezone.now()
        # Filtering the unapproved po projects based on model method
        po_projects = projects.filter(delay_job_po=True)
        unapproved_po_ids = [p.id for p in po_projects if not p.check_po_approved()]

        statuses = [
            ('inestimate', _(u"In\N{NO-BREAK SPACE}Estimate"), 'fa-circle', 'inestimate', Q(status=CREATED_STATUS)),
            ('estimated', _(u"Estimated"), 'fa-check-circle', 'estimated', Q(status=QUOTED_STATUS)),
            ('unassigned', _(u"Unassigned"), 'fa-square-o', 'unassigned', Q(status=STARTED_STATUS, project_manager=None)),
            ('active', _(u"Active"), 'fa-check-square-o', 'active', Q(status=STARTED_STATUS, due__gte=time_now)),
            ('hold', _(u"Hold"), 'fa-pause', 'hold', Q(status=HOLD_STATUS)),
            ('overdue', _(u"Overdue"), 'fa-exclamation-circle', 'overdue', Q(status=STARTED_STATUS, due__lt=time_now)),
            ('unapproved_pos', _(u"PO\N{NO-BREAK SPACE}Approval"), 'fa-check-circle', 'unapproved_pos', Q(id__in=unapproved_po_ids)),
            ('delivered', _(u"Delivered"), 'fa-square', 'delivered', Q(status=COMPLETED_STATUS, delivered__isnull=False, completed__isnull=True)),
            ('completed', _(u"Completed"), 'fa-check-square', 'completed', Q(status__in=[COMPLETED_STATUS, CLOSED_STATUS], completed__isnull=False)),
        ]

        status_counts = OrderedDict()
        url_name = 'via_jobs_status_list'
        for name, label, icon, job_status, query in statuses:
            url = reverse(url_name, args=(job_status,))
            if link_querystr:
                url = urljoin(url, link_querystr)
            status_counts[name] = {
                'id': '%s_count' % (name,),
                'label': label,
                'icon': icon,
                'class': 'peity_bar_%s' % (name,),
                'url': url,
                'count': projects.filter(query).count(),
            }

        return status_counts

    def get_context_data(self, **kwargs):
        context = super(ViaDashboardView, self).get_context_data(**kwargs)
        request = self.request
        is_user_type = self.get_is_user_type()

        client = None
        link_querystr = ""
        filter_form = DashboardFilterForm(self.request.GET)
        if filter_form.is_valid():
            client = filter_form.cleaned_data['client']
            link_querystr = '?' + urllib.urlencode({'client': client.account_number})
        else:
            if request.GET.getlist('client'):
                context['del_cookie'] = True
                client = None
                link_querystr = None
            elif self.request.COOKIES.has_key('client'):
                client_account_number = request.COOKIES['client']
                link_querystr = '?' + urllib.urlencode({'client': client_account_number})
                client = (Client.objects
                          .filter(account_number=client_account_number)
                          .order_by("parent")
                          .last())
                context['client'] = client
                context['redirect'] = link_querystr

        context['filter_form'] = filter_form
        if client:
            context['client'] = client

        all_jobs_url = reverse('via_jobs_list')
        if link_querystr:
            all_jobs_url = urljoin(all_jobs_url, link_querystr)
        context['all_jobs_url'] = all_jobs_url

        context['my_dashboard'] = 0
        context['team_dashboard'] = 0
        if self.is_my(is_user_type):
            link_querystr = '?' + urllib.urlencode({'user': self.request.user.id})
            context['my_dashboard'] = 1
        elif self.is_team(is_user_type):
            link_querystr = '?' + urllib.urlencode({'user': self.request.user.id})
            context['team_dashboard'] = 1

        projects = self.get_projects(is_user_type, client=client)
        context['status_counts'] = self.get_status_counts(projects, link_querystr)
        context['calendar_events'] = []
        not_for_calendar = Q(status__in=[
            QUEUED_STATUS, CREATED_STATUS, HOLD_STATUS, QUOTED_STATUS, CANCELED_STATUS, COMPLETED_STATUS
        ])
        #calendar data
        calendar_events = projects.exclude(not_for_calendar).order_by("due")
        for project in calendar_events:
            self._ensure_project_dates(project)

            project_started_timestamp = None
            project_due = None
            if project.is_approved_job_status():
                project_started_timestamp = project.started_timestamp
                project_due = project.due
            else:
                project_started_timestamp = project.created
                project_due = project.quote_due

            context['calendar_events'].append(
                {
                    'title': project.job_number,
                    'start': unicode(project_started_timestamp),
                    'end': unicode(project_due),
                    'status': unicode(project.status),
                    'url': reverse('via_job_detail_overview', args=(project.id,)),
                    'backgroundColor': project.calendar_status,
                    'borderColor': '#757575',
                    'warnings': '',
                }
            )

        my_tasks = ViaMyTasksViewModel(self.request.user, is_user_type, client)
        context['my_tasks'] = my_tasks
        context['client_notification_unread_count'] = Comment.objects.filter(comment_to=self.request.user.id,is_removed=False, comment_read_check=False, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION).count()
        return context

    def _ensure_project_dates(self, project):
        # This has been in the dashboard view as a fail-safe to prevent trying to add things to the calendar when
        # they don't have dates. However, it's pretty nuts that the act of viewing the dashboard may have the
        # side-effect of setting timestamps and deadlines, so log these as errors.
        project.current_user = self.request.user.id

        if project.is_created_status():
            if not project.quote_due:
                logger.error("%s (id=%s) is a %s project without quote_due" % (project.job_number, project.id, project.status), extra={'request': self.request})
                client_manifest_ignore_holiday_flag = project.client.manifest.ignore_holiday_flag
                project.ignore_holiday_flag = client_manifest_ignore_holiday_flag
                project.quote_due = add_delta_business_days(project.created, timedelta(days=1), client_manifest_ignore_holiday_flag)
                project.save()
        else:
            if not project.started_timestamp:
                logger.error("%s (id=%s) is a %s project without started_timestamp" % (project.job_number, project.id, project.status), extra={'request': self.request})
                project.started_timestamp = project.created
                project.save()
            if not project.due:
                logger.error("%s (id=%s) is a %s project without due date" % (project.job_number, project.id, project.status), extra={'request': self.request})
                project.due = get_due_date(project.started_timestamp, timedelta(days=3), project.ignore_holiday_flag)
                project.save()

    def render_to_response(self, context, **response_kwargs):
        response = super(ViaDashboardView, self).render_to_response(context, **response_kwargs)
        try:
            if 'redirect' in context:
                return HttpResponseRedirect(context['redirect'])
            if 'del_cookie' in context:
                response.delete_cookie('client')
            if 'client' in context:
                response.set_cookie("client", context['client'].account_number)
        except:
            ''
        else:
            ''
        return response


class ViaMyTasksStatusView(ViaLoginRequiredMixin, ViaPortalFiltersMixin, DefaultContextMixin, TemplateView):
    template_name = 'via/tasks/tasks.html'

    def render_to_response(self, context, **response_kwargs):
        response = super(ViaMyTasksStatusView, self).render_to_response(context, **response_kwargs)
        try:
            if 'del_cookie' in context:
                response.delete_cookie('client')
        except:
            ''
        else:
            ''
        return response

    def get_context_data(self, status=None, **kwargs):
        context = super(ViaMyTasksStatusView, self).get_context_data(**kwargs)
        if self.request.GET.getlist('client'):
                client = None
                context['del_cookie'] = True
        elif self.request.COOKIES.has_key('client'):
                client_account_number = self.request.COOKIES['client']
                client = (Client.objects
                          .filter(account_number=client_account_number)
                          .order_by("parent")
                          .last())
        else:
            client = None

        is_user_type = self.get_is_user_type()
        if self.is_my(is_user_type):
            context['home_url'] = reverse('my_dashboard', kwargs={'userid': self.request.user.id, 'is_user_type': is_user_type})
        elif self.is_team(is_user_type):
            context['home_url'] = reverse('team_dashboard', kwargs={'userid': self.request.user.id, 'is_user_type': is_user_type})
        else:
            context['home_url'] = reverse('via_dashboard')

        my_tasks = ViaMyTasksViewModel(self.request.user, is_user_type, client=client)
        context['is_user_type'] = is_user_type
        context['client'] = client
        context['via_tasks'] = my_tasks
        current_status = my_tasks.statuses.get(status)
        context['current_status_name'] = current_status.name
        context['current_status_status'] = current_status.status
        context['current_status_is_status_final_approval'] = current_status.is_status_final_approval
        context['ratingform'] = RatingForm()

        try:
            paginator = Paginator(current_status.tasks, settings.TASKS_PAGINATE_BY_STANDARD)
            page = self.request.GET.get('page')
            tasks = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            tasks = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            tasks = paginator.page(paginator.num_pages)

        context['tasks_status'] = tasks
        return context

    def post(self, request, *args, **kwargs):

        if 'task_rating_form' in request.POST:
            form = RatingForm(request.POST)
            if form.is_valid():
                instance = get_object_or_404(Task, id=request.POST.get('TaskId'))
                instance.rating = int(request.POST.get('rating'))
                instance.save()
                return HttpResponse(json.dumps({'message': 'Saved'}))
            else:
                return HttpResponse(json.dumps({'message': 'Error'}))

        if 'accept_pending_task' in request.POST:
            task_id = request.POST['accept_pending_task']
            try:
                accept_task(request, pk=task_id, locale_id=None)
            except:
                raise Http404

        if 'reject_active_task' in request.POST:
            task_id = request.POST['reject_active_task']
            try:
                reject_task(request, pk=task_id)
            except:
                raise Http404

        return HttpResponseRedirect(reverse('my_tasks_status', args=(self.kwargs['is_user_type'], self.kwargs['status'])))


def _via_projects(self, status=ALL_STATUS, via_projects_filtering=None, order_by_field=None, history_date=None, future_date=None):
    reversed_status = get_reversed_status(status)
    via_projects_filter = []
    if reversed_status in [ALL_STATUS]:
        via_projects_filter = []
    elif reversed_status in [QUEUED_STATUS]:
        via_projects_filter = [Q(status=QUEUED_STATUS)]
    elif reversed_status in [INESTIMATE_STATUS, CREATED_STATUS]:
        via_projects_filter = [Q(status=CREATED_STATUS)]
    elif reversed_status in [MY_ESTIMATES_STATUS]:
        via_projects_filter = [Q(estimator_id=self.request.user.id)]
    elif reversed_status in [UNASSIGNED_ESTIMATES_STATUS]:
        via_projects_filter = [Q(status=CREATED_STATUS) & Q(estimator_id=None)]
    elif reversed_status in [HOTLIST_STATUS]:
        via_projects_filter = [Q(status=CREATED_STATUS) & Q(quoted__isnull=True)]
    elif reversed_status in [ESTIMATED_STATUS, QUOTED_STATUS]:
        via_projects_filter = [Q(status=QUOTED_STATUS)]
    elif reversed_status in [HOLD_STATUS]:
        via_projects_filter = [Q(status=HOLD_STATUS)]
    elif reversed_status in [ACTIVE_STATUS, STARTED_STATUS, WARNING_STATUS]:
        via_projects_filter = [Q(status=STARTED_STATUS)]
    elif reversed_status in [OVERDUE_STATUS]:
        via_projects_filter = get_overdue_projects_filter()
    elif reversed_status in [DELIVERED_STATUS]:
        via_projects_filter = get_delivered_projects_filter()
    elif reversed_status in [COMPLETED_STATUS]:
        via_projects_filter = get_completed_projects_filter()
    elif reversed_status in [CANCELED_STATUS]:
        via_projects_filter = [Q(status=CANCELED_STATUS)]
    elif reversed_status in [UNASSIGNED_STATUS]:
        via_projects_filter = [Q(project_manager__isnull=True) & Q(status=STARTED_STATUS)]
    elif reversed_status in [UPDATE_TM_STATUS]:
        via_projects_filter = [
            Q(status=COMPLETED_STATUS) &
            Q(kit__analysis_code__gt='') &
            Q(kit__tm_update_completed__isnull=True)
        ]
    elif reversed_status in [MYJOBS_STATUS]:
        user_id = self.request.user.id
        via_projects_filter = [
            Q(team__contact_id=user_id) &
            Q(status__in=[CREATED_STATUS, QUOTED_STATUS, STARTED_STATUS])
        ]

    elif reversed_status in [UNAPPROVED_PO]:
        via_projects_filter = [
            Q(delay_job_po=True)
        ]

    if via_projects_filter is None:
        via_projects_filter = []

    if history_date and future_date:
        via_projects_filter.extend([Q(modified__range=(history_date, future_date))])

    if via_projects_filtering:
        via_projects_filter.extend(via_projects_filtering)

    project_obj = Project.objects

    project_results = project_obj.select_related()\
        .prefetch_related('target_locales', 'restricted_locations', 'services', 'services_global')\
        .filter(*via_projects_filter)\
        .distinct()


    # TODO Need to better handle this feature... can show to all VIA Users and let it project show Restricted message (hard to find)
    # project_results = project_obj.select_related() \
    #     .prefetch_related('target_locales', 'restricted_locations', 'services', 'services_global') \
    #     .filter(*via_projects_filter)\
    #     .filter(Q(is_secure_job=False))\
    #     .distinct()

    # Getting the secure jobs
    # secure_jobs_list = SecureJobAccess.objects.all().distinct().select_related()
    # secure_job_ids = []
    # for secure_job in secure_jobs_list:
    #     # Whether the current logged in VIA user is in the ClientTeamRole of this secure job
    #     on_secure_job_project_team = any([team.contact_id for team in secure_job.project.team.filter(contact_id=self.request.user.id)])
    #
    #     if on_secure_job_project_team or self.request.user.is_superuser:
    #         secure_job_ids.append(secure_job.project.id)
    #
    # secure_jobs = project_obj.filter(id__in=secure_job_ids).filter(*via_projects_filter).distinct()
    # project_results = project_results | secure_jobs

    if reversed_status in [UNAPPROVED_PO]:
        unapproved_po_ids = [p.id for p in project_results if not p.check_po_approved()]
        via_projects_filter = [
            Q(id__in=unapproved_po_ids)
        ]

        project_results = project_results.filter(*via_projects_filter).distinct()

    if order_by_field:
        reverse_order = False
        if '-' in order_by_field:
            reverse_order = True

        if 'price' in order_by_field:
            via_projects = sorted(project_results, key=lambda t: t.price(), reverse=reverse_order)
        elif 'auto_estimate' in order_by_field:
            via_projects = sorted(project_results, key=lambda t: t.is_auto_estimate(), reverse=reverse_order)
        elif 'warnings' in order_by_field:
            via_projects = sorted(project_results, key=lambda t: t.client_warnings(), reverse=reverse_order)
        elif 'express' in order_by_field:
            via_projects = sorted(project_results, key=lambda t: t.is_express_speed(), reverse=reverse_order)
        else:
            via_projects = project_results.order_by(order_by_field)
    else:
        via_projects = project_results.order_by('due', 'quote_due', 'created')

    if reversed_status in [WARNING_STATUS]:
        via_projects = [p for p in via_projects if p.warnings]

    return via_projects


class ProjectListMixin(object):
    template_name = 'via/projects/list.html'
    context_object_name = 'project_list'
    paginate_by = settings.PAGINATE_BY_STANDARD
    status = None
    _client = None
    _client_id = None
    _user = None
    _user_id = None

    def get_context_data(self, **kwargs):
        context = super(ProjectListMixin, self).get_context_data(**kwargs)

        list_url_parameter = []
        if self._client_id or self._user_id:
            list_url_parameter.append('?')
        if self._client_id:
            list_url_parameter.append('client=' + self._client_id)
        if self._user_id:
            if self._client_id:
                list_url_parameter.append('&')
            list_url_parameter.append('user=' + self._user_id)

        projects = context['project_list']
        service_dict = {}
        for project in projects:
            services = project.tasks_service()
            service_dict[project.id] = services
            project.status = _normalize_project_status(project.status)
            reversed_status = OVERDUE_STATUS if project.is_overdue() else get_reversed_status(project.status)
            project.workflow = VIA_STATUS_DETAIL[reversed_status]

        for status, status_details in VIA_STATUS_DETAIL.items():
            url_status_parameter = status_details.get('url_status_parameter')
            status_details_url = ''
            if not url_status_parameter:
                status_details_url = reverse('via_jobs_list')
            else:
                status_details_url = reverse('via_jobs_status_list', kwargs={'status': url_status_parameter})

            if list_url_parameter:
                status_details_url += ''.join(list_url_parameter)
            status_details['url'] = status_details_url

        context['service'] = service_dict
        context['client'] = self._client
        context['VIA_STATUS_DETAIL'] = VIA_STATUS_DETAIL
        reversed_status = get_reversed_status(self.status)
        context['workflow_status'] = VIA_STATUS_DETAIL[reversed_status]
        workflow_status_export_url = reverse('via_jobs_status_list_export', kwargs={'status': reversed_status})
        if list_url_parameter:
            workflow_status_export_url += ''.join(list_url_parameter)
        context['workflow_status']['export_url'] = workflow_status_export_url
        return context

    def get_queryset(self):

        request = self.request
        self.order_by = request.GET.get('order_by')
        self.first_char = ''
        self.order_by_field_name = None
        self.order_by_field_name_sort = None
        if self.order_by:
            if self.order_by[0] == '-':
                self.first_char = self.order_by[0]
                self.order_by = self.order_by[1:]

            self.order_by_field_name = get_order_by_filed_name(self.order_by)
            self.order_by_field_name_sort = str(self.first_char) + str(self.order_by_field_name)

        via_projects_filters = []
        if 'client' in request.GET:
            # lookup by account number because PMs know account numbers.
            # multiple departments have the same account number though, so try to find a parent.
            client_id = request.GET['client']
            self._client_id = client_id

            not_client = True if u'-' in client_id else False
            if not_client:
                client_id = client_id.replace(u'-', u'') if not_client else client_id

            try:
                client = (Client.objects
                          .filter(account_number=client_id)
                          .order_by("parent")
                          .last())
            except Client.DoesNotExist:
                messages.error(request, "Client ID not found: %s" % (client_id,))
            else:
                self._client = client

                client_filter = []
                if not_client:
                    client_filter = ~Q(client__account_number=client_id)
                    if client and client.children.exists():
                        client_filter = client_filter & ~Q(client__parent=client)
                else:
                    client_filter = Q(client__account_number=client_id)
                    if client and client.children.exists():
                        client_filter = client_filter | Q(client__parent=client)

                # projects = projects.filter(client_filter)
                via_projects_filters = [client_filter]

        if 'user' in request.GET:
            # lookup by current logged in user.
            user_id = request.GET['user']
            self._user_id = user_id
            try:
                via_projects_filters = [Q(team__contact_id=user_id)]
            except:
                messages.error(request, "User ID not found: %s" % (user_id,))

        # projects = Project.objects.select_related().order_by('-job_number')
        self.status = _normalize_project_status(self.kwargs.get('status') or 'all')
        projects = _via_projects(self, self.status, via_projects_filters, self.order_by_field_name_sort)
        return projects


class ProjectSearchView(ViaLoginRequiredMixin, ProjectListMixin, ProjectSearchMixin, DefaultContextMixin, ListView):
    status = ALL_STATUS
    template_name = 'via/projects/search.html'

    def get_context_data(self, **kwargs):
        context = super(ProjectSearchView, self).get_context_data(**kwargs)
        context['search_query'] = self.search_query
        return context

    def get_queryset(self):
        # noinspection PyAttributeOutsideInit
        self.search_query = self.request.GET.get('q', '').strip()
        if not self.search_query:
            self.search_query = ""
            return []

        projects = super(ProjectSearchView, self).get_queryset().order_by('-job_number')
        matches = self.get_matches(projects, self.search_query)
        matches = matches.prefetch_related('client_poc', 'account_executive', 'project_manager', 'estimator')
        return matches


class ProjectListView(ViaLoginRequiredMixin, ProjectListMixin, DefaultContextMixin, ListView):

    def get_queryset(self):
        return super(ProjectListView, self).get_queryset()

    def post(self, request, status=None, pk=None):
        form = ViaInstructionsForm(self.request.POST or None)
        if form.is_valid():
            project_id = self.request.POST['project_id']
            project = Project.objects.select_related().get(pk=project_id)
            project.instructions_via = self.request.POST.get('via_instructions')
            project.current_user = self.request.user.id
            project.save()
            return HttpResponse(json.dumps({'message': 'Saved'}))
        else:
            return HttpResponse(json.dumps({'message': 'Error'}))


class ProjectListViewExport(ViaLoginRequiredMixin, ProjectListMixin, DefaultContextMixin, ListView):
    paginate_by = settings.PAGINATE_BY_LARGE

    # get_matches doesn't use object state, so reduce our mixin count.
    _get_matches = ProjectSearchMixin().get_matches

    def get_queryset(self):
        # todo add filtering by client, team and user

        self.status = VIA_STATUS_DETAIL[self.kwargs.get('status')]
        projects = super(ProjectListViewExport, self).get_queryset()
        search_query = self.request.GET.get('q')
        if search_query:
            matches = self._get_matches(projects, search_query)
            matches = sorted(matches, key=lambda project: project.job_number, reverse=True)
            return matches
        return projects

    def csv(self, projects):
        """
        :type projects: iterable of projects.models.Project
        """
        stream = io.BytesIO()
        stream.write(u'\ufeff'.encode('utf8'))

        headers = [
            'Job', 'Speed', 'Warnings', 'Approved', 'Internal', 'Workflow',
            'Purchase Order', 'Files', 'Source', 'Targets', 'Price',
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
                'Internal': project.internal_via_project,
                'Job': project.job_number,
                'Workflow': project.workflow.get('text'),
                'Purchase Order': project.payment_details.ca_invoice_number,
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

        filename = 'via-jobs-%s%s.csv' % (get_reversed_status(self.status), query_slug)
        content = self.csv(context['project_list'])
        response = StreamingHttpResponse(content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="%s"' % (filename,)
        return response


class DocumentPriceExport(ViaLoginRequiredMixin, ListView):
    paginate_by = settings.PAGINATE_BY_LARGE
    model = Project

    def csv(self, project):
        """
        :type projects: iterable of projects.models.Project
        """
        stream = io.BytesIO()
        stream.write(u'\ufeff'.encode('utf8'))

        headers = [
            'Job', 'Target Language', 'Document', 'Price', 'Wordcount'
        ]

        csvwriter = DictWriter(stream, headers)
        csvwriter.writeheader()

        # project = Project.objects.select_related().get(pk=int(self.kwargs['project']))
        record = {}

        for target in project.target_locales.all():
            doc_price_details = {}

            for asset in project.kit.source_files():
                asset_object = asset_target_price(asset.id, target.id)
                target_details = project.target_price_details()
                target_object = target_details[target.id]
                if asset_object:
                    if len(project.kit.source_files()) == 1:
                        doc_price_details[asset.orig_name] = [target_object.target_price, asset_object.get('asset_wordcount')]
                    else:
                        doc_price_details[asset.orig_name] = [asset_object.get('asset_net_price'), asset_object.get('asset_wordcount')]

            for key, value in doc_price_details.iteritems():
                record.update({
                    'Job': project.job_number,
                    'Target Language': target,
                    'Document': key,
                    'Price': value[0],
                    'Wordcount': value[1],
                })

                csvwriter.writerow(record)

        return stream.getvalue()

    def render_to_response(self, context):
        project = Project.objects.select_related().get(pk=int(self.kwargs['project']))
        filename = 'job-language-price-per-document-%s.csv' % (project.id)
        content = self.csv(project)
        response = StreamingHttpResponse(content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="%s"' % (filename,)
        return response


class ProjectDetailMixin(DefaultContextMixin):
    model = Project
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        from notifications.models import NotificationMute

        context = super(ProjectDetailMixin, self).get_context_data(**kwargs)
        project = context.get('project')
        if project:
            #Removing the large_jobs_approvals when the job price is changed to below 10K
            if project.is_inestimate_status() and not project.large_jobs_check() and project.check_approvers_exists():
                project.remove_approvals_on_small_job()

            #Sometimes the approval doesnt fully make it so we have an Active job, not approved, so fix it.
            if project.is_approved_job_status() and not project.approved:
                project.approved = True
                project.current_user = self.request.user.id
                project.save()
            project.status = _normalize_project_status(project.status)
            reversed_status = OVERDUE_STATUS if project.is_overdue() else get_reversed_status(project.status)
            project.workflow = VIA_STATUS_DETAIL[reversed_status]
            context['VIA_STATUS_DETAIL'] = VIA_STATUS_DETAIL
            context['workflow_status'] = VIA_STATUS_DETAIL[reversed_status]
            context['muted'] = NotificationMute.objects.project_muted(project)
            context['is_sow_available'] = project.tasks_are_priced()
            context['can_edit_job'] = project.can_edit_job(self.request.user.country)

            context['secure_hierarchy'] = project.client.manifest.enforce_customer_hierarchy
            context['secure_jobs'] = project.client.manifest.secure_jobs
            context['restricted_locations'] = project.project_restricted_locations_list()
            context['can_access_secure_job'] = project.can_via_user_access_secure_job(self.request.user)
            # Show error message that a PHI job was created for a non-PHI Customer
            context['phi_for_non_phi_secure_client'] = project.is_phi_secure_job and not project.is_phi_secure_client_job()
            if project.is_phi_secure_job:
                context['via_user_phi_group_enabled'] = project.is_via_user_phi_group_enabled(self.request.user)

            note_parts = []
            if project.client.manifest.note:
                note_parts.append(html.escape(project.client.manifest.note))

            if project.client.parent:
                parent_note = ClientManifest.objects.get(client=project.client.parent).note
                if parent_note:
                    note_parts.append(html.escape(parent_note))

            context['client_note'] = '<hr />'.join(note_parts)
        return context


class ProjectOverviewView(ViaLoginRequiredMixin, ProjectDetailMixin, DefaultContextMixin, UpdateView):
    template_name = 'via/projects/detail/overview.html'
    form_class = ProjectForm

    def post(self, request, *args, **kwargs):

        if 'join_secure_job_phi_team' in request.POST:
            ProjectTeamRole.objects.create(project_id=request.POST.get('project_id'),
                                           contact_id=request.user.id,
                                           role=PHI_SECURE_JOB_TEAM_ROLE)
            messages.add_message(self.request, messages.SUCCESS, _(u"You have been added successfully as a PHI Secure Job Team Member."))
            return HttpResponseRedirect(reverse('via_job_detail_overview', args=(self.kwargs['pk'],)))

        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            #noinspection PyAttributeOutsideInit
            self.object = form.save(commit=False)
            #: :type: Project
            project = self.object
            project.current_user = self.request.user.id
            if project.is_phi_secure_job and not project.is_secure_job:
                project.is_secure_job = True
            project.save()
            form.save_m2m()
            project.assign_team()

            data = form.cleaned_data
            project.payment_details.payment_method = data['payment_method']
            project.payment_details.ca_invoice_number = data['ca_invoice_number']
            project.payment_details.save()

            reschedule_all_due_dates = None
            if any("started_timestamp" == s for s in form.changed_data):
                reschedule_all_due_dates = request.POST.get('reschedule_all_due_dates')
                if reschedule_all_due_dates:
                    self.object.save()
                    level, message = project.reschedule_due_dates(self.request.user)
                    messages.add_message(self.request, level, message)

            if request.POST['set_costs'] == 'true':
                project.set_rates_and_prices()

            # if DELAY PO = TRUE, then FALSE passed was we need to wait, vice versa
            project.set_create_po_needed(not project.delay_job_po)

            # If there are unassigned Final Approval tasks, have the PM pick them up.
            if project.project_manager and project.task_set.filter(
                    service__service_type__code=FINAL_APPROVAL_SERVICE_TYPE,
                    assignee_object_id__isnull=True).exists():
                project.pickup_final_approval_tasks(project.project_manager)

            if project.is_inestimate_status():
                # in case of target locale deletion, delete all obsolete LocaleTranslationKit and FileAnalysis
                # in case new language, need to generate base analysis and Clear Cache
                project.clean_target_locales()
                project.clean_pricing()

            _message_text = u''
            if reschedule_all_due_dates:
                _message_text += u'. {0}.'.format(_(u'Dates Rescheduled'))

            messages.add_message(self.request, messages.SUCCESS, _(u"Job Saved: {0} {1}").format(project.job_number, _message_text))
            return HttpResponseRedirect(self.get_success_url())
        else:
            messages.add_message(self.request, messages.ERROR,
                                 _(u"Job Not Saved.: {0}").format(remove_html_tags(str(form._errors))))
            return self.form_invalid(form)

    def get_success_url(self):
        return reverse('via_job_detail_overview', args=(self.object.id,))

    def get_context_data(self, **kwargs):
        context = super(ProjectOverviewView, self).get_context_data(**kwargs)
        # know whether the jog is over a holiday
        project = self.object

        context['has_instructions_client'] = True if project.instructions else False
        context['has_instructions_via'] = True if project.instructions_via else False
        context['has_instructions_vendor'] = True if project.instructions_vendor else False

        context['holidays_during_job'] = get_holidays_during_job(project)
        context['client_message_unread_count'] = Comment.objects.filter(object_pk=project.id, comment_to=self.request.user.id, is_removed=False, comment_read_check=False, notification_type=settings.NOTIFICATION_TYPE_MESSAGE).count()
        context['is_phi_secure_client'] = project.client.is_phi_secure_client()

        return context


class ProjectEstimateView(ViaLoginRequiredMixin, ProjectDetailMixin, DefaultContextMixin, UpdateView):
    template_name = 'via/projects/detail/estimate.html'
    form_class = EstimateForm
    # default active_tab
    active_tab = 'details'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        context = super(ProjectEstimateView, self).get_context_data(**kwargs)
        if self.object.kit.source_files().exists():
            context['active_tab'] = self.active_tab
        else:
            context['active_tab'] = 'source'

        project = context['project']
        project_targets = ProjectTargetSetViewModel(self.object)
        project_target_tasks = OrderedDict()
        for target in project_targets.targets:
            for task in sorted(target.tasks, key=lambda task: task.id):
                key = task.service.service_type.category
                if key not in project_target_tasks:
                    project_target_tasks[key] = []
                project_target_tasks[key].append(task)

        context['project_target_tasks'] = project_target_tasks

        target_analyses = OrderedDict()
        for target in project.target_locales.order_by("description"):
            target_analyses[target] = TargetAnalysisSetViewModel(target, project, include_placeholder=True)
        context['target_analyses'] = target_analyses
        if target_analyses:
            context['project_memory_bank_discount_exists'] = target_analyses.items()[0][1].memory_bank_discount_exists
            context['global_mbd_exists'] = any(item[1].total_memory_bank_discount for item in target_analyses.items() if item[1].total_memory_bank_discount)
        context['kit_vm'] = LocalizationKitForAnalysis(project.kit)
        context['due_date_flag'] = Project.is_due_date_changed(self.object, project.id, None)
        if context['due_date_flag']:
            days_between = workdays_between_dates(project.started_timestamp, project.due)
            holidays = get_number_holidays(project.started_timestamp.date(), project.due.date())

            if not project.client.manifest.ignore_holiday_flag:
                context['days_between'] = abs(days_between) - len(holidays)
            else:
                context['days_between'] = abs(days_between)

        if project.has_workflow_sub_tasks():
            context['quote'] = project.sub_task_quote()
        else:
            context['quote'] = project.quote()
        context['holidays_during_job'] = get_holidays_during_job(project)
        context['project_target_locales'] = ProjectTargetSetViewModel(project, billable_only=True)
        context['project_asset_documents'] = project.kit.source_files()
        context['client_message_unread_count'] = Comment.objects.filter(object_pk=project.id,comment_to=self.request.user.id,is_removed=False, comment_read_check=False, notification_type=settings.NOTIFICATION_TYPE_MESSAGE).count()
        service_list = [service for service in project.services.all() if service.translation_task is False]
        context['services'] = project.add_fa_service(service_list)
        context['service_value'] = ProjectServicesGlobal.objects.filter(project=project)
        standard_tat, express_tat = project.get_project_tat()
        if express_tat >= standard_tat:
            messages.add_message(self.request, messages.ERROR, _(u"Express TAT is equal/longer than Standard TAT : {0}").format(project.job_number))

        return context

    def get(self, request, *args, **kwargs):
        project = self.get_object()

        _verify_add_client_discount_task(project)

        self.active_tab = request.GET.get('active_tab', self.active_tab)
        return super(ProjectEstimateView, self).get(request, *args, **kwargs)

    def _import_analysis_file(self, analysis_file):
        extension = splitext(analysis_file.name)[1].lower()
        if extension == '.json':
            return self._import_analysis_json_file(analysis_file)
        else:
            return self._import_analysis_csv_file(analysis_file)

    def _import_analysis_json_file(self, json_file):
        project = self.object
        try:
            file_bytes = json_file.read()
            # These JSON files are saved by something which starts them with a
            # BOM, which our json-parsing tools do not expect.
            file_text = codecs.decode(file_bytes, 'utf-8-sig')
            json_analysis = json.loads(file_text)
            analysis_from_json(project.kit, json_analysis)
        except Exception, error:
            logger.error("ProjectEstimateView._import_analysis_from_json failed.", exc_info=True)
            messages.error(self.request, _(u"Error processing analysis JSON. %s" % (error,)))

    def _import_analysis_csv_file(self, csv_file):
        project = self.object
        errors = process_log_file(project, csv_file)
        if errors:
            msg = '\n'.join(errors)
            messages.error(self.request, _(u"Error processing log: %s" % (msg,)))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if 'save_global_services_defaults' in request.POST:
            self.object.clean_pricing()
            quantity_dic = self.object.generate_default_service_global_quantity()
            self.object.save_service_global_quantity(quantity_dic)
            messages.add_message(self.request, messages.SUCCESS, _(u"Job Saved : Service Global Quantity : Defaults : {0}").format(self.object.job_number))
            params = urllib.urlencode({'active_tab': 'services'})
            return HttpResponseRedirect(reverse('via_job_detail_estimate', args=(self.kwargs['pk'],)) + '?' + params)

        if 'save_global_services' in request.POST:
            self.object.clean_pricing()
            quantity_dic = dict(request.POST.iterlists())
            self.object.save_service_global_quantity(quantity_dic)
            messages.add_message(self.request, messages.SUCCESS, _(u"Job Saved : Service Global Quantity : Saved : {0}").format(self.object.job_number))
            params = urllib.urlencode({'active_tab': 'services'})
            return HttpResponseRedirect(reverse('via_job_detail_estimate', args=(self.kwargs['pk'],)) + '?' + params)

        if 'apply_tasks_global_services' in request.POST:
            self.object.clean_pricing()
            quantity_dic = dict(request.POST.iterlists())
            self.object.save_service_global_quantity(quantity_dic)
            self.object.generate_tasks(None, True)
            messages.add_message(self.request, messages.SUCCESS, _(u"Job Saved : Service Global Quantity : Apply to Tasks : {0}").format(self.object.job_number))
            params = urllib.urlencode({'active_tab': 'services'})
            return HttpResponseRedirect(reverse('via_job_detail_estimate', args=(self.kwargs['pk'],)) + '?' + params)

        if 'set_large_jobs_approvers' in request.POST:
            project = self.object
            project.project_manager_approver_id = form['project_manager_approver'].data
            project.ops_management_approver_id = form['ops_management_approver'].data
            project.sales_management_approver_id = form['sales_management_approver'].data
            project.large_job_approval_notes = form['large_job_approval_notes'].data

            project.large_job_approval_timestamp = None
            if project.check_approvers_all_set():
                large_job_approval_timestamp = timezone.now()
                if form['large_job_approval_timestamp'].data:
                    large_job_approval_timestamp = form['large_job_approval_timestamp'].data
                project.large_job_approval_timestamp = large_job_approval_timestamp

            project.current_user = self.request.user.id
            project.save()
            messages.add_message(self.request, messages.SUCCESS, _(u"Job Save : Set Large Job Approvers : {0}").format(self.object.job_number))
            params = urllib.urlencode({'active_tab': 'approvals'})
            return HttpResponseRedirect(reverse('via_job_detail_estimate', args=(self.kwargs['pk'],)) + '?' + params)

        if 'analysis_file_import' in request.POST:
            self.object.clean_pricing()
            csv_file = form.files['analysis_file']
            self._import_analysis_file(csv_file)
            self.active_tab = 'analysis'
            return HttpResponseRedirect(self.get_success_url())

        if 'mbd_edit' in request.POST:
            ttp_id = request.POST['mbd_edit']
            self.object.clean_pricing()
            translation_task_price = TranslationTaskClientPrice.objects.get(pk=ttp_id)

            translation_task_price.guaranteed = request.POST['guaranteed']
            translation_task_price.exact = request.POST['exact']
            translation_task_price.duplicate = request.POST['duplicate']
            translation_task_price.fuzzy9599 = request.POST['fuzzy9599']
            translation_task_price.fuzzy8594 = request.POST['fuzzy8594']
            translation_task_price.fuzzy7584 = request.POST['fuzzy7584']
            translation_task_price.fuzzy5074 = request.POST['fuzzy5074']
            translation_task_price.no_match = request.POST['no_match']
            translation_task_price.save()

            messages.add_message(self.request, messages.SUCCESS, _(u"Job Save : MBD Edit : {0}").format(self.object.job_number))
            params = urllib.urlencode({'active_tab': 'analysis'})
            return HttpResponseRedirect(reverse('via_job_detail_estimate', args=(self.kwargs['pk'],)) + '?' + params)

        if 'mbd_global_edit' in request.POST:
            self.object.clean_pricing()
            project_id = request.POST['mbd_global_edit']
            project = Project.objects.select_related().get(pk=project_id)
            root_tasks = (project.all_root_tasks_billable())

            tsk_id = []
            for tsk in root_tasks:
                tsk_id.append(tsk.id)

            if tsk_id:
                translation_task = TranslationTask.objects.select_related().filter(pk__in=tsk_id)
                client_price_id = []
                for tsk in translation_task:
                    client_price_id.append(tsk.client_price_id)
                    translation_task_client_price = list(TranslationTaskClientPrice.objects.filter(pk__in=client_price_id))

            for ttcp in translation_task_client_price:
                ttcp.guaranteed = request.POST['guaranteed']
                ttcp.exact = request.POST['exact']
                ttcp.duplicate = request.POST['duplicate']
                ttcp.fuzzy9599 = request.POST['fuzzy9599']
                ttcp.fuzzy8594 = request.POST['fuzzy8594']
                ttcp.fuzzy7584 = request.POST['fuzzy7584']
                ttcp.fuzzy5074 = request.POST['fuzzy5074']
                ttcp.no_match = request.POST['no_match']
                ttcp.save()

            if project.is_inestimate_status():
                project.quote_summary_recalculate_all()

            messages.add_message(self.request, messages.SUCCESS, _(u"Job Save : MBD Global Edit : {0}").format(self.object.job_number))
            params = urllib.urlencode({'active_tab': 'analysis'})
            return HttpResponseRedirect(reverse('via_job_detail_estimate', args=(self.kwargs['pk'],)) + '?' + params)

        if 'reset_global_mbd_standard' in request.POST:
            project_id = request.POST['reset_global_mbd_standard']
            project = Project.objects.select_related().get(pk=project_id)
            root_tasks = (project.all_root_tasks_billable())

            tsk_id = []
            for tsk in root_tasks:
                tsk_id.append(tsk.id)

            if tsk_id:
                translation_task = TranslationTask.objects.select_related().filter(pk__in=tsk_id)
                client_price_id = []
                for tsk in translation_task:
                    client_price_id.append(tsk.client_price_id)
                    translation_task_client_price = list(TranslationTaskClientPrice.objects.filter(pk__in=client_price_id))

            for ttcp in translation_task_client_price:
                ttcp.guaranteed = 0
                ttcp.exact = ttcp.duplicate = 0.5
                ttcp.fuzzy9599 = ttcp.fuzzy8594 = ttcp.fuzzy7584 = ttcp.fuzzy5074 = ttcp.no_match = 1
                ttcp.save()

            if project.is_inestimate_status():
                project.quote_summary_recalculate_all()

            messages.add_message(self.request, messages.SUCCESS, _(u"Job Save : Deleted MBD Global : {0}").format(self.object.job_number))
            params = urllib.urlencode({'active_tab': 'analysis'})
            return HttpResponseRedirect(reverse('via_job_detail_estimate', args=(self.kwargs['pk'],)) + '?' + params)

        if form.is_valid():
            # noinspection PyAttributeOutsideInit
            self.obj = self.object
            self.object = form.save(commit=False)
            # do stuff based on data and self.object!
            self.object.save()
            form.save_m2m()

            if 'add_services' in request.POST:
                ProjectServicesGlobal.objects.filter(project=self.object).delete()

                self.active_tab = 'services'
                quantity_dic = self.object.generate_default_service_global_quantity()
                self.object.save_service_global_quantity(quantity_dic)
                self.object.generate_tasks(None, False)

            messages.add_message(self.request, messages.SUCCESS, _(u"Job Saved: {0}").format(self.object.job_number))
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        params = urllib.urlencode({'active_tab': self.active_tab})
        success_url = reverse('via_job_detail_estimate', args=(self.kwargs['pk'],)) + '?' + params
        return success_url


class ProjectFilesView(ViaLoginRequiredMixin, ProjectDetailMixin, UpdateView):
    template_name = 'via/projects/detail/files.html'
    form_class = ProjectJobOptionsForm
    # default active_tab
    active_tab = 'source'
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

    def get_context_data(self, **kwargs):
        context = super(ProjectFilesView, self).get_context_data(**kwargs)
        if self.object.kit.source_files().exists():
            context['active_tab'] = self.active_tab
        else:
            context['active_tab'] = 'source'

        project = context['project']
        context['can_edit_job'] = project.can_edit_job(self.request.user.country)

        # Getting context for client reference files
        context['client_reference_files'] = ClientReferenceFiles.objects.\
            filter(client_id=project.client_id, source_id=project.source_locale_id, target_id__in=project.target_locales.all())

        context['tasks_fa'] = Task.objects.select_related().filter(project_id=project.id, service__service_type__code=FINAL_APPROVAL_SERVICE_TYPE, status=COMPLETED_STATUS)
        context['holidays_during_job'] = get_holidays_during_job(project)
        context['client_message_unread_count'] = Comment.objects.filter(object_pk=project.id,comment_to=self.request.user.id,is_removed=False, comment_read_check=False, notification_type=settings.NOTIFICATION_TYPE_MESSAGE).count()

        return context

    def get(self, request, *args, **kwargs):
        project = self.get_object()

        if request.user:
            from accounts.views import user_country
            request.user.country = user_country(request)

        if not project.can_edit_job(request.user.country):
            messages.add_message(request, messages.ERROR, u"You do not have access to this Job's Files")
            return redirect('via_job_detail_overview', project.id)

        self.active_tab = request.GET.get('active_tab', self.active_tab)
        return super(ProjectFilesView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = project = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if 'save_job_options' in request.POST:
            job_option, created = ProjectJobOptions.objects.get_or_create(project=self.object)
            form = ProjectJobOptionsForm(instance=job_option, data=request.POST)
            pjo_object = form.save(commit=False)
            pjo_object.project_id = self.object.id
            pjo_object.save()
            return HttpResponseRedirect(self.get_success_url())

        if 'available_to_supplier' in request.POST:
            obj = FileAsset.objects.get(id=request.POST['asset_id'])
            obj.available_on_supplier = request.POST['available_to_supplier']
            obj.save(update_fields=['available_on_supplier'])
            return HttpResponseRedirect(self.get_success_url())

        if 'kits_asset_analysis_delete' in request.POST:
            asset_id = request.POST['asset_id']
            try:
                obj = FileAsset.objects.get(id=asset_id)
                messages.add_message(request, messages.SUCCESS, u"{0} was deleted".format(obj.orig_name))
                obj.delete()
            except:
                logger.info("ProjectFilesView.post.kits_asset_analysis_delete : FileAsset did not exist failure.", exc_info=True)
                pass
            self.active_tab = 'source'

            project.clean_target_locales()

            return HttpResponseRedirect(self.get_success_url())

        if 'kits_asset_move_from_source_to_reference' in request.POST:
            asset_id = request.POST['asset_id']
            try:
                obj = FileAsset.objects.get(id=asset_id)
                messages.add_message(request, messages.SUCCESS, u"{0} was moved to Reference Files".format(obj.orig_name))
                obj.asset_type = REFERENCEFILE_ASSET
                obj.save()

                project.kit.clear_analysis()

            except:
                logger.info("ProjectFilesView.post.kits_asset_move_from_source_to_reference : FileAsset did not exist failure.", exc_info=True)
                pass

            self.active_tab = 'source'
            return HttpResponseRedirect(self.get_success_url())

        if 'kits_asset_move_from_reference_to_source' in request.POST:
            asset_id = request.POST['asset_id']
            try:
                obj = FileAsset.objects.get(id=asset_id)
                messages.add_message(request, messages.SUCCESS, u"{0} was moved to Source Files".format(obj.orig_name))
                obj.asset_type = SOURCEFILE_ASSET
                obj.save()

            except:
                logger.info("ProjectFilesView.post.kits_asset_move_from_reference_to_source : FileAsset did not exist failure.", exc_info=True)
                pass

            self.active_tab = 'reference'
            return HttpResponseRedirect(self.get_success_url())

        if 'delete_client_reference_file' in request.POST:
            lk_id = request.POST['asset_id']
            lk = FileAsset.objects.get(id=lk_id)
            lk.delete()

            self.active_tab = 'reference'
            return HttpResponseRedirect(self.get_success_url())

        if 'delete_glossary_styleguide_ref_file' in request.POST:
            ref_id = request.POST['asset_id']
            ref = ClientReferenceFiles.objects.get(id=ref_id)
            ref.delete()

            self.active_tab = 'glossary'
            return HttpResponseRedirect(self.get_success_url())

        if 'delete_translation_file' in request.POST:
            ltk_id = request.POST['ltk_id']
            ltk = LocaleTranslationKit.objects.get(id=ltk_id)
            ltk.remove_translation_file_analysis_code()

            project.workflow_root_tasks_target_locale_remove_assets(ltk.target_locale)

            self.active_tab = 'loc_kit'
            return HttpResponseRedirect(self.get_success_url())

        if 'refresh_translation_file' in request.POST:
            ltk_id = request.POST['ltk_id']
            ltk = LocaleTranslationKit.objects.get(id=ltk_id)
            ltk.remove_translation_file()

            project.workflow_root_tasks_target_locale_remove_assets(ltk.target_locale)
            project.pre_translate_and_prep_kit(ltk.kit, remove_current_files=False, target=ltk.target_locale)

            self.active_tab = 'loc_kit'
            return HttpResponseRedirect(self.get_success_url())

        if 'create_loc_kits' in request.POST:
            project.pre_translate_and_prep_kit(project.kit, remove_current_files=True)

            self.active_tab = 'loc_kit'
            return HttpResponseRedirect(self.get_success_url())

        if 'delete_loc_kits' in request.POST:
            translation_task_remove_current_files(project.id)

            self.active_tab = 'loc_kit'
            messages.add_message(request, messages.SUCCESS, u"Loc Kits deleted successfully...")
            return HttpResponseRedirect(self.get_success_url())

        if 'delete_reference_file' in request.POST:
            ltk_id = request.POST['ltk_id']
            ltk = LocaleTranslationKit.objects.get(id=ltk_id)
            ltk.reference_file = None
            ltk.save()

            project.workflow_root_tasks_target_locale_remove_reference_file(ltk.target_locale)

            self.active_tab = 'loc_kit'
            return HttpResponseRedirect(self.get_success_url())

        if 'delete_post_delivery_edit_file' in request.POST:
            task_loc_asset_id = request.POST['task_loc_asset_id']
            task_localized_asset = TaskLocalizedAsset.objects.get(id=task_loc_asset_id)
            task_localized_asset.post_delivery_file = ''
            task_localized_asset.post_delivery_notes = None
            task_localized_asset.save()

            self.active_tab = 'post_delivery'
            return HttpResponseRedirect(self.get_success_url())

        if 'client_notes' in request.POST:
            tla_task_id = request.POST.get('tla_task_id')
            tla_id = request.POST.get('tla_id')
            post_delivery_notes = request.POST.get('client_notes')
            tla = TaskLocalizedAsset.objects.get(id=tla_id, task_id=tla_task_id)
            tla.post_delivery_notes = post_delivery_notes
            tla.save()

            self.active_tab = 'post_delivery'
            return HttpResponseRedirect(self.get_success_url())

        if form.is_valid():
            # noinspection PyAttributeOutsideInit
            self.object = form.save(commit=False)
            # do stuff based on data and self.object!
            self.object.save()
            form.save_m2m()

            messages.add_message(self.request, messages.SUCCESS, _(u"Job Saved: {0}").format(self.object.job_number))
            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.form_invalid(form)

    def get_success_url(self):
        params = urllib.urlencode({'active_tab': self.active_tab})
        success_url = reverse('via_job_detail_files', args=(self.kwargs['pk'],)) + '?' + params
        return success_url


class ProjectTasksView(ViaLoginRequiredMixin, ProjectDetailMixin, DefaultContextMixin, DetailView):
    template_name = 'via/projects/detail/tasks.html'

    def render_to_response(self, context, **response_kwargs):
        response = super(ProjectTasksView, self).render_to_response(context, **response_kwargs)
        response.delete_cookie("task_view")
        return response

    def get_context_data(self, **kwargs):
        context = super(ProjectTasksView, self).get_context_data(**kwargs)
        project = self.object
        project_targets = ProjectTargetSetViewModel(project)
        context['project_target_locales'] = project_targets
        context['ratingform'] = RatingForm()
        context['holidays_during_job'] = get_holidays_during_job(project)
        context['client_message_unread_count'] = Comment.objects.filter(object_pk=project.id,comment_to=self.request.user.id,is_removed=False, comment_read_check=False, notification_type=settings.NOTIFICATION_TYPE_MESSAGE).count()

        my_tasks = ViaMyTasksViewModel(self.request.user, 'all', project_filter=project)
        context['my_tasks'] = my_tasks

        if project.is_started_status() and not project.show_start_workflow():
            if project.all_tasks_none_active():
                notify_no_task_active(project)
                messages.add_message(self.request, messages.WARNING, _('Tasks are not active'))

        #calendar data
        calendar_events = []
        context['calendar_events'] = calendar_events
        target_selected_id = self.request.GET.get('target')
        if target_selected_id and int(target_selected_id) > 0:
            context['target_selected_id'] = int(target_selected_id)
            for target in project_targets.targets:
                if target.id == int(target_selected_id):
                    calendar_events = target.wf_tasks
        else:
            calendar_events = list(project.all_workflow_tasks())

        for task in calendar_events:

            task_scheduled_started_timestamp = None
            task_due = None

            if task.scheduled_start_timestamp and task.due:
                task_scheduled_started_timestamp = task.scheduled_start_timestamp
                task_due = task.due
            else:
                task_scheduled_started_timestamp = project.created
                task_due = project.quote_due

            context['calendar_events'].append(
                {
                    'title': u'{0}: {1}'.format(task.service.target.code, task.service.service_type.code.upper()),
                    'start': unicode(task_scheduled_started_timestamp),
                    'end': unicode(task_due),
                    'status': unicode(project.status),
                    'url': reverse('projects_tasks_edit', args=(task.id,)),
                    'backgroundColor': task.calendar_status(),
                    'borderColor': '#757575',
                }
            )
        return context

    def post(self, request, pk=None):
        if request.POST.getlist("delete-sub-tasks"):
            task_id = request.POST["task-id"]
            task = get_object_or_404(Task, id=task_id)
            #Getting list of sub-tasks
            sub_task_list = Task.objects.filter(parent_id=task_id).values_list('id', flat=True).distinct()

            # Getting the id of last subtask
            task_obj = Task.objects
            last_sub_task = task_obj.filter(project_id=task.project_id, parent_id=task.id).last()
            next_workflow_task = task_obj.filter(predecessor_id=last_sub_task.id, parent=None)

            for wtsk in next_workflow_task:
                wtsk.predecessor_id = task.id
                wtsk.save()

            if sub_task_list:
                #deleting sub-tasks
                TaskLocaleTranslationKit.objects.filter(task_id__in=sub_task_list).delete()
                TranslationTask.objects.filter(pk__in=sub_task_list).delete()
                task_obj.filter(id__in=sub_task_list).delete()

            if request.COOKIES.get('task_view'):
                redirect_url = reverse('via_job_detail_tasks_view', kwargs={'pk': task.project.id, 'service_id': task.service.service_type.id})
                return redirect(redirect_url)
            else:
                redirect_url = reverse('via_job_detail_tasks', kwargs={'pk': task.project.id})
                return redirect(redirect_url)

        if request.POST["task-id"]:
            task_id = request.POST["task-id"]
            task = get_object_or_404(Task, id=task_id)

            task_obj = Task.objects
            sub_task_check_list = task_obj.filter(parent_id=task.id)

            sub_tasks = []
            if request.POST.getlist("parent-task-id"):

                task.assignee_object_id = None
                task.assigned_to = None
                task.accepted_timestamp = None
                task.save()

                sub_tasks = ServiceType.objects.filter(code__in=[TRANSLATION_ONLY_SERVICE_TYPE, PROOFREADING_SERVICE_TYPE]).values_list('id', flat=True).distinct().order_by('id')
            else:
                sub_tasks = request.POST.getlist('sub-tasks')

            for tsk in sub_tasks:
                st_list = sub_task_check_list.order_by('id').last()

                service, created = Service.objects.get_or_create(
                    service_type_id=tsk,
                    unit_of_measure=task.service.unit_of_measure,
                    source=task.service.source,
                    target=task.service.target,
                )

                if service.service_type.code == TRANSLATION_ONLY_SERVICE_TYPE:
                    sub_task_standard_days = (task.standard_days * 60)/100
                    sub_task_express_days = (task.express_days * 60)/100
                elif service.service_type.code == PROOFREADING_SERVICE_TYPE:
                    sub_task_standard_days = (task.standard_days * 40)/100
                    sub_task_express_days = (task.express_days * 40)/100

                sub_task = TranslationTask(
                    parent_id=task.id,
                    project_id=task.project_id,
                    status=CREATED_STATUS,
                    billable=service.service_type.billable,
                    standard_days=sub_task_standard_days,
                    express_days=sub_task_express_days,
                    # assignee_object_id=None,
                    # assigned_to=None,
                    # accepted_timestamp=None,
                    service_id=service.id,
                    predecessor_id=task.id if not st_list else st_list.id,
                )
                sub_task.save()

                # Changing the predecessors order for navigating the workflow tasks.
                # Getting the next task of the current parent task
                if st_list:
                    next_workflow_task = task_obj.filter(predecessor_id=task.id, parent=None)

                    for wtsk in next_workflow_task:
                        wtsk.predecessor_id = sub_task.id
                        wtsk.save()

                client_price_check = ClientTranslationPrice.objects.filter(service_id=service.id)
                set_rate(sub_task)
                if client_price_check:
                    set_price(sub_task)
                analysis = TranslationTaskAnalysis.objects.create_from_kit(sub_task.project.kit, sub_task.service.target)
                sub_task.analysis = analysis
                if sub_task.predecessor_id == task.id:
                    sub_task.status = task.status
                sub_task.save()

            # Adjusting the schedule due dates for sub_tasks
            if sub_tasks:
                task.project.reschedule_due_dates_sub_tasks(task.project)

            # Checking whether this task in the first in the subtask workflow
            sub_task_list = []
            sub_task_check = None

            for stcl in sub_task_check_list:
                sub_task_list.append(stcl.id)
            try:
                sub_task_check = TaskLocaleTranslationKit.objects.filter(task_id__in=sub_task_list)
            except:
                pass

            if not sub_task_check:
                get_first_sub_task = task_obj.get(parent_id=task.id, predecessor_id=task.id)
                if task.is_translation():
                    if task.has_trans_kit():
                        stltk = TaskLocaleTranslationKit(
                            task_id=get_first_sub_task.id,
                            input_file=task.trans_kit.input_file,
                        )
                        stltk.save()
                else:
                    for la in task.localized_assets.all():
                        stltk = TaskLocalizedAsset(
                            task_id=sub_task.id,
                            input_file=la.input_file,
                            source_asset=la.source_asset,
                            name=la.name,
                        )
                        stltk.save()

            if request.COOKIES.get('task_view'):
                redirect_url = reverse('via_job_detail_tasks_view', kwargs={'pk': task.project.id, 'service_id': task.service.service_type.id})
                return redirect(redirect_url)
            else:
                redirect_url = reverse('via_job_detail_tasks', kwargs={'pk': task.project.id})
                return redirect(redirect_url)

        form = RatingForm(request.POST)
        self.object = self.get_object()

        if request.POST.get('create_po_manually'):
            job_number = request.POST.get('create_po_manually')
            from django.core import management
            management.call_command('create_job_task_and_po', job_number, True)
            return HttpResponseRedirect(reverse('via_job_detail_tasks', args=(self.object.id,)))

        if form.is_valid():
            instance = get_object_or_404(Task, id=request.POST.get('TaskId'))
            instance.rating=int(request.POST.get('rating'))
            instance.save()
            return HttpResponse(json.dumps({'message': 'Saved'}))
        else:
            return HttpResponse(json.dumps({'message': 'Error'}))


class ProjectTasksNewView(ViaLoginRequiredMixin, ProjectDetailMixin, DetailView):
    template_name = 'via/projects/detail/tasks_view.html'

    def get_context_data(self, **kwargs):
        context = super(ProjectTasksNewView, self).get_context_data(**kwargs)
        service_id = self.kwargs['service_id']
        context['ratingform'] = RatingForm()
        project = self.object
        context['can_edit_job'] = project.can_edit_job(self.request.user.country)
        my_tasks = ViaMyTasksViewModel(self.request.user, 'all', project_filter=project)
        context['my_tasks'] = my_tasks

        service_tasks = project.all_workflow_tasks().filter(service__service_type_id=service_id)
        context['service_tasks'] = service_tasks

        project_targets = ProjectTargetSetViewModel(self.object)

        service_list = []
        for task in project_targets.targets[0].tasks:
            if task.service.service_type.workflow:
                service_list.append(task.service.service_type)

        context['service_list'] = service_list
        return context

    def render_to_response(self, context, **response_kwargs):
        response = super(ProjectTasksNewView, self).render_to_response(context, **response_kwargs)
        response.set_cookie("task_view", True)
        return response

    def post(self,request, pk=None):
        form = RatingForm(request.POST)
        self.object = self.get_object()

        if request.POST.get('create_po_manually'):
            job_number = request.POST.get('create_po_manually')
            from django.core import management
            management.call_command('create_job_task_and_po', job_number, True)
            return HttpResponseRedirect(reverse('via_job_detail_tasks', args=(self.object.id,)))

        if form.is_valid():
            instance = get_object_or_404(Task, id=request.POST.get('TaskId'))
            instance.rating=int(request.POST.get('rating'))
            instance.save()
            return HttpResponse(json.dumps({'message': 'Saved'}))
        else:
            return HttpResponse(json.dumps({'message': 'Error'}))


class ProjectTeamView(ViaLoginRequiredMixin, ProjectDetailMixin, DefaultContextMixin, DetailView):
    model = Project
    template_name = 'via/projects/detail/team.html'
    active_tab = 'via_team'

    def get_context_data(self, **kwargs):
        context = super(ProjectTeamView, self).get_context_data(**kwargs)
        project = self.object
        if project.is_phi_secure_client_job():
            team_list = Project.get_phi_assigned_team(self.object, settings.VIA_USER_TYPE)
            team_ids = (member.contact_id for member in team_list)
            context['all_via_users'] = CircusUser.objects.filter(~Q(id__in=team_ids), user_type=settings.VIA_USER_TYPE,
                                                             groups__name=PROTECTED_HEALTH_INFORMATION_GROUP)\
                                       .order_by('first_name')
        else:
            team_list = Project.get_assigned_team(self.object)
            team_ids = (member.contact_id for member in team_list)
            context['all_via_users'] = CircusUser.objects.filter(~Q(id__in=team_ids), user_type=settings.VIA_USER_TYPE)\
                                        .order_by('first_name')
        context['secure_job_team'] = SecureJobAccess.objects.filter(project_id=project.id)
        context['team_list'] = team_list

        context['holidays_during_job'] = get_holidays_during_job(project)
        context['client_message_unread_count'] = Comment.objects.filter(object_pk=project.id,comment_to=self.request.user.id,is_removed=False, comment_read_check=False, notification_type=settings.NOTIFICATION_TYPE_MESSAGE).count()
        context['active_tab'] = self.active_tab
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        project = self.object
        if 'team_member' in request.POST:
            member_id = request.POST['team_member']
            team_member_role = request.POST['team_member_role']
            ProjectTeamRole.objects.filter(project_id=project.id, contact_id=member_id, role=team_member_role).delete()
            messages.add_message(self.request, messages.SUCCESS, _(u"User is deleted successfully from Project Team."))
        elif 'secure_job_team_member' in request.POST:
            member_id = request.POST['secure_job_team_member']
            SecureJobAccess.objects.get(id=member_id).delete()
            messages.add_message(self.request, messages.SUCCESS, _(u"User is deleted successfully from Secure Job Team."))
        elif 'secure_job_team_role_user' in request.POST:
            if project.is_phi_secure_client_job():
                ProjectTeamRole.objects.create(project_id=project.id,
                                               contact_id=request.POST.get('secure_job_team_role_user'),
                                               role=PHI_SECURE_JOB_TEAM_ROLE)
            else:
                ProjectTeamRole.objects.create(project_id=request.POST.get('project_id'),
                                               contact_id=request.POST.get('secure_job_team_role_user'),
                                               role=SECURE_JOB_TEAM_ROLE)
            messages.add_message(self.request, messages.SUCCESS, _(u"User is added successfully to Secure Job Team Role."))
        return HttpResponseRedirect(reverse('via_job_detail_team', args=(self.object.id,)))


class ProjectDvxView(ViaLoginRequiredMixin, ProjectDetailMixin, DefaultContextMixin, UpdateView):
    model = Project
    fields = '__all__'
    template_name = 'via/projects/detail/tm_maintenance.html'
    context_object_name = 'project'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.POST.get('lk_id'):
            lk_id = self.request.POST['lk_id']
            kit = LocalizationKit.objects.get(pk=lk_id)
            if kit:
                kit.tm_update_completed = kit.tm_update_started = timezone.now()
                kit.is_manually_updated = True
                kit.save()
                from activity_log.models import Actions

                action_object = Actions.objects.create(action_content_type=ContentType.objects.get_for_model(self.object),
                                                       action_object_id=self.object.id,
                                                       action_object_name=self.object.job_number,
                                                       verb='Completed Offline',
                                                       description='Completed Offline',
                                                       actor=self.request.user.get_full_name(),
                                                       job_id=self.object.id,)
                action_object.save()

            return redirect('via_job_detail_dvx', self.object.id)
        if request.POST.get('updateTM'):
            from projects.tm_manager import queue_add_to_tm
            project = self.object
            queue_add_to_tm(project.kit)
            return HttpResponse(json.dumps({'message': 'Success'}))

        if 'tm_delete' in request.POST:
            tla_id = request.POST['tm_delete']
            try:
                obj = TaskLocaleTranslationKit.objects.get(id=tla_id)
                obj.tm_update_file = ''
                obj.tm_file_updated_at = None
                obj.current_user = request.user.id
                obj.save()
                messages.add_message(request, messages.SUCCESS, u"TM File was deleted successfully")
            except:
                pass
            return redirect('via_job_detail_dvx', self.object.id)

    def get_context_data(self, **kwargs):
        context = super(ProjectDvxView, self).get_context_data(**kwargs)
        context['project_target_locales'] = ProjectTargetSetViewModel(self.object)
        project = self.object
        context['holidays_during_job'] = get_holidays_during_job(project)
        context['client_message_unread_count'] = Comment.objects.filter(object_pk=project.id, comment_to=self.request.user.id,is_removed=False, comment_read_check=False, notification_type=settings.NOTIFICATION_TYPE_MESSAGE).count()
        return context


class ProjectLogView(ViaLoginRequiredMixin, ProjectDetailMixin, DefaultContextMixin, DetailView):
    template_name = 'via/projects/detail/log.html'


class ProjectAutoJobCreateView(ViaLoginRequiredMixin, ProjectDetailMixin, DefaultContextMixin, CreateView):
    template_name = 'via/projects/auto_job_create.html'
    form_class = ProjectNewAutoJobForm

    def form_valid(self, form):
        data = form.cleaned_data

        project = Project.objects.create(
            client=data['client_poc'].account.cast(Client),
            source_locale=Locale.objects.get(lcid=1033),
            client_poc=data['client_poc'],
            project_reference_name=data['project_reference_name'],
            internal_via_project=data['internal_via_project'],
        )
        project.job_number = str(project.id)
        project.name = "{0} ({1}): {2}".format(data['client_poc'].account.name, data['client_poc'].get_full_name(), unicode(date.today()))
        if settings.VIA_JAMS_INTEGRATION:
            # get Job Number from JAMS API
            project.name = "{0}: {1}".format(settings.APP_SLUG_INSTANCE, project.name)
            try:
                created, job_number, job_id = create_jams_job_number(project)
                if created:
                    project.job_number = job_number
                    project.jams_jobid = job_id
            except:
                messages.add_message(self.request, messages.ERROR, _(u"ERROR in Auto Job creation : {0}").format(project.job_name_display_name()))
                project.delete()
                return HttpResponseRedirect(reverse('via_auto_job_create'))

        cs = ClientService.objects.filter(client=data['client_poc'].account.cast(Client), available=True, job_default=True)
        default_services = [ds.service for ds in cs.all()]
        project.services = default_services
        project.current_user = self.request.user.id
        project.save()
        project.assign_team()

        messages.add_message(self.request, messages.SUCCESS, _(u"Job created: {0}").format(project.job_number))
        return HttpResponseRedirect(reverse('via_continue_auto_job', args=(project.id, project.client_id)))


def quote_project(project):
    ProjectServicesGlobal.objects.filter(project=project).delete()
    quantity_dic = project.generate_default_service_global_quantity()
    project.save_service_global_quantity(quantity_dic)

    status, msg = project.generate_tasks(None, False)

    if status != messages.SUCCESS:
        return False

    project.assign_tasks()

    if not project.has_price():
        project.quote()

    if CREATED_STATUS in [t.target.name for t in project.valid_transitions()]:
        project.transition(CREATED_STATUS)
        return True
    else:
        return False


@shared_task
def _analysis_complete_callback(project_id):
    project = Project.objects.select_related().get(id=project_id)

    quoted = quote_project(project)
    project.status = CREATED_STATUS
    project.save()

    if not quoted:
        # Analysis completed successfully but quote failed to assign prices,
        # either we've failed to generate a quote for the client.
        return _analysis_complete_errback(None, project_id)


@shared_task
def _analysis_complete_errback(task_id, project_id, error=None):
    # celery error handlers get task_id as the first argument, even if we don't use it.
    project = Project.objects.select_related().get(id=project_id)
    notify_via_analysis_complete(project)
    project.estimate_type = MANUAL_ESTIMATE
    project.status = QUEUED_STATUS
    project.save()


class ProjectAutoJobContinueView(ViaLoginRequiredMixin, ProjectDetailMixin, DefaultContextMixin, UpdateView):
    template_name = 'via/projects/auto_job_create_continue.html'
    form_class = ProjectAutoJobContinueForm

    def get_context_data(self, **kwargs):
        context = super(ProjectAutoJobContinueView, self).get_context_data(**kwargs)
        project = self.object
        client_id = self.kwargs['client']
        cs = ClientService.objects.filter(client=client_id, available=True)
        avail_services_id = cs.values_list("service_id", flat=True)
        context['service_types'] = ServiceType.objects.filter(pk__in=avail_services_id).order_by('-description')
        return context

    def get_queryset(self):
        client_id = self.kwargs['client']
        return Project.objects.select_related().filter(client=client_id, is_deleted=False, status__in=[QUEUED_STATUS, CREATED_STATUS, QUOTED_STATUS])

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
        project.status = QUEUED_STATUS
        self._make_name_for_project(project)
        project.current_user = self.request.user.id
        project.save()
        form.save_m2m()

        project.generate_localetranslationkit()
        project.generate_loc_kit_analysis()

        # figure out if we have a file or language combination that cannot be auto-quoted, if so send to manual
        if project.client.manifest.auto_estimate_jobs and \
                project.kit.can_auto_estimate_doctype()and \
                project.kit.can_auto_estimate_locale():

            project.kit.queue_analysis_tasks(
                callback=_analysis_complete_callback.si(project.id),
                errback=_analysis_complete_errback.s(project.id))

            response = HttpResponseRedirect(reverse('via_waiting_for_quote', args=(project.id,)))
            update_analysis_cookie(response, project)
            return response
        else:
            BackgroundTask.objects.revoke_analysis(project)
            project.kit.remove_analysis_code()
            project.estimate_type = MANUAL_ESTIMATE
            project.status = QUEUED_STATUS
            project.current_user = self.request.user.id
            project.save()
            return HttpResponseRedirect(reverse('via_continue_auto_job', args=(project.id, project.client_id)))
            # return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('via_job_detail_overview', args=(self.object.id,))


class WaitingQuoteView(ViaLoginRequiredMixin, DefaultContextMixin, DetailView):
    template_name = 'via/projects/waiting_quote.html'

    def get(self, request, *args, **kwargs):
        project = self.get_object()
        if not project.kit.analyzing():
            # Waiting is over already!
            return redirect('via_job_detail_estimate', project.id)
        return super(WaitingQuoteView, self).get(self, request, *args, **kwargs)

    def get_queryset(self):
        project_id = self.kwargs['pk']
        project_obj = Project.objects.select_related()
        project = project_obj.get(pk=project_id)
        return project_obj.filter(client=project.client_id)


def manual_estimate_job(request, pk=None):
    # Creating Manual Estimate job
    project = Project.objects.select_related().get(pk=pk)
    project.transition(CREATED_STATUS)
    return HttpResponseRedirect(reverse('projects_perform_project_action', args=(project.id, "create_jams_estimate")))


class WorkflowJobCreateView(ViaLoginRequiredMixin, ProjectDetailMixin, DefaultContextMixin, CreateView):
    template_name = 'via/projects/workflow_job_create.html'
    form_class = ViaWorkflowForm

    def form_valid(self, form):
        #noinspection PyAttributeOutsideInit
        self.object = form.save(commit=False)
        self.object.status = STARTED_STATUS
        self.object.estimate_type = AUTO_ESTIMATE
        self.object.internal_via_project = True

        self.object.quoted = None
        self.object.current_user = self.request.user.id
        self.object.save()
        form.save_m2m()

        self.object.assign_team()

        if not self.object.job_number:
            self.object.job_number = str(self.object.id)

        self.object.save()
        form.save_m2m()

        if any(map(lambda each: each in form.changed_data, ["price", "cost", "express_price", "express_cost"])):
            price_quote, created = PriceQuote.objects.get_or_create(project=self.object)
            if price_quote:
                price_quote.price = self.request.POST.get('price') or 0
                price_quote.cost = self.request.POST.get('cost') or 0
                price_quote.express_cost = self.request.POST.get('express_price') or 0
                price_quote.express_price = self.request.POST.get('express_cost') or 0
                price_quote.active = True
                price_quote.save()

        self.object.generate_tasks(None, False)
        messages.add_message(self.request, messages.SUCCESS, _(u"Job created: {0}").format(self.object.job_number))
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('via_job_detail_overview', args=(self.object.id,))


class ProjectCreateView(ViaLoginRequiredMixin, ProjectDetailMixin, DefaultContextMixin, CreateView):
    template_name = 'via/projects/create.html'
    form_class = ProjectForm

    def form_valid(self, form):
        # noinspection PyAttributeOutsideInit
        self.object = form.save(commit=False)
        self.object.status = CREATED_STATUS
        self.object.estimate_type = AUTO_ESTIMATE

        if not self.object.quote_due:
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
        self.object.current_user = self.request.user.id

        if self.object.is_phi_secure_job and not self.object.is_secure_job:
            self.object.is_secure_job = True

        self.object.save()
        form.save_m2m()

        data = form.cleaned_data
        # self.object.payment_details.payment_method = CA_PAYMENT_CHOICE
        self.object.payment_details.payment_method = data['payment_method']
        self.object.payment_details.ca_invoice_number = data['ca_invoice_number']
        self.object.payment_details.save()

        self.object.assign_team()
        # in case new language, need to generate base analysis
        self.object.generate_localetranslationkit()
        self.object.generate_loc_kit_analysis()

        if not self.object.job_number:
            self.object.job_number = str(self.object.id)

        if (settings.VIA_JAMS_INTEGRATION and
                self.object.client.account_number and
                self.object.job_number == str(self.object.id)):

            # get Job Number from JAMS API
            self.object.name = "{0}: {1}".format(settings.APP_SLUG_INSTANCE, self.object.name)

            created, job_number, job_id = create_jams_job_number(self.object)
            if created:
                self.object.job_number = job_number
                self.object.jams_jobid = job_id
                self.object.save()
            else:
                # todo send email to PM about Job not updated in JAMS
                pass

            # Only create a JAMS estimate if the quote date was explicitly
            # specified, otherwise assume estimate will be handled within VTP.
            # create_manual_estimate = data['quote_due'] or data['rush_estimate']
            # if create_manual_estimate and self.object.can_create_jams_estimate():
            #     self.object.create_jams_estimate(data['rush_estimate'])

            self.object.save()
            form.save_m2m()

        messages.add_message(self.request, messages.SUCCESS, _(u"Job created: {0}").format(self.object.job_number))
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('via_job_detail_overview', args=(self.object.id,))


class QualityDefectCreateView(ViaLoginRequiredMixin,  CreateView):
    template_name = 'via/quality_defects/create.html'
    form_class = QualityDefectForm

    def get_context_data(self, **kwargs):
        context = super(QualityDefectCreateView, self).get_context_data(**kwargs)
        return context

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.save()
        messages.add_message(self.request, messages.SUCCESS, _(u"Quality Defect added"))
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('via_quality_defect_list')


class QualityDefectListView(ViaLoginRequiredMixin, ListView):
    template_name = 'via/quality_defects/list.html'
    context_object_name = 'quality_defects'
    model = QualityDefect
    paginate_by = settings.PAGINATE_BY_STANDARD

    def get_queryset(self):
        eqd = super(QualityDefectListView, self).get_queryset()
        eqd = eqd.filter().order_by('-id')
        return eqd

    def get_context_data(self, **kwargs):
        #noinspection PyUnresolvedReferences
        context = super(QualityDefectListView, self).get_context_data(**kwargs)
        eqd = context['quality_defects']
        i = 0
        for QD in context['quality_defects']:
            context['quality_defects'][i].comments = QualityDefectComment.objects.filter(quality_defect_id=QD.id).order_by('-date_created')
            i += 1
        return context

    def post(self,request, pk=None):
        form = QualityDefectCommentForm(self.request.POST or None)
        if form.is_valid():
            qdc = QualityDefectComment()
            qdc.comment = self.request.POST.get('comment')
            qdc.comment_by = request.user
            qdc.quality_defect_id = self.request.POST.get('quality_defect_id')
            qdc.save()
            return HttpResponse(json.dumps({'message': 'Saved'}))
        else:
            return HttpResponse(json.dumps({'message': 'Error'}))


class QualityDefectEditView(ViaLoginRequiredMixin,  UpdateView):
    template_name = 'via/quality_defects/create.html'
    form_class = QualityDefectForm
    model = QualityDefect

    def get_context_data(self, **kwargs):
        context = super(QualityDefectEditView, self).get_context_data(**kwargs)
        form_class = self.get_form_class()
        context['form'] = self.get_form(form_class)
        QD = context['qualitydefect']
        context['comments'] = QualityDefectComment.objects.filter(quality_defect_id=QD.id).order_by('-date_created')
        return context

    def get_success_url(self):
        return reverse('via_quality_defect_list')

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_class = QualityDefectForm
        if self.request.POST.get('quality_defect_id'):
            form = QualityDefectCommentForm(self.request.POST or None)
            if form.is_valid():
                qdc = QualityDefectComment()
                qdc.comment = self.request.POST.get('comment')
                qdc.comment_by = request.user
                qdc.quality_defect_id = self.request.POST.get('quality_defect_id')
                qdc.save()
                return HttpResponse(json.dumps({'message': 'Saved'}))
        else:
            form_class = self.get_form_class()
            form = self.get_form(form_class)
            if form.is_valid():
                self.object = form.save(commit=False)
                QD = self.object
                QD.save()
            return HttpResponseRedirect(reverse('via_quality_defect_edit', args=(QD.id,)))


def rename_process(new_output_file, output_file, old_file, tla_id, delete_s3_old_file=True):
    #Renaming the file in AWS S3
    from_key = settings.MEDIA_URL[1:] + unicode(output_file)
    to_key = settings.MEDIA_URL[1:] + unicode(new_output_file)
    if from_key and output_file != new_output_file:
        utils.copy_file_asset(from_key, to_key)

    #Deleting the old file in AWS S3
    if delete_s3_old_file and output_file != new_output_file:
        delete_file_asset(from_key)

    #Updating in database
    d = TaskLocalizedAsset.objects.filter(id=tla_id).update(output_file=new_output_file)


def rename_approved_file(pk, new_file_name=None, locale_id=None):
    if locale_id is not None:
        target_obj_all = TaskLocalizedAsset.objects.filter(task_id=pk, id=locale_id)
    else:
        target_obj_all = TaskLocalizedAsset.objects.filter(task_id=pk)

    for ids in target_obj_all:
        tla_id = ids.id
        target_obj = TaskLocalizedAsset.objects.get(pk=tla_id)
        source_asset_id = target_obj.source_asset_id
        in_file = target_obj.input_file
        input_file = str(in_file)
        out_file = target_obj.output_file
        output_file = str(out_file)

        delete_s3_old_file = True
        if output_file == input_file:
            delete_s3_old_file = False

        # getting the file name without extension and prefix the code to the file
        output_file = output_file.decode('utf_8')
        get_path = output_file.rfind('/')
        file_extn_pos = output_file.rfind('.')
        extn_part = output_file[file_extn_pos:]
        old_file = output_file[get_path+1:]

        if new_file_name is not None:
            file_name = new_file_name
            new_output_file = output_file[:get_path+1] + file_name + extn_part
            rename_process(new_output_file, output_file, old_file, tla_id, delete_s3_old_file)
        else:
            task = Task.objects.get(pk=ids.task_id)
            tar_loc_id = task.service.target_id
            # getting the target locale code from database table service_locale
            serv_loc_obj = Locale.objects.get(id=tar_loc_id)
            targ_loc_code = serv_loc_obj.code
            file_name = output_file[get_path+1:file_extn_pos] + '-' + targ_loc_code
            new_output_file = output_file[:get_path+1] + file_name + extn_part
            rename_process(new_output_file, output_file, old_file, tla_id, delete_s3_old_file)
    return old_file


class ApproveTask(ViaLoginRequiredMixin, DefaultContextMixin, DetailView):
    template_name = 'via/projects/tasks/approve.html'
    context_object_name = 'task'

    def get_queryset(self):
        return Task.objects.select_related().filter(id=self.kwargs['pk'])

    def post(self, request, pk=None):
        task = self.get_object()

        if 'make_delivery' in request.POST:
            if not task.complete_fa_if_all_tla_files_ready():
                messages.add_message(request, messages.ERROR, _("Could not complete task {0}.  Are all files uploaded and approved?").format(task))
                return redirect('via_approve_task', task.id)

            # task.complete()
            messages.add_message(request, messages.SUCCESS, _("Delivery made for task {0}.").format(task))

            if task.project.all_tasks_complete():
                if task.project.is_not_completed_status():
                    task.project.transition(COMPLETED_STATUS)
                else:
                    # Providing a new delivery for an already-completed project
                    # does not change its status.
                    task.project.delivered = timezone.now()
                    task.project.save()
                    # TODO: for redelivery should we notify that it's this task
                    #    in particular that has a new file?

                notify_client_job_ready(task.project)
                ctype = ContentType.objects.get_for_model(task)
                obj_pk = task.project_id

                comment_text = _('Job Delivered')
                user = task.project.project_manager if task.project.project_manager else request.user
                if task.project.client.manifest.show_client_messenger:
                    comments = Comment(object_pk=obj_pk, user=user, comment=comment_text, user_type=user.user_type, comment_to=task.project.client_poc.id, ip_address=request.META.get("REMOTE_ADDR", None), via_comment_user_type=settings.VIA_USER_TYPE, content_type_id=ctype.id, site_id=settings.SITE_ID, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
                    comments.save()

                team_members = Project.get_assigned_team_comments(task.project)
                for member in team_members:
                    comments = Comment(object_pk=obj_pk, user=user, comment=comment_text, user_type=user.user_type, comment_to=member.contact_id, ip_address=request.META.get("REMOTE_ADDR", None), via_comment_user_type=settings.VIA_USER_TYPE, content_type_id=ctype.id, site_id=settings.SITE_ID, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
                    comments.save()

                return redirect('via_job_detail_overview', task.project.id)
            return redirect('via_job_detail_tasks', task.project.id)

        if 'delivery_file_rename' in request.POST:
            new_file_name = request.POST['new_file']
            pk = request.POST['la_task_id']
            locale_id = request.POST['la_id']
            old_file = rename_approved_file(pk,new_file_name,locale_id)
            messages.add_message(self.request, messages.SUCCESS,
                             _(u"{0} was renamed"). format(old_file))

        if 'via_notes' in request.POST:
            via_notes = request.POST['id_via_notes']
            pk = request.POST['la_task_id']
            task.via_notes = via_notes
            task.save()
            messages.add_message(request, messages.SUCCESS, _("Task Saved").format(task))
            return redirect('via_approve_task', task.id)

        if 'verify_files' in request.POST:
            verify = request.POST.get('verify', None)
            un_verify = request.POST.get('un_verify', None)
            verify_all = request.POST.get('verify_all', None)
            un_verify_all = request.POST.get('un_verify_all', None)
            task_id = request.POST.get('task_id', None)
            la_id = request.POST.get('la_id', None)

            if verify == '1':
                d = TaskLocalizedAsset.objects.filter(id=la_id).update(via_approved=True)
            if verify == '0':
                d = TaskLocalizedAsset.objects.filter(id=la_id).update(via_approved=False)
            if verify_all == '1':
                d = TaskLocalizedAsset.objects.filter(task__id=task_id).filter(output_file__isnull=False).exclude(output_file__exact='').update(via_approved=True)
            if verify_all == '0':
                d = TaskLocalizedAsset.objects.filter(task__id=task_id).update(via_approved=False)
            return HttpResponse(json.dumps({'message': 'success'}), content_type="application/json")

        return HttpResponseRedirect(reverse('via_approve_task', args=(pk,)))

    def get_context_data(self, **kwargs):
        context = super(ApproveTask, self).get_context_data(**kwargs)
        task = context['task']
        if task and task.predecessor and task.predecessor.vendor_notes:
             context['previous_task_vendor_notes'] = task.predecessor.vendor_notes
        return context


@via_login_required
def accept_task(request, pk=None, locale_id=None):
    try:
        task = Task.objects.pending_acceptance().get(pk=pk)
    except:
        raise Http404

    task.accepted_timestamp = timezone.now()
    task.assigned_to = request.user
    task.save()

    if request.user.is_via():
        # todo figure out how to better handle the user role, should we add a default role to the via user account setup
        ProjectTeamRole.objects.get_or_create(project=task.project, contact=request.user, role=TSG_ENG_ROLE)

    messages.add_message(request, messages.SUCCESS, _(u"Task accepted"))
    if locale_id == '0':
        return HttpResponseRedirect(reverse('projects_tasks_edit', args=(pk,)))
    else:
        return HttpResponseRedirect(reverse('via_approve_task', args=(pk,)))


@via_login_required
def reject_task(request, pk=None):
    try:
        task = Task.objects.pending_acceptance().get(pk=pk)
    except:
        raise Http404
    via_rejected_task(request.user.account, task)

    task.assigned_to = None
    task.unit_cost = None
    task.save()

    messages.add_message(request, messages.SUCCESS, _("Task rejected"))
    return HttpResponseRedirect(reverse('via_dashboard'))


@via_login_required
def final_approval_replace_delivery_redirect(request, pk=None):
    """ called by s3 when an upload is finished for a VIA Final Approval delivery """
    try:
        # this is cutting corners a bit, in the future assignees might be of other types so just comparing ID wouldn't be strict enough
        la = TaskLocalizedAsset.objects.get(pk=pk)
    except:
        raise Http404
    key = request.GET.get('key')
    la.output_file = re.sub('^media/', '', key)
    la.downloaded = None
    la.save()
    return HttpResponseRedirect(reverse('via_approve_task', args=(la.task_id,)))


def post_delivery_replace_redirect(request, pk=None):
    """ called by s3 when an upload is finished for a VIA Final Approval delivery """
    try:
        la = TaskLocalizedAsset.objects.get(pk=pk)
    except:
        raise Http404
    key = request.GET.get('key')
    la.post_delivery_file = re.sub('^media/', '', key)
    la.downloaded = None
    la.save()

    params = urllib.urlencode({'active_tab': 'post_delivery'})
    return HttpResponseRedirect(reverse('via_job_detail_files', args=(la.task.project.id,)) + '?' + params)


@via_login_required
def client_poc_lookup(request):
    try:
        client_id = request.GET.get('client')
        ret = []
        if client_id:
            from shared.forms import form_get_client_poc
            client_poc =  form_get_client_poc(client_id)
            for children in client_poc:
                first_name = '' if children.first_name is None else unicode(children.first_name)
                last_name = '' if children.last_name is None else unicode(children.last_name)
                email = '' if children.email is None else unicode(children.email)
                ret.append(dict(id=children.id, value=unicode(first_name + ' ' + last_name + ' (' + email + ')')))
        if len(ret) != 1:
            ret.insert(0, dict(id='', value='---'))
        return HttpResponse(json.dumps(ret), content_type='application/json')
    except:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        raise 500


def client_project_lookup(request):
    try:
        client_id = request.GET.get('client')
        ret = []
        if client_id:
            for job in Project.objects.select_related().filter(client_id=client_id).order_by('job_number'):
                job_number = '' if job.job_number is None else unicode(job.job_number)
                name = '' if job.name is None else unicode(job.name)
                ret.append(dict(id=job.id, value=unicode(job_number + ' : ' + name)))
        if len(ret) != 1:
            ret.insert(0, dict(id='', value='---'))
        return HttpResponse(json.dumps(ret), content_type='application/json')
    except:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        raise 500


def project_task_lookup(request):
    try:
        project_id = request.GET.get('project')
        ret = []
        if project_id:
            for task in Task.objects.filter(project_id=project_id):
                ret.append(dict(id=task.id, value=unicode(task)))
        if len(ret) != 1:
            ret.insert(0, dict(id='', value='---'))
        return HttpResponse(json.dumps(ret), content_type='application/json')
    except:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        raise 500


def kit_translation_file_upload_complete(request, pk=None):
    """ called by s3 when an upload is finished for a Loc Kit Translation File """
    try:
        ltk = LocaleTranslationKit.objects.get(pk=pk)
    except:
        raise Http404
    key = request.GET.get('key')
    ltk.translation_file = re.sub('^media/', '', key)
    project = ltk.kit.project
    if re.search(str(project.kit.analysis_code), str(ltk.translation_file)):
        ltk.analysis_code = project.kit.analysis_code
    else:
        ltk.analysis_code = None
    ltk.save()

    project.workflow_root_tasks_target_locale_copy_lockit(ltk.target_locale)

    params = urllib.urlencode({'active_tab': 'loc_kit'})
    success_url = reverse('via_job_detail_files', args=(ltk.kit.project.id,)) + '?' + params
    return HttpResponseRedirect(success_url)


def source_file_upload_redirect(request, pk=None):
    """ called by s3 when an upload is finished for a Loc Kit Translation File """
    key = request.GET.get('key')
    file_path = re.sub('^media/', '', key)
    file_path_no_name, file_name = file_path.rsplit('/', 1)
    try:
        asset, created = FileAsset.objects.get_or_create(
            asset_type=SOURCEFILE_ASSET,
            kit_id=pk,
            orig_file=file_path,
            orig_name=file_name
        )

        project = Project.objects.select_related().get(kit_id=pk)
        project.generate_loc_kit_analysis()

    except:
        raise Http404

    params = urllib.urlencode({'active_tab': 'source'})
    success_url = reverse('via_job_detail_files', args=(asset.kit.project.id,)) + '?' + params
    return HttpResponseRedirect(success_url)


def reference_file_upload_redirect(request, pk=None):
    """ called by s3 when an upload is finished for a Loc Kit Translation File """
    key = request.GET.get('key')
    file_path = re.sub('^media/', '', key)
    file_path_no_name, file_name = file_path.rsplit('/', 1)
    try:
        asset, created = FileAsset.objects.get_or_create(
            asset_type=REFERENCEFILE_ASSET,
            kit_id=pk,
            orig_file=file_path,
            orig_name=file_name
        )

        project = Project.objects.select_related().get(kit_id=pk)
        project.generate_loc_kit_analysis()

    except:
        raise Http404

    params = urllib.urlencode({'active_tab': 'reference'})
    success_url = reverse('via_job_detail_files', args=(asset.kit.project.id,)) + '?' + params
    return HttpResponseRedirect(success_url)


def reference_file_replace_redirect(request, pk=None):
    """ called by s3 when an upload is finished for a Loc Kit Translation File """
    key = request.GET.get('key')
    file_path = re.sub('^media/', '', key)
    file_path_no_name, file_name = file_path.rsplit('/', 1)
    try:
        asset = FileAsset.objects.get(pk=pk)
    except:
        raise Http404

    asset.orig_file = file_path
    asset.orig_name = file_name
    asset.save()

    params = urllib.urlencode({'active_tab': 'reference'})
    success_url = reverse('via_job_detail_files', args=(asset.kit.project.id,)) + '?' + params
    return HttpResponseRedirect(success_url)


def auto_job_source_file_upload_redirect(request, pk=None):
    """ called by s3 when an upload is finished for a Loc Kit Translation File """
    key = request.GET.get('key')
    file_path = re.sub('^media/', '', key)
    file_path_no_name, file_name = file_path.rsplit('/', 1)
    try:
        asset, created = FileAsset.objects.get_or_create(
            asset_type=SOURCEFILE_ASSET,
            kit_id=pk,
            orig_file=file_path,
            orig_name=file_name
        )

        project = Project.objects.select_related().get(kit_id=pk)
        project.generate_loc_kit_analysis()

    except:
        raise Http404

    success_url = reverse('via_continue_auto_job', args=(asset.kit.project.id, asset.kit.project.client_id))
    return HttpResponseRedirect(success_url)


def via_tltk_delivery_redirect(request, pk=None):
    """ called by s3 when an upload is finished for a vendor Translation delivery """
    try:
        # this is cutting corners a bit, in the future assignees might be of other types so just comparing ID wouldn't be strict enough
        ltk = TaskLocaleTranslationKit.objects.get(pk=pk)
    except:
        raise Http404
    key = request.GET.get('key')
    ltk.output_file = re.sub('^media/', '', key)
    ltk.current_user = request.user.id
    ltk.save()
    return HttpResponseRedirect(reverse('projects_tasks_edit', args=(ltk.task.id,)))


def via_tla_delivery_redirect(request, pk=None):
    """ called by s3 when an upload is finished for a vendor Non-Translation delivery """
    try:
        # this is cutting corners a bit, in the future assignees might be of other types so just comparing ID wouldn't be strict enough
        la = TaskLocalizedAsset.objects.get(pk=pk)
    except:
        raise Http404
    key = request.GET.get('key')
    la.output_file = re.sub('^media/', '', key)
    la.current_user = request.user.id
    la.save()
    return HttpResponseRedirect(reverse('projects_tasks_edit', args=(la.task.id,)))


def via_tlasf_delivery_redirect(request, pk=None):
    """ called by s3 when an upload is finished for a vendor Non-Translation delivery """
    try:
        # this is cutting corners a bit, in the future assignees might be of other types so just comparing ID wouldn't be strict enough
        la = TaskLocalizedAsset.objects.get(pk=pk)
    except:
        raise Http404
    key = request.GET.get('key')
    la.support_file = re.sub('^media/', '', key)
    la.current_user = request.user.id
    la.save()
    return HttpResponseRedirect(reverse('projects_tasks_edit', args=(la.task.id,)))


def via_tlsf_delivery_redirect(request, pk, tltk_id):
    """ called by s3 when an upload is finished for a vendor Translation delivery """
    ltk = TaskLocaleTranslationKit.objects.get(pk=tltk_id)
    import re
    key = request.GET.get('key')
    ltk.support_file = re.sub('^media/', '', key)
    ltk.current_user = request.user.id
    ltk.save()
    #ltk.task.complete_if_ready()
    # GET TASK

    return HttpResponseRedirect(reverse('projects_tasks_edit', kwargs={'pk': ltk.task.id}))


def via_tm_file_delivery_redirect(request, tltk_id):
    """ called by s3 when an upload is finished for a vendor Translation delivery """
    ltk = TaskLocaleTranslationKit.objects.get(pk=tltk_id)
    import re
    key = request.GET.get('key')
    ltk.tm_update_file = re.sub('^media/', '', key)
    ltk.tm_file_updated_at = datetime.now()
    ltk.current_user = request.user.id
    ltk.save()
    # GET TASK
    BackgroundTask.objects.start_with_callback(
        BackgroundTask.IMPORT_TRANSLATION,
        ltk.task.project,
        partial(import_translation_v2_for_tm, ltk)
    )
    return HttpResponseRedirect(reverse('via_job_detail_dvx', kwargs={'pk': ltk.task.project_id}))

def via_tla_input_delivery_redirect(request, pk=None):
    """ called by s3 when an upload is finished for a vendor Non-Translation delivery """
    try:
        # this is cutting corners a bit, in the future assignees might be of other types so just comparing ID wouldn't be strict enough
        la = TaskLocalizedAsset.objects.get(pk=pk)
    except:
        raise Http404
    key = request.GET.get('key')
    la.input_file = re.sub('^media/', '', key)
    la.current_user = request.user.id
    la.save()
    return HttpResponseRedirect(reverse('projects_tasks_edit', args=(la.task.id,)))


def ltk_reference_upload_redirect(request, ltk_id):
    """ Called by S3 when an upload is finished for a target-specific supplier reference"""
    try:
        ltk = LocaleTranslationKit.objects.get(id=int(ltk_id))
    except:
        raise Http404

    s3_key, filename = set_filefield_from_s3_redirect(request, ltk, 'reference_file')
    ltk.save()

    project = ltk.kit.project
    project.workflow_root_tasks_target_locale_copy_lockit(ltk.target_locale)

    msg = _(u"Supplier Reference File Uploaded for %(target)s: "
            "%(filename)s" % {
                'filename': filename,
                'target': ltk.target_locale,
                })

    messages.add_message(request, messages.SUCCESS, msg)

    params = urllib.urlencode({'active_tab': 'loc_kit'})
    success_url = reverse('via_job_detail_files', args=(ltk.kit.project.id,)) + '?' + params
    return HttpResponseRedirect(success_url)


def prepared_file_upload_redirect(request, file_asset_id):
    """ Called by S3 when an upload is finished for a prepared source file"""
    asset = FileAsset.objects.get(id=int(file_asset_id))

    s3_key, filename = set_filefield_from_s3_redirect(request, asset, 'prepared_file')
    asset.prepared_name = filename
    asset.save()

    msg = _(u"Prepared File Uploaded for %s" % (asset.orig_name,))
    messages.add_message(request, messages.SUCCESS, msg)

    params = urllib.urlencode({'active_tab': 'source'})
    success_url = reverse('via_job_detail_files', args=(asset.kit.project.id,)) + '?' + params
    return HttpResponseRedirect(success_url)


@require_POST
def prepared_file_remove(request, file_asset_id):
    asset = get_object_or_404(FileAsset, id=int(file_asset_id))

    prepared_name = asset.prepared_name
    asset.prepared_name = None
    asset.prepared_file = None
    asset.save()

    msg = _(u"Prepared File %s removed from source %s" % (
        prepared_name, asset.orig_name))
    messages.add_message(request, messages.SUCCESS, msg)

    params = urllib.urlencode({'active_tab': 'source'})
    success_url = reverse('via_job_detail_files', args=(asset.kit.project.id,)) + '?' + params
    return HttpResponseRedirect(success_url)


def current_background_tasks(request, hours=4):
    current = Q(completed__isnull=True)
    recent = Q(completed__gte=timezone.now() - timedelta(hours=hours))
    background_tasks = (BackgroundTask.objects.filter(current | recent)
                        .order_by('-created')
                        .prefetch_related('project'))
    context = {
        'background_tasks': background_tasks,
        'refresh_page_content': settings.BACKGROUND_PAGE_REFRESH_COUNTER,
    }
    return render(request=request, template_name='reports/background_tasks.html', context=context)


@require_POST
def complete_background_task(request, bgtask_id):
    bgtask = BackgroundTask.objects.get(id=bgtask_id)
    bgtask.completed = timezone.now()
    bgtask.save()

    msg = _(u"Background Task %s saved" % bgtask.project)
    messages.add_message(request, messages.SUCCESS, msg)

    return HttpResponseRedirect(reverse('background_tasks'))


def client_reference_file_download_handler(request, proj_id, asset_id):
    asset = ClientReferenceFiles.objects.get(id=asset_id)
    # todo file missing
    result = serve_file(request, asset.orig_file, save_as=True)
    return result


class ActivityLogView(ViaLoginRequiredMixin, ProjectDetailMixin, DefaultContextMixin, UpdateView):
    template_name = 'via/projects/detail/activitylog.html'
    fields = '__all__'
    active_tab = 'job_activity'
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        context = super(ActivityLogView, self).get_context_data(**kwargs)

        context['active_tab'] = 'job_activity'
        self.active_tab = 'job_activity'

        project = context['project']
        context['project'] = project
        context['job_price'] = project.price()

        project_actions_list = []
        project_actions_all = Actions.objects.filter(action_object_id=project.id,
                                                     action_content_type=ContentType.objects.get_for_model(Project))

        bg_tasks = Actions.objects.filter(action_content_type=ContentType.objects.get_for_model(BackgroundTask),
                                          job_id=project.id).order_by("-timestamp")

        tasks_list = Task.objects.select_related().filter(project_id=project.id).values_list('id', flat=True).distinct()
        tasks_actions_all = Actions.objects.filter(action_object_id__in=tasks_list,
                                                   action_content_type=ContentType.objects.get_for_model(Task))

        project_actions_list.extend(bg_tasks.filter(description=MEMORY_DB_TM).order_by("-timestamp"))
        project_actions_list.extend(project_actions_all.exclude(description='largejobs').order_by("-timestamp"))
        project_actions_list.extend(tasks_actions_all.filter(description="started_workflow").order_by("-timestamp"))

        project_actions_list = sorted(project_actions_list, key=lambda t: t.timestamp, reverse=True)

        context['project_actions'] = project_actions_list
        context['large_job_approvals_actions'] = project_actions_all.filter(description='largejobs').order_by("-timestamp")

        context['background_tasks'] = bg_tasks

        po_list = VendorPurchaseOrder.objects.filter(task_id__in=tasks_list).values_list('id', flat=True).distinct()
        po_actions_all = Actions.objects.filter(action_object_id__in=po_list,
                                                action_content_type=ContentType.objects.get_for_model(VendorPurchaseOrder))

        po_actions = po_actions_all.filter(file_type='').order_by("-timestamp")
        context['po_actions'] = po_actions

        tasks_actions = tasks_actions_all.filter(file_type='').order_by("-timestamp")
        context['tasks_actions'] = tasks_actions

        context['reference_files_actions'] = tasks_actions_all.filter(file_type='Reference').order_by("-timestamp")

        kit_file_list = TaskLocaleTranslationKit.objects.filter(task_id__in=tasks_list).values_list('id', flat=True).distinct()
        context['file_actions'] = Actions.objects.filter(action_object_id__in=kit_file_list,
                                                         action_content_type=ContentType.objects.get_for_model(TaskLocaleTranslationKit)
                                                         ).order_by("-timestamp")

        ntt_kit_file_list = TaskLocalizedAsset.objects.filter(task_id__in=tasks_list).values_list('id', flat=True).distinct()
        context['ntt_file_actions'] = Actions.objects.filter(action_object_id__in=ntt_kit_file_list,
                                                             action_content_type=ContentType.objects.get_for_model(TaskLocalizedAsset)
                                                             ).order_by("-timestamp")

        context['holidays_during_job'] = get_holidays_during_job(project)
        context['client_message_unread_count'] = Comment.objects.filter(object_pk=project.id, comment_to=self.request.user.id,is_removed=False, comment_read_check=False, notification_type=settings.NOTIFICATION_TYPE_MESSAGE).count()
        return context

    def get_success_url(self):
        params = urllib.urlencode({'active_tab': self.active_tab})
        success_url = reverse('via_job_detail_activitylog', args=(self.kwargs['pk'],)) + '?' + params
        return success_url


class ProjectClientCommentsView(ViaLoginRequiredMixin, DefaultContextMixin, ListView):
    template_name = 'via/projects/detail/project_comments.html'
    model = Project
    active_tab = 'client_comments'

    def get_context_data(self, **kwargs):
        context = super(ProjectClientCommentsView, self).get_context_data(**kwargs)
        project_id = self.kwargs['project_id']
        project = Project.objects.select_related().get(pk=project_id)
        if project:
            project.status = _normalize_project_status(project.status)
            reversed_status = OVERDUE_STATUS if project.is_overdue() else get_reversed_status(project.status)
            project.workflow = VIA_STATUS_DETAIL[reversed_status]
            context['VIA_STATUS_DETAIL'] = VIA_STATUS_DETAIL
            context['workflow_status'] = VIA_STATUS_DETAIL[reversed_status]
            context['can_edit_job'] = project.can_edit_job(self.request.user.country)
            context['project'] = project

        context['active_tab'] = 'vendor_comments'
        self.active_tab = 'vendor_comments'
        if project.client.manifest.show_client_messenger:
            context['show_client_messenger'] = project.client.manifest.show_client_messenger
            context['active_tab'] = 'client_comments'
            self.active_tab = 'client_comments'

        comments = Comment.objects.filter(object_pk=project_id, is_removed=False)
        comment_types_client = comment_filters(settings.CLIENT_USER_TYPE)
        context['client_comment_list_check'] = comments.filter(*comment_types_client)
        context['client_message_unread_count'] = Comment.objects.filter(object_pk=project_id, comment_to=self.request.user.id,is_removed=False, comment_read_check=False, notification_type=settings.NOTIFICATION_TYPE_MESSAGE).count()
        comment_types_vendor = comment_filters(settings.VENDOR_USER_TYPE)
        context['vendor_comment_list_check'] = comments.filter(*comment_types_vendor)
        context['holidays_during_job'] = get_holidays_during_job(project)
        context['can_access_secure_job'] = project.can_via_user_access_secure_job(self.request.user)
        return context

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

    def get_success_url(self):
        params = urllib.urlencode({'active_tab': self.active_tab})
        success_url = HttpResponseRedirect(reverse('project_comments', args=(self.kwargs['pk'],)) + '?' + params)
        return success_url


class ProjectCommentsListView(ViaLoginRequiredMixin, ListView):
    template_name = 'via/projects/detail/project_comments_list.html'
    context_object_name = 'messages_list'
    model = Comment
    paginate_by = settings.PAGINATE_BY_STANDARD

    def get_queryset(self):
        comments = super(ProjectCommentsListView, self).get_queryset()
        comments = comments.filter(comment_to=self.request.user.id, is_removed=False, filter_from_list=False, comment_read_check=False, notification_type=settings.NOTIFICATION_TYPE_MESSAGE).order_by('-id')
        return comments

    def get_context_data(self, **kwargs):
        context = super(ProjectCommentsListView, self).get_context_data(**kwargs)
        comments = context['messages_list']
        comments_obj = Comment.objects
        context['message_type'] = True
        i = 0
        for cmnt in context['messages_list']:
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
        return HttpResponseRedirect(reverse('job_messages_list_page'))


class ProjectNotificationsListView(ViaLoginRequiredMixin, ListView):
    template_name = 'via/projects/detail/project_comments_list.html'
    context_object_name = 'messages_list'
    model = Comment
    paginate_by = settings.PAGINATE_BY_STANDARD

    def get_queryset(self):
        comments = super(ProjectNotificationsListView, self).get_queryset()
        comments = comments.filter(comment_to=self.request.user.id, is_removed=False, filter_from_list=False, comment_read_check=False, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION).order_by('-id')
        return comments

    def get_context_data(self, **kwargs):
        context = super(ProjectNotificationsListView, self).get_context_data(**kwargs)
        comments = context['messages_list']
        comments_obj = Comment.objects
        context['message_type'] = False
        i = 0
        for cmnt in context['messages_list']:
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
            return HttpResponseRedirect(reverse('job_notifications_list_page'))
        if 'clear_all' in self.request.POST:
            comment = Comment.objects.filter(comment_to=self.request.user.id, comment_read_check=False, is_removed=False, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
            comment.update(comment_read_check=True, filter_from_list=True, comment_read_on=timezone.now())
            return HttpResponseRedirect(reverse('job_notifications_list_page'))


def project_price_per_document(request, pk):
    context = {}
    project = get_object_or_404(Project, id=pk)
    context['project'] = project
    context['quote'] = project.quote()
    return render(request=request, template_name='via/projects/tasks/_pricing_by_document.html', context=context)


