from __future__ import unicode_literals

import json
import urllib

from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.cache import add_never_cache_headers
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django_comments.models import Comment
from lib.filetransfers.api import serve_file
from localization_kits.forms import FileAnalysisForm
from localization_kits.models import LocalizationKit, FileAnalysis, FileAsset, LocaleTranslationKit, ANALYSIS_STATUS_SUCCESS, SOURCEFILE_ASSET, REFERENCEFILE_ASSET
from notifications.notifications import notify_via_job_completed, notify_new_content_added
from projects.models import Project
from tasks.models import TaskLocaleTranslationKit, TaskLocalizedAsset, TranslationTaskAnalysis

from projects.states import STARTED_STATUS

ANALYSIS_COOKIE_NAME = 'in_progress'


class AnalysisDetailView(generic.DetailView):
    template_name = 'via/projects/kits/assets/analysis/detail.html'
    model = FileAnalysis
    context_object_name = 'analysis'


class AnalysisUpdateView(generic.UpdateView):
    template_name = 'via/projects/kits/assets/analysis/edit.html'
    model = FileAnalysis
    form_class = FileAnalysisForm
    context_object_name = 'analysis'

    def get_success_url(self):
        params = urllib.urlencode({'active_tab': 'analysis'})
        return reverse('via_job_detail_estimate', args=(self.object.asset.kit.project.id,)) + '?' + params

    def form_valid(self, form):
        self.object = form.save(commit=False)

        self.object.message = u"Count Entered Manually"
        self.object.save()
        self.object.asset.status = ANALYSIS_STATUS_SUCCESS
        self.object.asset.save()

        analysis = TranslationTaskAnalysis.objects.create_from_kit(self.object.asset.kit, self.object.target_locale)
        if not analysis:
            messages.add_message(self.request, messages.ERROR, 'Could not update analysis')
            return HttpResponseRedirect(reverse('kits_asset_analysis_edit', args=(self.object,)))

        if form.initial['asset'] != self.object.asset.id:
            old_analysis = FileAnalysis.objects.filter(asset=self.object.asset, target_locale=self.object.target_locale).exclude(id=self.object.id)
            old_analysis.delete()
            old_file = FileAsset.objects.filter(id=form.initial['asset'])
            old_file_in_use = FileAnalysis.objects.filter(asset=old_file).exists()
            if not old_file_in_use:
                old_file.delete()

        self.object.asset.kit.project.set_rates_and_prices()
        messages.add_message(self.request, messages.SUCCESS, 'Analysis Updated')
        return HttpResponseRedirect(self.get_success_url())


def store_file(name, body):
    return name


@csrf_exempt
def upload_file_to_kit(request, proj_id):
    """accept a file upload via Xhr"""
    error = None

    kit = get_object_or_404(LocalizationKit, project__id=proj_id)

    # TODO process zip file here
    # check against file extension whitelist

    body = None
    try:
        if request.FILES.get('qqfile'):
            body = request.FILES.get('qqfile').file.read()

        if body:
            filename = request.FILES.get('qqfile').name
        else:
            filename = request.GET.get('qqfile')
            request.body._read_started = False
            body = request.body
    except:
        if request.GET.get('qqfile'):
            filename = request.GET.get('qqfile')
            request.body._read_started = False
            body = request.body
        else:
            raise

    asset_type = request.POST.get('asset_type')
    if asset_type == 'source':
        asset_type = SOURCEFILE_ASSET
    elif asset_type == 'reference':
        asset_type = REFERENCEFILE_ASSET
    else:
        asset_type = SOURCEFILE_ASSET

    asset = FileAsset.objects.create(
        kit=kit,
        orig_name=filename,
        asset_type=asset_type
    )

    try:
        asset.orig_file.save(filename, ContentFile(body))
        proj = Project.objects.get(id=proj_id)
        if proj.status == STARTED_STATUS and asset_type == REFERENCEFILE_ASSET:
            notify_new_content_added(proj)
    except:
        if asset.id:
            asset.delete()
        import traceback
        tb = traceback.format_exc()  # NOQA
        error = _('Could not save file.')

    return HttpResponse('{"error": %s}' % error if error else '{"success": true, "id": ' + unicode(asset.id) + ' }', content_type="text/html")


