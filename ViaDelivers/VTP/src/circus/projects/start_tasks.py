from __future__ import unicode_literals

import logging
from datetime import timedelta
from functools import partial

from celery import shared_task
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import mail_admins
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from localization_kits.engine import import_translation, generate_delivery_files, generate_task_files_manual, \
    generate_delivery_files_v2, import_translation_v2
from notifications.notifications import notify_pm_task_ready, notify_pm_on_task, notify_assigned_to_task_ready
from projects.duedates import get_due_date
from projects.states import TASK_ACTIVE_STATUS
from services.managers import POST_PROCESS_SERVICE_TYPE, DTP_SERVICE_TYPE, THIRD_PARTY_REVIEW_SERVICE_TYPE, \
    FINAL_APPROVAL_SERVICE_TYPE, IMAGE_LOCALIZATION_SERVICE_TYPE, ACCESSIBILITY_SERVICE_TYPE, \
    CLIENT_REVIEW_SERVICE_TYPE, ATTORNEY_REVIEW_SERVICE_TYPE, ATTESTATION_SERVICE_TYPE, NOTARIZATION_SERVICE_TYPE, \
    PROOFREADING_SERVICE_TYPE, LINGUISTIC_TASK_SERVICE_TYPE, PROOFREADING_THIRD_PARTY_REVIEW_SERVICE_TYPE, \
    LINGUISTIC_QA_SERVICE_TYPE, CLIENT_REVIEW_FINAL_PRODUCT_SERVICE_TYPE, CLIENT_REVIEW_BILINGUAL_FORMAT_SERVICE_TYPE, \
    RECREATE_SOURCE_FROM_PDF_SERVICE_TYPE, FILE_PREP_SERVICE_TYPE, LINGUISTIC_SIGN_OFF_SERVICE_TYPE, \
    MT_POST_EDIT_SERVICE_TYPE, DTP_EDITS_SERVICE_TYPE, L10N_ENGINEERING_SERVICE_TYPE

logger = logging.getLogger('circus.' + __name__)


def set_task_dates(task, start, ignore_holiday_flag=False, is_hourly_schedule=False, duedate=None):
    """Set the due date for this task and its children.

    :type task: tasks.models.Task
    :type start: datetime.datetime
    :return: The due date of this task or its latest child.
    :rtype : datetime.datetime
    """
    if start:
        via_tz = timezone.get_default_timezone()
        start = start.astimezone(via_tz)
        task.scheduled_start_timestamp = start
        if duedate:
            task.due = duedate
        elif task.is_subtask() and task.service.service_type.code == PROOFREADING_SERVICE_TYPE:
            task.due = task.parent.due
        else:
            task.due = get_due_date(start, timedelta(minutes=round(24*60*task.duration())), ignore_holiday_flag, is_hourly_schedule)
        task.save()
        return max([set_task_dates(child, task.due, ignore_holiday_flag, is_hourly_schedule) for child in task.children.all()] + [task.due])
    return None


def activate_translation_task(task):
    # input files have already copied by activate project (start_project) by the time this is called
    # done all at once for efficiency, rather than task by task
    # also, we don't notify here because presumably translation is the first step
    try:
        _activate_and_notify(task, True)
    except:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        mail_admins('Failed to activate translation task', 'Job = {0}, task id = {1}.'.format(task.project, task.id))


def _report_failure(task_id, fail_message):
    from tasks.models import NonTranslationTask
    task = NonTranslationTask.objects.get(id=task_id)
    task_type = task.service.service_type.code
    mail_admins(
        'Job {0}, Failed to activate {1} task'.format(task.project, task_type),
        'Job = {0}, task id = {1}, {2}. ({3})'.format(task.project, task.id, task,
                                                      fail_message))

    notify_pm_on_task(
        task,
        u"VTP failed to activate this task without any issues. "
        u"This generally means the previous task was marked complete but VTP could not automatically process the files provided. "
        u"Manual intervention is required before the assignee will be able to work on it")


@shared_task
def _generate_files_from_translation(tltk_id, to_task_id, callback=None):
    from tasks.models import Task, TaskLocaleTranslationKit
    tltk = TaskLocaleTranslationKit.objects.get(id=tltk_id)
    try:
        import_translation(tltk)
        generate_delivery_files(tltk, to_task_id)
       
    except Exception, err:
        # celery will mail us about the exception, but having a message with the
        # project and task ID prominently featured sounds helpful too. Chained
        # exceptions would be nice here.
        _report_failure(to_task_id, str(err))
        # fall back to what we would have done for a manual job
        generate_task_files_manual(tltk, Task.objects.get(id=to_task_id))
        raise

    if callback:
        callback()


