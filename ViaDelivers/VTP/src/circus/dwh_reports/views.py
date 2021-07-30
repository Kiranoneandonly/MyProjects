from __future__ import unicode_literals

import calendar
import csv
import io
import json
import logging
from collections import OrderedDict
from datetime import timedelta, datetime

from dateutil import parser
from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import resolve
from django.core.urlresolvers import reverse
from django.db.models import Q, Count, Sum, Avg
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import redirect, get_object_or_404, render
from django.utils import timezone
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.views.generic import ListView
from unicodecsv import DictWriter

from dwh_reports.exports import client_activity_csv, supplier_ratings_by_task_csv
from dwh_reports.forms import ClientsReportingFilterForm, ViaUserReportingFilterForm, VendorUserReportingFilterForm, \
    ClientManagerFilterForm, ClientsReportingClientManagerFilterForm, ClientsActivityReportingFilterForm
from dwh_reports.models import ClientsReporting, ProjectsReporting, TasksReporting, EqdReporting, ClientManager, TaskRating
from dwh_reports.states import CLIENT_REPORT_VIA_STATUS_DETAIL_CLIENT_PORTAL, QUOTED_STATUS, \
    CLIENT_REPORT_VIA_STATUS_DETAIL_VIA_PORTAL, client_report_via_normalize_status
from projects.states import ALL_STATUS, STARTED_STATUS, COMPLETED_STATUS, CLOSED_STATUS
from services.models import get_translation_task_service_types_code
from shared.utils import _make_aware_default
from projects.models import Project
from decimal import Decimal
from clients.models import Client

logger = logging.getLogger('circus.' + __name__)


def get_first_day(dt, d_years=0, d_months=0):
    # d_years, d_months are "deltas" to apply to dt
    # y, m = dt.year + d_years, dt.month + d_months
    # a, m = divmod(m-1, 12)
    # return date(y+a, m+1, 1)
    return dt.replace(day=1)


def get_last_day(dt):
    # return get_first_day(dt, 0, 1) + timedelta(-1)
    return dt.replace(day=calendar.monthrange(dt.year, dt.month)[1])


def user_type(request):
    current_user = request.user.is_client()
    if current_user:
        template_include = "shared/external/theme_base.html"
    else:
        template_include = "via/theme_base.html"
    return template_include


def merge_months_totals(jobs_dict, months_list, total_list, element=None):
    updated_month_list = months_list[:]

    for k, v in jobs_dict.items():
        updated_total_list = total_list[:]
        for month_name in v['month']:
            or_ind = v['month'].index(month_name)
            ind = months_list.index(month_name)
            updated_month_list[ind] = month_name
            updated_total_list[ind] = v[element][or_ind]
        v["month"] = updated_month_list
        v[element] = updated_total_list
    return jobs_dict


def get_months_list(tasks):
    months = []

    for d in tasks:
        months.append(parser.parse(d["month_firstday"]).strftime('%B'))

    months_list = list(set(months))
    months_list.sort(key=months.index)
    return months_list


def client_poc_lookup_managers(request):
    try:
        client_id = request.GET.get('client')
        ret = []
        clients = ClientsReporting.objects.exclude(name='').order_by('name')
        client_list = []
        is_parent = False

        # client is known. Now I can display the matching children.
        if client_id:
            parents = clients.filter(parent_id=int(client_id))
            if parents:
                for parent in parents:
                    client_list.append(parent.client_id)
                    is_parent = True

            if is_parent:
                client_poc = ClientManager.objects.filter(account__client_id__in=client_list).order_by('first_name')
            else:
                client_poc = ClientManager.objects.filter(account__client_id=client_id).order_by('first_name')

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


def client_poc_lookup_department(request):
    try:
        client_id = request.GET.get('client')
        ret = []
        clients = ClientsReporting.objects.exclude(name='').order_by('name')
        if client_id:
            for children in clients.filter(parent_id=client_id).order_by('name'):
                name = '' if children.name is None else unicode(children.name)
                ret.append(dict(id=children.client_id, value=unicode(name)))
        if len(ret) != 1:
            ret.insert(0, dict(id='', value='---'))
        return HttpResponse(json.dumps(ret), content_type='application/json')
    except:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        raise 500


def total_spend_by_customer(request, csv=False):
    now = timezone.now()
    then = now - timedelta(days=180)
    to_date = ''
    from_date = ''
    client = None
    department = None

    if request.user.is_client():
        client = request.user.account_id
        dash_board = 'client_dashboard'
    else:
        dash_board = 'via_dashboard'

    if request.method == "POST":

        if 'name' in request.POST:
            client = request.POST.get('name')

        if 'client_poc_department' in request.POST:
            department = request.POST.get('client_poc_department')

        if 'start_date' in request.POST:
            to_date = request.POST.get('end_date')
            from_date = request.POST.get('start_date')
            if from_date:
                then = _make_aware_default(datetime.strptime(from_date, '%Y-%m-%d'))
            if to_date:
                now = _make_aware_default(datetime.strptime(to_date, '%Y-%m-%d'))
        form = ClientsReportingFilterForm(request.POST, user=client)
    else:
        form = ClientsReportingFilterForm(user=client)

    base_first_day_month = get_first_day(then)
    base_last_day_month = get_last_day(now)
    template = user_type(request)

    clients_obj = ClientsReporting.objects
    if client:
        # be sure to add current client to the client_list
        client_list = [client]
        is_parent = False
        if department:
            client_list = [department]
        else:
            client_children = clients_obj.filter(parent_id=client)
            for client_child in client_children:
                client_list.append(client_child.client_id)
                is_parent = True

        # filter based on client_list
        clients_obj = clients_obj.filter(client_id__in=client_list)

    clients_obj = clients_obj.filter(projectsreporting__price__isnull=False, projectsreporting__start_date__range=[base_first_day_month, base_last_day_month])\
        .extra({'month_firstday': "date_part('month',  dwh_reports_projectsreporting.start_date) || '/1/' || date_part('year', dwh_reports_projectsreporting.start_date)",
                'year': "date_part('year', dwh_reports_projectsreporting.start_date)",
                'month': "date_part('month', dwh_reports_projectsreporting.start_date)"})

    if (client and not is_parent) or \
            (request.user.is_client() and not is_parent):
        jobs_dict = OrderedDict()
        regs = clients_obj \
            .values('client_id', 'name', 'year', 'month', 'month_firstday')\
            .annotate(sum_price=Sum('projectsreporting__price')) \
            .order_by('year', 'month', 'client_id')

        for reg in set([d['client_id'] for d in regs]):
            jobs_dict[reg] = {
                "name": [],
                "sum_price": [],
                "month": [],
                }

        for d in regs:
            jobs_dict[d["client_id"]]["name"].append(d["name"])
            jobs_dict[d["client_id"]]["sum_price"].append(int(d["sum_price"]))
            jobs_dict[d["client_id"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))

        jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['month']))
    else:
        regs = clients_obj.extra({'all': "1"})\
            .values('all', 'year', 'month', 'month_firstday')\
            .annotate(sum_price=Sum('projectsreporting__price'))\
            .order_by('year', 'month')

        jobs_dict = OrderedDict()
        for reg in set([d["all"] for d in regs]):
            jobs_dict[reg] = {
                "month": [],
                "sum_price": [],
                }

        for d in regs:
            jobs_dict[d["all"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
            jobs_dict[d["all"]]["sum_price"].append(int(d["sum_price"]))

        jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['month']))

    # Return the data as a dictionary
    data = {
        'jobs_dict': jobs_dict_sorted,
        'template': template,
        'dash_board': dash_board,
        'form': form,
        'start': from_date,
        'end': to_date
    }

    if request.GET.get('csv'):
        return csv_download(data['jobs_dict'],'total_spend_by_customer')
    else:
        return render(request=request, template_name='reports/total_spend_by_customer.html', context=data)


