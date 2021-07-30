from collections import namedtuple
from datetime import timedelta, datetime
from decimal import Decimal
import decimal
import logging
import posixpath
import pytz
utc=pytz.UTC

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.mail import mail_admins
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models import permalink, Q
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _

from localization_kits.models import LocaleTranslationKit, FileAsset, FileAnalysis
from matches.models import AnalysisFields, AnalysisCategoryCurrencyFields, ANALYSIS_FIELD_NAMES, \
    ANALYSIS_FIELD_NAMES_LABELS
from people.models import Account
from prices.constants import TWO_PLACES, MINIMUM_JOB_SURCHARGE
from projects.models import Project, EXPRESS_SPEED
from projects.quote import QuoteItem
from projects.states import TASK_STATUS, TASK_CREATED_STATUS, TASK_COMPLETED_STATUS, PO_STATUS, \
    PO_OPEN_STATUS, TASK_ACTIVE_STATUS, TASK_CANCELED_STATUS, COMPLETED_STATUS
from services.managers import FINAL_APPROVAL_SERVICE_TYPE, TRANSLATION_EDIT_PROOF_SERVICE_TYPE, \
    TRANSLATION_ONLY_SERVICE_TYPE, PM_HOUR_SERVICE_TYPE, HOURS_UNITS, PM_SERVICE_TYPE, DISCOUNT_SERVICE_TYPE, \
    POST_PROCESS_SERVICE_TYPE, THIRD_PARTY_REVIEW_SERVICE_TYPE
from services.models import ServiceType, PricingFormula, Locale, PricingBasis, Service, ScopeUnit
from shared.fields import CurrencyField
from shared.forms import S3UploadForm
from shared.models import CircusModel
from shared.utils import copy_file_asset
from tasks.managers import TaskManager, TranslationTaskAnalysisManager, TaskQuoteManager, TaskAssetQuoteManager
from tasks.states import VENDOR_STATUS_DETAILS, OVERDUE_STATUS, IMPORTANT_STATUS, WARNING_STATUS, INFO_STATUS
from vendors.models import Vendor
from services.managers import PROOFREADING_SERVICE_TYPE

logger = logging.getLogger('circus.' + __name__)


def wrapper(task, filename):
    return get_task_asset_path(task, filename, 'ref')


