# -*- coding: utf-8 -*-
from datetime import timedelta
from django.core.management.base import BaseCommand
from projects.models import BackgroundTask

TIMEOUT_MINUTES = 120


class Command(BaseCommand):
    help = "Expires old Background Tasks"

    def handle(self, *args, **options):
        timeout = timedelta(minutes=TIMEOUT_MINUTES)
        self.stdout.write("Expiring tasks older than %s" % (timeout,))
        count = BackgroundTask.objects.reap_expired(timeout)
        self.stdout.write("%s tasks expired." % (count,))
