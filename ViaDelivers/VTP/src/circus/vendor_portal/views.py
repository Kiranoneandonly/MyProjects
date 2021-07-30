from __future__ import unicode_literals

import json
import urllib
from collections import OrderedDict

from django.conf import settings
from django.contrib import messages
from django.contrib.messages import SUCCESS, WARNING
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, ListView, DetailView

from django_comments.models import Comment
from notifications.notifications import vendor_rejected_task
from projects.models import Project
from projects.states import COMPLETED_STATUS, ALL_STATUS
from shared.mixins import TaskSearchMixin
from shared.utils import comment_filters
from shared.viewmodels import VendorTasksViewModel, VendorCalendarTaskViewModel
from shared.views import DefaultContextMixin
from tasks.models import VendorPurchaseOrder, Task, TaskLocaleTranslationKit, TaskLocalizedAsset, NonTranslationTask, \
    TranslationTaskAnalysis
from vendor_portal.decorators import vendor_login_required
from vendors.models import Vendor


class VendorLoginRequiredMixin(object):
    @method_decorator(vendor_login_required)
    def dispatch(self, *args, **kwargs):
        # noinspection PyUnresolvedReferences
        return super(VendorLoginRequiredMixin, self).dispatch(*args, **kwargs)


class VendorTasksStatusView(VendorLoginRequiredMixin, DefaultContextMixin, TemplateView):
    template_name = 'vendors/tasks.html'

    def get_context_data(self, status=None, **kwargs):
        context = super(VendorTasksStatusView, self).get_context_data(**kwargs)
        vendor = self.request.user.account.cast(Vendor)
        context['can_access_phi_secure_job'] = vendor.can_access_phi_secure_job()
        vendor_tasks = VendorTasksViewModel(vendor)
        context['vendor_tasks'] = vendor_tasks
        current_status = vendor_tasks.statuses.get(status)
        context['current_status_name'] = current_status.name

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


class VendorTaskSearchView(VendorLoginRequiredMixin, TaskSearchMixin, DefaultContextMixin, ListView):
    status = ALL_STATUS
    template_name = 'vendors/search.html'
    context_object_name = 'tasks'

    def get_context_data(self, **kwargs):
        context = super(VendorTaskSearchView, self).get_context_data(**kwargs)
        context['search_query'] = self.search_query
        return context

    def get_queryset(self):
        self.search_query = self.request.GET.get('q')
        if not self.search_query:
            self.search_query = ""
            return []

        vendor = self.request.user.account.cast(Vendor)
        tasks = Task.objects.get_vendor_tasks(vendor)

        matches = self.get_matches(tasks, self.search_query)
        return sorted(matches, key=lambda task: task.project.job_number, reverse=True)


class VendorDashboardView(VendorLoginRequiredMixin, DefaultContextMixin, TemplateView):
    template_name = 'vendors/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super(VendorDashboardView, self).get_context_data(**kwargs)
        vendor = self.request.user.account.cast(Vendor)
        vendor_tasks = VendorTasksViewModel(vendor)

        context['vendor_tasks'] = vendor_tasks

        event_data = []
        non_translation_tasks = []
        for task in vendor_tasks.tasks_not_completed:
            ctvm = VendorCalendarTaskViewModel(task)
            event_data.append(ctvm.as_dict())

            if not task.is_translation():
                non_translation_tasks.append(NonTranslationTask.objects.get(id=task.id))

        context['event_data'] = json.dumps(event_data)
        context['non_translation_tasks'] = non_translation_tasks

        return context


