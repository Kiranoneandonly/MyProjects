import calendar
import json
import logging

from urlparse import urljoin

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.db.models import Q

from salesforce.backend.manager import SalesforceManager

from clients.models import Client
from shared.managers import manager_with_queryset_methods, get_overdue_projects_filter, \
    get_delivered_projects_filter, get_completed_projects_filter, GetOrNoneMixin, get_inestimate_projects_filter
from django.shortcuts import get_object_or_404
from accounts.models import CircusUser

logger = logging.getLogger('circus.' + __name__)


class ProjectManagerMixin(object):

    def project_select_prefetch_related(self):
        return self.select_related()

    def get_all_projects(self):
        return self.project_select_prefetch_related()

    def get_overdue_projects(self):
        return self.filter(*get_overdue_projects_filter())

    def get_inestimate_projects(self):
        return self.filter(*get_inestimate_projects_filter())

    def get_delivered_projects(self):
        return self.filter(*get_delivered_projects_filter())

    def get_completed_projects(self):
        return self.filter(*get_completed_projects_filter())

    def get_client_projects(self, user):
        client = get_object_or_404(Client, id=user.account.id)

        if client.manifest.enforce_customer_hierarchy:
            manager_user_ids = []
            managers_list = CircusUser.objects.filter(reports_to_id=user)
            for mgr in managers_list:
                manager_user_ids.append(mgr.id)

            if user.has_perm('projects.manager_can_view_teams_jobs') and user.has_perm('projects.view_child_company_jobs'):
                return self.filter(Q(client=user.account.cast(Client)) | Q(client_poc_id__in=manager_user_ids) | Q(client__in=user.account.children.all()))
            elif user.has_perm('projects.view_child_company_jobs'):
                return self.filter(Q(client=user.account.cast(Client)) | Q(client__in=user.account.children.all()))
            elif user.has_perm('projects.manager_can_view_teams_jobs'):
                return self.filter(Q(client=user.account.cast(Client)) | Q(client_poc_id__in=manager_user_ids))

        return self.filter(Q(client=user.account.cast(Client)))


ProjectManager = manager_with_queryset_methods(ProjectManagerMixin)


class BackgroundTimeout(Exception):
    pass


class ProjectServicesGlobalManager(models.Manager, GetOrNoneMixin):
    pass


class ProjectJobOptionsManager(models.Manager, GetOrNoneMixin):
    pass


class BackgroundTaskManager(models.Manager):

    def currently_adding_to_translation_memory(self, project):
        tasks = self.filter(project=project, name=self.model.MEMORY_DB_TM,
                            completed__isnull=True)
        return tasks.exists()

    def currently_pretranslating(self, project):
        tasks = self.filter(project=project, name=self.model.PRE_TRANSLATE,
                            completed__isnull=True)
        return tasks.exists()

    def currently_prepping(self, project):
        tasks = self.filter(project=project, name=self.model.PREP_KIT,
                            completed__isnull=True)
        return tasks.exists()

    def currently_analyzing(self, project):
        tasks = self.filter(project=project, name=self.model.ANALYSIS,
                            completed__isnull=True)
        return tasks.exists()

    def revoke_analysis(self, project):
        tasks = self.filter(project=project, name=self.model.ANALYSIS, completed__isnull=True)
        for task in tasks:
            task.revoke()

    def start(self, name, project, signature):
        result = signature.apply_async()
        bg_task = self.create(project=project, celery_task_id=result.task_id,
                              name=name)
        return result

    def start_with_callback(self, name, project, func, callback=None,
                            errback=None, task=None):
        """
        Create a new BackgroundTask which begins with calling the given
        function.

        The function is not queued, it is invoked immediately and is expected to
        return quickly.

        It's expected that some other action in the future (e.g. a request to
        a foo_complete API) will complete this BackgroundTask by calling
        .callback() or .errback() on it. At that point, the function described
        by `callback` or `errback` will be invoked.

        (This usage of BackgroundTask does not use Celery's task queue or
        workers, but it does use its Signature data structure as a way to store
        what the callback should be.)

        :param name: one of BackgroundTask.NAME_CHOICES
        :param projects.models.Project project: project this applies to
        :param callable func: This function will be invoked immediately with
            a `bg_task` keyword argument.
        :type callback: celery.canvas.Signature
        :type errback: celery.canvas.Signature
        :param tasks.models.Task task: task this applies to
        :rtype: projects.models.BackgroundTask
        """
        callback_str = json.dumps(callback) if (callback is not None) else None
        errback_str = json.dumps(errback) if (errback is not None) else None
        bg_task = self.create(project=project, name=name,
                              callback_sig=callback_str,
                              errback_sig=errback_str,
                              task=task)
        from activity_log.models import Actions

        action_object = Actions.objects.create(action_content_type=ContentType.objects.get_for_model(bg_task),
                                               action_object_id=bg_task.id,
                                               action_object_name=project.job_number,
                                               verb=name,
                                               description=name,
                                               job_id=project.id,)
        action_object.save()
        try:
            remote_id = func(bg_task=bg_task)
        except Exception, error:
            logger.error("Error invoking %r", func, exc_info=True)
            try:
                if errback:
                    errback(error)
            finally:
                bg_task.complete()
        else:
            if remote_id is not None:
                bg_task.remote_id = remote_id
                bg_task.save()

        return bg_task

    def reap_expired(self, timeout):
        """
        :param datetime.timedelta timeout: expiration age for non-completed tasks
        """
        cutoff = timezone.now() - timeout
        count = 0
        for bg_task in self.filter(completed=None, created__lt=cutoff):
            duration = timezone.now() - bg_task.created
            logger.info("Expiring %r after %s", bg_task, duration)
            try:
                bg_task.errback(BackgroundTimeout(duration))
            finally:
                bg_task.complete()
                bg_task.save()
            count += 1
        return count