def total_price_per_word(request, csv=False):
    now = timezone.now()
    then = now - timedelta(days=180)
    to_date = ''
    from_date = ''
    jobs_to_date = now.strftime('%Y-%m-%d')
    jobs_from_date = then.strftime('%Y-%m-%d')

    client = None
    department = None
    client_languages = None

    if request.user.is_client():
        client = request.user.account_id
        dash_board = 'client_dashboard'
    else:
        dash_board = 'via_dashboard'

    if request.method == "POST":
        if 'name' in request.POST:
            client = request.POST.get('name')

        if 'client_poc_department' in request.POST:
            department = request.POST.get('client_poc_department')

        if 'start_date' in request.POST:
            to_date = request.POST.get('end_date')
            from_date = request.POST.get('start_date')
            if from_date:
                then = _make_aware_default(datetime.strptime(from_date, '%Y-%m-%d'))
            if to_date:
                now = _make_aware_default(datetime.strptime(to_date, '%Y-%m-%d'))
        form = ClientsReportingFilterForm(request.POST, user=client)
    else:
        form = ClientsReportingFilterForm(user=client)

    if to_date:
        jobs_to_date = to_date
    if from_date:
        jobs_from_date = from_date

    base_first_day_month = get_first_day(then)
    base_last_day_month = get_last_day(now)
    template = user_type(request)

    clients_obj = ClientsReporting.objects
    if client:
        # be sure to add current client to the client_list
        client_list = [client]
        is_parent = False
        client_languages = client

        if department:
            client_list = [department]
            client_languages = department
        else:
            client_children = clients_obj.filter(parent_id=client)
            for client_child in client_children:
                client_list.append(client_child.client_id)
                is_parent = True

        # filter based on client_list
        clients_obj = clients_obj.filter(client_id__in=client_list)

    clients_obj = clients_obj.filter(projectsreporting__price__isnull=False, projectsreporting__start_date__range=[base_first_day_month, base_last_day_month])\
        .extra({'month_firstday': "date_part('month',  dwh_reports_projectsreporting.start_date) || '/1/' || date_part('year', dwh_reports_projectsreporting.start_date)",
                'year': "date_part('year', dwh_reports_projectsreporting.start_date)",
                'month': "date_part('month', dwh_reports_projectsreporting.start_date)"})

    if (client and not is_parent) or \
            (request.user.is_client() and not is_parent):
        words = clients_obj \
            .values('client_id', 'name', 'year', 'month', 'month_firstday')\
            .annotate(total_word_count=Sum('projectsreporting__tasksreporting__word_count'), total_price=Sum('projectsreporting__tasksreporting__price')) \
            .order_by('client_id', 'year', 'month')

        jobs_dict = OrderedDict()
        for reg in set([d['client_id'] for d in words]):
            jobs_dict[reg] = {
                "name": [],
                "month": [],
                "total_word_count": [],
                "total_price": [],
                "total_price_per_word": [],
                }

        for d in words:
            jobs_dict[d["client_id"]]["name"].append(d["name"])
            jobs_dict[d["client_id"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
            jobs_dict[d["client_id"]]["total_word_count"].append(int(d["total_word_count"]))
            jobs_dict[d["client_id"]]["total_price"].append(int(d["total_price"]))
            total_price_per_word = d["total_price"]/d["total_word_count"]
            jobs_dict[d["client_id"]]["total_price_per_word"].append(float(round(total_price_per_word,2)))

        jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['name']))
    else:
        words = clients_obj.extra({'all': "1"})\
            .values('all', 'year', 'month', 'month_firstday')\
            .annotate(total_word_count=Sum('projectsreporting__tasksreporting__word_count'), total_price=Sum('projectsreporting__tasksreporting__price'))\
            .order_by('year', 'month')

        jobs_dict = OrderedDict()
        for reg in set([d["all"] for d in words]):
            jobs_dict[reg] = {
                "month": [],
                "total_word_count": [],
                "total_price": [],
                "total_price_per_word": [],
            }

        for d in words:
            jobs_dict[d["all"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
            jobs_dict[d["all"]]["total_word_count"].append(int(d["total_word_count"]))
            jobs_dict[d["all"]]["total_price"].append(int(d["total_price"]))
            total_price_per_word = d["total_price"]/d["total_word_count"]
            jobs_dict[d["all"]]["total_price_per_word"].append(float(round(total_price_per_word, 2)))

        jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['month']))

    # Return the data as a dictionary
    data = {
        'jobs_dict': jobs_dict_sorted,
        'template': template,
        'dash_board': dash_board,
        'form': form,
        'start': from_date,
        'end': to_date,
        'jobs_from_date': jobs_from_date,
        'jobs_to_date': jobs_to_date,
        'client': client_languages
    }
    if request.GET.get('csv'):
        return csv_download(data['jobs_dict'], 'total_price_per_word')
    else:
        return render(request=request, template_name='reports/total_price_per_word.html', context=data)


def total_price_per_word_language(request, start, end, userid=None):
    now = timezone.now()
    then = now - timedelta(days=180)

    if start:
        from_date = start
        then = _make_aware_default(datetime.strptime(from_date, '%Y-%m-%d'))
    if end:
        to_date = end
        now = _make_aware_default(datetime.strptime(to_date, '%Y-%m-%d'))

    base_first_day_month = get_first_day(then)
    base_last_day_month = get_last_day(now)
    template = user_type(request)

    clients_obj = ClientsReporting.objects
    if userid:
        # be sure to add current client to the client_list
        client_list = [userid]
        client_children = clients_obj.filter(parent_id=userid)
        for client_child in client_children:
            client_list.append(client_child.client_id)
        # filter based on client_list
        clients_obj = clients_obj.filter(client_id__in=client_list)

    words = clients_obj\
        .filter(projectsreporting__start_date__range=[base_first_day_month, base_last_day_month])\
        .extra({'month_firstday': "date_part('month', dwh_reports_projectsreporting.start_date) || '/1/' || date_part('year', dwh_reports_projectsreporting.start_date)",
                'year': "date_part('year', dwh_reports_projectsreporting.start_date)",
                'month': "date_part('month', dwh_reports_projectsreporting.start_date)"})\
        .values('projectsreporting__tasksreporting__target_id', 'projectsreporting__tasksreporting__target', 'year', 'month', 'month_firstday')\
        .annotate(total_word_count=Sum('projectsreporting__tasksreporting__word_count'), total_price=Sum('projectsreporting__tasksreporting__price'))\
        .order_by('year', 'month')

    jobs_dict = OrderedDict()
    for reg in set([d['projectsreporting__tasksreporting__target_id'] for d in words]):
        jobs_dict[reg] = {
            "target": [],
            "month": [],
            "total_word_count": [],
            "total_price": [],
            "total_price_per_word": [],
        }

    for d in words:
        jobs_dict[d["projectsreporting__tasksreporting__target_id"]]["target"].append(d["projectsreporting__tasksreporting__target"])
        jobs_dict[d["projectsreporting__tasksreporting__target_id"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
        jobs_dict[d["projectsreporting__tasksreporting__target_id"]]["total_word_count"].append(int(d["total_word_count"]))
        jobs_dict[d["projectsreporting__tasksreporting__target_id"]]["total_price"].append(int(d["total_price"]))
        total_price_per_word = d["total_price"]/d["total_word_count"]
        jobs_dict[d["projectsreporting__tasksreporting__target_id"]]["total_price_per_word"].append(float(round(total_price_per_word,2)))

    jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['target']))

    if request.user.is_client():
        dash_board = 'client_dashboard'
    else:
        dash_board = 'via_dashboard'

    # Return the data as a dictionary
    data = {
        'jobs_dict': jobs_dict_sorted,
        'template': template,
        'dash_board': dash_board,
    }
    return render(request=request, template_name='reports/total_price_per_word_language.html', context=data)


def total_spend_by_tasks(request):
    now = timezone.now()
    then = now - timedelta(days=180)
    to_date = ''
    from_date = ''

    client = None
    department = None

    if request.user.is_client():
        client = request.user.account_id
        dash_board = 'client_dashboard'
    else:
        dash_board = 'via_dashboard'

    if request.method == "POST":
        if 'name' in request.POST:
            client = request.POST.get('name')

        if 'client_poc_department' in request.POST:
            department = request.POST.get('client_poc_department')

        if 'start_date' in request.POST:
            to_date = request.POST.get('end_date')
            from_date = request.POST.get('start_date')
            if from_date:
                then = _make_aware_default(datetime.strptime(from_date, '%Y-%m-%d'))
            if to_date:
                now = _make_aware_default(datetime.strptime(to_date, '%Y-%m-%d'))
        form = ClientsReportingFilterForm(request.POST, user=client)
    else:
        form = ClientsReportingFilterForm(user=client)

    base_first_day_month = get_first_day(then)
    base_last_day_month = get_last_day(now)

    template = user_type(request)
    projects = ProjectsReporting.objects.filter(Q(start_date__range=[base_first_day_month, base_last_day_month]))

    clients_obj = ClientsReporting.objects
    if client:
        # be sure to add current client to the client_list
        client_list = [client]

        if department:
            client_list = [department]

        else:
            client_children = clients_obj.filter(parent_id=client)
            for client_child in client_children:
                client_list.append(client_child.client_id)

        # filter based on client_list
        projects = projects.filter(customer__in=client_list)

    tasks = projects \
        .extra({'month_firstday': "date_part('month', dwh_reports_projectsreporting.start_date) || '/1/' || date_part('year', dwh_reports_projectsreporting.start_date)",
                    'year': "date_part('year', dwh_reports_projectsreporting.start_date)",
                    'month': "date_part('month', dwh_reports_projectsreporting.start_date)"}) \
        .values('tasksreporting__service_id', 'tasksreporting__service_type','year', 'month', 'month_firstday') \
        .annotate(total_spend_by_tasks=Sum('tasksreporting__price')) \
        .order_by('year', 'month')

    jobs_dict = OrderedDict()
    for reg in set([d['tasksreporting__service_id'] for d in tasks]):
        jobs_dict[reg] = {
            "service_type": [],
            "month": [],
            "total_spend_by_tasks": [],
        }

    months_list = get_months_list(tasks)
    total_list = []
    for i in range(len(months_list)):
        total_list.append(int(0))

    for d in tasks:
        jobs_dict[d["tasksreporting__service_id"]]["service_type"].append(d["tasksreporting__service_type"])
        jobs_dict[d["tasksreporting__service_id"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
        jobs_dict[d["tasksreporting__service_id"]]["total_spend_by_tasks"].append(int(d["total_spend_by_tasks"]))

    jobs_dict = merge_months_totals(jobs_dict, months_list, total_list, element='total_spend_by_tasks')
    jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['service_type']))
    # Return the data as a dictionary
    data = {
        'jobs_dict': jobs_dict_sorted,
        'template': template,
        'dash_board': dash_board,
        'start': from_date,
        'end': to_date,
        'form': form,
    }
    if request.GET.get('csv'):
        return csv_download(data['jobs_dict'],'total_price_per_word')
    else:
        return render(request=request, template_name='reports/total_spend_by_tasks.html', context=data)


