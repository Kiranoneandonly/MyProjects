import datetime
import tempfile
import zipfile
import logging

from django.http import StreamingHttpResponse
from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.http import Http404
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.http import require_POST
from wsgiref.util import FileWrapper


from clients.models import ClientReferenceFiles, Client
from django_comments.models import Comment
from notifications.notifications import notify_via_job_completed
from projects.models import Project
from projects.states import (
    CANCELED_STATUS, QUOTED_STATUS, STARTED_STATUS, TASK_COMPLETED_STATUS, VIA_STATUS_DETAIL, get_reversed_status)
from services.managers import FINAL_APPROVAL_SERVICE_TYPE
from services.models import Locale
from tasks.models import TaskLocalizedAsset

logger = logging.getLogger('circus.' + __name__)


def project_target_delivery_zip(request, proj_id, lcid):
    try:

        project = get_object_or_404(Project, id=proj_id)
        if lcid == '0':
            target = 'ALL'
            deliveries = TaskLocalizedAsset.objects.filter(
                task__project_id=project.id,
                task__service__service_type__code=FINAL_APPROVAL_SERVICE_TYPE,
                task__status=TASK_COMPLETED_STATUS,
            )

        else:
            target = Locale.objects.get(lcid=lcid)
            deliveries = TaskLocalizedAsset.objects.filter(
                task__project_id=project.id,
                task__service__service_type__code=FINAL_APPROVAL_SERVICE_TYPE,
                task__status=TASK_COMPLETED_STATUS,
                task__service__target=target
            )

        temp = tempfile.TemporaryFile()
        archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)
        for delivery in deliveries:
            archive.writestr(delivery.output_file_name(), delivery.output_file.read())
        archive.close()

        wrapper = FileWrapper(temp)
        response = StreamingHttpResponse(wrapper, content_type='application/zip')
        filename = 'attachment; filename={0}_{2}_delivery_{1}.zip'.format(
            project.job_number, str(datetime.datetime.now())[:10],
            target)
        response['Content-Disposition'] = filename
        response['Content-Length'] = temp.tell()
        temp.seek(0)

        # bail out?
        if project.completed or not request.user.is_client():
            return response

        # record that each file was downloaded by client
        for delivery in deliveries.filter(downloaded__isnull=True):
            delivery.downloaded = timezone.now()
            delivery.save()

        # all deliveries downloaded - record project complete
        project.completed = timezone.now()
        project.current_user = request.user.id
        project.save()
        notify_via_job_completed(project)

        ctype = ContentType.objects.get_for_model(Project)
        obj_pk = project.id
        comment_text = _('Job Completed')

        if project.client.manifest.show_client_messenger:
            user = project.project_manager if project.project_manager else request.user
            comments = Comment(object_pk=obj_pk, user=user, comment=comment_text, user_type=user.user_type, comment_to=project.client_poc.id, ip_address=request.META.get("REMOTE_ADDR", None), via_comment_user_type=settings.VIA_USER_TYPE, content_type_id=ctype.id, site_id=settings.SITE_ID, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
            comments.save()

        team_members = Project.get_assigned_team_comments(project)
        for member in team_members:
            comments = Comment(object_pk=obj_pk, user=request.user, comment=comment_text, user_type=request.user.user_type, comment_to=member.contact_id, ip_address=request.META.get("REMOTE_ADDR", None), via_comment_user_type=settings.VIA_USER_TYPE, content_type_id=ctype.id, site_id=settings.SITE_ID, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
            comments.save()

        return response

    except Exception, error:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        logger.error("project_target_delivery_zip error %s" % (error,), exc_info=True)
        messages.error(request, _(u"Job Delivery Zip download issue.  Please contact VIA Project Manager for further assistance."))
        return HttpResponseRedirect(reverse('client_project_detail', args=(proj_id,)))


def project_source_files_zip(request, proj_id=None):
    try:
        logger.info('project_source_files_zip: ' + proj_id)
        project = get_object_or_404(Project, id=proj_id)
        temp = tempfile.TemporaryFile()
        archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)
        for asset in project.kit.source_files():
            archive.writestr(asset.file_display_name(), asset.orig_file.read())
        archive.close()
        wrapper = FileWrapper(temp)
        response = StreamingHttpResponse(wrapper, content_type='application/zip')
        filename = 'attachment; filename={0}_source_{1}.zip'.format(project.job_number, str(datetime.datetime.now())[:10])
        response['Content-Disposition'] = filename
        response['Content-Length'] = temp.tell()
        temp.seek(0)
        return response
    except Exception, error:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        logger.error("project_source_files_zip error", exc_info=True)
        messages.error(request, _(u"Job Source File Zip download issue. %s" % (error,)))
        return HttpResponseRedirect(reverse('via_job_detail_files', args=(proj_id,)))


def project_reference_files_zip(request, proj_id=None):
    try:
        logger.info('project_reference_files_zip: ' + proj_id)
        project = get_object_or_404(Project, id=proj_id)
        temp = tempfile.TemporaryFile()
        archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)
        for asset in project.kit.reference_files():
            archive.writestr(asset.file_display_name(), asset.orig_file.read())
        archive.close()
        wrapper = FileWrapper(temp)
        response = StreamingHttpResponse(wrapper, content_type='application/zip')
        filename = 'attachment; filename={0}_reference_{1}.zip'.format(project.job_number, str(datetime.datetime.now())[:10])
        response['Content-Disposition'] = filename
        response['Content-Length'] = temp.tell()
        temp.seek(0)
        return response
    except Exception, error:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        logger.error("project_reference_files_zip error", exc_info=True)
        messages.error(request, _(u"Job Reference File Zip download issue. %s" % (error,)))
        return HttpResponseRedirect(reverse('via_job_detail_files', args=(proj_id,)))