class Task(CircusModel):
    objects = TaskManager()

    project = models.ForeignKey(Project)
    predecessor = models.ForeignKey('self', blank=True, null=True, related_name='children')

    service = models.ForeignKey(Service, blank=True, null=True, related_name='+')

    status = models.CharField(choices=TASK_STATUS, max_length=40, default=TASK_CREATED_STATUS)

    billable = models.BooleanField(default=False)

    assignee_content_type = models.ForeignKey(ContentType, blank=True, null=True)
    assignee_object_id = models.PositiveIntegerField(blank=True, null=True)
    assigned_to = GenericForeignKey('assignee_content_type', 'assignee_object_id')
    standard_days = models.DecimalField(decimal_places=2, default=0, max_digits=6)
    express_days = models.DecimalField(decimal_places=2, default=0, max_digits=6)

    accepted_timestamp = models.DateTimeField(blank=True, null=True)
    scheduled_start_timestamp = models.DateTimeField(blank=True, null=True)
    due = models.DateTimeField(blank=True, null=True)
    overdue_email_last_sent = models.DateTimeField(blank=True, null=True)
    started_timestamp = models.DateTimeField(blank=True, null=True)
    completed_timestamp = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    rating = models.IntegerField(default=0, blank=True, null=True)
    via_notes = models.TextField(_('Via Notes'), blank=True, null=True)
    vendor_notes = models.TextField(_('Vendor Notes'), blank=True, null=True)
    vendor_feedback = models.TextField(_('Vendor feedback'), blank=True, null=True)

    current_user = models.IntegerField(blank=True, null=True)

    # JAMS API
    jams_taskid = models.PositiveIntegerField(_('JAMS TaskID'), blank=True, null=True)
    create_po_needed = models.BooleanField(default=True)
    po_created_date = models.DateTimeField(blank=True, null=True)
    qa_approved = models.NullBooleanField(default=False, blank=True, null=True)
    qa_lead = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True)

    reference_file = models.FileField(
        max_length=settings.FULL_FILEPATH_LENGTH,
        null=True, blank=True,
        upload_to=wrapper)

    def set_assigned_to(self, assignee=None):
        return self.dispatch_subclass('set_assigned_to')(assignee)

    parent = models.ForeignKey('self', blank=True, null=True, related_name='sub_task')

    def ref_file_name(self, reference):
        val = getattr(self, reference + '_file')
        if val:
            # noinspection PyUnresolvedReferences
            head, tail = posixpath.split(val.name)
            return tail or posixpath.basename(head)
        return u''

    def supplier_reference_file_name(self):
        return self.ref_file_name('reference')

    @property
    def reference_file_name(self):
        return posixpath.basename(self.reference_file.name)

    @property
    def vendor_status_details(self):
        status_details = VENDOR_STATUS_DETAILS[self.vendor_status]
        return status_details

    @property
    def vendor_status(self):
        for status, status_details in VENDOR_STATUS_DETAILS.iteritems():
            if getattr(self, 'is_{0}'.format(status))():
                return status

    @property
    def is_accepted(self):
        return bool(self.accepted_timestamp)

    def is_assigned(self):
        return bool(self.assigned_to)

    def is_editable_by_pm(self):
        return self.status not in TASK_COMPLETED_STATUS

    def is_final_approval(self):
        return self.service.service_type.code == FINAL_APPROVAL_SERVICE_TYPE

    def is_final_approval_ready(self):
        return self.status in TASK_ACTIVE_STATUS and self.is_final_approval()

    def is_post_process(self):
        return self.service.service_type == ServiceType.objects.get_or_none(code=POST_PROCESS_SERVICE_TYPE)

    def is_client_discount(self):
        return self.service.service_type == ServiceType.objects.get_or_none(code=DISCOUNT_SERVICE_TYPE)

    def is_post_process_ready(self):
        return self.status in TASK_ACTIVE_STATUS and self.is_post_process()

    def is_project_management_percent(self):
        return self.service.service_type.code == PM_SERVICE_TYPE

    def dispatch_subclass(self, method):
        if hasattr(self, 'translationtask'):
            return getattr(self.translationtask, method)
        else:
            return getattr(self.nontranslationtask, method)

    def activate(self):
        import projects.start_tasks
        try:
            servicetype = self.service.service_type.code
            if servicetype == TRANSLATION_EDIT_PROOF_SERVICE_TYPE:
                servicetype = TRANSLATION_ONLY_SERVICE_TYPE
            getattr(projects.start_tasks, 'activate_{0}_task'.format(servicetype))(self)
        except Exception:
            logger.error("Error activating task %s", self, exc_info=True)

    def complete(self):
        self.completed_timestamp = timezone.now()
        self.status = TASK_COMPLETED_STATUS
        self.save()
        if self.is_subtask() and self.is_proofreading_subtask():
            if self.trans_kit:
                self.copy_locale_translation_kit_from(self.trans_kit, 'output_file', True)
        elif self.is_translation_task_parent() and self.has_sub_tasks():
            # Getting the normal task in the workflow after complteting the TEP task
            children_list = self.get_next_workflow_task()
            for child in children_list:
                if not child.parent_id:
                    child.activate()
                    break
        else:
            children = self.children.all()
            if children:
                for child in children:
                    child.activate()

    def complete_if_ready(self):
        if self.trans_kit and self.trans_kit.output_file:
            self.complete()
            return True
        else:
            return False

    def all_tla_files_ready(self):
        if not self.localized_assets.filter(output_file='').exists():
            return True
        return False

    def are_all_files_via_approved(self):
        if self.is_final_approval():
            return all(la_file.is_via_approved() for la_file in self.localized_assets.all())
        else:
            return True

    def complete_if_all_tla_files_ready(self):
        if self.all_tla_files_ready():
            self.complete()
            return True
        else:
            return False

    def complete_fa_if_all_tla_files_ready(self):
        if self.all_tla_files_ready() and self.are_all_files_via_approved():
            self.complete()
            return True
        else:
            return False

    def can_be_completed(self):
        return self.dispatch_subclass('can_be_completed')()

    def has_trans_kit(self):
        try:
            if self.trans_kit:
                return True
            else:
                return False
        except Exception:
            logger.error("Error has_trans_kit %s", self, exc_info=True)
            return False

    def remove_task_localized_assets(self):
        tla = TaskLocalizedAsset.objects.filter(task=self)
        if tla.count() > 0:
            tla.delete()
        return

    def is_translation_task_parent(self):
        return self.is_translation() and not self.parent_id

    def has_sub_tasks(self):
        return self.sub_task.all().count()

    def is_subtask(self):
        return self.parent_id

    def get_next_workflow_task(self):
        child_tasks = self.children.all()
        task_list = []
        for tsk in child_tasks:
            task_list.append(tsk)
            t = tsk
        if t.parent_id:
            task_list += t.get_next_workflow_task()
        return task_list

    def is_proofreading_subtask(self):
        return self.service.service_type.code == PROOFREADING_SERVICE_TYPE

    def is_translation_subtask(self):
        return self.service.service_type.code == TRANSLATION_ONLY_SERVICE_TYPE

    def due_date_check(self, due_date):
        if due_date and utc.localize(datetime.strptime(due_date, "%Y-%m-%d %H:%M")) > self.parent.due:
            return True
        else:
            return False

    def remove_trans_kit_assets(self):
        tltk = TaskLocaleTranslationKit.objects.filter(task=self)
        if tltk.count() > 0:
            tltk.delete()
        return

    def copy_trans_kit_assets_from(self, obj, from_field):
        try:
            tltk, created = TaskLocaleTranslationKit.objects.get_or_create(task=self)
            original_name = getattr(obj, from_field)
            if original_name:
                to_filename = get_task_input_asset_path(tltk, unicode(original_name).split('/')[-1])
                from_key = settings.MEDIA_URL[1:] + unicode(original_name)
                to_key = settings.MEDIA_URL[1:] + to_filename
                if from_key:
                    copy_file_asset(from_key, to_key)
                tltk.input_file = to_filename
                tltk.save()
            return True
        except Exception:
            import traceback
            tb = traceback.format_exc()  # NOQA
            print tb
            logger.error("copy_trans_kit_assets_from error", exc_info=True)
            return False

    def copy_trans_kit_assets_from_lockit(self):
        ltk, created = LocaleTranslationKit.objects.get_or_create(kit=self.project.kit, target_locale=self.service.target)
        if ltk.reference_file:
            self.reference_file = ltk.reference_file
            self.save()
        return self.copy_trans_kit_assets_from(ltk, 'translation_file')

    def copy_trans_kit_assets_from_predecessor(self):
        return self.copy_trans_kit_assets_from(self.predecessor.trans_kit, 'output_file')

    def copy_task_localized_assets_setup(self):
        loc_kit_exists = self.project.kit.localetranslationkit_files().filter(target_locale=self.service.target)

        #uncomment the code to copy the source file as task input for non translation task(Third Party Review) if required
        # if any(task.service.service_type.code == THIRD_PARTY_REVIEW_SERVICE_TYPE for task in self.project.workflow_root_tasks()):
        #     self.copy_task_localized_assets_from_source()
        #     return True

        if loc_kit_exists:
            self.copy_task_localized_asset_from_lockit(loc_kit_exists)
        else:
            self.copy_task_localized_assets_from_source()

        return True

    def copy_task_localized_assets_from_source(self):
        for source_asset in self.project.kit.source_files():
            file_path = source_asset.orig_file.name
            file_name = file_path.split('/')[-1]
            tla, created = TaskLocalizedAsset.objects.get_or_create(task=self,
                                                                    name=file_name,
                                                                    input_file=file_path,
                                                                    source_asset=source_asset)

    def copy_task_localized_asset_from_lockit(self, loc_kit=None):
        for asset in loc_kit:
            file_path = asset.translation_file.name
            file_name = file_path.split('/')[-1]
            tla, created = TaskLocalizedAsset.objects.get_or_create(task=self,
                                                                    name=file_name,
                                                                    input_file=file_path)

    def copy_localized_assets_from(self, obj, from_field):
        for prev_tla in obj.instance.localized_assets.all():
            original_name = getattr(prev_tla, from_field)
            source_asset_id = getattr(prev_tla, 'source_asset')
            tla, created = TaskLocalizedAsset.objects.get_or_create(task=self, source_asset=source_asset_id)
            to_filename = get_task_input_asset_path(tla, unicode(original_name).split('/')[-1])
            from_key = settings.MEDIA_URL[1:] + unicode(original_name)
            to_key = settings.MEDIA_URL[1:] + to_filename
            copy_file_asset(from_key, to_key)
            tla.input_file = to_filename
            tla.source_asset = source_asset_id
            tla.save()

    def copy_locale_translation_kit_from(self, obj, from_field, last_sub_task=None):
        original_name = getattr(obj, from_field)
        if last_sub_task:
            tla, created = TaskLocaleTranslationKit.objects.get_or_create(task=self.parent)
        else:
            tla, created = TaskLocaleTranslationKit.objects.get_or_create(task=self)
        to_filename = get_task_input_asset_path(tla, unicode(original_name).split('/')[-1])
        from_key = settings.MEDIA_URL[1:] + unicode(original_name)
        to_key = settings.MEDIA_URL[1:] + to_filename
        copy_file_asset(from_key, to_key)
        if last_sub_task:
            tla.output_file = to_filename
        else:
            tla.input_file = to_filename
        tla.save()

    def copy_localized_assets_from_input_to_output(self):
        for la in self.localized_assets.all():
            original_name = getattr(la, "input_file")
            from_key = settings.MEDIA_URL[1:] + unicode(original_name)
            to_filename = get_task_output_asset_path(la, unicode(original_name).split('/')[-1])
            to_key = settings.MEDIA_URL[1:] + to_filename
            copy_file_asset(from_key, to_key)
            la.output_file = to_filename
            la.save()

    def copy_locale_translation_kit_from_predecessor(self, copy_to_output=False):
        try:
            self.copy_locale_translation_kit_from(self.predecessor.trans_kit, 'output_file')
            # if copy_to_output:
            #     self.copy_localized_assets_from_input_to_output()
            return True
        except:
            return False

    def copy_localized_assets_from_predecessor(self, copy_to_output=False):
        try:
            self.copy_localized_assets_from(self.predecessor.localized_assets, 'output_file')
            if copy_to_output:
                self.copy_localized_assets_from_input_to_output()
            return True
        except:
            return False

    def is_overdue(self):
        now = timezone.now()
        if not self.is_complete_canceled() and self.due and now > self.due:
            return True
        else:
            return False

    def time_left_status(self):
        now = timezone.now()
        if self.due:
            if self.is_canceled_status():
                return COMPLETED_STATUS
            elif self.is_overdue():
                return OVERDUE_STATUS
            elif now + timedelta(hours=4) > self.due:
                return IMPORTANT_STATUS
            elif now + timedelta(hours=24) > self.due:
                return WARNING_STATUS
        return INFO_STATUS

    def duration(self, speed=None):
        """Return task duration for speed.

        :param speed: 'express' or 'standard'. Defaults to speed of project.
        :returns: number of days
        :rtype: int or Decimal ( not float )
        """
        if not speed:
            speed = self.project.project_speed
        days = getattr(self, '{0}_days'.format(speed))
        if (not days) and self.service.is_hourly():
            # BEWARE: Task.quantity is a function
            # NonTranslationTask.quantity is a Decimal field
            if callable(self.quantity):
                quantity = self.quantity()
            else:
                quantity = self.quantity
            quantity = quantity if quantity else 0
            days = float(quantity) / 24
        return float(days)

    def duration_with_children(self, speed=None):
        """
        Calculate duration for this task including its longest-lived children.

        If speed is not specified, uses project default (express or standard).
        """
        largest_found = 0
        for child in self.children.all():
            child_duration = child.duration_with_children(speed)
            if child_duration > largest_found:
                largest_found = child_duration
        return self.duration(speed) + largest_found

    @property
    def assets(self):
        return self.project.kit.source_files()

    def respond_by(self):
        if self.project.started_timestamp:
            return self.project.started_timestamp + timedelta(hours=settings.RESPOND_BY_TIMEDELTA)
        else:
            return timezone.now() + timedelta(hours=settings.RESPOND_BY_TIMEDELTA)

    def response_is_late(self):
        return not self.project.show_start_workflow() and not self.is_complete_canceled() and not self.accepted_timestamp and timezone.now() > self.respond_by()

    def response_left_status(self):
        now = timezone.now()
        if self.is_canceled_status():
            return COMPLETED_STATUS
        elif self.response_is_late():
            return OVERDUE_STATUS
        elif now + timedelta(hours=4) > self.respond_by():
            return IMPORTANT_STATUS
        elif now + timedelta(hours=24) > self.respond_by():
            return WARNING_STATUS
        return INFO_STATUS

    def calendar_status(self):
        if self.is_complete():
            return '#cccccc'
        elif self.is_pending():
            return '#cec1ff'
        elif self.is_upcoming():
            return '#c7e4f2'
        elif self.is_overdue():
            return '#f2deda'
        elif self.is_active():
            return '#cff2d0'
        elif self.is_created():
            return '#cec1ff'
        elif self.is_canceled_status():
            return '#bbbbbb'
        return '#bbbbbb'

    @property
    def files(self):
        return self.dispatch_subclass('files')

    @property
    def workflow_task(self):
        return self.service.service_type.workflow

    def get_taskassetquotes(self):
        return TaskAssetQuote.objects.filter(task=self).order_by('target', 'asset')

    def get_taskquote(self):
        return TaskQuote.objects.get_or_none(task=self)

    def express_mbd(self):
        obj = self.get_taskquote()
        if obj:
            return obj.express_mbd

    def express_gm(self):
        obj = self.get_taskquote()
        if obj:
            return obj.express_gm

    def express_net_price(self):
        obj = self.get_taskquote()
        if obj:
            return obj.express_net_price

    def express_raw_price(self):
        obj = self.get_taskquote()
        if obj:
            return obj.express_raw_price

    def express_quote_total_cost(self):
        obj = self.get_taskquote()
        if obj:
            return obj.express_total_cost

    def mbd(self):
        obj = self.get_taskquote()
        if obj:
            return obj.mbd

    def gm(self):
        obj = self.get_taskquote()
        if obj:
            return obj.gm

    def net_price(self):
        obj = self.get_taskquote()
        if obj:
            return obj.net_price

    def raw_price(self):
        obj = self.get_taskquote()
        if obj:
            return obj.raw_price

    def quote_total_cost(self):
        obj = self.get_taskquote()
        if obj:
            return obj.total_cost

    def task_wordcount(self):
        obj = self.get_taskquote()
        if obj:
            return obj.wordcount

    def is_valid(self):
        return self.dispatch_subclass('is_valid')()

    def is_workflow_ready(self):
        return self.dispatch_subclass('is_workflow_ready')()

    def is_translation(self):
        return self.dispatch_subclass('is_translation')()

    def has_input_file(self):
        return self.dispatch_subclass('has_input_file')()

    def is_unassigned(self):
        return not self.assigned_to

    def show_translation_note_reminder(self):
        return self.is_active() and self.is_translation() and self.project.is_auto_estimate()

    def is_assignee(self, user):
        """Is this user assigned to this task?

        Or are they a member of the account assigned to this task?

        :type user: accounts.models.CircusUser
        :rtype : bool
        """
        assigned_to = self.assigned_to
        if not assigned_to:
            return False
        if user.is_anonymous():
            return False

        # assigned_to has some polymorphic generic relation
        if user == assigned_to:
            return True
        elif isinstance(assigned_to, Account) and user.account == assigned_to:
            return True
        return False

    def total_cost(self):
        return self.dispatch_subclass('total_cost')()

    def field_wordcount_list(self):
        return self.dispatch_subclass('field_wordcount_list')()

    def is_minimum_vendor(self):
        return self.dispatch_subclass('is_minimum_vendor')()

    def is_minimum_client(self):
        return self.dispatch_subclass('is_minimum_client')()

    def detail_rows(self):
        return self.dispatch_subclass('detail_rows')()

    def quantity(self):
        return self.dispatch_subclass('get_quantity')()

    def unit_cost(self):
        if hasattr(self, 'nontranslationtask'):
            return self.nontranslationtask.unit_cost

    def unit_price(self):
        if hasattr(self, 'nontranslationtask'):
            return self.nontranslationtask.unit_price

    def vendor_minimum(self):
        if hasattr(self, 'nontranslationtask'):
            return self.nontranslationtask.vendor_minimum

    def price_is_percentage(self):
        if hasattr(self, 'nontranslationtask'):
            return self.nontranslationtask.price_is_percentage

    def formula(self):
        if hasattr(self, 'nontranslationtask'):
            if self.nontranslationtask.formula_id is None:
                return ''
            else:
                return self.nontranslationtask.formula.percent_calculation

    def actual_hours(self):
        if hasattr(self, 'nontranslationtask'):
            return self.nontranslationtask.actual_hours

    def is_active_status(self):
        return self.status == TASK_ACTIVE_STATUS

    def is_active_accepted(self):
        return self.is_active_status() and self.is_accepted

    def is_active(self):
        return self.is_active_accepted()

    def is_active_last_minute(self):
        return self.is_active_status() and self.started_timestamp and self.started_timestamp > timezone.now() - timedelta(seconds=20)

    def is_created(self):
        return self.is_created_status()

    def is_created_status(self):
        return self.status == TASK_CREATED_STATUS

    def is_upcoming(self):
        return self.is_accepted and self.is_created_status()

    def is_complete(self):
        return self.status == TASK_COMPLETED_STATUS

    def is_canceled_status(self):
        return self.status == TASK_CANCELED_STATUS

    def is_complete_canceled(self):
        return self.is_complete() or self.is_canceled_status()

    def is_pending(self):
        return not self.is_complete_canceled() and not self.is_accepted

    def is_billable(self):
        return self.billable

    def is_rated(self):
        return self.rating > 0

    def is_scheduled(self):
        return False

    def display_status(self):
        if self.is_complete():
            return 'completed'
        elif self.is_pending():
            return 'pending'
        elif self.is_upcoming():
            return 'upcoming'
        elif self.is_overdue():
            return 'error'
        elif self.is_active():
            return 'active'
        elif self.is_created():
            return 'created'
        elif self.is_canceled_status():
            return 'canceled'
        return 'canceled'

    def service_filters(self):
        return [
            Q(service__service_type=self.service.service_type, service__unit_of_measure=self.service.unit_of_measure),
            Q(service__source=self.service.source) | Q(service__source__isnull=True),
            Q(service__target=self.service.target) | Q(service__target__isnull=True)
        ]

    def service_match_score(self, service):
        # lower is better
        score = 0
        if service.source == self.service.source:
            score -= 1
        if service.target == self.service.target:
            score -= 1
        return score

    def set_from_vendor_rate(self, rate):
        if not rate:
            return False
        return self.dispatch_subclass('set_from_vendor_rate')(rate)

    def set_from_client_price(self, price):
        if not price:
            return False
        return self.dispatch_subclass('set_from_client_price')(price)

    def itemized_price_details(self, speed=None):
        # The interfaces are a little mismatched here. The higher-level
        # interfaces do "get me price for this speed", the lower-level
        # interfaces do "get me price for this multiplier." Which I think is
        # fine, although maybe then they need different names.
        if speed is None:
            speed = self.project.project_speed

        if speed == EXPRESS_SPEED:
            multiplier = Decimal(self.project.express_factor)
        else:
            multiplier = 1

        return self.dispatch_subclass('itemized_price_details')(multiplier)

    def itemized_cost_details(self):
        # task speed doesn't impact cost?
        return self.dispatch_subclass('itemized_cost_details')()

    def quote_percentage_of_min_price(self, price):
        if price < settings.PM_PRICE_MIN:
            from prices.models import ClientNonTranslationPrice

            pm_hour_service_type = ServiceType.objects.get_or_none(code=PM_HOUR_SERVICE_TYPE)
            hours = ScopeUnit.objects.get_or_none(code=HOURS_UNITS)
            pm_hour_service = None
            try:
                pm_hour_service = Service.objects.filter(service_type=pm_hour_service_type, unit_of_measure=hours, source=None, target=None)[0]
            except:
                pass

            pm_hour_price = None

            if pm_hour_service:
                pm_hour_price = ClientNonTranslationPrice.objects.get_or_none(client=self.project.client, service=pm_hour_service)

            price = pm_hour_price.unit_price if pm_hour_price and pm_hour_price.unit_price < settings.PM_PRICE_MIN else settings.PM_PRICE_MIN

        return price

    def quote_percentage_of_min_cost(self, total_price=0, unit_cost=None):
        if not unit_cost:
            unit_cost = settings.PM_PERCENT_UNIT_COST_CALC.quantize(TWO_PLACES)

        if unit_cost:
            self.unit_cost = unit_cost
            self.nontranslationtask.unit_cost = unit_cost
            self.nontranslationtask.save()
            self.save()

        # unit_cost * price is not a typo! Currently the only user of percentage-based costs does in fact
        # calculate the _cost_ based on the _price_.
        quote_cost = (unit_cost * total_price).quantize(TWO_PLACES)
        quote_cost = quote_cost if quote_cost > settings.PM_COST_MIN else settings.PM_COST_MIN
        return quote_cost

    def quote_percentage_of(self, task_quotes, speed=None):
        """Determine the price for this task, given prices of other tasks.

        Tasks with percentage-based pricing need to first have the prices of
        the other parts of the project. Given a list of quotes for tasks, this
        will decide which are related (i.e. those with the same target language)
        and apply its percentage to it, resulting in the dollar amount for this
        task.

        :param QuoteItem task_quotes: list of quotes for tasks.
        :rtype: QuoteItem
        """
        if not self.percentage_based():
            raise ValueError("quote_percentage_of called on non percentage-based task: %s" % (self,))

        def like_me(quote_item):
            return quote_item.target == target

        target = self.service.target
        # like_me = lambda quote_item: quote_item.target == target
        prices = [quote_item.price for quote_item in task_quotes if like_me(quote_item) and quote_item.price is not None]
        total_price = sum(prices) or Decimal(0)

        my_quote = QuoteItem.create_from_task(self, speed, include_price=False, include_cost=False)[0]

        unit_price = self.unit_price()
        my_quote.price = (unit_price * total_price).quantize(TWO_PLACES)

        if self.is_project_management_percent():
            my_quote.price = self.quote_percentage_of_min_price(my_quote.price)

            unit_cost = self.nontranslationtask.unit_cost
            my_quote.cost = self.quote_percentage_of_min_cost(total_price, unit_cost)

        return my_quote

    def percentage_based(self):
        try:
            return self.nontranslationtask.price_is_percentage
        except NonTranslationTask.DoesNotExist:
            return False

    def is_predecessor_null(self):
        predecessor_null_check = False
        if self.predecessor is None:
            predecessor_null_check = True
        return predecessor_null_check

    def reset_task_timestamps(self):
        self.accepted_timestamp = None
        self.scheduled_start_timestamp = None
        self.due = None
        self.started_timestamp = None
        self.completed_timestamp = None
        return self.save()

    def reset_task_vendor_costs(self):
        if self.is_translation():
            self.translationtask.vendor_rates = None
            self.translationtask.save()
        else:
            self.nontranslationtask.unit_cost = None
            self.nontranslationtask.vendor_minimum = None
            self.nontranslationtask.save()

        return True

    def can_delete_task(self, force_delete=False, predecessor=None):
        if self.workflow_task and self.is_predecessor_null() and (force_delete or predecessor):
            root_task_count = self.project.workflow_root_tasks_target_locale(self.service.target).count()
            if root_task_count == 1:
                return False
        return True

    def delete_task(self):
        return self.dispatch_subclass('delete_task')()

    def check_po_approved(self):
        try:
            po_exists = False
            try:
                if self.po.po_number:
                    po_exists = True
                    return True
            except VendorPurchaseOrder.DoesNotExist:
                pass
            return all([self.create_po_needed, self.actual_hours() > 0, self.is_complete(), po_exists])
        except:
            return False

    def can_assigned_to_work_on_files(self):
        if not self.project.is_phi_secure_job and not self.project.is_restricted_job:
            return True

        if self.assigned_to.account_type.code == settings.VENDOR_USER_TYPE:
            vendor = self.assigned_to.cast(Vendor)

            if self.project.is_phi_secure_job and vendor.can_access_phi_secure_job():
                return True
        return False

    @permalink
    def get_absolute_url(self):
        return 'via_job_detail_overview', [self.project.id]

    def __unicode__(self):
        return u'{0}: {1} ({2}): {3} to {4}'.format(self.project, self.service.service_type, self.service.unit_of_measure, self.service.source, self.service.target)