class VendorTaskDetailView(DefaultContextMixin, DetailView):
    template_name = 'vendors/detail.html'
    model = Task
    active_tab = 'details'

    def get_context_data(self, **kwargs):
        context = super(VendorTaskDetailView, self).get_context_data(**kwargs)
        context['project'] = context['task'].project
        task = context['task']

        if not task.is_translation():
            asset_dict = OrderedDict()
            for asset in task.project.kit.source_files():
                asset_dict[asset] = asset.analysis_for_target(task.service.target).total_wordcount()
            context['asset_dict'] = asset_dict

        comment_types_vendor = comment_filters(settings.VENDOR_USER_TYPE)
        comments = Comment.objects.filter(object_pk=task.project.id, is_removed=False).filter(*comment_types_vendor)
        context['vendor_comment_list_check'] = comments

        context['show_on_supplier'] = any(asset.available_on_supplier for asset in task.project.kit.reference_files() if asset.available_on_supplier)

        context['active_tab'] = 'details'
        self.active_tab = 'details'

        if self.request.session.get('tab_session_name', False):
            context['active_tab'] = 'job_messages'
            self.active_tab = 'job_messages'

        return context

    def get_success_url(self):
        params = urllib.urlencode({'active_tab': self.active_tab})
        success_url = HttpResponseRedirect(reverse('vendor_task_detail', args=(self.kwargs['pk'],)) + '?' + params)
        return success_url

    def post(self, request, pk=None):
        if 'task_completed' in request.POST:
            try:
                task_id = request.POST.get("task_id", "")
                task = Task.objects.select_related().filter(assignee_object_id=request.user.account.id).get(pk=task_id)
            except:
                raise Http404

            if task.is_complete():
                msg = _("Task Already Completed")
                messages.add_message(request, WARNING, msg)
            elif task.complete_if_all_tla_files_ready():
                if task.project.all_tasks_complete():
                    if task.project.is_not_completed_status():
                        task.project.transition(COMPLETED_STATUS)
                messages.add_message(request, SUCCESS, _("Task Completed"))
            else:
                messages.add_message(request, WARNING, _("Could not complete task {0}.  Are all files uploaded?").format(task))

            task.current_user = self.request.user.id
            task.save()
            return HttpResponseRedirect(reverse('vendor_task_detail', kwargs={'pk': task.id}))
        
        if 'estimate_hours' in request.POST:
            estimate_hours = request.POST['estimate_hours']
            task_id = request.POST.get("task_id", "")
            task = NonTranslationTask.objects.get(pk=task_id)
            task.quantity = estimate_hours
            task.save()
            messages.add_message(request, SUCCESS, _("Estimate hours saved"))
            return HttpResponseRedirect(reverse('vendor_task_detail', kwargs={'pk': task.id}))

        if 'vendor_notes' in request.POST:
            vendor_notes = request.POST['vendor_notes_content']
            task_id = request.POST.get("task_id", "")
            task = Task.objects.select_related().filter(assignee_object_id=request.user.account.id).get(pk=task_id)
            task.vendor_notes = vendor_notes
            task.save()
            messages.add_message(request, SUCCESS, _("Notes Saved"))
            return HttpResponseRedirect(reverse('vendor_task_detail', kwargs={'pk': task.id}))

        if 'actual_hours' in request.POST:
            actual_hours = request.POST['actual_hours']
            task_id = request.POST.get("task_id", "")
            task = NonTranslationTask.objects.get(pk=task_id)
            task.actual_hours = actual_hours
            task.save()
            messages.add_message(request, SUCCESS, _("Actual hours saved"))
            return HttpResponseRedirect(reverse('vendor_task_detail', kwargs={'pk': task.id}))

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
            new_comments = comments.filter(object_pk=request.POST.get('comment_project_id'), comment_to='', comment_read_check=False, is_removed=False, notification_type=settings.NOTIFICATION_TYPE_MESSAGE)
            new_comments.update(comment_read_check=True, filter_from_list=True, comment_read_on=timezone.now())
            if new_comments:
                return HttpResponse(json.dumps({'message': 'Success'}), content_type="application/json")
            else:
                return HttpResponse(json.dumps({'message': 'Error'}), content_type="application/json")


def accept_task(request, pk=None):
    try:
        task = Task.objects.pending_acceptance().filter(assignee_object_id=request.user.account.id).get(pk=pk)
    except:
        raise Http404

    try:
        # todo link this to JAMS API to create real PO
        po, created = VendorPurchaseOrder.objects.get_or_create(vendor_id=task.assignee_object_id,
                                                                task=task,
                                                                due=task.due)
    except:
        pass

    try:
        task.accepted_timestamp = timezone.now()
        task.current_user = request.user.id
        task.save()
        messages.add_message(request, messages.SUCCESS, u"Task accepted")
    except:
        messages.add_message(request, messages.ERROR, u"Task acceptance issue")
    return HttpResponseRedirect(reverse('vendor_task_detail', kwargs={'pk': task.id}))


def reject_task(request, pk=None):
    try:
        task = Task.objects.pending_acceptance().filter(assignee_object_id=request.user.account.id).get(pk=pk)
    except:
        raise Http404

    try:
        vendor_rejected_task(request.user.account.cast(Vendor), task)

        task.assigned_to = None
        task.unit_cost = None
        task.current_user = request.user.id
        task.save()

        messages.add_message(request, messages.SUCCESS, _("Task rejected"))
    except:
        messages.add_message(request, messages.ERROR, _("Task rejection issue"))
    return HttpResponseRedirect(reverse('vendor_dashboard'))


