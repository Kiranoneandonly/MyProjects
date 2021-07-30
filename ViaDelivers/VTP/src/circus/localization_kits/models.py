from functools import partial
import logging
import posixpath
from celery import shared_task

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.db import models

from matches.models import AnalysisFields, ANALYSIS_FIELD_NAMES
from services.models import Locale, DocumentType
from shared.models import CircusModel
from django.contrib.messages import ERROR, WARNING, SUCCESS


SOURCEFILE_ASSET = 'source'
REFERENCEFILE_ASSET = 'reference'
PLACEHOLDERFILE_ASSET = 'placeholder'

logger = logging.getLogger('circus.' + __name__)


def get_project_asset_path(instance, filename, prepared=False):
    from projects.models import Project
    project_id = ''
    if isinstance(instance, FileAsset):
        project_id = instance.project_id()
    elif isinstance(instance, LocalizationKit):
        project_id = instance.project.id
    elif isinstance(instance, Project):
        project_id = instance.id

    subdir = str(instance.id)
    if prepared:
        subdir += '-prep'
    return posixpath.join('projects', str(project_id), 'assets', subdir, filename)


def get_project_prepared_asset_path(instance, filename):
    return get_project_asset_path(instance, filename, prepared=True)


class LocalizationKit(CircusModel):
    notes = models.TextField(blank=True, null=True)
    analysis_code = models.CharField(blank=True, null=True, max_length=24)
    analysis_started = models.DateTimeField(blank=True, null=True)
    analysis_completed = models.DateTimeField(blank=True, null=True)
    tm_update_started = models.DateTimeField(blank=True, null=True)
    tm_update_completed = models.DateTimeField(blank=True, null=True)
    is_manually_updated = models.BooleanField(_('staff status'), default=False)

    # files = ForeignKey on FileAsset

    # flag to prevent overlapping analysis runs
    obsolete_analyzing = models.BooleanField(default=False, db_column='analyzing')

    def __unicode__(self):
        try:
            return u'{0.project.id}, {0.project.job_number}, {0.id}, {0.analysis_code}, {0.project.source_locale}'.format(self)
        except:
            return unicode(self.id)

    def analyzing(self):
        from projects.models import BackgroundTask
        return BackgroundTask.objects.currently_analyzing(self.project)

    def pretranslating(self):
        from projects.models import BackgroundTask
        return BackgroundTask.objects.currently_pretranslating(self.project)

    def prepping(self):
        from projects.models import BackgroundTask
        return BackgroundTask.objects.currently_prepping(self.project)

    def pretranslating_or_prepping(self):
        return self.prepping() or self.pretranslating()

    def source_files(self):
        """
        :rtype: QuerySet[FileAsset]
        """
        return self.files.filter(asset_type=SOURCEFILE_ASSET).order_by('orig_name')

    def placeholder_files(self):
        return self.files.filter(asset_type=PLACEHOLDERFILE_ASSET).order_by('orig_name')

    def source_and_placeholder_files(self):
        return self.files.filter(Q(asset_type=SOURCEFILE_ASSET) |
                                 Q(asset_type=PLACEHOLDERFILE_ASSET)).order_by('orig_name')

    def analysis_files(self):
        return FileAnalysis.objects.filter(asset__kit=self).order_by('asset')

    def clear_analysis(self):
        from localization_kits import make_kit_analysis
        self.delete_analysis_files()
        self.placeholder_files().delete()
        make_kit_analysis.make_project_loc_kit_analysis(self.project)
        return SUCCESS, u"Estimate > Analysis has been cleared"

    def delete_analysis_files(self):
        for asset in self.files.all():
            asset.fileanalysis_set.all().delete()

    def delete_localetranslationkits(self):
        return self.localetranslationkit_set.all().delete()

    def remove_localetranslationkits__translation_file(self):
        for ltk in self.localetranslationkit_set.all():
            ltk.remove_translation_file_analysis_code()

    def reference_files(self):
        return self.files.filter(asset_type=REFERENCEFILE_ASSET)

    def queue_analysis_tasks(self, callback=None, errback=None):
        from projects.models import BackgroundTask
        from localization_kits.engine import analyze_kit, analyze_kit_v2
        from projects.models import translation_task_remove_current_files

        self.remove_analysis_code()
        translation_task_remove_current_files(self.project.id)

        if settings.VIA_DVX_API_VERSION == 1:
            sig = analyze_kit.subtask((self.id,), {'callback': callback},
                                      link_error=errback)
            return BackgroundTask.objects.start(
                BackgroundTask.ANALYSIS, self.project, sig)
        elif settings.VIA_DVX_API_VERSION == 2:
            return BackgroundTask.objects.start_with_callback(
                BackgroundTask.ANALYSIS, self.project,
                partial(analyze_kit_v2, self), callback, errback
            )
        else:
            raise ImproperlyConfigured("Bad VIA_DVX_API_VERSION %r for "
                                       "queue_analysis_tasks" %
                                       (settings.VIA_DVX_API_VERSION,))

    def queue_pre_translation(self, call_prep_kit=False, callback=None, target=None):
        from projects.models import BackgroundTask
        from localization_kits.engine import pre_translate_kit_v2

        if BackgroundTask.objects.currently_pretranslating(self.project):
            logger.warn(
                u"project %s#%s kit#%s.queue_pre_translation: pretranslate already in progress, skipping." %
                (self.project.job_number, self.project.id, self.id))
            return None

        if not self.has_analysis_code():
            logger.warn(
                u"project %s#%s kit#%s.queue_pre_translation: no analysis_code, skipping." %
                (self.project.job_number, self.project.id, self.id))
            return None

        if settings.VIA_DVX_API_VERSION == 1:
            return self.queue_prep_kit(self, lk_id=None, callback=callback)
        elif settings.VIA_DVX_API_VERSION == 2:
            target_id = target.id if target else None
            callback_2 = self.queue_prep_kit.si(None, self.id, callback, target_id) if call_prep_kit else callback
            return BackgroundTask.objects.start_with_callback(
                BackgroundTask.PRE_TRANSLATE, self.project, partial(pre_translate_kit_v2, self), callback_2
            )
        else:
            raise ImproperlyConfigured("Bad VIA_DVX_API_VERSION %r for queue_pre_translation" %
                                       (settings.VIA_DVX_API_VERSION,))

    def remove_analysis_code(self):
        self.analysis_code = None
        self.analysis_started = None
        self.analysis_completed = None
        self.save()
        return self.analysis_code is None

    def has_analysis_code(self):
        return bool(self.analysis_code and self.analysis_code.strip())

    def is_tm_not_updated(self):
        return self.tm_update_completed is None

    @shared_task
    def queue_prep_kit(self, lk_id=None, callback=None, target_id=None):
        from projects.models import BackgroundTask
        from localization_kits.engine import prep_kit, prep_kit_v2
        from services.models import ServiceType
        from vendors.models import VendorManifest

        kit = LocalizationKit.objects.get(id=lk_id) if lk_id else self

        if BackgroundTask.objects.currently_prepping(kit.project) and target_id is None:
            logger.warn(
                u"project %s#%s kit#%s.queue_prep_kit: prep_kit already in progress, skipping." %
                (kit.project.job_number, kit.project.id, kit.id))
            return None

        if not kit.analysis_code:
            logger.warn(
                u"project %s#%s kit#%s.queue_prep_kit: no analysis_code, skipping." %
                (kit.project.job_number, kit.project.id, kit.id))
            return None

        if settings.VIA_DVX_API_VERSION == 1:
            sig = prep_kit.subtask((kit.id,), {'callback': callback})
            return BackgroundTask.objects.start(
                BackgroundTask.PREP_KIT, kit.project, sig)

        elif settings.VIA_DVX_API_VERSION == 2:
            tasks_list = None
            if target_id:
                tasks_list = list(kit.project.all_workflow_translation_tasks_target(target_id))
            else:
                tasks_list = list(kit.project.all_workflow_translation_tasks())

            if tasks_list:
                for task in tasks_list:
                    callback['tlang'] = task.service.target.description
                    kit.tep_task = task
                    BackgroundTask.objects.start_with_callback(BackgroundTask.PREP_KIT, kit.project, partial(prep_kit_v2, kit), callback)
                del tasks_list
                return True
            else:
                del tasks_list
                return False
        else:
            raise ImproperlyConfigured("Bad VIA_DVX_API_VERSION %r for queue_prep_kit" % (settings.VIA_DVX_API_VERSION,))

    def file_count(self):
        return self.files.all().count()

    def localetranslationkit_files(self):
        return self.localetranslationkit_set.all().order_by('target_locale')

    def is_valid_for_start(self):
        valid_for_quote = self.is_valid_for_quote()
        lockit_is_valid = self.ltk_is_valid()
        return valid_for_quote and lockit_is_valid

    def is_valid_for_quote(self):
        """A quote requires analyses but no LocaleTranslationKits."""
        files = self.source_files()
        ph_files = self.placeholder_files().exists()
        return (not ph_files and
                files.count() and
                all(f.is_valid() for f in files))

    def ltk_is_valid(self):
        ltk_locales = self.localetranslationkit_set.values_list('target_locale_id', flat=True)
        targets = self.project.target_locales.values_list('id', flat=True)
        ltk_exists_for_all_targets = set(ltk_locales) == set(targets)
        ltk_translation_files_exists = all(ltk.is_valid() for ltk in self.localetranslationkit_set.all())
        return (ltk_exists_for_all_targets and
                ltk_translation_files_exists)

    def can_auto_estimate_doctype(self, semiauto=False):
        for asset in self.source_files():
            name = asset.prepared_name or asset.orig_name
            doctype = name.rsplit('.', 1)[-1].strip().lower()

            auto_estimate_doctype = DocumentType.objects.filter(code=doctype)

            if semiauto:
                auto_estimate_doctype = auto_estimate_doctype.filter(can_semiauto_estimate=True)
            else:
                auto_estimate_doctype = auto_estimate_doctype.filter(can_auto_estimate=True)

            if not auto_estimate_doctype.exists():
                return False
        return True

    def can_auto_estimate_locale(self, semiauto=False):
        no_auto_estimate_source_locale = Locale.objects.filter(
            lcid=self.project.source_locale.lcid,
            if_source_no_auto_estimate=True,
            is_deleted=False,
            available=True).count()

        if no_auto_estimate_source_locale:
            return False

        if self.project.target_locales_count() > settings.LANGUAGE_COUNT_MAX_TO_AUTO_ESTIMATE:
            return False

        if not semiauto:
            if self.project.target_locales.filter(if_target_no_auto_estimate=True).exists():
                return False

        return True

    def can_auto_estimate(self, semiauto=False):
        return (self.can_auto_estimate_doctype(semiauto) and
                self.can_auto_estimate_locale(semiauto))

    def can_auto_prep_kit(self):
        return (self.can_auto_estimate_doctype(True) and
                self.can_auto_estimate_locale(True) and
                self.has_analysis_code())

    def has_any_translation_completed(self):
        already_complete = any((task.is_translation() and task.is_complete())
                               for task in self.project.all_workflow_tasks())
        return already_complete

    def show_pre_translate_and_prep_kit_auto(self):
        return self.has_analysis_code() and not self.has_any_translation_completed()