def asset_download_handler(request, proj_id, asset_id):
    asset = FileAsset.objects.get(id=asset_id)
    # todo file missing
    result = serve_file(request, asset.orig_file, save_as=True)
    return result


def localetranslationkit_file_download_handler(request, pk):
    ltk = LocaleTranslationKit.objects.get(id=pk)
    # todo file_missing
    return serve_file(request, ltk.translation_file, save_as=True)


def tasklocaletranslationkit_infile_download_handler(request, task_id, tltk_id):
    ltk = TaskLocaleTranslationKit.objects.get(id=tltk_id)
    # todo file_missing
    return serve_file(request, ltk.input_file, save_as=True)


def tasklocaletranslationkit_outfile_download_handler(request, task_id, tltk_id):
    ltk = TaskLocaleTranslationKit.objects.get(id=tltk_id)
    # todo file_missing
    return serve_file(request, ltk.output_file, save_as=True)

def tasklocaletranslationkit_supfile_download_handler(request, task_id, tltk_id):
    ltk = TaskLocaleTranslationKit.objects.get(id=tltk_id)
    # todo file_missing
    return serve_file(request, ltk.support_file, save_as=True)

def tasklocaletranslationkit_tmfile_download_handler(request, task_id, tltk_id):
    ltk = TaskLocaleTranslationKit.objects.get(id=tltk_id)
    # todo file_missing
    return serve_file(request, ltk.tm_update_file, save_as=True)

def tasklocalizedasset_infile_download_handler(request, task_id, tla_id):
    la = TaskLocalizedAsset.objects.get(id=tla_id)
    # todo file_missing
    return serve_file(request, la.input_file, save_as=True)


def tasklocalizedasset_outfile_download_handler(request, task_id, tla_id):
    # todo file_missing
    la = TaskLocalizedAsset.objects.get(id=tla_id)
    result = serve_file(request, la.output_file, save_as=True)

    # BAIL
    project = Project.objects.select_related().get(id=la.task.project_id)
    if project.completed or not request.user.is_client():
        return result

    # record that the file was downloaded by client
    if not la.downloaded:
        la.downloaded = timezone.now()
        la.save()
        # todo verify if this is really needed, but it does spam a lot of emails.  It will send final completion below.
        # send VIA email about file downloaded.
        # notify_via_client_asset_pickup(la, project)

    # record completed if all deliveries downloaded
    if project.all_deliveries_complete():
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

    return result


def tasklocalizedasset_post_deliveryfile_download_handler(request, task_id, tla_id):
    # todo file_missing
    la = TaskLocalizedAsset.objects.get(id=tla_id)
    result = serve_file(request, la.post_delivery_file, save_as=True)

    # BAIL
    # project = Project.objects.select_related().get(id=la.task.project_id)
    # if project.completed or not request.user.is_client():
    #     return result
    #
    # # record that the file was downloaded by client
    # if not la.downloaded:
    #     la.downloaded = timezone.now()
    #     la.save()
    #     # todo verify if this is really needed, but it does spam a lot of emails.  It will send final completion below.
    #     # send VIA email about file downloaded.
    #     # notify_via_client_asset_pickup(la, project)
    #
    # # record completed if all deliveries downloaded
    # if project.all_deliveries_complete():
    #     project.completed = timezone.now()
    #     project.save()
    #     notify_via_job_completed(project)

    return result


def tasklocalizedasset_supfile_download_handler(request, task_id, tla_id):
    la = TaskLocalizedAsset.objects.get(id=tla_id)
    # todo file_missing
    return serve_file(request, la.support_file, save_as=True)