class TranslationTaskAnalysis(CircusModel, AnalysisFields):
    objects = TranslationTaskAnalysisManager()

    # decoupled foreign key to FileAnalysis
    source_of_analysis = models.IntegerField()
    source = models.ForeignKey(Locale, related_name='+', null=True)
    target = models.ForeignKey(Locale, related_name='+', null=True)

    def total_wordcount(self):
        return sum(getattr(self, field) for field in ANALYSIS_FIELD_NAMES)

    def clear_counts(self):
        for field in ANALYSIS_FIELD_NAMES:
            setattr(self, field, 0)

    def field_wordcount_list(self):
        result = [getattr(self, field) for field in ANALYSIS_FIELD_NAMES]
        result.insert(0, self.total_wordcount())
        return result

    def __unicode__(self):
        return u'{0} ({1} to {2})'.format(self.source_of_analysis, self.source, self.target)


class TaskQuote(CircusModel):

    project = models.ForeignKey(Project)
    task = models.ForeignKey(Task)
    total_cost = models.DecimalField(default=0, max_digits=15, decimal_places=4, blank=True, null=True)
    raw_price = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    mbd = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    net_price = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    gm = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)

    total_express_cost = models.DecimalField(default=0, max_digits=15, decimal_places=4, blank=True, null=True)
    express_raw_price = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    express_mbd = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    express_net_price = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    express_gm = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    wordcount = models.IntegerField(blank=True, null=True)

    standard_tat = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, blank=True, null=True)
    express_tat = models.DecimalField(max_digits=15, decimal_places=2, default=0.0, blank=True, null=True)

    objects = TaskQuoteManager()

    def __unicode__(self):
        return u'{0} : {1} - {2}'.format(self.task, self.total_cost, self.net_price)


