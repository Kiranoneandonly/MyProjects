import datetime
import tempfile
from collections import OrderedDict
import zipfile
from urlparse import urljoin, urlparse

from django.conf import settings
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from wsgiref.util import FileWrapper
from django.http import HttpResponseRedirect, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, UpdateView
from django_comments.models import Comment

from notifications.notifications import notify_client_job_ready, notify_assigned_to_task_assigned, notify_due_dates_changed, project_quote_ready
from shared.forms import S3UploadForm
from projects.models import Project
from projects.set_prices import set_task_set_rates_and_prices, set_rate
from projects.states import QUOTED_STATUS, CREATED_STATUS, COMPLETED_STATUS
from shared.viewmodels import TargetAnalysisSetViewModel
from shared.views import set_filefield_from_s3_redirect, DefaultContextMixin
from tasks.forms import TaskForm
from tasks.models import Task, VendorPurchaseOrder, TaskLocalizedAsset, TaskLocaleTranslationKit, get_task_output_asset_path
from shared.utils import copy_file_asset
from accounts.models import CircusUser
from jams_api.management.commands.create_job_task_and_po import create_jams_job_tasks_and_po


def task_input_files_zip(request, pk=None):
    task = get_object_or_404(Task, pk=pk)
    temp = tempfile.TemporaryFile()
    archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)
    for f in task.files:
        input_file = f['input']
        archive.writestr(input_file['name'],
                         input_file['file'].file.read())
    archive.close()
    wrapper = FileWrapper(temp)
    response = StreamingHttpResponse(wrapper, content_type='application/zip')
    filename = 'attachment; filename={0}_input_{1}.zip'.format(
        task.project.job_number, str(datetime.datetime.now())[:10])
    response['Content-Disposition'] = filename
    response['Content-Length'] = temp.tell()
    temp.seek(0)
    return response


def task_output_files_zip(request, pk=None):
    task = get_object_or_404(Task, pk=pk)
    temp = tempfile.TemporaryFile()
    archive = zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED)
    for f in task.files:
        output_file = f['output']
        archive.writestr(output_file['name'],
                         output_file['file'].file.read())
    archive.close()
    wrapper = FileWrapper(temp)
    response = StreamingHttpResponse(wrapper, content_type='application/zip')
    filename = 'attachment; filename={0}_output_{1}.zip'.format(
        task.project.job_number, str(datetime.datetime.now())[:10])
    response['Content-Disposition'] = filename
    response['Content-Length'] = temp.tell()
    temp.seek(0)
    return response


def _remove_reference_file(request, task_id):
    task = Task.objects.get(id=task_id)
    task.reference_file = None
    task.current_user = request.user.id
    task.save()
    messages.add_message(request, messages.SUCCESS, _("Reference file removed."))
    return redirect('projects_tasks_edit', task_id)


remove_reference_file = require_POST(_remove_reference_file)


