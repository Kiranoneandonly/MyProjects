from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.utils import timezone
from localization_kits.models import LocalizationKit
from projects.states import COMPLETED_STATUS
from projects.tm_manager import queue_add_to_tm
from celery import signature


def update_tm():
    """ Fetch lockits of completed projects and run TM update. """
    lockits = LocalizationKit.objects.filter(tm_update_started__isnull=True).filter(project__status=COMPLETED_STATUS)
    for lockit in lockits: 
        lockit.tm_update_started = timezone.now()
        lockit.tm_update_completed = None
        lockit.save()   
        callback = signature('_callback_update_tm', args=lockit)
        queue_add_to_tm(lockit.project.kit, callback=callback)

        # this is not real time so limiting the call to every 10 seconds
        from time import sleep
        sleep(settings.UPDATE_TM_CALL_DELAY)  # Time in seconds.


class Command(NoArgsCommand):
    help = "Updates Translation memory"
    # requires_model_validation = False

    def handle_noargs(self, **options):
        update_tm()
