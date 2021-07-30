from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.db.models.signals import post_save
from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType
from activity_log.models import Actions
from accounts.models import CircusUser
from projects.models import Project
from people.models import Account
from projects.states import get_reversed_status
from tasks.models import TaskLocaleTranslationKit, TaskLocalizedAsset, VendorPurchaseOrder
from tasks.models import Task
from datetime import timedelta
from django.utils import timezone

import logging

logger = logging.getLogger('circus.' + __name__)


def get_actor_name(assignee_content_id, assignee_id):
    actor_name = ''
    get_model = ContentType.objects.get(pk=assignee_content_id)
    model_name = get_model.model
    if model_name == 'circususer':
        user = CircusUser.objects.get(id=assignee_id)
        actor_name = user.get_full_name()
    elif model_name == 'account':
        user = Account.objects.get(id=assignee_id)
        actor_name = user.name

    return actor_name


def get_last_record(instance_id):
    last_job_record = None
    action_obj = Actions.objects.filter(action_object_id=instance_id)
    if action_obj:
        last_job_record = action_obj.order_by("-pk")[0]

    return last_job_record


# def get_last_record_approvals(instance_id):
#     last_job_record = None
#     action_obj = Actions.objects.filter(action_object_id=instance_id, description='largejobs')
#     if action_obj:
#         last_job_record = action_obj.order_by("-pk")[0]
#
#     return last_job_record


def get_current_user(user_id):
    user_name = ''
    if user_id:
        user = CircusUser.objects.get(pk=user_id)
        user_name = user.get_full_name()

    return user_name


def large_jobs_active_log_check(instance):
    verb = _('Saved')
    approver = _('No Approvers Set')

    approvers = [instance.project_manager_approver_id, instance.ops_management_approver_id, instance.sales_management_approver_id]

    if any(approvers):
        pm = CircusUser.objects.get_or_none(id=approvers[0] or 0)
        om = CircusUser.objects.get_or_none(id=approvers[1] or 0)
        sm = CircusUser.objects.get_or_none(id=approvers[2] or 0)
        approver = _('PM: %s, OM: %s, SM: %s') % (pm, om, sm)

    return verb, approver


def large_job_approvals_activity_log(instance, current_user, job_price, normal_status, **kwargs):
    try:
        approver = ''
        activity_log = None

        verb, approver = large_jobs_active_log_check(instance)

        time_threshold = timezone.now() - timedelta(minutes=1)

        activity_log = Actions.objects.filter(
            Q(timestamp__gt=time_threshold) &
            Q(action_content_type=ContentType.objects.get_for_model(Project)) &
            Q(action_object_id=instance.id) &
            Q(action_object_name=instance.job_number) &
            Q(verb=verb) &
            Q(actor=current_user) &
            Q(job_id=instance.id) &
            Q(description='largejobs') &
            Q(task_price=job_price) &
            Q(status=normal_status) &
            Q(data=approver)
        ).latest('timestamp')

        # do nothing as we already logged this Action to the activity log
        return True

    except ObjectDoesNotExist:

        if instance and current_user and approver:
            activity_log = Actions.objects.create(
                action_content_type=ContentType.objects.get_for_model(Project),
                action_object_id=instance.id,
                action_object_name=instance.job_number,
                verb=verb,
                actor=current_user,
                job_id=instance.id,
                description='largejobs',
                task_price=job_price,
                status=normal_status,
                data=approver,
                project_manager_approver=instance.project_manager_approver_id if instance.project_manager_approver_id else 0,
                ops_management_approver=instance.ops_management_approver_id if instance.ops_management_approver_id else 0,
                sales_management_approver=instance.sales_management_approver_id if instance.sales_management_approver_id else 0,
            )

            if activity_log:
                return True
            else:
                return False

    except Exception, error:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        logger.error("large_job_approvals_activity_log error", exc_info=True)
        return False


