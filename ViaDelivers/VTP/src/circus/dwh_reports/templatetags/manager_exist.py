from django import template
from dwh_reports.models import ClientsReporting, ClientManager, ClientReport, ClientReportAccess

import calendar

register = template.Library()


@register.filter
def month_name(month_number):
    return calendar.month_name[int(month_number)]


@register.filter
def filter_distinct(report_list):
    name = None
    if report_list:
        name = report_list[0]
        name = name.replace("'", r"\'")
        name = name.replace('"', r'\"')
    return name


@register.simple_tag
def manager_client_exists(key):
    report_id_exist = None
    clients = None
    if key:
        clients = ClientsReporting.objects.filter(reports_to_id=key)
    if clients:
        for client in clients:
            report_id_exist = client.reports_to_id
    return report_id_exist


@register.simple_tag
def parent_client_exists(key):
    parent_id_exist = None
    clients = None
    if key:
        clients = ClientsReporting.objects.filter(parent_id=key)
    if clients:
        for client in clients:
            parent_id_exist = client.parent_id
    return parent_id_exist


@register.simple_tag
def client_department(key):
    department = None
    clients = None
    if key:
        clients = ClientManager.objects.get(id=key)
    if clients:
        department = clients.department
    return department


@register.simple_tag
def client_full_name(key):
    full_name = None
    clients = None
    if key:
        clients = ClientManager.objects.get(id=key)
    if clients:
        full_name = clients.first_name + ' ' + clients.last_name
    return full_name


@register.simple_tag
def client_email(key):
    email = None
    clients = None
    if key:
        clients = ClientManager.objects.get(id=key)
    if clients:
        email = clients.email
    return email


@register.simple_tag
def manager_name(key):
    manager_full_name = None
    clients = None
    if key:
        clients = ClientManager.objects.get(id=key)
    if clients:
        manager_full_name = clients.first_name + ' ' + clients.last_name
    return manager_full_name


@register.simple_tag
def get_available_reports(user):
    reports = None
    if user:
        reports = ClientReportAccess.objects.select_related().filter(client=user, access=True)
    return reports