def get_translation_file_path(instance, filename):
    return posixpath.join('projects', str(instance.kit.project.id), str(instance.target_locale.dvx_lcid), 'lockit', filename)


def get_reference_file_path(instance, filename):
    return posixpath.join('projects', str(instance.kit.project.id), str(instance.target_locale.dvx_lcid), 'ref', filename)


class LocaleTranslationKit(CircusModel):
    kit = models.ForeignKey(LocalizationKit)
    target_locale = models.ForeignKey(Locale)
    translation_file = models.FileField(max_length=settings.FULL_FILEPATH_LENGTH, upload_to=get_translation_file_path, null=True, blank=True)
    reference_file = models.FileField(max_length=settings.FULL_FILEPATH_LENGTH, upload_to=get_reference_file_path, null=True, blank=True)

    # having an analysis_code means we can use the translation_file with the DVX API.
    analysis_code = models.CharField(blank=True, null=True, max_length=24)

    class Meta:
        unique_together = ['kit', 'target_locale']

    def remove_translation_file(self):
        self.translation_file = ""
        self.save()

    def remove_translation_file_analysis_code(self):
        self.translation_file = ""
        self.analysis_code = None
        self.save()

    def translation_file_name(self):
        if self.translation_file:
            head, tail = posixpath.split(self.translation_file.name)
            return tail or posixpath.basename(head)

    def is_valid(self):
        if self.translation_file_name():
            return True
        else:
            return False

    def reference_file_name(self):
        return posixpath.basename(self.reference_file.name)