def project_status_activity_log(sender, instance, created, **kwargs):
    try:
        current_user = ''
        normal_status = ''
        approvals_save = ''
        current_user = get_current_user(instance.current_user)
        normal_status = get_reversed_status(instance.status).title()
        job_price = instance.price()
        time_threshold = timezone.now() - timedelta(minutes=1)

        if job_price >= settings.LARGE_JOB_PRICE:
            approvals_save = large_job_approvals_activity_log(instance, current_user, job_price, normal_status)

        activity_log = Actions.objects.filter(
            Q(timestamp__gt=time_threshold) &
            Q(action_content_type=ContentType.objects.get_for_model(Project)) &
            Q(action_object_id=instance.id) &
            Q(action_object_name=instance.job_number) &
            Q(verb=instance.status) &
            Q(actor=current_user) &
            Q(job_id=instance.id) &
            Q(task_price=job_price) &
            Q(status=normal_status) &
            Q(user=instance.client.name)
        ).latest('timestamp')

        # do nothing as we already logged this Action to the activity log
        return True

    except ObjectDoesNotExist:

        if instance and current_user:
            activity_log = Actions.objects.create(
                action_content_type=ContentType.objects.get_for_model(Project),
                action_object_id=instance.id,
                action_object_name=instance.job_number,
                verb=instance.status,
                actor=current_user,
                job_id=instance.id,
                task_price=job_price,
                status=normal_status,
                user=instance.client.name)

            if activity_log:
                return True
            else:
                return False

    except Exception, error:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        logger.error("project_status_activity_log error", exc_info=True)
        return False


def task_supplier_reference_file_activity_log_verb(instance, last_job_record):
    verb = ''
    file_type = ''

    if instance.reference_file:
        file_type = _('Reference')
        if last_job_record:
            if last_job_record.supplier_reference_file:
                if not last_job_record.supplier_reference_file == instance.supplier_reference_file_name():
                    verb = _('Replaced')
            else:
                verb = _('Uploaded')

    elif not instance.reference_file:
        if last_job_record:
            if last_job_record.supplier_reference_file:
                verb = _('Deleted')
                file_type = _('Reference')

    return verb, file_type


def task_status_active_log(sender, instance, created, **kwargs):
    try:
        actor_name = ''
        task_verb = ''
        verb = ''
        file_type = ''

        last_job_record = get_last_record(instance.id)

        verb, file_type = task_supplier_reference_file_activity_log_verb(instance, last_job_record)

        if verb:
            task_verb = verb
            file_type = _('Reference')
        else:
            task_verb = instance.status
            file_type = ''

        if last_job_record:
            actor_name = last_job_record.actor

        if instance.assignee_content_type_id:
            actor_name = get_actor_name(instance.assignee_content_type_id, instance.assignee_object_id)

        user = instance.project.current_user if instance.current_user == 0 or instance.current_user is None else instance.current_user
        current_user = get_current_user(user)
        net_price = 0

        if instance and current_user:
            if instance.is_translation():
                task_price = instance.itemized_price_details()
                for task_rate in task_price:
                    net_price = task_rate.net
                    if net_price:
                        Actions.objects.create(action_content_type=ContentType.objects.get_for_model(Task),
                                               action_object_id=instance.id,
                                               action_object_name=instance,
                                               verb=task_verb,
                                               actor=current_user,
                                               job_id=instance.project.id,
                                               task_id=instance.id,
                                               task_service_type= u'{0} {1} to {2}'.format(instance.service.service_type.description, instance.service.source.description, instance.service.target.description),
                                               user=actor_name,
                                               file_type=file_type,
                                               supplier_reference_file=instance.supplier_reference_file_name(),
                                               task_price=net_price,
                                               task_hours=(instance.quantity() if not instance.is_translation() else 0)
                                               )
    except Exception, error:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        logger.error("task_status_active_log error", exc_info=True)
        return False


def start_workflow_log(sender, instance, created, **kwargs):
    try:
        workflow_started = False
        task_set = instance.project.workflow_root_tasks()
        if instance in task_set:
            if instance.is_active_last_minute():
                workflow_started = True

        user = instance.project.current_user if instance.current_user == 0 or instance.current_user is None else instance.current_user
        current_user = get_current_user(user)
        normal_status = get_reversed_status(instance.project.status).title()

        if instance and current_user and workflow_started:
            Actions.objects.create(action_content_type=ContentType.objects.get_for_model(Task),
                                   action_object_id=instance.id,
                                   action_object_name=instance.project.job_number,
                                   actor=current_user,
                                   verb=_('workflow_started'),
                                   description='started_workflow',
                                   job_id=instance.project.id,
                                   task_id=instance.id,
                                   status=normal_status,
                                   task_service_type= u'{0} {1} to {2}'.format(instance.service.service_type.description, instance.service.source.description, instance.service.target.description),
                                   )
    except Exception, error:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        logger.error("start_workflow_log error", exc_info=True)
        return False