def total_spend_by_manager(request, csv=False):
    now = timezone.now()
    then = now - timedelta(days=180)
    to_date = ''
    from_date = ''

    manager = None
    customer = None
    department = None
    client_manager = None
    if request.method == "POST":
        if request.user.is_client():
            form = ClientManagerFilterForm(request.POST, user=request.user.account_id)
        else:
            form = ClientsReportingClientManagerFilterForm(request.POST)
        if 'customer' in request.POST:
            customer = request.POST.get('customer')
        if 'client_poc' in request.POST:
            manager = request.POST.get('client_poc')
        if 'client_poc_department' in request.POST:
            department = request.POST.get('client_poc_department')
        if 'client_manager' in request.POST:
                client_manager = request.POST.get('client_manager')
        if 'start_date' in request.POST:
            to_date = request.POST.get('end_date')
            from_date = request.POST.get('start_date')
            if from_date:
                then = _make_aware_default(datetime.strptime(from_date, '%Y-%m-%d'))
            if to_date:
                now = _make_aware_default(datetime.strptime(to_date, '%Y-%m-%d'))
    else:
        if request.user.is_client():
            form = ClientManagerFilterForm(user=request.user.account_id)
        else:
            form = ClientsReportingClientManagerFilterForm()

    base_first_day_month = get_first_day(then)
    base_last_day_month = get_last_day(now)
    template = user_type(request)

    projects = ProjectsReporting.objects.filter(Q(start_date__range=[base_first_day_month, base_last_day_month]))

    jobs_dict = OrderedDict()

    if request.user.is_client():
        dash_board = 'client_dashboard'
        customer = request.user.account_id

        clients_obj = ClientsReporting.objects
        if customer:
            # be sure to add current client to the client_list
            client_list = [customer]
            if department:
                client_list = [department]
            else:
                client_children = clients_obj.filter(parent_id=customer)
                for client_child in client_children:
                    client_list.append(client_child.client_id)
            # filter based on client_list
            projects = projects.filter(customer__in=client_list)

        if client_manager:
            client_poc_list = [client_manager]
            client = get_object_or_404(Client, id=request.user.account.id)
            if client.manifest.enforce_customer_hierarchy and request.user.has_perm('dwh_reports.reporting_direct_reports'):
                client_pocs = ClientManager.objects.filter(reports_to_id=client_manager)

                for poc in client_pocs:
                    client_poc_list.append(poc.id)

            projects = projects.filter(client_poc__in=client_poc_list)

        tasks = projects\
            .extra({'month_firstday': "date_part('month', dwh_reports_projectsreporting.start_date) || '/1/' || date_part('year', dwh_reports_projectsreporting.start_date)",
                    'year': "date_part('year', dwh_reports_projectsreporting.start_date)",
                    'month': "date_part('month', dwh_reports_projectsreporting.start_date)"})\
            .values('client_poc', 'client_poc__first_name', 'year', 'month', 'month_firstday')\
            .annotate(total_spent=Sum('tasksreporting__price'))\
            .order_by('year', 'month')

        for reg in set([d['client_poc'] for d in tasks]):
            jobs_dict[reg] = {
                "month": [],
                "client_poc__first_name": [],
                "total_spent": [],
            }

        months_list = get_months_list(tasks)
        total_list = []
        for i in range(len(months_list)):
            total_list.append(int(0))

        for d in tasks:
            jobs_dict[d["client_poc"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
            jobs_dict[d["client_poc"]]["client_poc__first_name"].append(str(d["client_poc__first_name"]))
            jobs_dict[d["client_poc"]]["total_spent"].append(int(d["total_spent"]))

        jobs_dict = merge_months_totals(jobs_dict, months_list, total_list, element='total_spent')
        jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['month']))
    else:
        dash_board = 'via_dashboard'

        clients_obj = ClientsReporting.objects
        if customer:
            # be sure to add current client to the client_list
            client_list = [customer]
            if department:
                client_list = [department]
            else:
                client_children = clients_obj.filter(parent_id=customer)
                for client_child in client_children:
                    client_list.append(client_child.client_id)
            # filter based on client_list
            projects = projects.filter(customer__in=client_list)

            if manager:
                client_poc_list = [manager]
                client_pocs = ClientManager.objects.filter(reports_to_id=manager)

                for poc in client_pocs:
                    client_poc_list.append(poc.id)

                projects = projects.filter(client_poc__in=client_poc_list)

            tasks = projects \
                .extra({'month_firstday': "date_part('month', dwh_reports_projectsreporting.start_date) || '/1/' || date_part('year', dwh_reports_projectsreporting.start_date)",
                        'year': "date_part('year', dwh_reports_projectsreporting.start_date)",
                        'month': "date_part('month', dwh_reports_projectsreporting.start_date)"})\
                .values('client_poc', 'client_poc__first_name', 'year', 'month', 'month_firstday')\
                .annotate(total_spent=Sum('tasksreporting__price'))\
                .order_by('year', 'month')

            for reg in set([d['client_poc'] for d in tasks]):
                jobs_dict[reg] = {
                    "month": [],
                    "client_poc__first_name": [],
                    "total_spent": [],
                }

            months_list = get_months_list(tasks)
            total_list = []
            for i in range(len(months_list)):
                total_list.append(int(0))

            for d in tasks:
                jobs_dict[d["client_poc"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
                jobs_dict[d["client_poc"]]["client_poc__first_name"].append(str(d["client_poc__first_name"]))
                jobs_dict[d["client_poc"]]["total_spent"].append(int(d["total_spent"]))

            jobs_dict = merge_months_totals(jobs_dict, months_list, total_list, element='total_spent')
            jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['month']))
        else:
            jobs_dict_sorted = 1
    # Return the data as a dictionary
    data = {
        'jobs_dict': jobs_dict_sorted,
        'template': template,
        'dash_board': dash_board,
        'form': form,
        'start': from_date,
        'end': to_date,
    }
    if request.GET.get('csv'):
        return csv_download(data['jobs_dict'], 'total_spend_by_manager')
    else:
        return render(request=request, template_name='reports/total_spend_by_mgr_stacked_area.html', context=data)


def customer_tm_savings(request, csv=False):
    now = timezone.now()
    then = now - timedelta(days=180)
    to_date = ''
    from_date = ''
    jobs_to_date = now.strftime('%Y-%m-%d')
    jobs_from_date = then.strftime('%Y-%m-%d')

    client = None
    department = None
    client_jobs = None

    if request.user.is_client():
        client = request.user.account_id
        dash_board = 'client_dashboard'
    else:
        dash_board = 'via_dashboard'

    if request.method == "POST":
        if 'name' in request.POST:
            client = request.POST.get('name')

        if 'client_poc_department' in request.POST:
            department = request.POST.get('client_poc_department')

        if 'start_date' in request.POST:
            to_date = request.POST.get('end_date')
            from_date = request.POST.get('start_date')
            if from_date:
                then = _make_aware_default(datetime.strptime(from_date, '%Y-%m-%d'))
            if to_date:
                now = _make_aware_default(datetime.strptime(to_date, '%Y-%m-%d'))
        form = ClientsReportingFilterForm(request.POST, user=client)
    else:
        form = ClientsReportingFilterForm(user=client)

    if to_date:
        jobs_to_date = to_date
    if from_date:
        jobs_from_date = from_date

    base_first_day_month = get_first_day(then)
    base_last_day_month = get_last_day(now)
    template = user_type(request)

    report_filter = Q(projectsreporting__start_date__range=[base_first_day_month, base_last_day_month])
    trans_service_type_code = get_translation_task_service_types_code()
    report_filter &= Q(projectsreporting__tasksreporting__service_code__in=trans_service_type_code)

    clients_obj = ClientsReporting.objects
    if client:
        # be sure to add current client to the client_list
        client_list = [client]
        is_parent = False
        client_jobs = client

        if department:
            client_jobs = department
            client_list = [department]
        else:
            client_children = clients_obj.filter(parent_id=client)
            for client_child in client_children:
                client_list.append(client_child.client_id)
                is_parent = True

        # filter based on client_list
        report_filter &= Q(client_id__in=client_list)

    clients_obj = clients_obj.filter(report_filter)\
        .select_related()\
        .extra({'month_firstday': "date_part('month', dwh_reports_projectsreporting.start_date) || '/1/' || date_part('year', dwh_reports_projectsreporting.start_date)",
                'year': "date_part('year', dwh_reports_projectsreporting.start_date)",
                'month': "date_part('month', dwh_reports_projectsreporting.start_date)"})

    if (client and not is_parent) or \
            (request.user.is_client() and not is_parent):
        regs = clients_obj \
            .values('client_id', 'name', 'year', 'month', 'month_firstday') \
            .annotate(tm_savings=Avg('projectsreporting__tasksreporting__memory_bank_discount')) \
            .order_by('year', 'month')

        jobs_dict = OrderedDict()
        for reg in set([d['client_id'] for d in regs]):
            jobs_dict[reg] = {
                "name": [],
                "tm_savings": [],
                "month": [],
                }

        for d in regs:
            jobs_dict[d["client_id"]]["name"].append(d["name"])
            jobs_dict[d["client_id"]]["tm_savings"].append(round(float(d["tm_savings"]), 2))
            jobs_dict[d["client_id"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))

        jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['name']))
    else:
        regs = clients_obj.extra({'all': "1"})\
            .values('all', 'year', 'month', 'month_firstday')\
            .annotate(tm_savings=Avg('projectsreporting__tasksreporting__memory_bank_discount'))\
            .order_by('year', 'month')

        jobs_dict = OrderedDict()
        for reg in set([d["all"] for d in regs]):
            jobs_dict[reg] = {
                "month": [],
                "tm_savings": [],
            }

        for d in regs:
            jobs_dict[d["all"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
            jobs_dict[d["all"]]["tm_savings"].append(round(float(d["tm_savings"]), 2))

        jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['month']))
    # Return the data as a dictionary
    data = {
        'jobs_dict': jobs_dict_sorted,
        'template': template,
        'dash_board': dash_board,
        'form': form,
        'start': from_date,
        'end': to_date,
        'jobs_from_date': jobs_from_date,
        'jobs_to_date': jobs_to_date,
        'client': client_jobs
    }
    if request.GET.get('csv'):
        return csv_download(data['jobs_dict'],'customer_tm_savings')
    else:
        return render(request=request, template_name='reports/customer_tm_savings.html', context=data)


