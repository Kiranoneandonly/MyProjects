from django import template
from django.conf import settings

from django_comments.models import Comment
from shared.utils import comment_filters

register = template.Library()


@register.simple_tag
def client_comments_exist(project_id):
    comment = None
    comment_types = comment_filters(settings.CLIENT_USER_TYPE)
    comment = Comment.objects.filter(object_pk=project_id, is_removed=False).filter(*comment_types)
    if comment:
        return True
    return False


@register.simple_tag
def vendor_comments_exist(project_id):
    comment = None
    comment_types = comment_filters(settings.VENDOR_USER_TYPE)
    comment = Comment.objects.filter(object_pk=project_id, is_removed=False).filter(*comment_types)
    if comment:
        return True
    return False
