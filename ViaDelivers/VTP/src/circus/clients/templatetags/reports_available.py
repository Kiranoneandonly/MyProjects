from django import template
from clients.models import ClientManifest


register = template.Library()


@register.simple_tag
def reports_available(key):
    report_availability = False
    users = None
    if key:
        users = ClientManifest.objects.filter(client__id=key)
    if users:
        for user in users:
            report_availability = user.is_reports_menu_available
    return report_availability

