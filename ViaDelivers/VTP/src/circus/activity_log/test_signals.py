from django.test import TestCase
from django.conf import settings
from activity_log.models import Actions
from activity_log.signals import project_status_activity_log
from services.models import Locale
from shared.datafactory import create_project, TaskFactory


class Signalstestcase(TestCase):
    def test_is_large_job(self):
        self.en_US = Locale.objects.get(lcid=1033)
        self.ru = Locale.objects.get(lcid=1049)
        project = create_project(self.id(),
                                 started_timestamp=None,
                                 source=self.en_US,
                                 targets=[self.ru],
                                 )
        project.price = 10000
        self.assertGreaterEqual(project.price, settings.LARGE_JOB_PRICE)