class CustomerJobsTmSavings(ListView):
    template_name = 'reports/customer_tm_savings_jobs.html'
    context_object_name = 'jobs_tm_list'

    def get_queryset(self):
        now = timezone.now()
        then = now - timedelta(days=180)

        if self.kwargs['start']:
            from_date = self.kwargs['start']
            then = _make_aware_default(datetime.strptime(from_date, '%Y-%m-%d'))
        if self.kwargs['end']:
            to_date = self.kwargs['end']
            now = _make_aware_default(datetime.strptime(to_date, '%Y-%m-%d'))

        base_first_day_month = get_first_day(then)
        base_last_day_month = get_last_day(now)

        report_filter = Q(projectsreporting__start_date__range=[base_first_day_month, base_last_day_month])

        client = self.kwargs['client_id']
        clients_obj = ClientsReporting.objects
        if client:
            # be sure to add current client to the client_list
            client_list = [client]
            is_parent = False
            client_children = clients_obj.filter(parent_id=client)
            for client_child in client_children:
                client_list.append(client_child.client_id)
                is_parent = True
            # filter based on client_list
            report_filter &= Q(client_id__in=client_list)


        trans_service_type_code = get_translation_task_service_types_code()
        report_filter &= Q(projectsreporting__tasksreporting__service_code__in=trans_service_type_code)

        clients_obj = clients_obj.filter(report_filter)\
            .select_related()\
            .extra({'month_firstday': "date_part('month', dwh_reports_projectsreporting.start_date) || '/1/' || date_part('year', dwh_reports_projectsreporting.start_date)",
                    'year': "date_part('year', dwh_reports_projectsreporting.start_date)",
                    'month': "date_part('month', dwh_reports_projectsreporting.start_date)"})\
            .values('name', 'projectsreporting__tasksreporting__project', 'year', 'month', 'month_firstday',
                    'projectsreporting__tasksreporting__target', 'projectsreporting__tasksreporting__memory_bank_discount',
                    'projectsreporting__tasksreporting__source_file', 'projectsreporting__job_number', 'projectsreporting__project_id',
                    'projectsreporting__name', 'projectsreporting__project_status', 'projectsreporting__client_poc', 'projectsreporting__is_secure_job',
                    'projectsreporting')\
            .distinct()\
            .order_by('year', 'month', 'projectsreporting__tasksreporting__project')

        return clients_obj

    def get_context_data(self, **kwargs):
        context = super(CustomerJobsTmSavings, self).get_context_data(**kwargs)
        tasks = context['jobs_tm_list']
        if self.request.user.is_client():
            context['dash_board'] = 'client_dashboard'
        else:
            context['dash_board'] = 'via_dashboard'
        template = user_type(self.request)
        context['template'] = template
        return context


def customer_jobs_tm_savings(request, client_id):
    now = timezone.now()
    then = now - timedelta(days=180)
    base_first_day_month = get_first_day(then)
    base_last_day_month = get_last_day(now)
    template = user_type(request)

    clients_obj = ClientsReporting.objects

    if request.user.is_client():
        dash_board = 'client_dashboard'
    else:
        dash_board = 'via_dashboard'

    regs = clients_obj.filter(projectsreporting__start_date__range=[base_first_day_month, base_last_day_month], client_id=client_id)\
        .extra({'month_firstday': "date_part('month',  dwh_reports_projectsreporting.start_date) || '/1/' || date_part('year', dwh_reports_projectsreporting.start_date)",
                'year': "date_part('year', dwh_reports_projectsreporting.start_date)",
                'month': "date_part('month', dwh_reports_projectsreporting.start_date)"})\
        .values('projectsreporting__tasksreporting__project', 'year', 'month', 'month_firstday', 'projectsreporting__name')\
        .annotate(tm_savings=Avg('projectsreporting__tasksreporting__memory_bank_discount'))\
        .order_by('projectsreporting__tasksreporting__project')

    jobs_dict = OrderedDict()
    for reg in set([d['projectsreporting__tasksreporting__project'] for d in regs]):
         jobs_dict[reg] = {
            "name": [],
            "tm_savings": [],
            "month": [],
        }

    for d in regs:
         jobs_dict[d["projectsreporting__tasksreporting__project"]]["name"].append(d["projectsreporting__name"])
         jobs_dict[d["projectsreporting__tasksreporting__project"]]["tm_savings"].append(float(d["tm_savings"]))
         jobs_dict[d["projectsreporting__tasksreporting__project"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))

    jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['name']))
    # Return the data as a dictionary
    data = {
        'jobs_dict': jobs_dict_sorted,
        'template': template,
        'dash_board': dash_board,
    }
    return render(request=request, template_name='reports/customer_tm_savings_jobs.html', context=data)