class TaskAssetQuote(CircusModel):
    task = models.ForeignKey(Task)
    asset = models.ForeignKey(FileAsset, null=True)
    asset_total_cost = models.DecimalField(default=0, max_digits=15, decimal_places=4, blank=True, null=True)
    asset_raw_price = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    asset_mbd = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    asset_net_price = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    asset_gm = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    asset_is_minimum_price = models.BooleanField(default=False)
    asset_wordcount = models.IntegerField(blank=True, null=True)
    target = models.ForeignKey(Locale, blank=True, null=True)

    asset_total_express_cost = models.DecimalField(default=0, max_digits=15, decimal_places=4, blank=True, null=True)
    asset_express_raw_price = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    asset_express_mbd = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    asset_express_net_price = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)
    asset_express_gm = models.DecimalField(max_digits=15, decimal_places=4, default=0.0, blank=True, null=True)

    objects = TaskAssetQuoteManager()

    def __unicode__(self):
        return u'{0} : {1} - {2} - {3}'.format(self.task, self.asset, self.asset_total_cost, self.asset_net_price)


class TranslationTaskVendorRates(CircusModel, AnalysisCategoryCurrencyFields):
    # decoupled foreign key to VendorTranslationRate
    source_of_vendor_rates = models.IntegerField()
    minimum = CurrencyField(null=True, blank=True)
    basis = models.ForeignKey(PricingBasis, blank=True, null=True, related_name='+')
    word_rate = CurrencyField(default=0.0)

    def is_valid(self):
        return True

    def is_workflow_ready(self):
        return True

    def _get_analysis(self, asset):
        target = self.translationtask.service.target
        return asset.analysis_for_target(target)

    def _assets(self):
        kit = self.translationtask.project.kit
        return kit.source_files()

    def weighted_words(self, analysis):
        """
        Analysis contains word counts by buckets.
        client_price has weighting for each bucket (e.g. words in "duplicates" bucket may count for half).
        The result is a total weighted word count.

        :type analysis: matches.models.AnalysisFields
        :rtype: Decimal
        """
        weighted_words = sum(getattr(analysis, f) *
                             getattr(self, f)
                             for f in ANALYSIS_FIELD_NAMES)
        return weighted_words

    def analysis_cost_details(self, analysis, multiplier=Decimal(1)):
        weighted_words = self.weighted_words(analysis)
        total_words = analysis.total_wordcount()

        total_words = 1 if total_words == 0 else total_words
        mbd = (weighted_words / total_words) - 1

        # Assume all vendor rates are source-based, as we don't have
        # vendor expansion rates.
        net_price = weighted_words * self.word_rate * multiplier
        raw_price = total_words * self.word_rate * multiplier

        return TranslationTaskItemPrice(
            analysis,
            net_price.quantize(TWO_PLACES),
            raw_price.quantize(TWO_PLACES),
            mbd)

    def itemized_cost_details(self, multiplier=Decimal(1)):
        costs = []
        total_cost = Decimal('0.00')
        for asset in self._assets():
            analysis = self._get_analysis(asset)
            cost_row = self.analysis_cost_details(analysis, multiplier)
            costs.append(cost_row)
            total_cost += cost_row.net

        minimum_cost = self.minimum * multiplier

        if total_cost < minimum_cost:
            cost = minimum_cost - total_cost
            raw_cost = max(0, minimum_cost - sum(row.raw for row in costs))
            costs.append(TranslationTaskItemPrice(
                MINIMUM_JOB_SURCHARGE, cost, raw_cost, 0))

        return costs

    def total_cost(self, multiplier=Decimal(1)):
        cost = sum(row.net for row in self.itemized_cost_details(multiplier))
        return cost

    def __unicode__(self):
        return u'ID: {0}, Source: {1} ({2})'.format(self.id, self.source_of_vendor_rates, self.basis)