class TaskCreateView(DefaultContextMixin, CreateView):
    template_name = "via/projects/tasks/create.html"
    form_class = TaskForm
    context_object_name = 'task'

    def get_form_kwargs(self):
        kwargs = super(TaskCreateView, self).get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def get_project(self):
        return Project.objects.select_related().get(pk=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        context = super(TaskCreateView, self).get_context_data(**kwargs)
        self.project = self.get_project()
        context['project'] = self.project
        return context

    def form_valid(self, form):
        task = form.save(commit=False)
        project = self.get_project()
        task.project = project
        task.current_user = self.request.user.id
        task.save()
        form.save_m2m()
        messages.add_message(self.request, messages.SUCCESS, _('Task created'))
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('via_job_detail_estimate', args=(self.kwargs.get('pk'),))


class TaskUpdateView(DefaultContextMixin, UpdateView):
    template_name = "via/projects/tasks/edit.html"
    form_class = TaskForm
    context_object_name = 'task'
    queryset = Task.objects.all()
    model = Task

    def get_success_url(self):
        if self.object.project.is_inestimate_status():
            return reverse('via_job_detail_estimate', args=(self.object.project_id,))
        else:
            return reverse('via_job_detail_tasks', args=(self.object.project_id,))

    def get_context_data(self, **kwargs):
        context = super(TaskUpdateView, self).get_context_data(**kwargs)
        task = context['task']
        task.project.quote()
        # task.project.quote_summary()
        if task.project.has_workflow_sub_tasks():
            quote = task.project.sub_task_quote()
            context['task_quote'] = quote.tasks[task]
        if task.is_translation():
            target_analyses = OrderedDict()
            for target in task.project.target_locales.order_by("description"):
                target_analyses[target] = TargetAnalysisSetViewModel(target, task.project, include_placeholder=True)
            context['target_analyses'] = target_analyses

        context['reference_upload_form'] = self.reference_upload_form(task)
        referer_url = ''
        url_referer = self.request.META.get('HTTP_REFERER')
        if url_referer:
            o = urlparse(url_referer)
            from django.core.urlresolvers import resolve
            referer_url = resolve(o.path).url_name
        context['is_from_mytaskview'] = False
        if referer_url == 'my_tasks_status':
            context['is_from_mytaskview'] = True

        context['restricted_locations'] = task.project.project_restricted_locations_list()
        context['can_edit_job'] = task.project.can_edit_job(self.request.user.country)
        if task.predecessor and task.predecessor.vendor_notes:
            context['previous_task_vendor_notes'] = task.predecessor.vendor_notes

        context['is_task_view'] = self.request.COOKIES.get('task_view')
        if task.qa_approved:
            vp = VendorPurchaseOrder.objects.filter(task=task)
            if not vp:
                create_jams_job_tasks_and_po(task.project.job_number)
        return context

    def get_form_kwargs(self):
        kwargs = super(TaskUpdateView, self).get_form_kwargs()
        kwargs["project"] = self.get_project()
        return kwargs

    def reference_upload_form(self, task):
        # the '${filename}' is a placeholder S3 looks for
        asset_path_part = (
            settings.MEDIA_URL[1:] +
            task.reference_file.field.generate_filename(task, '${filename}'))
        import re
        if re.search(r"\\+", asset_path_part):
            asset_path_part = re.sub(r"\\+", '/', asset_path_part)

        asset_path = asset_path_part.replace("filename", "${filename}")

        redirect_to = reverse('task_supplier_ref_uploaded',
                              kwargs={'task_id': task.id})

        redirect_to = urljoin(settings.BASE_URL, redirect_to)
        return S3UploadForm(asset_path, redirect_to)

    def get_project(self):
        return Project.objects.select_related().get(pk=self.object.project_id)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.current_user = self.request.user.id
        if 'task_completed' in request.POST:
            successful = True
            if self.object.is_translation():
                if not self.object.complete_if_ready():
                    successful = False
            elif self.object.complete_if_all_tla_files_ready():
                if self.object.project.all_tasks_complete():
                    if self.object.project.is_not_completed_status():
                        self.object.project.transition(COMPLETED_STATUS)
                    notify_client_job_ready(self.object.project)

                    ctype = ContentType.objects.get_for_model(self.object.project)
                    obj_pk = self.object.project.id
                    comment_text = _('Job Delivered')

                    if self.object.project.client.manifest.show_client_messenger:
                        user = self.object.project.project_manager if self.object.project.project_manager else request.user
                        comments = Comment(object_pk=obj_pk, user=user, comment=comment_text, user_type=user.user_type, comment_to=self.object.project.client_poc.id, ip_address=request.META.get("REMOTE_ADDR", None), via_comment_user_type=settings.VIA_USER_TYPE, content_type_id=ctype.id, site_id=settings.SITE_ID, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
                        comments.save()

                    team_members = Project.get_assigned_team_comments(self.object.project)
                    for member in team_members:
                        comments = Comment(object_pk=obj_pk, user=request.user, comment=comment_text, user_type=request.user.user_type, comment_to=member.contact_id, ip_address=request.META.get("REMOTE_ADDR", None), via_comment_user_type=settings.VIA_USER_TYPE, content_type_id=ctype.id, site_id=settings.SITE_ID, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
                        comments.save()

            else:
                successful = False

            if successful:
                comment_text = _('Task Completed')
                messages.add_message(request, messages.SUCCESS, comment_text)
                ctype = ContentType.objects.get_for_model(self.object)
                obj_pk = self.object.id
                pm_id = self.object.project.project_manager.id if self.object.project.project_manager else None
                if pm_id:
                    comments = Comment(object_pk=obj_pk, user=request.user, comment=comment_text, user_type=request.user.user_type, comment_to=pm_id, ip_address=request.META.get("REMOTE_ADDR", None), via_comment_user_type=settings.VIA_USER_TYPE, content_type_id=ctype.id, site_id=settings.SITE_ID, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
                    comments.save()
                return redirect('via_job_detail_tasks', self.object.project_id)
            else:
                messages.add_message(request, messages.WARNING, _("Could not complete task {0}.  Are all files uploaded?").format(self.object))
                return redirect('projects_tasks_edit', self.object.id)

        # removing the file line file_line_delete
        if 'tla_input_delete' in request.POST:
            tla_id = request.POST['tla_input_delete']
            try:
                obj = TaskLocalizedAsset.objects.get(id=tla_id)
                obj.input_file = ''
                obj.current_user = request.user.id
                obj.save()
                messages.add_message(request, messages.SUCCESS, u"Task Localized Input file was deleted successfully")
            except:
                pass
            return redirect('projects_tasks_edit', self.object.id)

        # removing the out file line file_line_delete
        if 'tla_output_delete' in request.POST:
            tla_id = request.POST['tla_output_delete']
            try:
                obj = TaskLocalizedAsset.objects.get(id=tla_id)
                obj.output_file = ''
                obj.current_user = request.user.id
                obj.save()
                messages.add_message(request, messages.SUCCESS, u"Task Localized Output file was deleted successfully")
            except:
                pass
            return redirect('projects_tasks_edit', self.object.id)

        # removing the locale translation out file_delete
        if 'tltk_output_delete' in request.POST:
            trans_kit_id = request.POST['tltk_output_delete']
            try:
                obj = TaskLocaleTranslationKit.objects.get(id=trans_kit_id)
                obj.output_file = ''
                obj.current_user = request.user.id
                obj.save()
                messages.add_message(request, messages.SUCCESS, u"Task Locale Translation Output file was deleted successfully")
            except:
                pass
            return redirect('projects_tasks_edit', self.object.id)

        # removing the locale translation support file_delete
        if 'tltk_support_delete' in request.POST:
            trans_kit_id = request.POST['tltk_support_delete']
            try:
                obj = TaskLocaleTranslationKit.objects.get(id=trans_kit_id)
                obj.support_file = ''
                obj.current_user = request.user.id
                obj.save()
                messages.add_message(request, messages.SUCCESS, u"Task Locale Translation Support file was deleted successfully")
            except:
                pass
            return redirect('projects_tasks_edit', self.object.id)

        if 'tla_delete_row' in request.POST:
            tla_id = request.POST['tla_delete_row']
            try:
                obj = TaskLocalizedAsset.objects.get(id=tla_id)
                obj.delete()
                messages.add_message(request, messages.SUCCESS, u"Task Localized Asset File was deleted successfully")
            except:
                pass
            return redirect('projects_tasks_edit', self.object.id)

        if 'manual_tl_asset_file' in request.POST:
            for source_file in self.object.project.kit.source_files():
                la, created = TaskLocalizedAsset.objects.get_or_create(
                    task=self.object,
                    name=source_file.orig_name
                )
                la.input_file = None
                la.output_file = None
                la.source_asset_id = source_file.id
                la.save()
            return redirect('projects_tasks_edit', self.object.id)

        if 'previous_task_complete' in request.POST:
            successful = False
            TaskLocalizedAsset.objects.filter(task=self.object).delete()
            if self.object.predecessor.is_translation():
                if self.object.predecessor.complete_if_ready():
                    successful = True
            elif self.object.predecessor.complete_if_all_tla_files_ready():
                successful = True

            if successful:
                messages.add_message(request, messages.SUCCESS, _("Executing Previous Task Completed..."))
            else:
                messages.add_message(request, messages.WARNING, _("Could not complete task {0}.  Are all files uploaded?").format(self.object))

            return redirect('projects_tasks_edit', self.object.id)

        form_class = self.get_form_class()
        form = self.get_form(form_class)

        if form.is_valid():
            self.object = form.save(commit=False)
            # todo need to make sure user doesnt change the service_type between nontranslation/translation tasks
            # data = form.cleaned_data
            # do stuff based on data and self.object!

            try:
                if any("qa_approved" == s for s in form.changed_data):
                    self.object.qa_lead = request.user

                po_number_orig = None
                if any("po_number" == s for s in form.changed_data):
                    try:
                        po_number_orig = self.object.po.po_number
                    except ObjectDoesNotExist:
                        pass

                    po_number = form.cleaned_data['po_number']

                    if not po_number == po_number_orig:
                        # todo link this to JAMS API to create real PO
                        VendorPurchaseOrder.objects.filter(task=self.object).exclude(vendor_id=self.object.assignee_object_id).delete()
                        po, created = VendorPurchaseOrder.objects.get_or_create(vendor_id=self.object.assignee_object_id, task=self.object)
                        if po:
                            po.po_number = po_number
                            po.save()
            except:
                import traceback
                tb = traceback.format_exc()  # NOQA
                print tb
                pass

            force_delete = False
            predecessor = request.POST.get('predecessor')
            current_task = self.get_object()
            # do not let the first task get removed if no other tasks exists.
            if not current_task.can_delete_task(force_delete, predecessor):
                messages.add_message(self.request, messages.ERROR, _('Cannot update Task Predecessor since there would be no initial task in the language workflow'))
                return redirect('projects_tasks_edit', self.object.id)

            # need to deal with create_po_needed
            if self.object.is_translation():
                self.object.quantity = None
                self.object.actual_hours = None
                self.object.create_po_needed = True
            else:
                if self.object.is_billable() and not self.object.project.delay_job_po:
                    self.object.actual_hours = None
                    self.object.create_po_needed = not self.object.project.delay_job_po
            #Checking whether the current sub-task due date is not greater than its parent due data
            if current_task.is_subtask() and current_task.due_date_check(request.POST.get('due_0')):
                messages.add_message(self.request, messages.ERROR, _("Current Sub-task due date is greater than its parent task"))
                return redirect('projects_tasks_edit', self.object.id)

            try:
                if not request.POST.get('parent-id') == "None":
                    self.object.parent_id = request.POST.get('parent-id')
                self.object.save()
            except:
                import traceback
                tb = traceback.format_exc()  # NOQA
                print tb
                pass

            if any("status" == s for s in form.changed_data):
                if self.object.is_active_status():
                    ctype = ContentType.objects.get_for_model(self.object)
                    obj_pk = self.object.id

                    try:
                        self.object.assigned_to.user_type
                        flag = False
                    except:
                        flag = True

                    if flag:
                        vendor_id = ''
                        if self.object.assigned_to:
                            vendor = CircusUser.objects.filter(account=self.object.assigned_to)
                            for v in vendor:
                                vendor_id = v.id
                    else:
                        vendor_id = self.object.assigned_to.id

                    comment_text = _('Task Active')

                    user = self.object.project.project_manager if self.object.project.project_manager else request.user
                    comments = Comment(object_pk=obj_pk, user=user, comment=comment_text, user_type=user.user_type, comment_to=vendor_id, ip_address=request.META.get("REMOTE_ADDR", None), via_comment_user_type=settings.VIA_USER_TYPE, content_type_id=ctype.id, site_id=settings.SITE_ID, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
                    comments.save()

                    comments = Comment(object_pk=obj_pk, user=request.user, comment=comment_text, user_type=request.user.user_type, comment_to=user.id, ip_address=request.META.get("REMOTE_ADDR", None), via_comment_user_type=settings.VIA_USER_TYPE, content_type_id=ctype.id, site_id=settings.SITE_ID, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
                    comments.save()

                if self.object.is_complete():
                    comment_text = _('Task Completed')
                    ctype = ContentType.objects.get_for_model(self.object)
                    obj_pk = self.object.id
                    user = self.object.project.project_manager if self.object.project.project_manager else request.user
                    if user:
                        comments = Comment(object_pk=obj_pk, user=request.user, comment=comment_text, user_type=request.user.user_type, comment_to=user, ip_address=request.META.get("REMOTE_ADDR", None), via_comment_user_type=settings.VIA_USER_TYPE, content_type_id=ctype.id, site_id=settings.SITE_ID, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
                    comments.save()

            if any("assignee" == s for s in form.changed_data):
                self.object.set_assigned_to(self.object.assigned_to)
                if self.object.assigned_to:
                    ctype = ContentType.objects.get_for_model(self.object)
                    obj_pk = self.object.id
                    try:
                        self.object.assigned_to.user_type
                        flag = False
                    except:
                        flag = True
                    if flag:
                        vendor = CircusUser.objects.filter(account=self.object.assigned_to)
                        vendor_id = ''
                        for v in vendor:
                            vendor_id = v.id
                    else:
                        vendor_id = self.object.assigned_to.id

                    comment_text = _('Task Assigned')
                    user = self.object.project.project_manager if self.object.project.project_manager else request.user
                    comments = Comment(object_pk=obj_pk, user=user, comment=comment_text, user_type=user.user_type, comment_to=vendor_id, ip_address=request.META.get("REMOTE_ADDR", None), via_comment_user_type=settings.VIA_USER_TYPE, content_type_id=ctype.id, site_id=settings.SITE_ID, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
                    comments.save()

                    if self.object.assigned_to and self.object.is_active_status():
                        # send notification if active
                        notify_assigned_to_task_assigned(self.object)
                else:
                    if not self.object.is_translation():
                        rate = None
                        self.object.nontranslationtask.assigned_to = self.object.assigned_to
                        self.object.nontranslationtask.save()
                        self.object.nontranslationtask.set_from_vendor_rate(rate)

            changed_list = ["assignee", "quantity", "unit_cost", "unit_price", "standard_days", "express_days"]
            changed_list_tat = ["standard_days", "express_days"]

            if any(map(lambda each: each in form.changed_data, changed_list)):
                # reset vendor costs / rates
                if "assignee" in form.changed_data:
                    set_rate(self.object)

                custom_tat = False
                if any(map(lambda each: each in form.changed_data, changed_list_tat)):
                    custom_tat = True

                if self.object.project.is_inestimate_status():
                    self.object.project.quote_summary_recalculate(self.object, custom_tat)

            code = messages.SUCCESS
            reschedule_all_due_dates = None
            if any(map(lambda each: each in form.changed_data, ["scheduled_start_timestamp", "due"])):
                if "due" in form.changed_data:
                    date_changed = "Due"
                else:
                    date_changed = "Scheduled_start"
                reschedule_all_due_dates = request.POST.get('reschedule_all_due_dates')
                if reschedule_all_due_dates:
                    if self.object.due and self.object.project.due and self.object.due > self.object.project.due:
                        messages.add_message(self.request, messages.ERROR, _('Current Task Due Date should not be more than Project Due Date'))
                        return self.form_invalid(form)

                    self.object.save()

                    success, message = self.object.project.reschedule_due_dates(self.request.user, self.object, date_changed)
                    if success == messages.ERROR:
                        messages.add_message(self.request, messages.ERROR, _('Latest Tasks Workflow Due Date more than Project Due Date'))

                    self.object.project.is_due_date_changed(self.object.project_id, date_changed)

                    ctype = ContentType.objects.get_for_model(self.object)
                    obj_pk = self.object.id

                    try:
                        self.object.assigned_to.user_type
                        flag = False
                    except:
                        flag = True

                    if flag:
                        vendor = CircusUser.objects.filter(account=self.object.assigned_to)
                        vendor_id = ''
                        for v in vendor:
                            vendor_id = v.id
                    else:
                        vendor_id = self.object.assigned_to.id

                    comment_text = _('Rescheduled due date')
                    user = self.object.project.project_manager if self.object.project.project_manager else request.user
                    comments = Comment(object_pk=obj_pk, user=user, comment=comment_text, user_type=user.user_type, comment_to=vendor_id, ip_address=request.META.get("REMOTE_ADDR", None), via_comment_user_type=settings.VIA_USER_TYPE, content_type_id=ctype.id, site_id=settings.SITE_ID, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
                    comments.save()

                else:
                    self.object.save()

            # resend notification if dates changed
            resend_notification = request.POST.get('resend_notification')
            if resend_notification:
                notify_due_dates_changed(self.object)
                ctype = ContentType.objects.get_for_model(self.object)
                obj_pk = self.object.id
                try:
                    self.object.assigned_to.user_type
                    flag = False
                except:
                    flag = True
                if flag:
                    vendor = CircusUser.objects.filter(account=self.object.assigned_to)
                    vendor_id = ''
                    for v in vendor:
                        vendor_id = v.id
                else:
                    vendor_id = self.object.assigned_to.id

                comment_text = _('Rescheduled due date')
                user = self.object.project.project_manager if self.object.project.project_manager else request.user
                comments = Comment(object_pk=obj_pk, user=user, comment=comment_text, user_type=user.user_type, comment_to=vendor_id, ip_address=request.META.get("REMOTE_ADDR", None), via_comment_user_type=settings.VIA_USER_TYPE, content_type_id=ctype.id, site_id=settings.SITE_ID, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
                comments.save()

            _message_text = ''
            if reschedule_all_due_dates:
                _message_text += _(' Dates Rescheduled.')
            if resend_notification:
                _message_text += _(' Notification Resent.')

            if code == messages.SUCCESS:
                messages.add_message(self.request, messages.SUCCESS, _('Task updated!') + _message_text)
            elif code == messages.WARNING:
                messages.add_message(self.request, messages.WARNING, _('No Supplier Rates!'))
            else:
                messages.add_message(self.request, messages.ERROR, _('An error occurred during save!'))

            if 'save_and_close' in request.POST:
                if request.POST['save_and_close']:
                    if request.COOKIES.get('task_view'):
                        redirect_url = reverse('via_job_detail_tasks_view', kwargs={'pk': self.object.project.id, 'service_id': self.object.service.service_type.id})
                        return redirect(redirect_url)
                    else:
                        return HttpResponseRedirect(request.POST['save_and_close'])
                else:
                    if request.COOKIES.get('task_view'):
                        redirect_url = reverse('via_job_detail_tasks_view', kwargs={'pk': self.object.project.id, 'service_id': self.object.service.service_type.id})
                        return redirect(redirect_url)
                    else:
                        return HttpResponseRedirect(self.get_success_url())
            else:
                return redirect('projects_tasks_edit', self.object.id)
            
        else:
            messages.add_message(self.request, messages.ERROR, _('Task not updated!'))
            print form.errors
            return self.form_invalid(form)


def delete_task(request, pk):
    task = get_object_or_404(Task, id=pk)
    url_name = 'via_job_detail_estimate' if task.project.status in (CREATED_STATUS, QUOTED_STATUS) else 'via_job_detail_tasks'

    force_delete = True
    if not task.can_delete_task(force_delete):
        messages.add_message(request, messages.ERROR, _('Cannot delete this task since this is the first root task in the language workflow'))
        return redirect(url_name, task.project.id)

    if task.delete_task():
        messages.add_message(request, messages.SUCCESS, u"{0} task was deleted".format(task.service.service_type))
    else:
        messages.add_message(request, messages.ERROR, u"{0} task was not able to be deleted".format(task.service.service_type))

    return redirect(url_name, task.project.id)


def copy_to_tla_output_file(request, pk, tla_id):
    tla = get_object_or_404(TaskLocalizedAsset, id=tla_id)
    if tla:
        original_name = tla.input_file
        from_key = settings.MEDIA_URL[1:] + unicode(original_name)
        to_filename = get_task_output_asset_path(tla, unicode(original_name).split('/')[-1])
        to_key = settings.MEDIA_URL[1:] + to_filename
        copy_file_asset(from_key, to_key)
        tla.output_file = to_filename
        tla.save()
    return redirect('projects_tasks_edit', pk)


def supplier_reference_redirect(request, task_id):
    """Called by S3 when an upload is finished for a target-specific supplier reference"""

    task = Task.objects.get(id=int(task_id))

    s3_key, filename = set_filefield_from_s3_redirect(request, task, 'reference_file')
    task.current_user = request.user.id
    task.save()

    msg = _("Supplier Reference File Uploaded: %s" % (filename,))
    messages.add_message(request, messages.SUCCESS, msg)
    return redirect('projects_tasks_edit', task_id)
