from django import template

from tasks.models import TaskAssetQuote
from dwh_reports.models import TasksReporting
from django.db.models import Sum, Avg
from projects.models import SecureJobAccess, BackgroundTask
from projects.models import SecureJobAccess
from services.models import ServiceType
from django.db.models import Q
from collections import OrderedDict

register = template.Library()


@register.filter()
def get_item(a_dict, key):
    if key in a_dict:
        return a_dict[key]


@register.simple_tag
def get_sorted_task_list(task_list):
    return sorted(task_list, key=lambda task: task.id)


@register.simple_tag
def get_background_task(bg_task_id):
    return BackgroundTask.objects.get(id=bg_task_id)


@register.simple_tag
def get_taskassetquote(task, asset):
    return TaskAssetQuote.objects.filter(task_id=task, asset=asset).aggregate(
        asset_total_cost=Sum('asset_total_cost'),
        asset_raw_price=Sum('asset_raw_price'),
        asset_mbd=Avg('asset_mbd'),
        asset_net_price=Sum('asset_net_price'),
        asset_wordcount=Sum('asset_wordcount'),
        asset_gm=Avg('asset_gm'),
        asset_express_net_price=Sum('asset_express_net_price'),
        asset_express_gm=Avg('asset_express_gm')
    )


@register.simple_tag
def asset_is_minimum_price(task, asset):
    obj = TaskAssetQuote.objects.get_or_none(task_id=task, asset=asset)
    if obj:
        return obj.asset_is_minimum_price


@register.simple_tag
def asset_minimum_price_object(task, asset):
    obj = TaskAssetQuote.objects.get_or_none(asset=None, task=task)
    if obj:
        return obj


@register.simple_tag
def asset_target_price(asset, target):
    obj = TaskAssetQuote.objects.filter(asset=asset, target_id=target).aggregate(
        asset_total_cost=Sum('asset_total_cost'),
        asset_raw_price=Sum('asset_raw_price'),
        asset_mbd=Avg('asset_mbd'),
        asset_net_price=Sum('asset_net_price'),
        asset_wordcount=Avg('asset_wordcount'),
        asset_gm=Avg('asset_gm'),
        asset_express_net_price=Sum('asset_express_net_price'),
        asset_express_gm=Avg('asset_express_gm')
    )
    if obj:
        return obj

@register.simple_tag
def project_service_tasks(project, servicetype):
    return project.all_workflow_tasks().filter(service__service_type=servicetype)


@register.simple_tag
def get_document_price_report(task, task_target, document):
    tasks = TasksReporting.objects.filter(project_id=task['project_id'], target=task_target, source_file=document)
    tasks = tasks.values('project_id', 'target', 'source_file').annotate(sum_pricing=Sum('price'))
    for task in tasks:
        price = task['sum_pricing']

    return price


@register.simple_tag
def check_secure_job_team_member(user, account, project, client_poc=None, is_secure_job=False):
    check = True
    if is_secure_job:
        if not user == client_poc:
            check = SecureJobAccess.objects.filter(user_id=user,
                                           account_id=account,
                                           project_id=project)

    return check


@register.simple_tag
def check_via_secure_job_role(user, project):
    check = False
    team_role_ids = [team.contact_id for team in project.team.all()]
    if user in team_role_ids:
        check = True

    return check


@register.assignment_tag
def get_sub_services(service_id, category_id):
    services = ServiceType.objects.filter(Q(category_id=category_id) & Q(available=True) & ~Q(id=service_id)).order_by('id')
    sub_tasks = OrderedDict()
    for ser in services:
        sub_tasks[ser.id] = ser.description

    return sub_tasks