def task_upload_files_status_activity_log_verb(instance, last_job_record):
    verb = _('Uploaded')
    file_type = ''

    if instance.output_file_name() and not instance.support_file_name():
        file_type = _('Translation')
        if last_job_record:
            if last_job_record.support_file_name:
                file_type = _('Support')
                verb = _('Deleted')

            elif last_job_record.trans_file_name:
                verb = _('Replaced')

    elif instance.support_file_name() and not instance.output_file_name():
        file_type = _('Support')
        if last_job_record:
            if last_job_record.trans_file_name:
                file_type = _('Translation')
                verb = _('Deleted')

            elif last_job_record.support_file_name:
                verb = _('Replaced')

    elif instance.output_file_name() and instance.support_file_name():
        if last_job_record:
            if instance.output_file_name() == last_job_record.trans_file_name:
                file_type = _('Support')
                if last_job_record.support_file_name:
                    verb = _('Replaced')
                else:
                    verb = _('Uploaded')
            elif instance.support_file_name() == last_job_record.support_file_name:
                file_type = _('Translation')
                if last_job_record.trans_file_name:
                    verb = _('Replaced')
                else:
                    verb = _('Uploaded')

    elif not instance.output_file_name() and not instance.support_file_name():
        if last_job_record:
            if last_job_record.trans_file_name:
                file_type = _('Translation')
                verb = _('Deleted')
            elif last_job_record.support_file_name:
                file_type = _('Support')
                verb = _('Deleted')

    return verb, file_type


def task_upload_files_status_activity_log(sender, instance, created, **kwargs):
    try:
        actor_name = ''

        last_job_record = get_last_record(instance.id)

        if last_job_record:
            actor_name = last_job_record.actor

        if instance.task.assignee_content_type_id:
            actor_name = get_actor_name(instance.task.assignee_content_type_id, instance.task.assignee_object_id)

        user = instance.task.project.current_user if instance.current_user == 0 or instance.current_user is None else instance.current_user
        current_user = get_current_user(user)

        verb, file_type = task_upload_files_status_activity_log_verb(instance, last_job_record)

        if instance and current_user:
            Actions.objects.create(action_content_type=ContentType.objects.get_for_model(TaskLocaleTranslationKit),
                                   action_object_id=instance.id,
                                   action_object_name=instance.task,
                                   verb=verb,
                                   trans_file_name=instance.output_file_name(),
                                   support_file_name=instance.support_file_name(),
                                   file_type=file_type,
                                   actor=current_user,
                                   job_id=instance.task.project.id,
                                   task_id=instance.task.id,
                                   user=actor_name,
                                   data=instance.task
                                   )

    except Exception, error:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        logger.error("task_upload_files_status_activity_log error", exc_info=True)
        return False