TranslationTaskItemPrice = namedtuple("TranslationTaskItemPrice", ["analysis", "net", "raw", "mbd"])


def sum_items(items):
    """
    :type items: [TranslationTaskItemPrice]
    """
    if items:
        analysis = sum((item.analysis for item in items[1:]
                        if item.analysis != MINIMUM_JOB_SURCHARGE),
                       items[0].analysis)
    else:
        analysis = FileAnalysis()
    total_net = sum((item.net for item in items), Decimal(0))
    total_raw = sum((item.raw for item in items), Decimal(0))
    with decimal.localcontext(decimal.ExtendedContext):
        total_mbd = (total_net / total_raw) - 1
    return TranslationTaskItemPrice(analysis, total_net, total_raw, total_mbd)


class TranslationTaskClientPrice(CircusModel, AnalysisCategoryCurrencyFields):
    # decoupled foreign key to ClientTranslationPrice
    source_of_client_prices = models.IntegerField()
    basis = models.ForeignKey(PricingBasis, blank=True, null=True, related_name='+')
    expansion_rate = models.FloatField(default=1.0)
    minimum_price = CurrencyField(default=0.0, null=True, blank=True)
    word_rate = CurrencyField(default=0.0)

    def is_valid(self):
        return True

    def is_workflow_ready(self):
        return True

    def _get_analysis(self, asset):
        target = self.translationtask.service.target
        return asset.analysis_for_target(target)

    def _assets(self):
        kit = self.translationtask.project.kit
        return kit.source_files()

    def weighted_words(self, analysis):
        """
        Analysis contains word counts by buckets.
        client_price has weighting for each bucket (e.g. words in "duplicates" bucket may count for half).
        The result is a total weighted word count.

        :type analysis: matches.models.AnalysisFields
        :rtype: Decimal
        """
        weighted_words = sum(Decimal(getattr(analysis, f)) * Decimal(getattr(self, f)) for f in ANALYSIS_FIELD_NAMES)
        return weighted_words

    def _get_expansion_rate(self):
        expansion = 1.0
        try:
            # but the expansion rate is only allowed to make the price go _up_, never down unless overwritten by client manifest.
            if self.expansion_rate > 1 or (
                    self.expansion_rate < 1 and self.translationtask and self.translationtask.project.client.manifest.expansion_rate_floor_override):
                expansion = self.expansion_rate
            return Decimal(expansion)
        except:
            logger.warning("%s._get_expansion_rate called but %s has no expansion rate", self.__class__.__name__, self)
            return Decimal(1)

    def analysis_price_details(self, analysis, multiplier=Decimal(1)):
        weighted_words = self.weighted_words(analysis)
        total_words = analysis.total_wordcount()

        total_words = 1 if total_words == 0 else total_words
        mbd = (weighted_words / total_words) - 1

        # that was words in the source document, but we may charge by projected words in the *target* language.
        client_basis = self.basis
        expansion = target_weighted_words = target_total_words = Decimal(1.0)
        if client_basis and client_basis.is_basis_target():
            expansion = self._get_expansion_rate()
            target_weighted_words = weighted_words * expansion
            target_total_words = total_words * expansion

        net_price = Decimal(weighted_words) * Decimal(expansion) * Decimal(self.word_rate) * multiplier
        raw_price = Decimal(total_words) * Decimal(expansion) * Decimal(self.word_rate) * multiplier

        return TranslationTaskItemPrice(
            analysis,
            net_price.quantize(TWO_PLACES),
            raw_price.quantize(TWO_PLACES),
            mbd)

    def itemized_price_details(self, multiplier=Decimal(1)):
        prices = []
        total_price = Decimal('0.00')
        for asset in self._assets():
            analysis = self._get_analysis(asset)
            price_row = self.analysis_price_details(analysis, multiplier)
            prices.append(price_row)
            total_price += price_row.net

        minimum_price = Decimal(self.minimum_price) * multiplier

        if total_price < minimum_price:
            price = minimum_price - total_price
            raw_price = max(0, minimum_price - sum(row.raw for row in prices))
            prices.append(TranslationTaskItemPrice(
                MINIMUM_JOB_SURCHARGE, price, raw_price, 0))

        return prices

    def total_price(self, multiplier=Decimal(1)):
        price = sum(price.net for price in
                    self.itemized_price_details(multiplier))
        return price

    def __unicode__(self):
        return u'ID: {0}, Source: {1} ({2})'.format(self.id, self.source_of_client_prices, self.basis)


def analysis_detail_hash(label, quantity, rate, vendor_rate_bucket, vendor_rate_basis_target, vendor_rate_expansion_rate, price, client_price_bucket, client_price_basis_target, client_price_expansion_rate):

    if not vendor_rate_basis_target:
        vendor_rate_expansion_rate = 1.0

    if not client_price_basis_target:
        client_price_expansion_rate = 1.0

    unit_cost = float(rate) * float(vendor_rate_bucket) * float(vendor_rate_expansion_rate)
    total_cost = float(rate) * float(vendor_rate_bucket) * float(vendor_rate_expansion_rate) * float(quantity)
    total_price = float(price) * float(client_price_bucket) * float(client_price_expansion_rate) * float(quantity)

    if not quantity:
        return None
    return {
        'label': label,
        'unit_cost': unit_cost,
        'quantity': quantity,
        'total_cost': total_cost,
        'unit_price': price,
        'total_price': total_price,
        'gross_margin': "{0:.2f}%".format(((float(total_price) - float(total_cost)) / (float(total_price) + 0.00001)) * 100),
    }


