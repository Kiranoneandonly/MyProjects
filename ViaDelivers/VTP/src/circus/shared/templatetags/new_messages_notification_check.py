import pytz
from django import template
from django.conf import settings
from django.db.models import Q

from django_comments.models import Comment
from shared.utils import comment_filters

register = template.Library()


@register.simple_tag
def new_messages_notification_check(request):
    new_comments = None
    if request and request.user.id:
        cmnt_to = request.user.id

        timestamp = request.user.last_login
        pst_timestamp = timestamp.astimezone(pytz.timezone(settings.PST_TIME_ZONE))
        new_comments = Comment.objects.filter(
                                       Q(comment_read_check=False) &
                                       Q(is_removed=False) &
                                       Q(comment_to=cmnt_to) &
                                       Q(notification_type=settings.NOTIFICATION_TYPE_MESSAGE))
    if new_comments:
        return True
    return False


@register.simple_tag
def mark_as_read_check(comment_id, request):
    new_comment = None
    if request and request.user.id:
        cmnt_to = request.user.id

        timestamp = request.user.last_login
        pst_timestamp = timestamp.astimezone(pytz.timezone(settings.PST_TIME_ZONE))
        comments = Comment.objects
        new_comment = comments.get(id=comment_id)
        if new_comment.comment_read_check is False \
                and new_comment.comment_to == str(cmnt_to): \
                # and new_comment.submit_date >= pst_timestamp:
            return True

    return False


@register.simple_tag
def mark_all_as_read_check(request, project_id=None, comment_types=None):
    new_comments = None
    if request and request.user.id:
        cmnt_to = request.user.id
        timestamp = request.user.last_login
        pst_timestamp = timestamp.astimezone(pytz.timezone(settings.PST_TIME_ZONE))
        new_comments = Comment.objects\
            .filter(*comment_types)\
            .filter(Q(object_pk=project_id) &
                    Q(is_removed=False) &
                    Q(comment_read_check=False) &
                    Q(comment_to=cmnt_to)
                    )
    if new_comments:
        return True
    return False


@register.simple_tag
def mark_all_as_read_check_client(request, project_id=None):
    comment_types = comment_filters(settings.CLIENT_USER_TYPE)
    return mark_all_as_read_check(request, project_id, comment_types)


@register.simple_tag
def mark_all_as_read_check_vendor(request, project_id=None):
    comment_types = comment_filters(settings.VENDOR_USER_TYPE)
    return mark_all_as_read_check(request, project_id, comment_types)