def ntt_task_upload_files_status_activity_log_verb(instance, last_job_record):
    verb = _('Uploaded')
    file_type = ''

    if instance.input_file_name() and not instance.output_file_name() and not instance.support_file_name():
        file_type = _(instance.task.service.service_type.description + ' Input file')
        if last_job_record:
            if last_job_record.ntt_output_file_name:
                file_type = _(instance.task.service.service_type.description + ' Output file')
                verb = _('Deleted')
            elif last_job_record.ntt_support_file_name:
                file_type = _(instance.task.service.service_type.description + ' Support file')
                verb = _('Deleted')
            elif last_job_record.ntt_input_file_name:
                file_type = _(instance.task.service.service_type.description + ' Input file')
                verb = _('Replaced')

    elif instance.output_file_name() and not instance.input_file_name() and not instance.support_file_name():
        file_type = _(instance.task.service.service_type.description + ' Output file')
        if last_job_record:
            if last_job_record.ntt_input_file_name:
                file_type = _(instance.task.service.service_type.description + ' Input file')
                verb = _('Deleted')
            elif last_job_record.ntt_support_file_name:
                file_type = _(instance.task.service.service_type.description + ' Support file')
                verb = _('Deleted')
            elif last_job_record.ntt_output_file_name:
                file_type = _(instance.task.service.service_type.description + ' Output file')
                verb = _('Replaced')

    elif instance.support_file_name() and not instance.input_file_name() and not instance.output_file_name():
        file_type = _(instance.task.service.service_type.description + ' Support file')
        if last_job_record:
            if last_job_record.ntt_input_file_name:
                file_type = _(instance.task.service.service_type.description + ' Input file')
                verb = _('Deleted')
            elif last_job_record.ntt_output_file_name:
                file_type = _(instance.task.service.service_type.description + ' Output file')
                verb = _('Deleted')
            elif last_job_record.ntt_support_file_name:
                file_type = _(instance.task.service.service_type.description + ' Support file')
                verb = _('Replaced')

    #If any two files exist
    elif instance.input_file_name() and instance.output_file_name() and not instance.support_file_name():
        if last_job_record:
            if instance.output_file_name() == last_job_record.ntt_output_file_name and not instance.input_file_name() == last_job_record.ntt_input_file_name:
                file_type = _(instance.task.service.service_type.description + ' Input file')
                if last_job_record.ntt_input_file_name:
                    verb = _('Replaced')
            if not instance.output_file_name() == last_job_record.ntt_output_file_name and instance.input_file_name() == last_job_record.ntt_input_file_name:
                file_type = _(instance.task.service.service_type.description + ' Output file')
                if last_job_record.ntt_output_file_name:
                    verb = _('Replaced')
            elif last_job_record.ntt_support_file_name:
                file_type = _(instance.task.service.service_type.description + ' Support file')
                verb = _('Deleted')

    elif instance.input_file_name() and instance.support_file_name() and not instance.output_file_name():
        if last_job_record:
            if instance.support_file_name() == last_job_record.ntt_support_file_name and not instance.input_file_name() == last_job_record.ntt_input_file_name:
                file_type = _(instance.task.service.service_type.description + ' Input file')
                if last_job_record.ntt_input_file_name:
                    verb = _('Replaced')
            if not instance.support_file_name() == last_job_record.ntt_support_file_name and instance.input_file_name() == last_job_record.ntt_input_file_name:
                file_type = _(instance.task.service.service_type.description + ' Support file')
                if last_job_record.ntt_support_file_name:
                    verb = _('Replaced')
            elif last_job_record.ntt_output_file_name:
                file_type = _(instance.task.service.service_type.description + ' Output file')
                verb = _('Deleted')

    elif instance.output_file_name() and instance.support_file_name() and not instance.input_file_name():
        if last_job_record:
            if instance.support_file_name() == last_job_record.ntt_support_file_name and not instance.output_file_name() == last_job_record.ntt_output_file_name:
                file_type = _(instance.task.service.service_type.description + ' Output file')
                if last_job_record.ntt_output_file_name:
                    verb = _('Replaced')
            if not instance.support_file_name() == last_job_record.ntt_support_file_name and instance.output_file_name() == last_job_record.ntt_output_file_name:
                file_type = _(instance.task.service.service_type.description + ' Support file')
                if last_job_record.ntt_support_file_name:
                    verb = _('Replaced')
            elif last_job_record.ntt_input_file_name:
                file_type = _(instance.task.service.service_type.description + ' Input file')
                verb = _('Deleted')

    #If three files exist
    elif instance.output_file_name() and instance.input_file_name() and instance.support_file_name():
        if last_job_record:
            if instance.output_file_name() == last_job_record.ntt_output_file_name \
                    and instance.input_file_name() == last_job_record.ntt_input_file_name\
                    and not instance.support_file_name() == last_job_record.ntt_support_file_name:
                file_type = _(instance.task.service.service_type.description + ' Support file')
                if last_job_record.ntt_support_file_name:
                    verb = _('Replaced')

            elif instance.output_file_name() == last_job_record.ntt_output_file_name \
                    and instance.support_file_name() == last_job_record.ntt_support_file_name\
                    and not instance.input_file_name() == last_job_record.ntt_input_file_name:
                file_type = _(instance.task.service.service_type.description + ' Input file')
                if last_job_record.ntt_input_file_name:
                    verb = _('Replaced')

            elif instance.input_file_name() == last_job_record.ntt_input_file_name \
                    and instance.support_file_name() == last_job_record.ntt_support_file_name\
                    and not instance.output_file_name() == last_job_record.ntt_output_file_name:
                file_type = _(instance.task.service.service_type.description + ' Output file')
                if last_job_record.ntt_output_file_name:
                    verb = _('Replaced')

    elif not instance.output_file_name() and not instance.input_file_name() and not instance.support_file_name():
        if last_job_record:
            if last_job_record.ntt_output_file_name:
                file_type = _(instance.task.service.service_type.description + ' Output file')
                verb = _('Deleted')
            elif last_job_record.ntt_input_file_name:
                file_type = _(instance.task.service.service_type.description + ' Input file')
                verb = _('Deleted')
            elif last_job_record.ntt_support_file_name:
                file_type = _(instance.task.service.service_type.description + ' Support file')
                verb = _('Deleted')

    return verb, file_type


