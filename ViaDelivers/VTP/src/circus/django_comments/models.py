from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core import urlresolvers
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from django_comments.managers import CommentManager
from tasks.models import Task

COMMENT_MAX_LENGTH = getattr(settings, 'COMMENT_MAX_LENGTH', 3000)


class BaseCommentAbstractModel(models.Model):
    """
    An abstract base class that any custom comment models probably should
    subclass.
    """

    # Content-object field
    content_type = models.ForeignKey(ContentType,
                                     verbose_name=_('content type'),
                                     related_name="content_type_set_for_%(class)s")
    object_pk = models.TextField(_('object ID'))
    content_object = GenericForeignKey(ct_field="content_type", fk_field="object_pk")

    # Metadata about the comment
    site = models.ForeignKey(Site)

    class Meta:
        abstract = True

    def get_content_object_url(self):
        """
        Get a URL suitable for redirecting to the content object.
        """
        return urlresolvers.reverse(
            "comments-url-redirect",
            args=(self.content_type_id, self.object_pk)
        )


@python_2_unicode_compatible
class Comment(BaseCommentAbstractModel):
    """
    A user comment about some object.
    """

    # Who posted this comment? If ``user`` is set then it was an authenticated
    # user; otherwise at least user_name should have been set and the comment
    # was posted by a non-authenticated user.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('user'),
                             blank=True, null=True, related_name="%(class)s_comments")

    comment = models.TextField(_('comment'), max_length=COMMENT_MAX_LENGTH)

    # Metadata about the comment
    submit_date = models.DateTimeField(_('date/time submitted'), default=None)
    ip_address = models.GenericIPAddressField(_('IP address'), unpack_ipv4=True, blank=True, null=True)
    is_public = models.BooleanField(_('is public'), default=True,
                                    help_text=_('Uncheck this box to make the comment effectively disappear from the site.'))
    is_removed = models.BooleanField(_('is removed'), default=False,
                                     help_text=_('Check this box if the comment is inappropriate. '
                                                 'A "This comment has been removed" message will be displayed instead.'))

    user_type = models.CharField(_('users type'), max_length=50, blank=True)
    via_comment_user_type = models.CharField(_('via comment users type'), max_length=50, blank=True)

    via_flag = models.BooleanField(_('via user flag'), default=True)
    client_flag = models.BooleanField(_('client flag'), default=True)
    vendor_flag = models.BooleanField(_('vendor flag'), default=True)

    task = models.ForeignKey(Task, null=True)
    comment_to = models.CharField(_('Comment To'), max_length=50, blank=True)
    filter_from_list = models.BooleanField(_('vendor flag'), default=False)
    comment_read_on = models.DateTimeField(_('comment read on'), blank=True, null=True)
    comment_read_check = models.BooleanField(_('comment read check'), default=False)
    notification_type = models.CharField(_('users type'), max_length=50, blank=True, default=settings.NOTIFICATION_TYPE_MESSAGE)

    # Manager
    objects = CommentManager()

    class Meta:
        db_table = "django_comments"
        ordering = ('submit_date',)
        permissions = [("can_moderate", "Can moderate comments")]
        verbose_name = _('comment')
        verbose_name_plural = _('comments')

    def __str__(self):
        return "%s..." % (self.comment[:50])

    def save(self, *args, **kwargs):
        if self.submit_date is None:
            self.submit_date = timezone.now()
        super(Comment, self).save(*args, **kwargs)

    def get_absolute_url(self, anchor_pattern="#c%(id)s"):
        return self.get_content_object_url() + (anchor_pattern % self.__dict__)

    def get_as_text(self):
        """
        Return this comment as plain text.  Useful for emails.
        """
        d = {
            'user': self.user,
            'date': self.submit_date,
            'comment': self.comment,
            'domain': self.site.domain,
            'url': self.get_absolute_url()
        }
        return _('Posted by %(user)s at %(date)s\n\n%(comment)s\n\nhttp://%(domain)s%(url)s') % d

    def is_client_comment(self):
        return self.user_type == settings.CLIENT_USER_TYPE

    def is_vendor_comment(self):
        return self.user_type == settings.VENDOR_USER_TYPE

    def is_via_comment(self):
        return self.user_type == settings.VIA_USER_TYPE

    def is_via_client_comment(self):
        return self.is_via_comment() and self.via_comment_user_type == settings.CLIENT_USER_TYPE

    def is_via_vendor_comment(self):
        return self.is_via_comment() and self.via_comment_user_type == settings.VENDOR_USER_TYPE

    def client_comments_access(self):
        return self.is_client_comment() or self.is_via_client_comment()

    def vendor_comments_access(self):
        return self.is_vendor_comment() or self.is_via_vendor_comment()

    def vendor_comments_delete(self):
        return self.is_vendor_comment()

    def client_comments_delete(self):
        return self.is_client_comment()

    def via_comments_delete(self):
        return self.is_via_comment()




@python_2_unicode_compatible
class CommentFlag(models.Model):
    """
    Records a flag on a comment. This is intentionally flexible; right now, a
    flag could be:

        * A "removal suggestion" -- where a user suggests a comment for (potential) removal.

        * A "moderator deletion" -- used when a moderator deletes a comment.

    You can (ab)use this model to add other flags, if needed. However, by
    design users are only allowed to flag a comment with a given flag once;
    if you want rating look elsewhere.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name=_('user'), related_name="comment_flags",
        on_delete=models.CASCADE,
    )
    comment = models.ForeignKey(
        # Translators: 'comment' is a noun here.
        Comment, verbose_name=_('comment'), related_name="flags", on_delete=models.CASCADE,
    )
    # Translators: 'flag' is a noun here.
    flag = models.CharField(_('flag'), max_length=30, db_index=True)
    flag_date = models.DateTimeField(_('date'), default=None)

    # Constants for flag types
    SUGGEST_REMOVAL = "removal suggestion"
    MODERATOR_DELETION = "moderator deletion"
    MODERATOR_APPROVAL = "moderator approval"

    class Meta:
        db_table = 'django_comment_flags'
        unique_together = [('user', 'comment', 'flag')]
        verbose_name = _('comment flag')
        verbose_name_plural = _('comment flags')

    def __str__(self):
        return "%s flag of comment ID %s by %s" % (
            self.flag, self.comment_id, self.user.get_username()
        )

    def save(self, *args, **kwargs):
        if self.flag_date is None:
            self.flag_date = timezone.now()
        super(CommentFlag, self).save(*args, **kwargs)


class JobMailsTracking(models.Model):
    last_refreshed_timestamp = models.DateTimeField(auto_now_add=True)