class TranslationTask(Task):
    analysis = models.ForeignKey(TranslationTaskAnalysis, null=True)
    vendor_rates = models.OneToOneField(TranslationTaskVendorRates, null=True)
    client_price = models.OneToOneField(TranslationTaskClientPrice, null=True)

    def set_assigned_to(self, assignee=None):
        self.assigned_to = assignee
        self.save()

    @property
    def files(self):
        # returns a list of file pairs each containing a file input and file output
        # TranslationTask always returns a list of length 1
        # It's a list so it's polymorphic with nontranslation task
        # TODO DGF 2013-10-24: give 'trans_kit' and 'la' a common name
        # to make them polymorphic for easier uploading templates
        f = {}
        if self.trans_kit.input_file:
            f['input'] = {
                'file': self.trans_kit.input_file,
                'name': self.trans_kit.input_file_name,
                'url': reverse(
                    'download_tasklocaletranslationkit_in_file',
                    kwargs={'task_id': self.id,
                            'tltk_id': self.trans_kit.id}
                ),
            }
        if self.trans_kit.output_file:
            f['output'] = {
                'file': self.trans_kit.output_file,
                'name': self.trans_kit.output_file_name,
                'url': reverse(
                    'download_tasklocaletranslationkit_out_file',
                    kwargs={'task_id': self.id,
                            'tltk_id': self.trans_kit.id}
                ),
            }
        if self.trans_kit.support_file:
            f['support'] = {
                'file': self.trans_kit.support_file,
                'name': self.trans_kit.support_file_name,
                'url': reverse(
                    'download_tasklocaletranslationkit_sup_file',
                    kwargs={'task_id': self.id,
                            'tltk_id': self.trans_kit.id}
                ),
            }
        f['trans_kit'] = self.trans_kit           

        return [f]

    def get_quantity(self):
        if self.analysis:
            return self.analysis.total_wordcount()
        return None

    def is_valid(self):
        # PRICE CHECK
        # is not billable, skip price check
        if not self.billable:
            return True
        # is billable, check price
        elif self.analysis and self.client_price and self.client_price.is_valid():
            return True

        return False

    def is_workflow_ready(self):
        if self.assigned_to and \
                (not self.billable or
                    (self.vendor_rates and self.vendor_rates.is_valid() and
                        self.analysis and
                        self.client_price and self.client_price.is_valid())):
            return True
        return False

    def total_price(self):
        raw_price = 0.000001

        if not self.analysis:
            return None
        elif not self.client_price:
            return float(raw_price)

        return float(self.client_price.total_price())  # TODO: decimalize cost

    def itemized_price_details(self, multiplier=Decimal(1)):
        if not self.client_price:
            logger.warning("%s.itemized_price_details called but %s has no client_price",
                           self.__class__.__name__, self)
            return []

        return self.client_price.itemized_price_details(multiplier)

    def total_cost(self):
        raw_cost = 0.000001

        if not self.analysis or not self.assigned_to:
            return None
        elif not self.vendor_rates:
            return float(raw_cost)

        return float(self.vendor_rates.total_cost())  # TODO: decimalize cost

    def itemized_cost_details(self):
        if not self.vendor_rates:
            logger.warning("%s.itemized_cost_details called but %s has no vendor_rates",
                           self.__class__.__name__, self)
            return []
        return self.vendor_rates.itemized_cost_details()

    def detail_rows(self):
        vendor_cost_basis_target = self.is_vendor_cost_basis_target()
        vendor_rate_expansion_rate = 1.0  # todo get expansion rate for vendors
        client_price_basis_target = self.is_client_price_basis_target()
        client_price_expansion_rate = self.client_price.expansion_rate

        if self.vendor_rates and self.client_price:
            return filter(bool, [analysis_detail_hash(l, getattr(self.analysis, f, 0), self.vendor_rates.word_rate, getattr(self.vendor_rates, f, 0.0), vendor_cost_basis_target, vendor_rate_expansion_rate, self.client_price.word_rate, getattr(self.client_price, f, 0.0), client_price_basis_target, client_price_expansion_rate) for f, l in ANALYSIS_FIELD_NAMES_LABELS])

    def field_wordcount_list(self):
        return self.analysis.field_wordcount_list()

    def set_from_vendor_rate(self, rate):
        if not self.vendor_rates:
            self.vendor_rates = TranslationTaskVendorRates.objects.create(source_of_vendor_rates=rate.id,
                                                                          basis=rate.basis)
            self.save()
        else:
            self.vendor_rates.source_of_vendor_rates = rate.id

        self.vendor_rates.minimum = rate.minimum
        for field in (list(ANALYSIS_FIELD_NAMES) + ['minimum', 'word_rate']):
            setattr(self.vendor_rates, field, getattr(rate, field))
        self.vendor_rates.save()
        return True

    def set_from_client_price(self, price):
        """
        :type price: prices.models.ClientTranslationPrice
        """
        my_price = self.client_price or TranslationTaskClientPrice()
        my_price.source_of_client_prices = price.id
        my_price.basis = price.basis
        my_price.expansion_rate = price.service.expansion_rate
        my_price.word_rate = price.word_rate

        manifest = self.project.client.manifest
        if self.project.is_restricted_job:
            my_price.word_rate = my_price.word_rate + my_price.word_rate*manifest.restricted_pricing

        client_specific = price.client is not None

        for field in ANALYSIS_FIELD_NAMES:
            price_field = None

            if not manifest.pricing_memory_bank_discount:
                price_field = 1  # client does not get MBD, reset to 100% of word_rate
            else:
                if not client_specific:
                    price_field = getattr(manifest, field)

                if price_field is None:
                    price_field = getattr(price, field)

            setattr(my_price, field, price_field)

        # Minimum price from the manifest overrides a
        # ClientTranslationPrice.minimum_price if CTP.client is not set.
        if not client_specific and manifest.minimum_price is not None:
            my_price.minimum_price = manifest.minimum_price
        else:
            my_price.minimum_price = price.minimum_price

        my_price.save()

        if not self.client_price:
            self.client_price = my_price
            self.save()

        return True

    def can_be_completed(self):
        return (self.is_active() and self.trans_kit and
                self.trans_kit.output_file)

    def is_translation(self):
        return True

    def has_input_file(self):
        return self.trans_kit.input_file if self.trans_kit else False

    def is_client_price_basis_target(self):
        client_basis = self.client_price.basis
        # return client_basis and client_basis.code == TARGET_BASIS
        return client_basis and client_basis.is_basis_target()

    def is_vendor_cost_basis_target(self):
        vendor_basis = self.vendor_rates.basis if self.vendor_rates else None
        # return vendor_basis and vendor_basis.code == TARGET_BASIS
        return vendor_basis and vendor_basis.is_basis_target()

    def is_minimum_vendor(self):
        try:
            return self.vendor_rates.minimum >= self.total_cost() if self.vendor_rates else False
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            print tb
            mail_admins('[TranslationTask.is_minimum_vendor()]: failed', 'task = {0}.\n{1}'.format(self, tb))
            return False

    def is_minimum_client(self):
        try:
            return self.client_price.minimum_price >= self.total_price() if self.client_price else False
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            print tb
            mail_admins('[TranslationTask.is_minimum_client()]: failed', 'task = {0}.\n{1}'.format(self, tb))
            return False

    def delete_task(self):
        try:
            if self.analysis:
                self.analysis.delete()
            if self.client_price:
                self.client_price.delete()
            if self.vendor_rates:
                self.vendor_rates.delete()

            if self.predecessor:
                try:
                    child_task = Task.objects.get(predecessor=self.id)
                    child_task.predecessor = self.predecessor
                    child_task.save()
                except:
                    pass

            self.delete()
            return True
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            print tb
            mail_admins('[TranslationTask.delete_task()]: failed', 'task = {0}.\n{1}'.format(self, tb))
            return False