def last_day_of_month():
    date = timezone.now().date()
    days = calendar.monthrange(date.year, date.month)[1]
    date = date.replace(day=days)
    return date


class SalesforceOpportunityManager(SalesforceManager):

    def create_for_project(self, project):
        from projects.models import SalesforceOpportunityContactRole
        opportunity = self.from_project(project)
        opportunity.save()
        if not project.salesforce_opportunity_id:
            project.salesforce_opportunity_id = opportunity.pk
            project.save()

        if project.client_poc:
            if project.client_poc.salesforce_contact_id:
                if not SalesforceOpportunityContactRole.objects.filter(
                        opportunity=opportunity,
                        contact_id=project.client_poc.salesforce_contact_id).exists():
                    SalesforceOpportunityContactRole.objects.create(
                        opportunity=opportunity,
                        contact_id=project.client_poc.salesforce_contact_id)
            else:
                logger.info(u"%s: client_poc %s has no salesforce ID",
                            opportunity, project.client_poc)

        return opportunity


    def from_project(self, project):
        """Makes an Opportunity from the data for a Project, *does not save*.

        :type project: projects.models.Project
        :rtype: projects.models.SalesforceOpportunity
        """
        # Opportunity names, by convention, get jammed with things from other
        # fields because those fields aren't included in some summary report.
        # That might be fixable on the salesforce side by altering the report?
        name = u"%(client)s VTP %(job_number)s (%(contact)s)" % {
            'client': project.client.name,
            'job_number': project.job_number,
            'contact': project.client_poc.get_full_name(),
        }
        if project.account_executive:
            owner_id = project.account_executive.salesforce_user_id
            if not owner_id:
                logger.warning(u"%s: Account Executive %s "
                               u"has no salesforce_user_id",
                               project.job_number, project.account_executive)
                owner_id = settings.SALESFORCE_DEFAULT_OPPORTUNITY_OWNER
        else:
            # owner is not an optional field.
            logger.warning(u"No Account Executive assigned for %s (%s)",
                           project.job_number, project.client.name)
            owner_id = settings.SALESFORCE_DEFAULT_OPPORTUNITY_OWNER

        project_url = urljoin(
            settings.BASE_URL,
            reverse('via_job_detail_overview', args=(project.id,)))

        description = (u"%(name)s\n"
                       u"%(url)s" % {
                           'name': project.name,
                           'url': project_url,
                       })

        if project.approved:
            stage = self.model.STAGE_Closed_Won
            # better if Project had an "approved" date field.
            close_date = timezone.now()
        else:
            close_date = last_day_of_month()
            if project.is_canceled_status():
                stage = self.model.STAGE_Closed_Lost
            elif project.is_quoted_status():
                stage = self.model.STAGE_P2_Wildcard
            else:
                stage = self.model.STAGE_P1_Wildcard

        opportunity = self.model(
            pk=project.salesforce_opportunity_id,
            name=name,
            account_id=project.client.salesforce_account_id,
            owner_id=owner_id,
            amount=project.price(),
            close_date=close_date,
            description=description,
            stage=stage,
        )
        return opportunity


class PriceQuoteManager(models.Manager, GetOrNoneMixin):
    pass


class PriceQuoteDetailsManager(models.Manager, GetOrNoneMixin):
    pass
