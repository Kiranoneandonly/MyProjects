from datetime import timedelta
import logging

from django.db.models import Q
from django.db import models, IntegrityError
from django.utils.timezone import now

from accounts.models import CircusUser
from shared.managers import CircusManager
from shared.models import CircusModel


DEFAULT_MUTE_TIME = timedelta(hours=3)

logger = logging.getLogger('circus.' + __name__)


class NotificationMuteManager(CircusManager):

    def project_muted(self, project):
        try:
            return self.filter(project=project).get(
                Q(expires_at__gte=now()) |
                Q(expires_at__isnull=True))
        except self.model.DoesNotExist:
            return None


    def mute(self, project, creator, duration=DEFAULT_MUTE_TIME):
        """
        :param projects.models.Project project: this project will not generate notifications
        :param CircusUser creator: the user requesting the mute
        :param timedelta duration: the maximum time for the mute to last
        """
        self.delete_expired(project)

        expires_at = (now() + duration) if (duration is not None) else None

        try:
            mute = self.create(project=project, creator=creator, expires_at=expires_at)
        except IntegrityError:
            logger.warning("%s already muted?", project, exc_info=True)

            mute = self.get(project=project)
            mute.creator = creator
            mute.expires_at = expires_at
            mute.save()

        logger.info(u"Notifications for %r muted by %s until %s",
                    project, creator.email, expires_at)

        return mute

    def unmute(self, project):
        self.filter(project=project).delete()
        logger.info(u"Notifications for %r unmuted.", project)

    def delete_expired(self, project):
        self.filter(project=project, expires_at__lte=now()).delete()



class NotificationMute(CircusModel):
    project = models.OneToOneField('projects.Project', unique=True, null=False,
                                   related_name="notification_mute",
                                   on_delete=models.CASCADE)
    creator = models.ForeignKey(CircusUser, null=False, on_delete=models.CASCADE)

    expires_at = models.DateTimeField(null=True, blank=True)

    objects = NotificationMuteManager()