class NonTranslationTask(Task):
    formula = models.ForeignKey(PricingFormula, blank=True, null=True, related_name='+')
    quantity = models.DecimalField(max_digits=19, decimal_places=2, blank=True, null=True)
    unit_cost = CurrencyField(blank=True, null=True)
    unit_price = CurrencyField(blank=True, null=True)
    price_is_percentage = models.BooleanField(default=False)
    vendor_minimum = CurrencyField(null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=19, decimal_places=2, blank=True, null=True)

    def set_assigned_to(self, assignee=None):
        self.assigned_to = assignee
        self.save()

    @property
    def files(self):
        # returns a list of file pairs each containing a file input and file output
        # TODO DGF 2013-10-24: give 'trans_kit' and 'la' a common name
        # to make them polymorphic for easier uploading templates
        result = []
        for la in self.localized_assets.all():
            f = {}

            if la.input_file:
                f['input'] = {
                    'file': la.input_file,
                    'name': la.input_file_name(),
                    'url': reverse(
                        'download_tasklocalizedasset_in_file',
                        kwargs={'task_id': self.id,
                                'tla_id': la.id}
                    ),
                }
            if la.output_file:
                f['output'] = {
                    'file': la.output_file,
                    'name': la.output_file_name(),
                    'url': reverse(
                        'download_tasklocalizedasset_out_file',
                        kwargs={'task_id': self.id,
                                'tla_id': la.id}
                    ),
                }
            if la.support_file:
                f['support'] = {
                    'file': la.support_file,
                    'name': la.support_file_name(),
                    'url': reverse(
                        'download_tasklocalizedasset_sup_file',
                        kwargs={'task_id': self.id,
                                'tla_id': la.id}
                    ),
                }
            result.append(f)
            f['la'] = la

        return result

    def get_quantity(self):
        return self.quantity

    def total_cost(self):

        if not self.assigned_to:
            if self.unit_cost and self.quantity:
                total = self.unit_cost * self.quantity
                return Decimal(total)
            else:
                return None

        total = 0
        if self.unit_cost and self.quantity:
            total = self.unit_cost * self.quantity
        if self.vendor_minimum > total:
            return Decimal(self.vendor_minimum)
        if not total:
            total = 0.000001
        return Decimal(total)

    # noinspection PyMethodOverriding
    def itemized_cost_details(self):
        """Cost per source file.

        So we fudge more here, and instead of building up a predictable
        list of line items and using their sum as the cost, we use the
        price for the whole kit and then work backwards to see how much
        each document is in proportion.

        At the moment, all quantities-of-work scale linearly with word count
        and are the same for all document types, so at least the math is simple.

        :rtype: [TranslationTaskItemPrice]
        """
        return self._itemized_cost_details(self.project.kit, self.service.target)

    def _itemized_cost_details(self, kit, target):
        # fudging!
        total_cost = self.total_cost()

        if total_cost is None:
            return []

        word_counts = []

        for asset in kit.source_files():
            # not that target much matters, as we only need the total word count
            analysis = asset.analysis_for_target(target)

            word_count = analysis.total_wordcount()
            word_counts.append((analysis, word_count))

        if not word_counts:
            return [TranslationTaskItemPrice(None, total_cost, total_cost, 0)]

        total_words = sum(word_count for asset, word_count in word_counts)

        costs = []

        for analysis, word_count in word_counts:
            if total_words:
                cost = total_cost * word_count / total_words
            else:
                # No sources had word counts; distribute the price evenly.
                cost = total_cost / len(word_counts)
            cost = cost.quantize(TWO_PLACES)
            costs.append(TranslationTaskItemPrice(analysis, cost, cost, 0))

        if len(costs) > 1:
            # may be off by a bit due to cumulative rounding error
            summed_cost = sum(cost.net for cost in costs)
            rounding_error = total_cost - summed_cost
            assert rounding_error < 1, ("Rounding error over a dollar: "
                                        "task %s cost amount %s" %
                                        (self.id, rounding_error))
            if rounding_error:
                # tack it on to the last
                costs[-1] = TranslationTaskItemPrice(
                    costs[-1].analysis,
                    costs[-1].net + rounding_error,
                    costs[-1].raw + rounding_error,
                    costs[-1].mbd
                )

        return costs

    def can_be_completed(self):
        if (self.is_active() and
                not self.localized_assets.filter(output_file='').exists()):
            return True
        else:
            return False

    def standard_price(self, multiplier=Decimal(1)):
        if self.price_is_percentage:
            # raise ValueError("%r.standard_price called but price_is_percentage" % (self,))
            return None
        if self.unit_price and self.quantity:
            total = self.unit_price * self.quantity * multiplier
            return total.quantize(TWO_PLACES)

    # noinspection PyMethodOverriding
    def itemized_price_details(self, multiplier):
        """Price per source file.

        ClientNonTranslationPrice has no minimum_price, but "quantity" is
        discrete, i.e. we don't bill "1.37 hours," we bill "2 hours."
        I don't think anyone can complain if we round each file in each
        translation task to the nearest whole word count, rounding each file up
        to the nearest _hour_ would change prices a lot.

        And while it seems okay to me to include a line item that says
        "minimum fee" if you've submitted a small job, we can't really
        make line items that say "minimum fraction of an hour." Especially
        because it applies to clients who don't otherwise have minimums.

        So we fudge more here, and instead of building up a predictable
        list of line items and using their sum as the price, we use the
        price for the whole kit and then work backwards to see how much
        each document is in proportion.

        At the moment, all quantities-of-work scale linearly with word count
        and are the same for all document types, so at least the math is simple.

        :rtype: [TranslationTaskItemPrice]
        """
        return self._itemized_price_details(
            self.project.kit, self.service.target, multiplier)

    def _itemized_price_details(self, kit, target, multiplier, percent_price=None):
        if percent_price:
            total_price = percent_price
        else:
            total_price = self.standard_price(multiplier)

        if total_price is None:
            return []

        word_counts = []

        for asset in kit.source_files():
            # not that target much matters, as we only need the total word count
            analysis = asset.analysis_for_target(target)

            word_count = analysis.total_wordcount()
            word_counts.append((analysis, word_count))

        if not word_counts:
            # price, but no source files?  MINIMUM_JOB_SURCHARGE is not quite
            # what we mean; fix that if this is ever anything but a bizarre
            # corner case.
            return [TranslationTaskItemPrice(MINIMUM_JOB_SURCHARGE, total_price, total_price, 0)]

        total_words = sum(word_count for asset, word_count in word_counts)

        prices = []

        for analysis, word_count in word_counts:
            if total_words:
                price = total_price * word_count / total_words
            else:
                # No sources had word counts; distribute the price evenly.
                price = total_price / len(word_counts)
            price = price.quantize(TWO_PLACES)
            prices.append(TranslationTaskItemPrice(analysis, price, price, 0))

        if len(prices) > 1:
            # may be off by a bit due to cumulative rounding error
            summed_price = sum(price.net for price in prices)
            rounding_error = total_price - summed_price
            assert rounding_error < 1, ("Rounding error over a dollar: "
                                        "task %s amount %s" %
                                        (self.id, rounding_error))
            if rounding_error:
                # tack it on to the last
                prices[-1] = TranslationTaskItemPrice(
                    prices[-1].analysis,
                    prices[-1].net + rounding_error,
                    prices[-1].raw + rounding_error,
                    prices[-1].mbd
                )

        return prices

    def is_valid(self):
        # PRICE CHECK
        # is not billable, skip price check
        if not self.billable:
            return True
        # is billable, check price
        elif self.unit_price:
            return True

        return False

    def is_workflow_ready(self):
        if not self.assigned_to:
            return False
        elif (not self.billable or
           (self.unit_price and self.unit_cost)):
            return True
        else:
            return False

    def is_translation(self):
        return False

    def has_input_file(self):
        la = self.localized_assets
        return la.count() > 0 and not la.filter(input_file='').exists()

    def is_minimum_vendor(self):
        return self.vendor_minimum >= self.total_cost()

    def is_minimum_client(self):
        return self.client_price.minimum_price >= self.total_price()

    def detail_rows(self):
        return None

    def set_from_vendor_rate(self, rate):
        if rate is None:
            if self.is_project_management_percent():
                self.unit_cost = settings.PM_PERCENT_UNIT_COST_CALC
                self.save()
                return True
            elif self.service.service_type.code == DISCOUNT_SERVICE_TYPE:
                return False
            else:
                self.unit_cost = settings.NON_TRANSLATION_DEFAULT_COST
                self.save()
                return True
        elif rate.unit_cost and not self.unit_cost == rate.unit_cost:
            self.unit_cost = rate.unit_cost
            self.save()
            return True
        return False

    def set_from_client_price(self, price):
        is_percent = price.service.is_percent()
        change = self.price_is_percentage != is_percent

        if price.unit_price:
            change = change or (self.unit_price != price.unit_price)

        if change:
            self.price_is_percentage = is_percent

            if is_percent and self.unit_price:
                self.unit_price = self.unit_price
            else:
                self.unit_price = price.unit_price
            self.save()

        return change

    def delete_task(self):
        try:
            if self.predecessor:
                try:
                    child_task = Task.objects.get(predecessor=self.id)
                    child_task.predecessor = self.predecessor
                    child_task.save()
                except:
                    pass

            self.delete()
            return True
        except:
            import traceback
            tb = traceback.format_exc()  # NOQA
            print tb
            mail_admins('[NonTranslationTask.delete_task()]: failed', 'task = {0}.\n{1}'.format(self, tb))
            return False

    def __unicode__(self):
        return u'{0}: {1} {2}(s) from {3} to {4}'.format(self.service.service_type, self.quantity, self.service.unit_of_measure, self.service.source, self.service.target)


# these get_*_asset_path functions have a signature that fits
# FileField.upload_to: f(instance, filename) -> path
def get_task_asset_path(task, filename, in_or_out):
    service = task.service
    task_type = service.service_type.code
    return posixpath.join(
        'projects', str(task.project.id), str(service.target.lcid),
        slugify(task_type), in_or_out, filename)


def get_task_input_asset_path(instance, filename):
    return get_task_asset_path(instance.task, filename, 'in')


def get_task_output_asset_path(instance, filename):
    return get_task_asset_path(instance.task, filename, 'out')


def get_task_support_asset_path(instance, filename):
    return get_task_asset_path(instance.task, filename, 'sup')


def get_task_post_delivery_asset_path(instance, filename):
    return get_task_asset_path(instance.task, filename, 'post')