def vendor_tltk_input_delivery_redirect(request, pk, tltk_id):
    """ called by s3 when an upload is finished for a vendor Translation delivery """
    tltk = TaskLocaleTranslationKit.objects.get(pk=tltk_id)
    import re
    key = request.GET.get('key')
    tltk.input_file = re.sub('^media/', '', key)
    tltk.current_user = request.user.id
    tltk.save()
    return HttpResponseRedirect(reverse('vendor_task_detail', kwargs={'pk': tltk.task.id}))


def vendor_tltk_delivery_redirect(request, pk, tltk_id):
    """ called by s3 when an upload is finished for a vendor Translation delivery """
    tltk = TaskLocaleTranslationKit.objects.get(pk=tltk_id)
    import re
    key = request.GET.get('key')
    tltk.output_file = re.sub('^media/', '', key)
    tltk.current_user = request.user.id
    tltk.save()
    return HttpResponseRedirect(reverse('vendor_task_detail', kwargs={'pk': tltk.task.id}))


def vendor_tlsf_delivery_redirect(request, pk, tltk_id):
    """ called by s3 when an upload is finished for a vendor Translation delivery """
    ltk = TaskLocaleTranslationKit.objects.get(pk=tltk_id)
    import re
    key = request.GET.get('key')
    ltk.support_file = re.sub('^media/', '', key)
    ltk.current_user = request.user.id
    ltk.save()
    #ltk.task.complete_if_ready()
    # GET TASK

    return HttpResponseRedirect(reverse('vendor_task_detail', kwargs={'pk': ltk.task.id}))


def vendor_tla_delivery_redirect(request, pk, tla_id):
    """ called by s3 when an upload is finished for a vendor Non-Translation delivery """
    tla = TaskLocalizedAsset.objects.get(id=tla_id)
    import re
    key = request.GET.get('key')
    tla.output_file = re.sub('^media/', '', key)
    tla.current_user = request.user.id
    tla.save()
    return HttpResponseRedirect(reverse('vendor_task_detail', kwargs={'pk': tla.task.id}))


def vendor_tlasf_delivery_redirect(request, pk, tla_id):
    """ called by s3 when an upload is finished for a vendor Non-Translation delivery """
    tla = TaskLocalizedAsset.objects.get(id=tla_id)
    import re
    key = request.GET.get('key')
    tla.support_file = re.sub('^media/', '', key)
    tla.current_user = request.user.id
    tla.save()
    return HttpResponseRedirect(reverse('vendor_task_detail', kwargs={'pk': tla.task.id}))


class ProjectCommentsView(VendorLoginRequiredMixin, ListView):
    template_name = 'vendors/vendor_project_comments.html'
    model = Project

    def get_context_data(self, **kwargs):
        context = super(ProjectCommentsView, self).get_context_data(**kwargs)
        project_id = self.kwargs['project_id']

        comment_types_vendor = comment_filters(settings.VENDOR_USER_TYPE)
        comments = Comment.objects.filter(object_pk=project_id, is_removed=False).filter(*comment_types_vendor)
        context['vendor_comment_list_check'] = comments

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
            new_comments = Comment.objects.filter(object_pk=request.POST.get('comment_project_id'), comment_to='', comment_read_check=False, is_removed=False, notification_type=settings.NOTIFICATION_TYPE_MESSAGE)
            new_comments.update(comment_read_check=True, filter_from_list=True, comment_read_on=timezone.now())
            if new_comments:
                return HttpResponse(json.dumps({'message': 'Success'}), content_type="application/json")
            else:
                return HttpResponse(json.dumps({'message': 'Error'}), content_type="application/json")


class VendorProjectNotificationsListView(VendorLoginRequiredMixin, ListView):
    template_name = 'vendors/vendor_project_comments_list.html'
    context_object_name = 'messages_list'
    model = Comment
    paginate_by = settings.PAGINATE_BY_STANDARD

    def get_queryset(self):
        comments = super(VendorProjectNotificationsListView, self).get_queryset()
        comments = comments.filter(comment_to=self.request.user.id, is_removed=False, filter_from_list=False, comment_read_check=False, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION).order_by('-id')
        return comments

    def get_context_data(self, **kwargs):
        context = super(VendorProjectNotificationsListView, self).get_context_data(**kwargs)
        comments = context['messages_list']
        comments_obj = Comment.objects
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
            return HttpResponseRedirect(reverse('vendor_notification_unread_count'))
       if 'clear_all' in self.request.POST:
            comment = Comment.objects.filter(comment_to=self.request.user.id, comment_read_check=False, is_removed=False, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
            comment.update(comment_read_check=True, filter_from_list=True, comment_read_on=timezone.now())
            return HttpResponseRedirect(reverse('vendor_notification_unread_count'))