@require_POST
def queue_analysis(request, loc_kit_id):
    loc_kit = get_object_or_404(LocalizationKit, id=loc_kit_id)
    if loc_kit.analyzing():
        messages.add_message(request, messages.WARNING,
                             _('An analysis is already pending.'))
    else:
        loc_kit.queue_analysis_tasks()
        messages.add_message(request, messages.SUCCESS, _('Analysis Queued'))

    response = HttpResponseRedirect(reverse('via_job_detail_estimate',
                                    args=(loc_kit.project.id,)) +
                                    '?active_tab=analysis')

    update_analysis_cookie(response, loc_kit.project)
    return response


def update_analysis_cookie(response, project):
    # Setting this cookie lets notifications.js know it should be
    # checking to see when the analysis is done.
    analyses = [project.id]
    if ANALYSIS_COOKIE_NAME in response.cookies:
        old_analyses = json.loads(response.cookies[ANALYSIS_COOKIE_NAME])
        if old_analyses:
            analyses.extend(old_analyses)
    response.set_cookie(ANALYSIS_COOKIE_NAME, json.dumps(analyses))



class AJAXAnalysisStatusCheck(object):
    """Is analysis complete on these projects?

    Takes query parameter `projects`, a JSON-encoded list of project IDs.
    Also checks the cookie named by ANALYSIS_COOKIE_NAME.

    The logic here is that there are cookies so the client knows what to poll
    for without having to get that information into the base template, and we
    get the bonus of finding out about new analyses started in other tabs.

    But if one tab polls and gets the "completed" notification (and that project
    removed from the things-to-poll-for cookie), we don't one the notification
    to appear in only that tab, so the poller also includes the query parameter
    for things it doesn't want to forget about.
    """
    def __init__(self, project_filter, project_ready_url):
        """
        :type project_filter: (django.http.request.HttpRequest, QuerySet[Project]) -> QuerySet[Project]
        :type project_ready_url: Project -> str
        """
        self.project_filter = project_filter
        self.project_ready_url = project_ready_url

    def __call__(self, request):
        """
        :param request: django.http.request.HttpRequest
        :return: json {'id': int, 'complete': bool, 'name': text, 'url': text}
        """
        if not request.user.is_authenticated():
            # not using @login_required, as we don't want a json API endpoint to
            # redirect to a HTML page.
            return HttpResponseForbidden(json.dumps({
                'error': 'You are not logged in.'
            }))

        project_ids = json.loads(request.GET['projects'])

        if ANALYSIS_COOKIE_NAME in request.COOKIES:
            cookie_project_ids = json.loads(request.COOKIES[ANALYSIS_COOKIE_NAME])
            project_ids.extend(cookie_project_ids)

        results = []
        remaining = []

        projects = Project.objects.select_related().filter(id__in=project_ids).order_by('id')
        projects = self.project_filter(request, projects)

        for project in projects:
            complete = not project.kit.analyzing()

            if not complete:
                remaining.append(project.id)

            results.append({
                'id': project.id,
                'complete': complete,
                'name': project.name,
                'url': self.project_ready_url(project),
            })

        response = HttpResponse(json.dumps(results),
                                content_type='application/json')

        if remaining:
            response.set_cookie(ANALYSIS_COOKIE_NAME, json.dumps(remaining))
        else:
            response.delete_cookie(ANALYSIS_COOKIE_NAME)

        # Needed especially for IE and GET requests, or it just returns the
        # response from the first time it asked, making polling ineffective.
        add_never_cache_headers(response)
        return response


via_check_analysis_status = AJAXAnalysisStatusCheck(
    project_filter=lambda request, projects: projects,  # staff view, not filtered
    project_ready_url=lambda project: (
        reverse('via_job_detail_estimate', args=(project.id,))
        + '?active_tab=details')
)
