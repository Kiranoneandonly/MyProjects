from collections import OrderedDict
from decimal import Decimal

from django.core.urlresolvers import reverse
from django.db.models import Q
from localization_kits.models import FileAnalysis
from projects.states import (TASK_ACTIVE_STATUS, TASK_COMPLETED_STATUS, TASK_CREATED_STATUS)
from tasks.models import TaskLocalizedAsset, TranslationTaskClientPrice
from matches.models import ANALYSIS_FIELD_NAMES
from services.managers import FINAL_APPROVAL_SERVICE_TYPE
from tasks.models import Task
from tasks.states import VENDOR_STATUS_DETAILS, VIA_STATUS_DETAILS, TASK_STATUS_FINAL_APPROVAL

# task views
VIEW_TASKS_ALL = 'all'
VIEW_TASKS_MY = 'my'
VIEW_TASKS_TEAM = 'team'


class CloneAttr(object):
    def clone_attrs(self, parent, attrs_to_clone):
        for attr in attrs_to_clone:
            parent_attr = getattr(parent, attr, None)
            setattr(self, attr, parent_attr)


class TargetAnalysisSetViewModel(object):
    def __init__(self, target, project, include_placeholder=False):
        self.target = target
        self.project = project
        self.all_memo = None
        self.translation_task_client_price = []
        self.include_placeholder = include_placeholder

        if self.include_placeholder:
            files = self.project.kit.source_and_placeholder_files()
        else:
            files = self.project.kit.source_files()

        self.assets_fileanalysis = list(FileAnalysis.objects.filter(asset__in=[x.id for x in files.all()]).select_related('asset'))

        root_tasks = (self.project.all_root_tasks_target(self.target))

        for tsk in root_tasks:
            if tsk.is_translation():
                self.translation_task_client_price = list(TranslationTaskClientPrice.objects.filter(pk=tsk.translationtask.client_price_id))
                break

    def all(self):
        result = []
        [result.append(analysis) for analysis in self.assets_fileanalysis if analysis.target_locale_id == self.target.id]
        return result

    def mbd_all(self):
        result = []
        [result.append(analysis) for analysis in self.translation_task_client_price]
        return result

    @property
    def translation_task_client_price_id(self):
        for item in self.mbd_all():
            translation_task_client_price_id = item.id
            if translation_task_client_price_id:
                break
        return translation_task_client_price_id

    @property
    def mbd_total_guaranteed(self):
        return sum(item.guaranteed or 0 for item in self.mbd_all())

    @property
    def mbd_total_exact(self):
        return sum(item.exact or 0 for item in self.mbd_all())

    @property
    def mbd_total_duplicate(self):
        return sum(item.duplicate or 0 for item in self.mbd_all())

    @property
    def mbd_total_fuzzy9599(self):
        return sum(item.fuzzy9599 or 0 for item in self.mbd_all())

    @property
    def mbd_total_fuzzy8594(self):
        return sum(item.fuzzy8594 or 0 for item in self.mbd_all())

    @property
    def mbd_total_fuzzy7584(self):
        return sum(item.fuzzy7584 or 0 for item in self.mbd_all())

    @property
    def mbd_total_fuzzy5074(self):
        return sum(item.fuzzy5074 or 0 for item in self.mbd_all())

    @property
    def mbd_total_no_match(self):
        return sum(item.no_match or 0 for item in self.mbd_all())

    @property
    def total_guaranteed(self):
        return sum(item.guaranteed or 0 for item in self.all())

    @property
    def total_exact(self):
        return sum(item.exact or 0 for item in self.all())

    @property
    def total_duplicate(self):
        return sum(item.duplicate or 0 for item in self.all())

    @property
    def total_fuzzy9599(self):
        return sum(item.fuzzy9599 or 0 for item in self.all())

    @property
    def total_fuzzy8594(self):
        return sum(item.fuzzy8594 or 0 for item in self.all())

    @property
    def total_fuzzy7584(self):
        return sum(item.fuzzy7584 or 0 for item in self.all())

    @property
    def total_fuzzy5074(self):
        return sum(item.fuzzy5074 or 0 for item in self.all())

    @property
    def total_no_match(self):
        return sum(item.no_match or 0 for item in self.all())

    @property
    def total_words(self):
        return sum([getattr(self, 'total_{0}'.format(field)) for field in ANALYSIS_FIELD_NAMES])

    @staticmethod
    def word_percentage(total_words, word_percentage_per_bucket, placeholder=0):
        total_count_percentage = Decimal(total_words) / Decimal(100)
        if word_percentage_per_bucket == 0:
            word_percentage_of_total = 0
        else:
            word_percentage_of_total = word_percentage_per_bucket / total_count_percentage
        return round(word_percentage_of_total, placeholder)

    @property
    def word_percentage_guaranteed(self):
        return self.word_percentage(self.total_words, self.total_guaranteed, 1)

    @property
    def word_percentage_exact(self):
        return self.word_percentage(self.total_words, self.total_exact, 1)

    @property
    def word_percentage_duplicate(self):
        return self.word_percentage(self.total_words, self.total_duplicate, 1)

    @property
    def word_percentage_fuzzy9599(self):
        return self.word_percentage(self.total_words, self.total_fuzzy9599, 1)

    @property
    def word_percentage_fuzzy8594(self):
        return self.word_percentage(self.total_words, self.total_fuzzy8594, 1)

    @property
    def word_percentage_fuzzy7584(self):
        return self.word_percentage(self.total_words, self.total_fuzzy7584, 1)

    @property
    def word_percentage_fuzzy5074(self):
        return self.word_percentage(self.total_words, self.total_fuzzy5074, 1)

    @property
    def word_percentage_no_match(self):
        return self.word_percentage(self.total_words, self.total_no_match, 1)

    @property
    def leveraged_rate_guaranteed(self):
        return round(Decimal(self.mbd_total_guaranteed) * Decimal(self.word_percentage_guaranteed), 1)

    @property
    def leveraged_rate_exact(self):
        return round(Decimal(self.mbd_total_exact) * Decimal(self.word_percentage_exact), 1)

    @property
    def leveraged_rate_duplicate(self):
        return round(Decimal(self.mbd_total_duplicate) * Decimal(self.word_percentage_duplicate), 1)

    @property
    def leveraged_rate_fuzzy9599(self):
        return round(Decimal(self.mbd_total_fuzzy9599) * Decimal(self.word_percentage_fuzzy9599), 1)

    @property
    def leveraged_rate_fuzzy8594(self):
        return round(Decimal(self.mbd_total_fuzzy8594) * Decimal(self.word_percentage_fuzzy8594), 1)

    @property
    def leveraged_rate_fuzzy7584(self):
        return round(Decimal(self.mbd_total_fuzzy7584) * Decimal(self.word_percentage_fuzzy7584), 1)

    @property
    def leveraged_rate_fuzzy5074(self):
        return round(Decimal(self.mbd_total_fuzzy5074) * Decimal(self.word_percentage_fuzzy5074), 1)

    @property
    def leveraged_rate_no_match(self):
        return round(Decimal(self.mbd_total_no_match) * Decimal(self.word_percentage_no_match), 1)

    @property
    def leveraged_rate_total(self):
        return self.leveraged_rate_guaranteed + self.leveraged_rate_exact + self.leveraged_rate_duplicate + \
               self.leveraged_rate_fuzzy9599 + self.leveraged_rate_fuzzy8594 + self.leveraged_rate_fuzzy7584 + \
               self.leveraged_rate_fuzzy5074 + self.leveraged_rate_no_match

    @property
    def total_memory_bank_discount(self):
        return -100.00 + self.leveraged_rate_total

    @property
    def memory_bank_discount_exists(self):
        return True if self.mbd_all() else False