def jobs_per_pm(request, csv=False):
    now = timezone.now()
    then = now - timedelta(days=180)
    to_date = ''
    from_date = ''
    pm = None
    if request.method == "POST":
        form = ViaUserReportingFilterForm(request.POST)
        if 'project_manager' in request.POST:
            pm = request.POST.get('project_manager')

        if 'start_date' in request.POST:
            to_date = request.POST.get('end_date')
            from_date = request.POST.get('start_date')
            if from_date:
                then = _make_aware_default(datetime.strptime(from_date, '%Y-%m-%d'))
            if to_date:
                now = _make_aware_default(datetime.strptime(to_date, '%Y-%m-%d'))
    else:
        form = ViaUserReportingFilterForm()

    base_first_day_month = get_first_day(then)
    base_last_day_month = get_last_day(now)

    projects = ProjectsReporting.objects.filter(Q(start_date__range=[base_first_day_month, base_last_day_month]), project_manager_id__isnull=False)
    if pm:
        projects = projects.filter(project_manager_id=pm)

    projects = projects\
        .extra({'month_firstday': "date_part('month', start_date) || '/1/' || date_part('year', start_date)",
                'year': "date_part('year', start_date)",
                'month': "date_part('month', start_date)"})
    if pm:
        tasks = projects.values('project_manager_id', 'project_manager', 'year', 'month', 'month_firstday')\
            .annotate(total_jobs=Count('project_id'))\
            .order_by('year', 'month')

        jobs_dict = OrderedDict()
        for reg in set([d['project_manager_id'] for d in tasks]):
            jobs_dict[reg] = {
                "project_manager": [],
                "month": [],
                "total_jobs": [],
            }
        for d in tasks:
            jobs_dict[d["project_manager_id"]]["project_manager"].append(d["project_manager"])
            jobs_dict[d["project_manager_id"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
            jobs_dict[d["project_manager_id"]]["total_jobs"].append(int(d["total_jobs"]))
    else:
        tasks = projects.extra({'all': "1"})\
            .values('all', 'year', 'month', 'month_firstday')\
            .annotate(total_jobs=Count('project_id'))\
            .order_by('year', 'month')

        jobs_dict = OrderedDict()
        for reg in set([d["all"] for d in tasks]):
            jobs_dict[reg] = {
                "project_manager": [],
                "month": [],
                "total_jobs": [],
            }
        for d in tasks:
            jobs_dict[d["all"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
            jobs_dict[d["all"]]["total_jobs"].append(int(d["total_jobs"]))

    jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['month']))

    # Return the data as a dictionary
    data = {
        'jobs_dict': jobs_dict_sorted,
        'form': form,
        'start': from_date,
        'end': to_date
    }
    if request.GET.get('csv'):
        return csv_download(data['jobs_dict'], 'jobs_per_pm')
    else:
        return render(request=request, template_name='reports/jobs_per_pm.html', context=data)


def csv_download(data, name='report'):
    response = StreamingHttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="' + name + '.csv"'
    title_list = []
    result = {}
    i = 0
    for i in data:
        for col in data[i]:
            if data[i][col]:
                title_list.append(col)
            j = 1
            for item in data[i][col]:
                if j not in result:
                    result[j] = []
                result[j].append(item)
                j += 1
    result[0] = title_list
    writer = csv.writer(response)
    for row in result:
        writer.writerow(result[row])
    return response


def jobs_otd(request, csv=False):
    now = timezone.now()
    then = now - timedelta(days=180)
    to_date = ''
    from_date = ''
    pm = None
    if request.method == "POST":
        form = ViaUserReportingFilterForm(request.POST)
        if 'project_manager' in request.POST:
            pm = request.POST.get('project_manager')

        if 'start_date' in request.POST:
            to_date = request.POST.get('end_date')
            from_date = request.POST.get('start_date')
            if from_date:
                then = _make_aware_default(datetime.strptime(from_date, '%Y-%m-%d'))
            if to_date:
                now = _make_aware_default(datetime.strptime(to_date, '%Y-%m-%d'))
    else:
        form = ViaUserReportingFilterForm()

    base_first_day_month = get_first_day(then)
    base_last_day_month = get_last_day(now)

    projects = ProjectsReporting.objects.filter(Q(start_date__range=[base_first_day_month, base_last_day_month]), on_time_delivery__isnull=False)

    if pm:
        projects = projects.filter(project_manager_id=pm)

    projects = projects\
        .extra({'month_firstday': "date_part('month', start_date) || '/1/' || date_part('year', start_date)",
                'year': "date_part('year', start_date)",
                'month': "date_part('month', start_date)"})
    if pm:
        tasks = projects\
            .values('on_time_delivery', 'year', 'month', 'month_firstday')\
            .annotate(on_time_deliveries=Count('on_time_delivery'))\
            .order_by('year', 'month')

        jobs_dict = OrderedDict()
        for reg in set([d['on_time_delivery'] for d in tasks]):
            jobs_dict[reg] = {
                "on_time_delivery": [],
                "month": [],
                "on_time_deliveries": [],
            }


        months_list = get_months_list(tasks)
        total_list = []
        for i in range(len(months_list)):
            total_list.append(int(0))

        for d in tasks:
            jobs_dict[d["on_time_delivery"]]["on_time_delivery"].append(d["on_time_delivery"])
            jobs_dict[d["on_time_delivery"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
            jobs_dict[d["on_time_delivery"]]["on_time_deliveries"].append(int(d["on_time_deliveries"]))


        jobs_dict = merge_months_totals(jobs_dict, months_list, total_list, element='on_time_deliveries')
        jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['on_time_delivery']))
    else:
        tasks = projects\
            .values('on_time_delivery', 'year', 'month', 'month_firstday')\
            .annotate(on_time_deliveries=Count('on_time_delivery'))\
            .order_by('year', 'month')

        jobs_dict = OrderedDict()
        for reg in set([d["on_time_delivery"] for d in tasks]):
            jobs_dict[reg] = {
                "on_time_delivery":[],
                "month": [],
                "on_time_deliveries": [],
            }

        months_list = get_months_list(tasks)
        total_list = []
        for i in range(len(months_list)):
            total_list.append(int(0))

        for d in tasks:
            jobs_dict[d["on_time_delivery"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
            jobs_dict[d["on_time_delivery"]]["on_time_delivery"].append(d["on_time_delivery"])
            jobs_dict[d["on_time_delivery"]]["on_time_deliveries"].append(int(d["on_time_deliveries"]))

        jobs_dict = merge_months_totals(jobs_dict, months_list, total_list, element='on_time_deliveries')
        jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['on_time_delivery']))

    # Return the data as a dictionary
    data = {
        'jobs_dict': jobs_dict_sorted,
        'form': form,
        'start': from_date,
        'end': to_date
    }
    if request.GET.get('csv'):
        return csv_download(data['jobs_dict'], 'total_price_per_word')
    else:
        return render(request=request, template_name='reports/jobs_otd.html', context=data)


def client_activity_report(request, client_id, status=None, from_days=None, to_days=None):
    try:
        client = get_object_or_404(ClientsReporting, pk=client_id)
        content = client_activity_csv(client, status, from_days, to_days)
        response = StreamingHttpResponse(content, content_type='text/csv; charset=utf-8')
        filename = '%s-activity-%s.csv' % (client.name, timezone.now())
        response['Content-Disposition'] = 'attachment; filename="%s"' % (filename,)
        return response
    except Exception, error:
        logger.error("Reports : client_activity_report failed.", exc_info=True)
        messages.error(request, _(u"Error processing client_activity_report. %s" % (error,)))
        if request.user.is_client():
            return redirect(reverse('client_activity_report_client_portal', args=(client_id,)))
        else:
            return redirect(reverse('client_activity_report', args=(client_id,)))


def client_form_view(request, view_id=None):
    template = user_type(request)
    days = settings.REPORT_DEFAULT_DAYS_FROM
    now = timezone.now()
    then = now - timedelta(days=days)
    from_date = ''
    to_date = ''
    is_client = request.user.is_client()
    client_id = request.user.account_id
    if request.method == "POST":
            form = ClientsActivityReportingFilterForm(request.POST)
            if is_client or form.is_valid():
                client_id = request.POST.get('name')
                if 'start_date' in request.POST:
                    to_date = request.POST.get('end_date')
                    from_date = request.POST.get('start_date')
                    if from_date:
                        then = _make_aware_default(datetime.strptime(from_date, '%Y-%m-%d'))
                    if to_date:
                        now = _make_aware_default(datetime.strptime(to_date, '%Y-%m-%d'))

                delta = now - then
                from_days = delta.days
                delta2 = timezone.now() - now
                to_days = delta2.days

                if view_id == '0':
                    if request.user.is_client():
                        return redirect(reverse('client_activity_report_client_portal', args=(client_id,)))
                    else:
                        return redirect(reverse('client_activity_report', args=(client_id,)))
                if view_id == '2':
                    if request.user.is_client():
                        return redirect(reverse('client_activity_report_client_portal', args=(client_id,)))
                    else:
                        return redirect(reverse('client_activity_pricing_breakdown_by_document_report', kwargs={'client_id': client_id, 'from_days': from_days, 'to_days': to_days}))
                else:
                    if request.user.is_client():
                        return redirect(reverse('client_activity_report_view_client_portal', kwargs={'client_id': request.user.account_id, 'status': 'all', 'from_days': from_days, 'to_days': to_days}))
                    else:
                        return redirect(reverse('client_activity_report_view', kwargs={'client_id': client_id, 'status': 'all', 'from_days': from_days, 'to_days': to_days}))
    else:
        form = ClientsActivityReportingFilterForm()

    if request.user.is_client():
        dash_board = 'client_dashboard'
    else:
        dash_board = 'via_dashboard'
    # Return the data as a dictionary
    data = {
        'form': form,
        'view_id': view_id,
        'template': template,
        'dash_board': dash_board,
        'start': from_date,
        'end': to_date
    }
    return render(request=request, template_name='reports/client_form_view.html', context=data)


class ClientActivityReportView(ListView):
    template_name = 'reports/client_activity_report_view_list.html'
    paginate_by = settings.PAGINATE_BY_STANDARD
    context_object_name = 'activity_list'
    status = ALL_STATUS

    def get_queryset(self):
        client_id = self.kwargs['client_id']
        status = self.kwargs['status']
        self.status = status
        client = get_object_or_404(ClientsReporting, pk=client_id)

        from_days = to_days = None
        if 'from_days' in self.kwargs:
            from_days = int(self.kwargs['from_days'])
        if 'to_days' in self.kwargs:
            to_days = int(self.kwargs['to_days'])

        taskreports_filter = Q(project__project_status__in=[QUOTED_STATUS, STARTED_STATUS, COMPLETED_STATUS, CLOSED_STATUS])

        if self.status != ALL_STATUS:
            taskreports_filter = taskreports_filter & Q(project__project_status=self.status)
        if client:
            taskreports_filter = taskreports_filter & (Q(project__customer=client.client_id) | Q(project__customer__parent_id=client.client_id))
        # if days:
        if from_days or to_days:
            to_date = (timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=to_days))
            from_date = (to_date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=from_days))

            taskreports_filter = taskreports_filter & (Q(project__quoted__gte=from_date) | Q(project__start_date__gte=from_date)) & (Q(project__quoted__lt=to_date) | Q(project__start_date__lt=to_date))

            # from_date = (timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=days))
            # taskreports_filter = taskreports_filter & (Q(project__quoted__gte=from_date) | Q(project__start_date__gte=from_date))
        tasks = TasksReporting.objects.filter(taskreports_filter).select_related().order_by('project__job_number', 'target', 'source_file', 'service_type')
        return tasks

    def get_context_data(self, **kwargs):
        context = super(ClientActivityReportView, self).get_context_data(**kwargs)
        tasks = context['activity_list']
        if self.request.user.is_client():
            context['dash_board'] = 'client_dashboard'
            CLIENT_REPORT_VIA_STATUS_DETAIL = CLIENT_REPORT_VIA_STATUS_DETAIL_CLIENT_PORTAL
        else:
            context['dash_board'] = 'via_dashboard'
            CLIENT_REPORT_VIA_STATUS_DETAIL = CLIENT_REPORT_VIA_STATUS_DETAIL_VIA_PORTAL

        for task in tasks:
            task.project.project_status = client_report_via_normalize_status(task.project.project_status)
            task.project.workflow = CLIENT_REPORT_VIA_STATUS_DETAIL[task.project.project_status]
        context['VIA_STATUS_DETAIL'] = CLIENT_REPORT_VIA_STATUS_DETAIL
        # noinspection PyUnresolvedReferences
        context['workflow_status'] = CLIENT_REPORT_VIA_STATUS_DETAIL[self.status]
        context['workflow_statuses'] = CLIENT_REPORT_VIA_STATUS_DETAIL
        context['from_days'] = int(self.kwargs['from_days']) if 'from_days' in self.kwargs else settings.REPORT_DEFAULT_DAYS_FROM
        context['to_days'] = int(self.kwargs['to_days']) if 'to_days' in self.kwargs else 0
        context['days'] = context['from_days']
        context['customer_filter_id'] = self.kwargs['client_id']
        context['status_filter'] = self.kwargs['status']
        template = user_type(self.request)
        context['template'] = template
        return context