def glossary_styleguide_files_zip(request, proj_id=None):
    try:
        logger.info('glossary_styleguide_files_zip: ' + proj_id)
        project = get_object_or_404(Project, id=proj_id)
        temp = tempfile.TemporaryFile()
        archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)
        client_files = ClientReferenceFiles.objects.filter(project_id=project.id)
        for files in client_files:
            archive.writestr(files.file_display_name(), files.orig_file.read())
        archive.close()
        wrapper = FileWrapper(temp)
        response = StreamingHttpResponse(wrapper, content_type='application/zip')
        filename = 'attachment; filename={0}_client_ref_{1}.zip'.format(project.job_number, str(datetime.datetime.now())[:10])
        response['Content-Disposition'] = filename
        response['Content-Length'] = temp.tell()
        temp.seek(0)
        return response
    except Exception, error:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        logger.error("glossary_styleguide_files_zip error", exc_info=True)
        messages.error(request, _(u"Job Client Reference File Zip download issue. %s" % (error,)))
        return HttpResponseRedirect(reverse('via_job_detail_files', args=(proj_id,)))


def perform_action(request, pk=None, action_slug=None):
    try:
        project = Project.objects.select_related().get(pk=pk)
        action = next(action for action in project.actions() if action.slug == action_slug)
        action_function = action.function
        project.current_user = request.user.id
        project.save()
    except:
        import traceback
        tb = traceback.format_exc()  # NOQA
        raise Http404

    level, message = action_function(project, request.user)
    messages.add_message(request, level, message)

    if project.is_started_status():
        return HttpResponseRedirect(reverse('via_job_detail_tasks', args=(project.id,)))
    elif project.is_inestimate_status():
        return HttpResponseRedirect(reverse('via_job_detail_estimate', args=(project.id,)))
    else:
        return HttpResponseRedirect(reverse('via_job_detail_overview', args=(project.id,)))