def _generate_files_from_translation_v2(tltk, task, generate_callback):
    from projects.models import BackgroundTask

    # From the outside this is one action, but "import" and "generate files"
    # are two distinct asynchronous calls. So we end up passing a callback to
    # a callback. :-/

    import_callback = _generate_after_import.si(tltk.id, task.id, generate_callback)
    import_callback['tlang'] = tltk.task.translationtask.service.target.description
    
    return BackgroundTask.objects.start_with_callback(
        BackgroundTask.IMPORT_TRANSLATION,
        task.project,
        partial(import_translation_v2, tltk),
        import_callback,
        _generate_failed.s(tltk.id, task.id)
    )


@shared_task
def _generate_failed(bg_task, tltk_id, to_task_id, error=None):
    from tasks.models import Task, TaskLocaleTranslationKit
    if error is not None:
        error_msg = unicode(error)
    else:
        error_msg = u''

    tltk = TaskLocaleTranslationKit.objects.get(id=tltk_id)
    task = Task.objects.get(id=to_task_id)
    # Activate task for VIA users so it shows up on their Task list
    if task.assigned_to and task.assigned_to.is_via():
        _activate_task(task)
    generate_task_files_manual(tltk, task)
    _report_failure(to_task_id, error_msg)


@shared_task
def _generate_after_import(tltk_id, to_task_id, generate_callback):
    from projects.models import BackgroundTask
    from tasks.models import Task, TaskLocaleTranslationKit
    to_task = Task.objects.get(id=to_task_id)
    tltk = TaskLocaleTranslationKit.objects.get(id=tltk_id)
    return BackgroundTask.objects.start_with_callback(
        BackgroundTask.GENERATE_DELIVERY,
        to_task.project,
        partial(generate_delivery_files_v2, tltk),
        generate_callback,
        _generate_failed.s(tltk_id, to_task_id),
        to_task
    )


def _activate_task(task):
    task.status = TASK_ACTIVE_STATUS
    task.started_timestamp = timezone.now()
    task.completed_timestamp = None
    task.save()