#For future implementation on Project real time budget
def clients_gross_margin_report(request):
    now = timezone.now()
    then = now - timedelta(days=180)
    base_first_day_month = get_first_day(then)
    base_last_day_month = get_last_day(now)
    template = user_type(request)
    clients = ClientsReporting.objects
    tasks = clients.filter(projectsreporting__start_date__range=[base_first_day_month, base_last_day_month])\
        .extra({'month_firstday': "date_part('month', dwh_reports_projectsreporting.start_date) || '/1/' || date_part('year', dwh_reports_projectsreporting.start_date)",
                'year': "date_part('year', dwh_reports_projectsreporting.start_date)",
                'month': "date_part('month', dwh_reports_projectsreporting.start_date)"})\
        .values('client_id', 'name', 'year', 'month', 'month_firstday')\
        .annotate(total_gross_margin=Sum('projectsreporting__gross_margin'))\
        .order_by('year', 'month', 'client_id')

    jobs_dict = OrderedDict()
    for reg in set([d['client_id'] for d in tasks]):
         jobs_dict[reg] = {
            "name":[],
            "month": [],
            "total_gross_margin": [],
        }

    for d in tasks:
        jobs_dict[d["client_id"]]["name"].append(d["name"])
        jobs_dict[d["client_id"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
        jobs_dict[d["client_id"]]["total_gross_margin"].append(int(d["total_gross_margin"]))

    jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['name']))

    if request.user.is_client():
            dash_board = 'client_dashboard'
    else:
            dash_board = 'via_dashboard'
    # Return the data as a dictionary
    data = {
        'jobs_dict': jobs_dict_sorted,
        'template': template,
        'dash_board': dash_board,
    }
    return render(request=request, template_name='reports/clients_gross_margin_report.html', context=data)


def jobs_gross_margin_report(request, client_id):
    now = timezone.now()
    start_date = '2000-01-01'
    end_date = now.strftime("%Y-%m-%d %H:%M:%S")
    template = user_type(request)
    if request.method == "POST":
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
    xdata=[]
    ydata=[]
    regs = ProjectsReporting.objects\
        .filter(start_date__range=(start_date, end_date), customer=client_id)\
        .values('job_number')\
        .annotate(total_gross_margin=Sum('gross_margin'))\
        .order_by('job_number')

    for reg in regs:
        if reg['job_number']:
            xdata.append(reg['job_number'])
            ydata.append(str(reg['total_gross_margin']))

    extra_serie = {"tooltip": {"y_start": "", "y_end": " GM "}}
    chartdata = {
        'x': xdata, 'y': ydata, 'extra': extra_serie
    }

    if request.user.is_client():
            dash_board = 'client_dashboard'
    else:
            dash_board = 'via_dashboard'
    charttype = "multiBarChart"
    chartcontainer = 'linechart_container'
    data = {
        'charttype': charttype,
        'chartdata': chartdata,
        'chartcontainer': chartcontainer,
        'extra': {
            'x_is_date': False,
            'x_axis_format': '',
            'rotateLabels': False,
            'tag_script_js': True,
            'jquery_on_ready': False,
        },
        'template': template,
        'dash_board': dash_board
    }
    return render(request=request, template_name='reports/jobs_gross_margin_report.html', context=data)