def _perform_transition(request, pk=None, transition_slug=None):
    #: :type: Project
    project = Project.objects.select_related().get(pk=pk)
    project.transition(transition_slug)
    project.current_user = request.user.id
    if transition_slug == CANCELED_STATUS:
        project.canceled = datetime.datetime.now()
    else:
        if project.canceled:
            project.canceled = None
    project.save()
    ctype = ContentType.objects.get_for_model(Project)
    obj_pk = project.id
    if transition_slug == QUOTED_STATUS:
        if project.client.manifest.show_client_messenger:
            user = project.project_manager if project.project_manager else request.user
            comment_text = _('Estimate ready')
            comments = Comment(object_pk=obj_pk, user=user, comment=comment_text, user_type=request.user.user_type, comment_to=project.client_poc.id, ip_address=request.META.get("REMOTE_ADDR", None), via_comment_user_type=settings.VIA_USER_TYPE, content_type_id=ctype.id, site_id=settings.SITE_ID, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
            comments.save()
    if transition_slug == STARTED_STATUS:
        comment_text = _('Job Active')
        team_members = Project.get_assigned_team_comments(project)
        for member in team_members:
            comments = Comment(object_pk=obj_pk, user=request.user, comment=comment_text, user_type=request.user.user_type, comment_to=member.contact_id, ip_address=request.META.get("REMOTE_ADDR", None), via_comment_user_type=settings.VIA_USER_TYPE, content_type_id=ctype.id, site_id=settings.SITE_ID, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
            comments.save()
    redirect_url = reverse('via_job_detail_overview', args=(project.id,))

    current_status = VIA_STATUS_DETAIL[get_reversed_status(project.status)]['text']
    messages.success(request, u"Job moved to %s" % (current_status,))

    return HttpResponseRedirect(redirect_url)


perform_transition = require_POST(_perform_transition)


# cancel should also require_POST (with CSRF protection), but doesn't yet.
def cancel(request, proj_id):
    client = request.user.account.cast(Client)
    if client.manifest.enforce_customer_hierarchy and not request.user.has_perm('projects.add_project'):
        messages.add_message(request, messages.ERROR, u"Not enough access to perform action")
        return HttpResponseRedirect(reverse('client_dashboard'))

    project = Project.objects.select_related().get(id=proj_id)
    project.transition(CANCELED_STATUS)
    project.current_user = request.user.id
    project.canceled = datetime.datetime.now()
    project.save()
    redirect_url = reverse('client_dashboard')
    messages.success(request, u"Job %s canceled." % (project.job_number,))
    return HttpResponseRedirect(redirect_url)


def show_files(request , proj_id):
    project = Project.objects.select_related().get(id=proj_id)
    if (project.is_restricted_job and request.user.id == project.client_poc.id) or (not project.is_restricted_job):
        return True
    else:
        return False


def get_order_by_filed_name(order_by_field):
    order_by_field_name = None
    if order_by_field == 'job_id':
        order_by_field_name = 'job_number'
    elif order_by_field == 'workflow':
        order_by_field_name = 'status'
    elif order_by_field == 'company':
        order_by_field_name = 'client__name'
    elif order_by_field == 'file':
        order_by_field_name = 'kit__files'
    elif order_by_field == 'source':
        order_by_field_name = 'source_locale'
    elif order_by_field == 'targets':
        order_by_field_name = 'target_locales'
    elif order_by_field == 'price':
        order_by_field_name = 'price'
    elif order_by_field == 'requester':
        order_by_field_name = 'client_poc__first_name'
    elif order_by_field == 'pm':
        order_by_field_name = 'project_manager__first_name'
    elif order_by_field == 'ae':
        order_by_field_name = 'account_executive__first_name'
    elif order_by_field == 'tsg':
        order_by_field_name = 'estimator__first_name'
    elif order_by_field == 'estimate_number':
        order_by_field_name = 'jams_estimateid'
    elif order_by_field == 'estimate_due':
        order_by_field_name = 'quote_due'
    elif order_by_field == 'estimated':
        order_by_field_name = 'quoted'
    elif order_by_field == 'started':
        order_by_field_name = 'started_timestamp'
    elif order_by_field == 'due':
        order_by_field_name = 'due'
    elif order_by_field == 'delivered':
        order_by_field_name = 'delivered'
    elif order_by_field == 'completed':
        order_by_field_name = 'completed'
    elif order_by_field == 'purchase_order':
        order_by_field_name = 'payment_details__ca_invoice_number'
    elif order_by_field == 'job_reference':
        order_by_field_name = 'project_reference_name'
    elif order_by_field == 'department':
        order_by_field_name = 'client_poc__department'
    elif order_by_field == 'approved':
        order_by_field_name = 'approved'
    elif order_by_field == 'restricted':
        order_by_field_name = 'is_restricted_job'
    elif order_by_field == 'warnings':
        order_by_field_name = 'warnings'
    elif order_by_field == 'express':
        order_by_field_name = 'express'
    elif order_by_field == 'auto_estimate':
        order_by_field_name = 'auto_estimate'
    elif order_by_field == 'internal_via':
        order_by_field_name = 'internal_via_project'
    elif order_by_field == 'phi':
        order_by_field_name = 'is_phi_secure_job'

    return order_by_field_name