def ntt_task_upload_files_status_activity_log(sender, instance, created, **kwargs):
    try:
        actor_name = ''

        last_job_record = get_last_record(instance.id)

        if last_job_record:
            actor_name = last_job_record.actor

        if instance.task.assignee_content_type_id:
            actor_name = get_actor_name(instance.task.assignee_content_type_id, instance.task.assignee_object_id)

        user = instance.task.project.current_user if instance.current_user == 0 or instance.current_user is None else instance.current_user
        current_user = get_current_user(user)

        verb, file_type = ntt_task_upload_files_status_activity_log_verb(instance, last_job_record)

        task_service_type = instance.task.service.service_type.description

        if instance and current_user:
            Actions.objects.create(action_content_type=ContentType.objects.get_for_model(TaskLocalizedAsset),
                                   action_object_id=instance.id,
                                   action_object_name=instance.task,
                                   verb=verb,
                                   ntt_input_file_name=instance.input_file_name(),
                                   ntt_output_file_name=instance.output_file_name(),
                                   ntt_support_file_name=instance.support_file_name(),
                                   task_service_type=task_service_type,
                                   file_type=file_type,
                                   actor=current_user,
                                   job_id=instance.task.project.id,
                                   task_id=instance.task.id,
                                   user=actor_name,
                                   data=instance.task
                                   )

    except Exception, error:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        logger.error("ntt_task_upload_files_status_activity_log error", exc_info=True)
        return False


def po_creation_command_status_activity_log(sender, instance, created, **kwargs):

    try:
        actor_name = ''

        last_job_record = get_last_record(instance.id)

        if last_job_record:
            actor_name = last_job_record.actor

        if instance.task.assignee_content_type_id:
            actor_name = get_actor_name(instance.task.assignee_content_type_id, instance.task.assignee_object_id)

        user = instance.task.current_user if instance.task.current_user == 0 or instance.task.current_user is None else instance.task.current_user
        current_user = get_current_user(user)
        # verb, file_type = ntt_task_upload_files_status_activity_log_verb(instance, last_job_record)

        task_service_type = instance.task.service.service_type.description

        if instance and current_user:
            task_price = instance.task.itemized_cost_details()
            for task_rate in task_price:
                    cost = task_rate.net
            Actions.objects.create(action_content_type=ContentType.objects.get_for_model(VendorPurchaseOrder),
                                   action_object_id=instance.id,
                                   action_object_name=instance.task,
                                   verb="created",
                                   task_service_type=task_service_type,
                                   actor=instance.task.assigned_to,
                                   job_id=instance.task.project.id,
                                   task_id=instance.task.id,
                                   user=actor_name,
                                   data=instance.task,
                                   po_number=instance.po_number,
                                   po_cost=cost
                                   )

    except Exception, error:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        logger.error("po_creation_command_status_activity_log error", exc_info=True)
        return False

# connecting receiver function to the signal
post_save.connect(project_status_activity_log, sender=Project, dispatch_uid="projects.project.activity_log")
post_save.connect(task_status_active_log, sender=Task)
post_save.connect(start_workflow_log, sender=Task)
post_save.connect(task_upload_files_status_activity_log, sender=TaskLocaleTranslationKit)
post_save.connect(ntt_task_upload_files_status_activity_log, sender=TaskLocalizedAsset)
post_save.connect(po_creation_command_status_activity_log, sender=VendorPurchaseOrder)