class TaskLocalizedAsset(CircusModel):
    """ used by dtp task or final delivery to track the set of translated files in final format """
    task = models.ForeignKey(Task, related_name='localized_assets')
    name = models.CharField(max_length=255, blank=True, null=True)
    input_file = models.FileField(max_length=settings.FULL_FILEPATH_LENGTH, upload_to=get_task_input_asset_path, null=True, blank=True)
    output_file = models.FileField(max_length=settings.FULL_FILEPATH_LENGTH, upload_to=get_task_output_asset_path, null=True, blank=True)
    support_file = models.FileField(max_length=settings.FULL_FILEPATH_LENGTH, upload_to=get_task_support_asset_path, null=True, blank=True)
    source_asset = models.ForeignKey(FileAsset, null=True, blank=True)
    downloaded = models.DateTimeField(blank=True, null=True)
    post_delivery_file = models.FileField(max_length=settings.FULL_FILEPATH_LENGTH, upload_to=get_task_post_delivery_asset_path, null=True, blank=True)
    post_delivery_notes = models.TextField(_('Post-Delivery Comments'), blank=True, null=True)
    current_user = models.IntegerField(blank=True, null=True)
    via_approved = models.BooleanField(default=False)

    def file_name(self, in_or_out):
        val = getattr(self, in_or_out + '_file')
        if val:
            # noinspection PyUnresolvedReferences
            head, tail = posixpath.split(val.name)
            return tail or posixpath.basename(head)
        return u''

    def input_file_name(self):
        return self.file_name('input')

    def output_file_name(self):
        return self.file_name('output')

    def support_file_name(self):
        return self.file_name('support')

    def post_delivery_file_name(self):
        return self.file_name('post_delivery')

    def is_via_approved(self):
        return self.via_approved

    def via_final_approval_upload_form(self):
        # todo this method should be moved to a template tag
        # not so good to have this in the model...
        redirect = reverse('via_final_approval_replace_delivery', args=(self.id,))

        asset_path = settings.MEDIA_URL[1:] + get_task_output_asset_path(
            self, '${filename}')

        return S3UploadForm(asset_path, settings.BASE_URL + redirect)

    def via_post_delivery_upload_form(self):
        # todo this method should be moved to a template tag
        # not so good to have this in the model...
        redirect = reverse('via_post_delivery_replace_delivery', args=(self.id,))

        asset_path = settings.MEDIA_URL[1:] + get_task_post_delivery_asset_path(
            self, '${filename}')

        return S3UploadForm(asset_path, settings.BASE_URL + redirect)

    def client_post_delivery_upload_form(self):
        # todo this method should be moved to a template tag
        # not so good to have this in the model...
        redirect = reverse('client_post_delivery_replace_delivery', args=(self.id,))

        asset_path = settings.MEDIA_URL[1:] + get_task_post_delivery_asset_path(
            self, '${filename}')

        return S3UploadForm(asset_path, settings.BASE_URL + redirect)

    def vendor_tla_upload_form(self):
        # todo this method should be moved to a template tag
        # not so good to have this in the model...
        redirect = reverse('vendor_tla_delivery_complete',
                           kwargs={'pk': self.task.id, 'tla_id': self.id})

        asset_path = settings.MEDIA_URL[1:] + get_task_output_asset_path(
            self, '${filename}')

        return S3UploadForm(asset_path, settings.BASE_URL + redirect)

    def via_tla_upload_form(self):
        # todo this method should be moved to a template tag
        # not so good to have this in the model...
        redirect = reverse('via_tla_delivery_complete', args=(self.id,))

        asset_path = settings.MEDIA_URL[1:] + get_task_output_asset_path(
            self, '${filename}')

        return S3UploadForm(asset_path, settings.BASE_URL + redirect)
    
    def via_tla_input_upload_form(self):
        # todo this method should be moved to a template tag
        # not so good to have this in the model...
        redirect = reverse('via_tla_input_delivery_complete', args=(self.id,))

        asset_path = settings.MEDIA_URL[1:] + get_task_input_asset_path(
            self, '${filename}')

        return S3UploadForm(asset_path, settings.BASE_URL + redirect)

    #Method to handle new support files upload functionality for non translation files for via
    def via_tlasf_upload_form(self):
        # todo this method should be moved to a template tag
        # not so good to have this in the model...
        redirect = reverse('via_tlasf_delivery_complete',
                           kwargs={'pk': self.task.id, 'tla_id': self.id})

        asset_path = settings.MEDIA_URL[1:] + get_task_support_asset_path(
            self, '${filename}')

        return S3UploadForm(asset_path, settings.BASE_URL + redirect)

    #Method to handle new support files upload functionality for non translation files
    def vendor_tlasf_upload_form(self):
        # todo this method should be moved to a template tag
        # not so good to have this in the model...
        redirect = reverse('vendor_tlasf_delivery_complete',
                           kwargs={'pk': self.task.id, 'tla_id': self.id})

        asset_path = settings.MEDIA_URL[1:] + get_task_support_asset_path(
            self, '${filename}')

        return S3UploadForm(asset_path, settings.BASE_URL + redirect)


class TaskLocaleTranslationKit(CircusModel):
    task = models.OneToOneField(Task, related_name='trans_kit')
    input_file = models.FileField(max_length=settings.FULL_FILEPATH_LENGTH, upload_to=get_task_input_asset_path, null=True, blank=True)
    output_file = models.FileField(max_length=settings.FULL_FILEPATH_LENGTH, upload_to=get_task_output_asset_path, null=True, blank=True)
    support_file = models.FileField(max_length=settings.FULL_FILEPATH_LENGTH, upload_to=get_task_output_asset_path, null=True, blank=True)
    tm_update_file = models.FileField(max_length=settings.FULL_FILEPATH_LENGTH, upload_to=get_task_output_asset_path, null=True, blank=True)
    tm_file_updated_at = models.DateTimeField(blank=True, null=True)
    current_user = models.IntegerField(blank=True, null=True)

    def file_name(self, in_or_out):
        val = getattr(self, in_or_out + '_file')
        if val:
            # noinspection PyUnresolvedReferences
            head, tail = posixpath.split(val.name)
            return tail or posixpath.basename(head)
        return u''

    def input_file_name(self):
        return self.file_name('input')

    def output_file_name(self):
        return self.file_name('output')
    
    def support_file_name(self):
        return self.file_name('support')

    def tm_update_file_name(self):
        return self.file_name('tm_update')

    def can_dvx_import(self):
        task = self.task
        ltk = LocaleTranslationKit.objects.get(
            kit__project__task=task,
            target_locale__services_as_target=self.task.service)
        return bool(ltk.analysis_code)

    def vendor_tltk_upload_form(self):
        # todo this method should be moved to a template tag
        # not so good to have this in the model...
        redirect = reverse('vendor_tltk_delivery_complete',
                           kwargs={'pk': self.task.id, 'tltk_id': self.id})

        asset_path = settings.MEDIA_URL[1:] + get_task_output_asset_path(
            self, '${filename}')

        return S3UploadForm(asset_path, settings.BASE_URL + redirect)

    def vendor_tltk_input_upload_form(self):
        # todo this method should be moved to a template tag
        # not so good to have this in the model...
        redirect = reverse('vendor_tltk_input_delivery_complete',
                           kwargs={'pk': self.task.id, 'tltk_id': self.id })

        asset_path = settings.MEDIA_URL[1:] + get_task_output_asset_path(
            self, '${filename}')

        return S3UploadForm(asset_path, settings.BASE_URL + redirect)

    #Method to handle new support files upload functionality for via
    def via_tlsf_upload_form(self):
        # todo this method should be moved to a template tag
        # not so good to have this in the model...
        redirect = reverse('via_tlsf_delivery_complete',
                           kwargs={'pk': self.task.id, 'tltk_id': self.id})

        asset_path = settings.MEDIA_URL[1:] + get_task_support_asset_path(
            self, '${filename}')

        return S3UploadForm(asset_path, settings.BASE_URL + redirect)

    # Method to handle new support files upload functionality
    def vendor_tlsf_upload_form(self):
        # todo this method should be moved to a template tag
        # not so good to have this in the model...
        redirect = reverse('vendor_tlsf_delivery_complete',
                           kwargs={'pk': self.task.id, 'tltk_id': self.id})

        asset_path = settings.MEDIA_URL[1:] + get_task_support_asset_path(
            self, '${filename}')

        return S3UploadForm(asset_path, settings.BASE_URL + redirect)

    def via_tltk_upload_form(self):
        # todo this method should be moved to a template tag
        # not so good to have this in the model...
        redirect = reverse('via_tltk_delivery_complete', args=(self.id,))

        asset_path = settings.MEDIA_URL[1:] + get_task_output_asset_path(
            self, '${filename}')

        return S3UploadForm(asset_path, settings.BASE_URL + redirect)

    # Method to handle new TM update file
    def via_tm_file_upload_form(self):
        # todo this method should be moved to a template tag
        # not so good to have this in the model...
        redirect = reverse('via_tm_file_delivery_complete', args=(self.id,))

        asset_path = settings.MEDIA_URL[1:] + get_task_output_asset_path(
            self, '${filename}')

        return S3UploadForm(asset_path, settings.BASE_URL + redirect)


class VendorPurchaseOrder(CircusModel):
    vendor = models.ForeignKey(Vendor)
    task = models.OneToOneField(Task, related_name='po')
    po_number = models.IntegerField(blank=True, null=True)
    status = models.CharField(choices=PO_STATUS, max_length=40, default=PO_OPEN_STATUS)
    notes = models.TextField(blank=True, null=True)
    due = models.DateTimeField(blank=True, null=True)
    paid = models.BooleanField(default=False)
    acct_purchaseorder_txn_id = models.CharField(max_length=50, blank=True, null=True)
    acct_bill_txn_id = models.CharField(max_length=50, blank=True, null=True)

    def total_cost(self):
        return self.task.total_cost()

    def number(self):
        return self.po_number

    def description(self):
        return self.task.service.service_type