def task_completion_velocity(request, csv=False):
    now = timezone.now()
    then = now - timedelta(days=180)
    to_date = ''
    from_date = ''
    assignee = None
    current_url = resolve(request.path_info).url_name
    if request.method == "POST":
        if current_url == 'task_completion_velocity_via':
            form = ViaUserReportingFilterForm(request.POST)
        else:
            form = VendorUserReportingFilterForm(request.POST)

        if 'project_manager' in request.POST:
            assignee = request.POST.get('project_manager')

        if 'start_date' in request.POST:
            to_date = request.POST.get('end_date')
            from_date = request.POST.get('start_date')
            if from_date:
                then = _make_aware_default(datetime.strptime(from_date, '%Y-%m-%d'))
            if to_date:
                now = _make_aware_default(datetime.strptime(to_date, '%Y-%m-%d'))
    else:
        if current_url == 'task_completion_velocity_via':
            form = ViaUserReportingFilterForm()
        else:
            form = VendorUserReportingFilterForm()

    base_first_day_month = get_first_day(then)
    base_last_day_month = get_last_day(now)

    tasks = TasksReporting.objects.filter(Q(started__range=[base_first_day_month, base_last_day_month]), completed__isnull=False)
    if assignee:
        tasks = tasks.filter(assignee_object_id=assignee)

    tasks = tasks\
        .extra({'month_firstday': "date_part('month', started) || '/1/' || date_part('year', started)",
                'year': "date_part('year', started)",
                'month': "date_part('month', started)"})
    if assignee:
        tasks = tasks.values('assignee_object_id', 'year', 'month', 'month_firstday')\
            .annotate(total_tasks_completed=Count('completed'))\
            .order_by('year', 'month')

        jobs_dict = OrderedDict()
        for reg in set([d['assignee_object_id'] for d in tasks]):
            jobs_dict[reg] = {
                "month": [],
                "total_tasks_completed": [],
            }

        for d in tasks:
            jobs_dict[d["assignee_object_id"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
            jobs_dict[d["assignee_object_id"]]["total_tasks_completed"].append(int(d["total_tasks_completed"]))
    else:
        tasks = tasks.extra({'all': "1"})\
            .values('all', 'year', 'month', 'month_firstday')\
            .annotate(total_tasks_completed=Count('completed'))\
            .order_by('year', 'month')

        jobs_dict = OrderedDict()
        for reg in set([d["all"] for d in tasks]):
            jobs_dict[reg] = {
                "month": [],
                "total_tasks_completed": [],
            }

        for d in tasks:
            jobs_dict[d["all"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
            jobs_dict[d["all"]]["total_tasks_completed"].append(int(d["total_tasks_completed"]))

    jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['month']))
    # Return the data as a dictionary
    data = {
        'jobs_dict': jobs_dict_sorted,
        'form': form,
        'start': from_date,
        'end': to_date,
    }
    if request.GET.get('csv'):
        return csv_download(data['jobs_dict'],'task_completion_velocity')
    else:
        return render(request=request, template_name='reports/task_completion_velocity.html', context=data)


def estimation_completion_velocity(request, csv=False):
    now = timezone.now()
    then = now - timedelta(days=180)
    to_date = ''
    from_date = ''
    estimator = None
    if request.method == "POST":
        form = ViaUserReportingFilterForm(request.POST)
        if 'project_manager' in request.POST:
            estimator = request.POST.get('project_manager')

        if 'start_date' in request.POST:
            to_date = request.POST.get('end_date')
            from_date = request.POST.get('start_date')
            if from_date:
                then = _make_aware_default(datetime.strptime(from_date, '%Y-%m-%d'))
            if to_date:
                now = _make_aware_default(datetime.strptime(to_date, '%Y-%m-%d'))
    else:
        form = ViaUserReportingFilterForm()

    base_first_day_month = get_first_day(then)
    base_last_day_month = get_last_day(now)
    projects = ProjectsReporting.objects.filter(Q(start_date__range=[base_first_day_month, base_last_day_month]), quoted__isnull=False)

    if estimator:
        projects = projects.filter(estimator_id=estimator)

    projects = projects\
        .extra({'month_firstday': "date_part('month', start_date) || '/1/' || date_part('year', start_date)",
                'year': "date_part('year', start_date)",
                'month': "date_part('month', start_date)"})
    if estimator:
        tasks = projects.values('estimator_id', 'estimator', 'year', 'month', 'month_firstday')\
            .annotate(total_est_completion_velocity=Count('quoted'))\
            .order_by('year', 'month')

        jobs_dict = OrderedDict()
        for reg in set([d['estimator_id'] for d in tasks]):
            jobs_dict[reg] = {
                "estimator": [],
                "month": [],
                "total_est_completion_velocity": [],
            }

        for d in tasks:
            jobs_dict[d["estimator_id"]]["estimator"].append(d["estimator"])
            jobs_dict[d["estimator_id"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
            jobs_dict[d["estimator_id"]]["total_est_completion_velocity"].append(int(d["total_est_completion_velocity"]))
    else:
        tasks = projects.extra({'all': "1"})\
            .values('all', 'year', 'month', 'month_firstday')\
            .annotate(total_est_completion_velocity=Count('quoted'))\
            .order_by('year', 'month')

        jobs_dict = OrderedDict()
        for reg in set([d["all"] for d in tasks]):
            jobs_dict[reg] = {
                "month": [],
                "total_est_completion_velocity": [],
            }

        for d in tasks:
            jobs_dict[d["all"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
            jobs_dict[d["all"]]["total_est_completion_velocity"].append(int(d["total_est_completion_velocity"]))

    jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['month']))

    # Return the data as a dictionary
    data = {
        'jobs_dict': jobs_dict_sorted,
        'form': form,
        'start': from_date,
        'end': to_date
    }
    if request.GET.get('csv'):
        return csv_download(data['jobs_dict'], 'estimation_completion_velocity')
    else:
        return render(request=request, template_name='reports/estimation_completion_velocity.html', context=data)


def eqd_report(request, csv=False):
    now = timezone.now()
    then = now - timedelta(days=180)
    to_date = ''
    from_date = ''
    pm = None
    if request.method == "POST":
        form = ViaUserReportingFilterForm(request.POST)
        if 'project_manager' in request.POST:
            pm = request.POST.get('project_manager')

        if 'start_date' in request.POST:
            to_date = request.POST.get('end_date')
            from_date = request.POST.get('start_date')
            if from_date:
                then = _make_aware_default(datetime.strptime(from_date, '%Y-%m-%d'))
            if to_date:
                now = _make_aware_default(datetime.strptime(to_date, '%Y-%m-%d'))
    else:
        form = ViaUserReportingFilterForm()

    base_first_day_month = get_first_day(then)
    base_last_day_month = get_last_day(now)
    projects = EqdReporting.objects.filter(Q(due_created__range=[base_first_day_month, base_last_day_month]))
    if pm:
        projects = projects.filter(project_manager_id=pm)

    projects = projects\
        .extra({'month_firstday': "date_part('month', due_created) || '/1/' || date_part('year', due_created)",
                'year': "date_part('year', due_created)",
                'month': "date_part('month', due_created)"})
    if pm:
        tasks = projects.values('project_manager_id', 'year', 'month', 'month_firstday')\
                .annotate(total_eqds=Count('id'))\
                .order_by('year', 'month')

        jobs_dict = OrderedDict()
        for reg in set([d['project_manager_id'] for d in tasks]):
             jobs_dict[reg] = {
                "month": [],
                "total_eqds": [],
        }

        for d in tasks:
            jobs_dict[d["project_manager_id"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
            jobs_dict[d["project_manager_id"]]["total_eqds"].append(int(d["total_eqds"]))
    else:
        tasks = projects.extra({'all': "1"})\
            .values('all', 'year', 'month', 'month_firstday')\
            .annotate(total_eqds=Count('id'))\
            .order_by('year', 'month')

        jobs_dict = OrderedDict()
        for reg in set([d["all"] for d in tasks]):
            jobs_dict[reg] = {
                "month": [],
                "total_eqds": [],
            }

        for d in tasks:
            jobs_dict[d["all"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
            jobs_dict[d["all"]]["total_eqds"].append(int(d["total_eqds"]))

    jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['month']))
    # Return the data as a dictionary
    data = {
        'jobs_dict': jobs_dict_sorted,
        'form': form,
        'start': from_date,
        'end': to_date
    }
    if request.GET.get('csv'):
        return csv_download(data['jobs_dict'], 'eqd_report')
    else:
        return render(request=request, template_name='reports/eqd_report.html', context=data)


def report_estimates_total(request):
    try:
        now = timezone.now()
        then = now - timedelta(days=180)
        to_date = now.strftime('%Y-%m-%d')
        from_date = then.strftime('%Y-%m-%d')
        if request.method == "POST":
            if 'start_date' in request.POST:
                to_date = request.POST.get('end_date')
                from_date = request.POST.get('start_date')
                if from_date:
                    then = _make_aware_default(datetime.strptime(from_date, '%Y-%m-%d'))
                if to_date:
                    now = _make_aware_default(datetime.strptime(to_date, '%Y-%m-%d'))

        logger.info("Reports : report_estimates_total : from %s to %s ." % (str(from_date), str(to_date),), exc_info=True)

        project_filtered_list = ProjectsReporting.objects.filter(quoted__gte=then, quoted__lt=now)

        auto_est_projects = project_filtered_list.filter(estimate_type='Automatic')

        auto_est_prices = (project.price for project in auto_est_projects)
        # these projects are in all states so they may not all have prices.
        auto_est_total_price = sum(price for price in auto_est_prices if price is not None)

        man_est_projects = project_filtered_list.filter(estimate_type='Manual')

        man_est_prices = (project.price for project in man_est_projects)
        # these projects are in all states so they may not all have prices.
        man_est_total_price = sum(price for price in man_est_prices if price is not None)

        data = {
            'auto_est_price': auto_est_total_price,
            'auto_est_count': auto_est_projects.count(),
            'man_est_price': man_est_total_price,
            'man_est_count': man_est_projects.count(),
            'start': from_date,
            'end': to_date,
        }
        return render(request=request, template_name='reports/estimates_summary_report.html', context=data)

    except Exception, error:
        logger.error("Reports : report_estimates_total failed.", exc_info=True)
        messages.error(request, _(u"Error processing report_estimates_total. %s" % (error,)))

        data = {
            'auto_est_price': "",
            'auto_est_count': "",
            'man_est_price': "",
            'man_est_count': "",
            'start': from_date,
            'end': to_date,
        }
        return render(request=request, template_name='reports/estimates_summary_report.html', context=data)


def supplier_ratings_by_task(request, csv=False):
    now = timezone.now()
    then = now - timedelta(days=180)
    to_date = ''
    from_date = ''
    jobs_to_date = now.strftime('%Y-%m-%d')
    jobs_from_date = then.strftime('%Y-%m-%d')
    days = settings.REPORT_DEFAULT_DAYS_FROM

    assignee = 0
    if request.method == "POST":

        form = VendorUserReportingFilterForm(request.POST)

        if 'project_manager' in request.POST:
            if request.POST.get('project_manager'):
                assignee = request.POST.get('project_manager')

        if 'start_date' in request.POST:
            to_date = request.POST.get('end_date')
            from_date = request.POST.get('start_date')
            if from_date:
                then = _make_aware_default(datetime.strptime(from_date, '%Y-%m-%d'))
            if to_date:
                now = _make_aware_default(datetime.strptime(to_date, '%Y-%m-%d'))

            delta = now - then
            days = delta.days
    else:
        form = VendorUserReportingFilterForm()

    if to_date:
        jobs_to_date = to_date
    if from_date:
        jobs_from_date = from_date

    base_first_day_month = get_first_day(then)
    base_last_day_month = get_last_day(now)

    tasks = TaskRating.objects.filter(Q(started__range=[base_first_day_month, base_last_day_month]), rating__isnull=False)
    if assignee:
        tasks = tasks.filter(assignee_object_id=assignee)

    tasks = tasks\
        .extra({'month_firstday': "date_part('month', started) || '/1/' || date_part('year', started)",
                'year': "date_part('year', started)",
                'month': "date_part('month', started)"})
    if assignee:
        tasks = tasks.values('assignee_object_id', 'service_id', 'service_type', 'year', 'month', 'month_firstday')\
            .annotate(supplier_ratings_by_task=Avg('rating'))\
            .order_by('year', 'month')

        jobs_dict = OrderedDict()
        for reg in set([d['service_id'] for d in tasks]):
            jobs_dict[reg] = {
                "service_type": [],
                "month": [],
                "supplier_ratings_by_task": [],
            }

        months_list = get_months_list(tasks)
        total_list = []
        for i in range(len(months_list)):
            total_list.append(int(0))

        for d in tasks:
            jobs_dict[d["service_id"]]["service_type"].append(d["service_type"])
            jobs_dict[d["service_id"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
            jobs_dict[d["service_id"]]["supplier_ratings_by_task"].append(round(d["supplier_ratings_by_task"], 1))
    else:
        tasks = tasks\
            .values('service_id', 'service_type', 'year', 'month', 'month_firstday')\
            .annotate(supplier_ratings_by_task=Avg('rating'))\
            .order_by('year', 'month')

        jobs_dict = OrderedDict()
        for reg in set([d["service_id"] for d in tasks]):
            jobs_dict[reg] = {
                "service_type": [],
                "month": [],
                "supplier_ratings_by_task": [],
            }

        months_list = get_months_list(tasks)
        total_list = []
        for i in range(len(months_list)):
            total_list.append(int(0))

        for d in tasks:
                jobs_dict[d["service_id"]]["service_type"].append(d["service_type"])
                jobs_dict[d["service_id"]]["month"].append(parser.parse(d["month_firstday"]).strftime('%B'))
                jobs_dict[d["service_id"]]["supplier_ratings_by_task"].append(round(d["supplier_ratings_by_task"], 1))

    jobs_dict = merge_months_totals(jobs_dict, months_list, total_list, element='supplier_ratings_by_task')
    jobs_dict_sorted = OrderedDict(sorted(jobs_dict.items(), key=lambda t: t[1]['service_type']))

    # Return the data as a dictionary
    data = {
        'jobs_dict': jobs_dict_sorted,
        'start': from_date,
        'end': to_date,
        'form': form,
        'jobs_from_date': jobs_from_date,
        'jobs_to_date': jobs_to_date,
        'assignee_id': assignee,
        'days': days
    }
    if request.GET.get('csv'):
        return csv_download(data['jobs_dict'], 'task_completion_velocity')
    else:
        return render(request=request, template_name='reports/ratings_by_task.html', context=data)


class SupplierTasksRating(ListView):
    template_name = 'reports/ratings_by_task_details.html'
    context_object_name = 'supplier_ratings_by_task'

    def get_queryset(self):
        now = timezone.now()
        then = now - timedelta(days=180)

        if self.kwargs['start']:
            from_date = self.kwargs['start']
            then = _make_aware_default(datetime.strptime(from_date, '%Y-%m-%d'))
        if self.kwargs['end']:
            to_date = self.kwargs['end']
            now = _make_aware_default(datetime.strptime(to_date, '%Y-%m-%d'))

        base_first_day_month = get_first_day(then)
        base_last_day_month = get_last_day(now)

        report_filter = Q(started__range=[base_first_day_month, base_last_day_month])

        assignee_id = self.kwargs['assignee_id']
        rating_obj = TaskRating.objects
        if assignee_id and not assignee_id == '0':
            report_filter &= Q(assignee_object_id=assignee_id)

        rating_obj = rating_obj.filter(report_filter)\
            .extra({'month_firstday': "date_part('month', started) || '/1/' || date_part('year', started)",
                    'year': "date_part('year', started)",
                    'month': "date_part('month', started)"})\
            .values('assignee_object_id', 'assignee_name', 'task_name', 'job_number',
                    'rating', 'year', 'month', 'month_firstday',
                    'task_id', 'project_id',
                    'service_type', 'notes',
                    'via_notes', 'vendor_notes',
                    'started', 'completed')\
            .distinct()\
            .order_by('year', 'month')

        return rating_obj

    def get_context_data(self, **kwargs):
        context = super(SupplierTasksRating, self).get_context_data(**kwargs)
        days = settings.REPORT_DEFAULT_DAYS_FROM

        if self.kwargs['start']:
            from_date = self.kwargs['start']
            then = _make_aware_default(datetime.strptime(from_date, '%Y-%m-%d'))
        if self.kwargs['end']:
            to_date = self.kwargs['end']
            now = _make_aware_default(datetime.strptime(to_date, '%Y-%m-%d'))

        delta = now - then
        days = delta.days
        context['days'] = days
        context['assignee_id'] = self.kwargs['assignee_id']
        return context


def supplier_ratings_by_task_details_csv_export(request, assignee_id, days=None):
    try:
        content = supplier_ratings_by_task_csv(assignee_id, int(days))
        response = StreamingHttpResponse(content, content_type='text/csv; charset=utf-8')
        filename = '%s-task_rating-%s.csv' % (assignee_id, now())
        response['Content-Disposition'] = 'attachment; filename="%s"' % (filename,)
        return response
    except Exception, error:
        logger.error("Reports : supplier_ratings_by_task_details_csv_export failed.", exc_info=True)
        messages.error(request, _(u"Error processing supplier_ratings_by_task_details_csv_export. %s" % (error,)))
        return redirect(reverse('supplier_ratings_by_task'))


class ClientActivityReportPricingBreakdownByDocumentView(ListView):
    template_name = 'reports/client_activity_pricing_breakdown_by_document.html'
    paginate_by = settings.PAGINATE_BY_STANDARD
    context_object_name = 'activity_pricing_by_document_list'
    status = ALL_STATUS

    def get_queryset(self):
        client_id = self.kwargs['client_id']
        client = get_object_or_404(ClientsReporting, pk=client_id)
        # days = int(self.kwargs['days'])

        from_days = int(self.kwargs['from_days'])
        to_days = int(self.kwargs['to_days'])

        taskreports_filter = Q(project__project_status__in=[STARTED_STATUS, COMPLETED_STATUS, CLOSED_STATUS])

        if client:
            taskreports_filter = taskreports_filter & (Q(project__customer=client.client_id) | Q(project__customer__parent_id=client.client_id))

        if from_days or to_days:
            to_date = (timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=to_days))
            from_date = (to_date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=from_days))

            taskreports_filter = taskreports_filter & (Q(project__quoted__gte=from_date) | Q(project__start_date__gte=from_date)) & (Q(project__quoted__lt=to_date) | Q(project__start_date__lt=to_date))

        taskreports_filter = taskreports_filter & (~Q(source_file=''))
        tasks = TasksReporting.objects.filter(taskreports_filter).select_related().order_by('project', 'source_file')
        tasks = tasks.values('project__job_number', 'project_id', 'target', 'source_file').annotate(sum_pricing=Sum('price'))
        return tasks

    def get_context_data(self, **kwargs):
        context = super(ClientActivityReportPricingBreakdownByDocumentView, self).get_context_data(**kwargs)
        tasks = context['activity_pricing_by_document_list']
        if self.request.user.is_client():
            context['dash_board'] = 'client_dashboard'
        else:
            context['dash_board'] = 'via_dashboard'
        # context['days'] = self.kwargs['days']
        context['from_days'] = int(self.kwargs['from_days'])
        context['to_days'] = int(self.kwargs['to_days'])
        context['customer_filter_id'] = self.kwargs['client_id']
        template = user_type(self.request)
        context['template'] = template
        return context


def get_item(a_dict, key):
    return a_dict[key]


class ClientActivityPricingByDocumentCsvExport(ListView):
    paginate_by = settings.PAGINATE_BY_LARGE
    model = TasksReporting

    def csv(self, client_id):
        """
        :type projects: iterable of projects.models.Project
        """
        stream = io.BytesIO()
        stream.write(u'\ufeff'.encode('utf8'))

        headers = [
            'Job Number', 'File', 'Target',  'Price'
        ]
        csvwriter = DictWriter(stream, headers)
        csvwriter.writeheader()

        record = {}
        client = get_object_or_404(ClientsReporting, pk=client_id)
        # days = int(self.kwargs['days'])

        from_days = int(self.kwargs['from_days'])
        to_days = int(self.kwargs['to_days'])

        taskreports_filter = Q(project__project_status__in=[STARTED_STATUS, COMPLETED_STATUS, CLOSED_STATUS])

        if client:
            taskreports_filter = taskreports_filter & (Q(project__customer=client.client_id) | Q(project__customer__parent_id=client.client_id))

        if from_days or to_days:
            to_date = (timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=to_days))
            from_date = (to_date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=from_days))

            taskreports_filter = taskreports_filter & (Q(project__quoted__gte=from_date) | Q(project__start_date__gte=from_date)) & (Q(project__quoted__lt=to_date) | Q(project__start_date__lt=to_date))

        taskreports_filter = taskreports_filter & (~Q(source_file=''))
        tasks = TasksReporting.objects.filter(taskreports_filter).select_related().order_by('project', 'source_file')
        tasks = tasks.values('project__job_number', 'project_id', 'target', 'source_file').annotate(sum_pricing=Sum('price'))

        for task in tasks:

            record.update({
                'Job Number': task['project__job_number'],
                'File': task['source_file'],
                'Target': task['target'],
                'Price': task['sum_pricing'],
                })

            csvwriter.writerow(record)
        return stream.getvalue()

    def render_to_response(self, context):
        client_id = self.kwargs['client_id']
        client = get_object_or_404(ClientsReporting, pk=client_id)
        filename = 'customer-job-price-per-document (%s).csv' % (client.name)
        content = self.csv(client_id)
        response = StreamingHttpResponse(content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="%s"' % (filename,)
        return response