ASSET_TYPE = (
    (SOURCEFILE_ASSET, 'Source'),
    (REFERENCEFILE_ASSET, 'Reference item'),
    (PLACEHOLDERFILE_ASSET, 'Placeholder'),
)

ANALYSIS_STATUS_NEW = 'new'
ANALYSIS_STATUS_QUEUED = 'queued'
ANALYSIS_STATUS_SUCCESS = 'analysis_complete'
ANALYSIS_STATUS_ERROR = 'analysis_error'

ASSET_STATUS = (
    (ANALYSIS_STATUS_NEW, 'New'),
    (ANALYSIS_STATUS_QUEUED, 'Queued'),
    (ANALYSIS_STATUS_SUCCESS, 'Analysis Complete'),
    (ANALYSIS_STATUS_ERROR, 'Analysis Error'),
)


class FileAsset(CircusModel):
    asset_type = models.CharField(choices=ASSET_TYPE, max_length=20, default=PLACEHOLDERFILE_ASSET, db_index=True)
    status = models.CharField(choices=ASSET_STATUS, max_length=20, default=ANALYSIS_STATUS_NEW, db_index=True)
    kit = models.ForeignKey(LocalizationKit, related_name='files')
    orig_name = models.CharField(max_length=255, verbose_name="Original Name")
    orig_file = models.FileField(verbose_name="Original File",
                                 max_length=settings.FULL_FILEPATH_LENGTH,
                                 upload_to=get_project_asset_path,
                                 null=True, blank=True)
    prepared_name = models.CharField(max_length=255, verbose_name="Prepared Name",
                                     null=True, blank=True)
    prepared_file = models.FileField(verbose_name="Prepared File",
                                     max_length=settings.FULL_FILEPATH_LENGTH,
                                     upload_to=get_project_prepared_asset_path,
                                     null=True, blank=True)

    source_locale = models.ForeignKey(Locale, blank=True, null=True)
    queued_timestamp = models.DateTimeField(blank=True, null=True)
    available_on_supplier = models.NullBooleanField(default=False, blank=True, null=True)

    def short_name(self):
        if len(self.orig_name) > 40:
            return self.orig_name[:40] + '...'
        return self.orig_name

    def source_word_count(self):
        try:
            return _("{0}").format(self.fileanalysis_set.all()[0].total_wordcount())
        except:
            return _("No analysis")

    def file_display_name(self):
        full = unicode(self.orig_file)
        prefix = unicode(get_project_asset_path(self, ''))
        return full.replace(prefix, '')

    def project_id(self):
        try:
            return self.kit.project.id
        except:
            return u'unknown'

    def file_exists(self):
        if self.orig_file:
            return True
        else:
            return False

    def is_valid(self):
        # file is valid if it has analysis for every project locale
        analysis_set = self.fileanalysis_set.all()
        project_locales = set(l.id for l in self.kit.project.target_locales.all())
        analysis_locales = set(a.target_locale_id for a in analysis_set)
        if project_locales == analysis_locales and all(a.is_valid() for a in analysis_set):
            return True
        return False

    def delivery(self):
        try:
            return self.working_files.filter(file_type='trans_rtf').order_by('-created')[0]
        except:
            return None

    def analysis_for_target(self, target):
        """Get this file's analysis for the given locale.

        :type target: Locale
        :rtype: FileAnalysis
        """
        # I don't think we intentionally keep multiple analyses around for a single target,
        # but FileAnalysis -> FileAsset is many-to-one because there are multiple targets.
        return self.fileanalysis_set.filter(target_locale=target).latest("modified")

    def __unicode__(self):
        return unicode(self.orig_name)


