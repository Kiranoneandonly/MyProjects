"""Web-based views of the notification templates.

Currently just for debugging (urls restricted to VIA users).
"""

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.template.defaultfilters import date
from django.utils.timezone import localtime
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST

from clients.models import ClientContact, Client
from projects.models import Project


def via_new_client_user(request, user_id):
    user = get_object_or_404(ClientContact, id=user_id)
    context = {
        'user': user,
        'vtp_url': settings.BASE_URL,
    }
    return render(request=request, template_name='notifications/via_new_client_user.html', context=context)


def via_new_client_account(request, account_id):
    client = get_object_or_404(Client, id=account_id)

    contacts = client.contacts.all()

    context = {
        'client': client,
        'contacts': contacts,
        'vtp_url': settings.BASE_URL,
    }
    return render(request=request, template_name='notifications/via_new_client_account.html', context=context)


def project_manual_quote_needed(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    context = {
        'project': project,
        'vtp_url': settings.BASE_URL,
    }
    return render(request=request, template_name='notifications/project_manual_quote_needed.html', context=context)


def project_manual_quote_needed_via(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    context = {
        'project': project,
        'vtp_url': settings.BASE_URL,
    }
    return render(request=request, template_name='notifications/project_manual_quote_needed_via.html', context=context)


@require_POST
def mute(request, project_id):
    from .models import NotificationMute

    project = get_object_or_404(Project, id=project_id)

    if 'mute' in request.POST:
        nmute = NotificationMute.objects.mute(project, request.user)
        messages.success(request, _("Notifications for %s muted until %s" %
                                    (project.job_number,
                                     date(localtime(nmute.expires_at),
                                          "DATETIME_FORMAT"))))
    elif 'unmute' in request.POST:
        NotificationMute.objects.unmute(project)
        messages.success(request, _("Notifications for %s are now unmuted." %
                                    (project.job_number,)))

    if project.approved:
        view_name = 'via_job_detail_tasks'
    else:
        view_name = 'via_job_detail_estimate'
    return redirect(view_name, project.id)
