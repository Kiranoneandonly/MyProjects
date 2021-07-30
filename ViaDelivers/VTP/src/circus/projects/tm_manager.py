from __future__ import unicode_literals
from functools import partial
import logging
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from shared.api_engine import api_get
from django.utils import timezone

logger = logging.getLogger('circus.' + __name__)


def add_to_tm_v2(localization_kit, bg_task):
    """
    :type localization_kit: LocalizationKit
    :raises DVXFailure: if the connection to the server fails, or the server
        returns a non-success status code for this action.
    :rtype: None
    """
    payload = {
        's3Bucket': settings.AWS_STORAGE_BUCKET_NAME,
        'jobID': localization_kit.project.id,
        'analysisCode': localization_kit.analysis_code,
        'bg_task': bg_task.id,
    }

    r = api_get(settings.VIA_MEMORYDB_URL, payload)


def queue_add_to_tm(self, callback=None, errback=None):
    from projects.models import BackgroundTask

    if BackgroundTask.objects.currently_adding_to_translation_memory(self.project):
        logger.warn(
            u"project %s#%s kit#%s.queue_add_to_tm: already in progress, skipping." %
            (self.project.job_number, self.project.id, self.id))
        return None

    if not self.has_analysis_code():
        logger.warn(
            u"project %s#%s kit#%s.queue_add_to_tm: no analysis_code, skipping." %
            (self.project.job_number, self.project.id, self.id))
        return None

    if settings.VIA_DVX_API_VERSION == 1:
        return None
    elif settings.VIA_DVX_API_VERSION == 2:

        self.is_manually_updated = False
        self.tm_update_started = timezone.now()
        self.tm_update_completed = None
        self.save()

        return BackgroundTask.objects.start_with_callback(
            BackgroundTask.MEMORY_DB_TM, self.project, partial(add_to_tm_v2, self), callback
        )
    else:
        raise ImproperlyConfigured("Bad VIA_DVX_API_VERSION %r for queue_add_to_tm" %
                                   (settings.VIA_DVX_API_VERSION,))


def _callback_update_tm(localization_kit):
    localization_kit.tm_update_completed = timezone.now()
    localization_kit.save()
    return True


#def _errback_update_tm(self, callback=None, errback=None):
    #pass