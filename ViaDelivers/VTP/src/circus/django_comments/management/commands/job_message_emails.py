#!/usr/bin/python
# -*- coding: utf-8 -*-
import logging

import pytz
from django.core.management.base import BaseCommand
import datetime
from django.conf import settings
from django.db.models import Q
from notifications.notifications import notify_job_messages_email
from django_comments.models import Comment, JobMailsTracking
from accounts.models import CircusUser

logger = logging.getLogger('circus.' + __name__)


def send_job_messages_email():
    try:
        logger.info(u'Sending job message emails')

        last_modified = None
        report_filter = ~Q(comment=None)
        refresh_track_obj = JobMailsTracking.objects.all()
        if refresh_track_obj:
            last_modified = refresh_track_obj.order_by("-pk")[0].last_refreshed_timestamp

        if last_modified:
            last_modified = last_modified.astimezone(pytz.timezone(settings.PST_TIME_ZONE))
            report_filter = Q(submit_date__gte=last_modified)

        comments = Comment.objects.filter(report_filter)

        email_user_list = []
        for cmt in comments:
            if cmt.comment_to:
                email_user_list.append(cmt.comment_to)

        email_user_list = list(set(email_user_list))

        for user in email_user_list:
            mail_to_user = CircusUser.objects.get(id=user).email
            email_comment = comments.filter(comment_to=user)
            email_count = email_comment.count()
            notify_job_messages_email(email_comment, mail_to_user, email_count, last_modified)

        last_refreshed_timestamp_track = datetime.datetime.now()
        refresh_table = JobMailsTracking(
            last_refreshed_timestamp=last_refreshed_timestamp_track
        )
        refresh_table.save()

        logger.info(u'Job messages email has been sent')

    except Exception, exc:
        import pprint
        msg = [
            u'Exception:',
            pprint.pformat(exc),
        ]
        logger.error(msg)
        raise


class Command(BaseCommand):
    args = ''
    help = 'Scheduler to send job messages email.'

    def handle(self, *args, **options):
        try:
            logger.info("Sending Job messages email")
            send_job_messages_email()
            logger.info("All done!")
        except Exception:
            # unlike django request handling, management commands don't have
            # any top-level exception logger. add one here as this is run
            # unattended by heroku scheduler.
            logger.error("error in sending job messages email", exc_info=True)
            raise
