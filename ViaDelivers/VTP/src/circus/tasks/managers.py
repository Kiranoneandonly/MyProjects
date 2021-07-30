import datetime
from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from localization_kits.models import FileAnalysis
from people.models import Account
from matches.models import ANALYSIS_FIELD_NAMES
from projects.models import Project
from projects.states import (STARTED_STATUS, CANCELED_STATUS, QUEUED_STATUS,
                             CREATED_STATUS, COMPLETED_STATUS, QUOTED_STATUS,
                             TASK_CREATED_STATUS, TASK_ACTIVE_STATUS, TASK_COMPLETED_STATUS, TASK_CANCELED_STATUS)
from services.managers import FINAL_APPROVAL_SERVICE_TYPE, POST_PROCESS_SERVICE_TYPE
from shared.managers import manager_with_queryset_methods, CircusManager, GetOrNoneMixin
from shared.utils import get_first_day, get_last_day


class TaskManagerMixin(object):

    def task_select_prefetch_related(self):
        return self.select_related().prefetch_related('project', 'service', 'assigned_to')

    def created_active(self):
        return self.task_select_prefetch_related().filter(status__in=(TASK_CREATED_STATUS, TASK_ACTIVE_STATUS)).order_by('due', 'project')

    def pending_acceptance(self):
        return self.task_select_prefetch_related().filter(status__in=(TASK_CREATED_STATUS, TASK_ACTIVE_STATUS), accepted_timestamp__isnull=True).order_by('due', 'project')

    def billable_pending_acceptance(self):
        return self.task_select_prefetch_related().pending_acceptance().filter(billable=True).order_by('due', 'project')

    def rejected(self):
        return self.task_select_prefetch_related().filter(project__status=STARTED_STATUS, assignee_object_id__isnull=True).order_by('due', 'project')

    def pending_completion(self):
        return self.task_select_prefetch_related().filter(status=TASK_ACTIVE_STATUS, assignee_object_id__isnull=False).order_by('due', 'project')

    def billable_pending_completion(self):
        return self.task_select_prefetch_related().pending_completion().filter(billable=True).order_by('due', 'project')

    def manual_quote(self):
        return self.task_select_prefetch_related().filter(project__status=CREATED_STATUS, assignee_object_id__isnull=True).order_by('due', 'project')

    def pending_final_approval(self):
        return self.task_select_prefetch_related().filter(project__status=STARTED_STATUS,
                                                          service__service_type__code=FINAL_APPROVAL_SERVICE_TYPE,
                                                          status=TASK_ACTIVE_STATUS)\
            .order_by('due')

    def overdue(self):
        return self.task_select_prefetch_related().created_active().filter(project__status=STARTED_STATUS, due__lt=timezone.now()).order_by('due', 'project')

    def get_vendor_tasks(self, vendor):
        active_projects_list = [p.id for p in Project.objects.select_related().filter(status__in=(STARTED_STATUS, COMPLETED_STATUS)) if not p.show_start_workflow()]
        return self.task_select_prefetch_related().filter(
            assignee_content_type=ContentType.objects.get_for_model(Account),
            assignee_object_id=vendor.id,
            project__id__in=active_projects_list,
            service__service_type__workflow=True,
        ).order_by('due', 'project')

    def get_user_tasks(self, user):
        """Tasks assigned to this user, or this user's account.

        :type user: CircusUser
        """
        account = user.account
        assigned_to_account = Q(
            assignee_content_type=ContentType.objects.get_for_model(account),
            assignee_object_id=account.id)
        assigned_to_user = Q(
            assignee_content_type=ContentType.objects.get_for_model(user),
            assignee_object_id=user.id)
        return self.task_select_prefetch_related().filter(assigned_to_account | assigned_to_user).order_by('due', 'project')

    def get_active_jobs_workflow_tasks(self):
        active_projects_list = [p.id for p in Project.objects.select_related().filter(status__in=(STARTED_STATUS, COMPLETED_STATUS)) if not p.show_start_workflow()]
        return self.task_select_prefetch_related().filter(project__id__in=active_projects_list, service__service_type__workflow=True).order_by('due', 'project')

    def get_pending_tasks(self):
        return self.task_select_prefetch_related().pending_acceptance().order_by('due', 'project')

    def get_post_process_tasks(self):
        return self.task_select_prefetch_related().filter(service__service_type__code=POST_PROCESS_SERVICE_TYPE, status=TASK_ACTIVE_STATUS)

    def get_active_tasks(self):
        return self.task_select_prefetch_related().filter(accepted_timestamp__isnull=False, status=TASK_ACTIVE_STATUS).order_by('due', 'project')

    def get_upcoming_tasks(self):
        return self.task_select_prefetch_related().filter(accepted_timestamp__isnull=False, status=TASK_CREATED_STATUS).order_by('due', 'project')

    def get_unapproved_po_tasks(self):
        return self.task_select_prefetch_related().filter(create_po_needed=False)

    def get_complete_tasks_within_history_date_range(self):
        now = datetime.datetime.now()
        then = now - datetime.timedelta(days=settings.HISTORY_DATE_RANGE_MONTH)
        base_first_day_month = get_first_day(then)
        base_last_day_month = get_last_day(now)
        return self.task_select_prefetch_related().filter(status=TASK_COMPLETED_STATUS, completed_timestamp__range=[base_first_day_month, base_last_day_month]).order_by('-due', 'project')

    def get_complete_tasks(self):
        return self.task_select_prefetch_related().filter(status=TASK_COMPLETED_STATUS).order_by('-due', 'project')

    def get_overdue_tasks(self):
        return self.task_select_prefetch_related().overdue().order_by('due', 'project')

    def get_unrated_tasks(self):
        return self.task_select_prefetch_related().get_complete_tasks().filter(Q(billable=True) & (Q(rating=0) | Q(rating__isnull=True))).order_by('-due', 'project')
    
    def get_final_approval_tasks(self):
        return self.task_select_prefetch_related().pending_final_approval().order_by('due', 'project')
   
    def get_unassigned_tasks(self):
        return self.task_select_prefetch_related().filter(assignee_object_id=None, status__in=(TASK_CREATED_STATUS, TASK_ACTIVE_STATUS)).order_by('due', 'project')

    def select_for_pricing(self, *also_related):
        """Include the related models necessary for price calculation."""
        related_fields = [
            "translationtask__analysis",
            "translationtask__client_price",
            "service__target",
            "nontranslationtask",
            "project__kit"
        ]
        # You can't chain select_related calls before django 1.7
        #   https://code.djangoproject.com/ticket/16855
        # so allow passing in more select_related fields here.
        if also_related:
            related_fields.extend(also_related)
        return self.task_select_prefetch_related().select_related(*related_fields)


TaskManager = manager_with_queryset_methods(TaskManagerMixin)


class TranslationTaskAnalysisManager(CircusManager):
    def create_from_kit(self, kit, target):
        source = kit.project.source_locale
        obj, created = self.get_or_create(source_of_analysis=kit.id, source=source, target=target)
        obj.clear_counts()
        for asset in kit.source_files():
            try:
                file_analysis = asset.analysis_for_target(target)
            except FileAnalysis.DoesNotExist:
                file_analysis = FileAnalysis.objects.create(asset=asset, source_locale=source, target_locale=target)
            else:
                for field in ANALYSIS_FIELD_NAMES:
                    setattr(obj, field, getattr(obj, field, 0) + getattr(file_analysis, field))
        obj.save()
        return obj


class TaskQuoteManager(CircusManager):
    pass


class TaskAssetQuoteManager(CircusManager):
    pass