def _activate_and_notify(task, notify_assigned_to=False, pm_message=None):
    _activate_task(task)
    if notify_assigned_to and task.assigned_to:
        notify_assigned_to_task_ready(task)

        from django_comments.models import Comment
        ctype = ContentType.objects.get_for_model(task)
        obj_pk = task.id
        from tasks.middleware import get_current_request
        from tasks.middleware import get_current_user

        g_request = get_current_request();
        g_user = get_current_user()

        comment_text = _('Task Active')
        if task.project.project_manager:
            comments = Comment(object_pk=obj_pk, user=g_user, comment=comment_text, user_type=g_user.user_type, comment_to=task.project.project_manager.id, ip_address=g_request.META.get("REMOTE_ADDR", None), via_comment_user_type=settings.VIA_USER_TYPE, content_type_id=ctype.id, site_id=settings.SITE_ID, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
            comments.save()

        from accounts.models import CircusUser
        try:
            task.assigned_to.user_type
            flag = False
        except:
            flag = True

        if flag:
            vendor = CircusUser.objects.filter(account=task.assigned_to)
            vendor_id = ''
            for v in vendor:
                vendor_id = v.id
        else:
            vendor_id = task.assigned_to.id

        comments = Comment(object_pk=obj_pk, user=g_user, comment=comment_text, user_type=g_user.user_type, comment_to=vendor_id, ip_address=g_request.META.get("REMOTE_ADDR", None), via_comment_user_type=settings.VIA_USER_TYPE, content_type_id=ctype.id, site_id=settings.SITE_ID, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION)
        comments.save()

    else:
        if pm_message:
            notify_pm_on_task(task, pm_message)
        else:
            notify_pm_task_ready(task)


@shared_task
def _activate_and_notify_by_id(task_id, notify_assigned_to=False, pm_message=None):
    from tasks.models import Task
    task = Task.objects.get(id=task_id)
    return _activate_and_notify(task, notify_assigned_to, pm_message)


def activate_non_translation_task(task, task_type, notify_assigned_to=False, copy_to_output=False):
    from projects.models import BackgroundTask

    pm_message = ''
    if not task.predecessor_id:
        # already copy source files for first task
        success = True
    elif task.predecessor and task.predecessor.is_translation() and task.parent:
        success = task.copy_locale_translation_kit_from_predecessor(copy_to_output)
    elif task.predecessor and task.predecessor.is_translation():
        tltk = task.predecessor.trans_kit
        if tltk.can_dvx_import():
            # This involves a few external calls so we queue it.
            callback = _activate_and_notify_by_id.si(task.id, notify_assigned_to, pm_message)
            if settings.VIA_DVX_API_VERSION == 1:
                return BackgroundTask.objects.start(
                    BackgroundTask.GENERATE_DELIVERY,
                    task.project,
                    _generate_files_from_translation.si(tltk.id, task.id, callback=callback))
            elif settings.VIA_DVX_API_VERSION == 2:
                return _generate_files_from_translation_v2(tltk, task, callback)
            else:
                raise ImproperlyConfigured("Bad VIA_DVX_API_VERSION %r" % (settings.VIA_DVX_API_VERSION,))
        else:
            # Otherwise we will need some manual intervention here.
            success = generate_task_files_manual(tltk, task)
            pm_message = 'Manual Estimate: Job {0}, Task {1}, could not generate delivery files trans kit with id={2}.  Please work on manually.'.format(task.project, task_type, tltk.id)
    else:
        success = task.copy_localized_assets_from_predecessor(copy_to_output)

    if success:
        _activate_and_notify(task, notify_assigned_to, pm_message)


def activate_post_process_task(task):
    return activate_non_translation_task(task, POST_PROCESS_SERVICE_TYPE, True, False)


def activate_dtp_task(task):
    return activate_non_translation_task(task, DTP_SERVICE_TYPE, True, False)


def activate_third_party_review_task(task):
    return activate_non_translation_task(task, THIRD_PARTY_REVIEW_SERVICE_TYPE, True, False)


def activate_proof_third_party_review_task(task):
    return activate_non_translation_task(task, PROOFREADING_THIRD_PARTY_REVIEW_SERVICE_TYPE, True, False)


def activate_final_approval_task(task):
    if not task.assigned_to:
        task.assigned_to = task.project.project_manager
        task.save()
    return activate_non_translation_task(task, FINAL_APPROVAL_SERVICE_TYPE, True, True)


def activate_image_localization_task(task):
    return activate_non_translation_task(task, IMAGE_LOCALIZATION_SERVICE_TYPE, False, False)


def activate_accessibility_task(task):
    return activate_non_translation_task(task, ACCESSIBILITY_SERVICE_TYPE, False, False)


def activate_notarization_task(task):
    return activate_non_translation_task(task, NOTARIZATION_SERVICE_TYPE, False, False)


def activate_attestation_task(task):
    return activate_non_translation_task(task, ATTESTATION_SERVICE_TYPE, False, False)


def activate_attorney_review_task(task):
    return activate_non_translation_task(task, ATTORNEY_REVIEW_SERVICE_TYPE, False, False)


def activate_client_review_task(task):
    return activate_non_translation_task(task, CLIENT_REVIEW_SERVICE_TYPE, False, False)


def activate_linguistic_task_task(task):
    return activate_non_translation_task(task, LINGUISTIC_TASK_SERVICE_TYPE, True, False)


def activate_proof_task(task):
    return activate_non_translation_task(task, PROOFREADING_SERVICE_TYPE, True, False)


def activate_linguistic_qa_task(task):
    return activate_non_translation_task(task, LINGUISTIC_QA_SERVICE_TYPE, True, False)


def activate_l10n_engineering_task(task):
    return activate_non_translation_task(task, L10N_ENGINEERING_SERVICE_TYPE, True, False)


def activate_dtp_edits_task(task):
    return activate_non_translation_task(task, DTP_EDITS_SERVICE_TYPE, True, False)


def activate_mt_pe_task(task):
    return activate_non_translation_task(task, MT_POST_EDIT_SERVICE_TYPE, True, False)


def activate_lso_task(task):
    return activate_non_translation_task(task, LINGUISTIC_SIGN_OFF_SERVICE_TYPE, True, False)


def activate_file_prep_task(task):
    return activate_non_translation_task(task, FILE_PREP_SERVICE_TYPE, True, False)


def activate_recreate_of_pdf_task(task):
    return activate_non_translation_task(task, RECREATE_SOURCE_FROM_PDF_SERVICE_TYPE, True, False)


def activate_client_review_bilingual_format_task(task):
    return activate_non_translation_task(task, CLIENT_REVIEW_BILINGUAL_FORMAT_SERVICE_TYPE, True, False)


def activate_client_review_final_product_task(task):
    return activate_non_translation_task(task, CLIENT_REVIEW_FINAL_PRODUCT_SERVICE_TYPE, True, False)