class BulkDeliveryViewModel(CloneAttr):
    def __init__(self, deliveries, project):
        self.total_files = deliveries.count()
        if self.total_files > 1 and self.total_files == project.kit.source_files().count():
            self.deliveries = deliveries
            self.source_asset_name = unicode(self.total_files) + ' Files'
            self.out_file_name = unicode(self.total_files) + ' Files'
            self.size = self.get_size()
            self.created = self.get_created_timestamp()
            self.downloaded = self.get_downloaded_timestamp()

    def get_size(self):
        size = 0
        for delivery in self.deliveries:
            size += delivery.output_file.size
        return size

    def get_created_timestamp(self):
        latest_created = None
        for delivery in self.deliveries:
            if not delivery.created:
                # all output files must be created,
                # in theory the logic should never get here
                # unless all files have been created
                return None

            if not latest_created:
                latest_created = delivery.created
            elif delivery.created > latest_created:
                latest_created = delivery.created

        return latest_created

    def get_downloaded_timestamp(self):
        latest_downloaded = None
        for delivery in self.deliveries:
            if not delivery.downloaded:
                # all files must be downloaded
                return None

            if not latest_downloaded:
                latest_downloaded = delivery.downloaded
            elif delivery.downloaded > latest_downloaded:
                latest_downloaded = delivery.downloaded

        return latest_downloaded