class FileAnalysis(CircusModel, AnalysisFields):
    asset = models.ForeignKey(FileAsset, null=True)
    page_count = models.IntegerField(default=0)
    image_count = models.IntegerField(default=0)
    source_locale = models.ForeignKey(Locale, related_name='+', null=True)
    target_locale = models.ForeignKey(Locale, related_name='+', null=True)
    message = models.CharField(max_length=255, blank=True, null=True)

    def __unicode__(self):
        name = self.asset.orig_name if self.asset else u"None"
        return u'{0.id}, {1}, from {0.source_locale} to ' \
               u'{0.target_locale}'.format(self, name)

    def total_wordcount(self):
        return sum(getattr(self, field) for field in ANALYSIS_FIELD_NAMES)

    def field_wordcount_list(self):
        result = [getattr(self, field) for field in ANALYSIS_FIELD_NAMES]
        result.insert(0, self.total_wordcount())
        return result

    def total_pagecount(self):
        return sum(self.page_count)

    def is_valid(self):
        return self.total_wordcount() > 0

    def __add__(self, other):
        if not (self.source_locale == other.source_locale and
                self.target_locale == other.target_locale):
            raise ValueError("Analyses have different locales.")
        result = FileAnalysis(
            source_locale=self.source_locale,
            target_locale=self.target_locale,
            page_count=self.page_count + other.page_count,
            image_count=self.image_count + other.image_count,
        )
        for field in ANALYSIS_FIELD_NAMES:
            my_value = getattr(self, field, 0)
            other_value = getattr(other, field, 0)
            setattr(result, field, my_value + other_value)
        return result


CLIENT_REFERENCE_FILE_TYPES = (
    ('glossary', 'Glossary'),
    ('style_guide', 'StyleGuide'),
)