class ProjectTargetDeliveryViewModel(CloneAttr):
    def __init__(self, project, target):
        self.project = project
        self.target = target

        self.deliveries = self.get_deliveries()
        self.delivery_note = self.get_delivery_note()
        self.bulk_delivery = BulkDeliveryViewModel(self.deliveries, self.project)

    def get_deliveries(self):
        deliveries = TaskLocalizedAsset.objects.filter(
            task__project_id=self.project.id,
            task__service__service_type__code=FINAL_APPROVAL_SERVICE_TYPE,
            task__status=TASK_COMPLETED_STATUS,
            task__service__target=self.target
        )
        return deliveries.all()

    def get_delivery_note(self):
        fa_task = Task.objects.select_related().filter(
            project_id=self.project.id,
            service__service_type__code=FINAL_APPROVAL_SERVICE_TYPE,
            status=TASK_COMPLETED_STATUS,
            service__target=self.target
        )

        r = list(fa_task[:1])
        if r:
            return r[0].via_notes
        return None


class ProjectTargetViewModel(CloneAttr):
    def __init__(self, project, target, billable_only=False):
        self.project = project
        self.target = target
        self.clone_attrs(target, ['id', 'lcid'])

        root_tasks = (self.project.task_set.filter(service__target=self.target, predecessor=None, parent_id=None))
        tasks = self._build_task_list_sorted_by_predecessor_and_subtasks(root_tasks)

        '''
        Via notes is stored in final approval task. so we take non billable task
        '''
        self.target.nbtask = [nbtask for nbtask in tasks if nbtask.billable is False]
        
        if billable_only:
            tasks = [task for task in tasks if task.billable]

        self.tasks = tasks
        self.wf_tasks = [task for task in tasks if task.workflow_task]

    def __unicode__(self):
        return unicode(self.target)

    def has_delivery(self):
        return TaskLocalizedAsset.objects.filter(
            task__project_id=self.project.id,
            task__service__service_type__code=FINAL_APPROVAL_SERVICE_TYPE,
            task__status=TASK_COMPLETED_STATUS,
            task__service__target=self.target
        ).exists()

    def is_workflow_all_completed(self):
        if not self.wf_tasks:
            return False
        return all([task.is_complete() is True for task in self.wf_tasks])

    def has_issues(self):
        if not self.wf_tasks:
            return False
        return any([task.response_is_late() is True or task.is_overdue() is True for task in self.wf_tasks])

    def has_started(self):
        if not self.wf_tasks:
            return False
        return any([task.is_active_status() is True for task in self.wf_tasks])

    def has_not_started(self):
        if not self.wf_tasks:
            return False
        return all([task.is_created_status() is True for task in self.wf_tasks])

    # def _build_task_list_sorted_by_predecessor(self, tasks):
    #     sorted_tasks = []
    #     for task in tasks:
    #         sorted_tasks.append(task)
    #         children = task.children.all()
    #         sorted_tasks += self._build_task_list_sorted_by_predecessor(children)
    #     return sorted_tasks

    def _build_task_list_sorted_by_predecessor_and_subtasks(self, tasks):
        sorted_tasks = []
        for task in tasks:
            sorted_tasks.append(task)
            if task.has_sub_tasks():
                st = task.sub_task.all().order_by('id')
                sorted_tasks += self._build_task_list_sorted_by_predecessor_and_subtasks(st)
            children = task.children.filter(parent_id=None)
            sorted_tasks += self._build_task_list_sorted_by_predecessor_and_subtasks(children)
        return sorted_tasks


class ProjectTargetSetViewModel(object):
    '''
    takes a project and locale as arguments
    returns a list of locales with tasks and per-source-file pricing
    '''

    locales = []

    def __init__(self, project, **kwargs):
        self.project = project

        project_target_set = []
        for target in self.project.target_locales.all():
            project_target_vm = ProjectTargetViewModel(self.project, target, **kwargs)
            project_target_set.append(project_target_vm)
        self.targets = project_target_set


class VendorCalendarTaskViewModel(object):
    def __init__(self, task):
        self.task = task
        self.title = task.project.job_number + ': ' + task.service.service_type.code.upper()
        self.url = reverse('vendor_task_detail', args=(task.id,))

    def as_dict(self):
        result = {}
        for prop in ['title', 'start', 'end', 'url', 'className']:
            result[prop] = getattr(self, prop)
        return result

    @property
    def start(self):
        start = self.task.started_timestamp
        if self.task.is_upcoming:
            start = self.task.scheduled_start_timestamp
        return unicode(start)

    @property
    def end(self):
        return unicode(self.task.due)

    @property
    def className(self):
        if self.task.is_overdue():
            return 'overdue'
        else:
            return self.task.vendor_status


class VendorTaskStatusViewModel(object):
    def __init__(self, tasks, status):
        self.url = reverse('vendor_tasks_status', kwargs={'status': status})
        self.description = VENDOR_STATUS_DETAILS[status]['description']
        self.icon = VENDOR_STATUS_DETAILS[status]['icon']
        self.name = VENDOR_STATUS_DETAILS[status]['name']
        self.tasks = getattr(tasks, 'get_{0}_tasks'.format(status))()


class VendorTasksViewModel(object):
    def __init__(self, vendor):
        self.vendor = vendor
        self.tasks = Task.objects.get_vendor_tasks(vendor)
        self.tasks_not_completed = self.tasks.filter(status__in=[TASK_CREATED_STATUS, TASK_ACTIVE_STATUS])
        self.statuses = OrderedDict()
        for (status, status_detail) in VENDOR_STATUS_DETAILS.iteritems():
            vts = VendorTaskStatusViewModel(self.tasks, status)
            self.statuses[status] = vts


class MyTaskStatusViewModel(object):
    def __init__(self, tasks, status, is_user_type):
        self.status = status
        self.url = reverse('my_tasks_status', kwargs={'is_user_type': is_user_type, 'status': status})
        self.description = VIA_STATUS_DETAILS[status]['description']
        self.icon = VIA_STATUS_DETAILS[status]['icon']
        self.name = VIA_STATUS_DETAILS[status]['name']
        self.tasks = getattr(tasks, 'get_{0}_tasks'.format(status))()

    @property
    def is_status_final_approval(self):
        return self.status == TASK_STATUS_FINAL_APPROVAL


class ViaMyTasksViewModel(object):
    def __init__(self, user_id, is_user_type, client=None, project_filter=None):
        self.tasks = ()

        if project_filter:
            self.tasks = Task.objects.select_related().filter(project=project_filter, service__service_type__workflow=True)
        elif is_user_type == VIEW_TASKS_MY:
            self.tasks = Task.objects.get_active_jobs_workflow_tasks().get_user_tasks(user_id)
        elif is_user_type == VIEW_TASKS_TEAM:
            self.tasks = Task.objects.get_active_jobs_workflow_tasks().filter(Q(project__team__contact_id=user_id)).distinct()
        elif client:
            self.tasks = Task.objects.get_active_jobs_workflow_tasks().filter(Q(project__client=client) | Q(project__client__parent=client))
        else:
            self.tasks = Task.objects.get_active_jobs_workflow_tasks()

        self.statuses = OrderedDict()
        for (status, status_detail) in VIA_STATUS_DETAILS.iteritems():
            vts = MyTaskStatusViewModel(self.tasks, status, is_user_type)
            self.statuses[status] = vts
