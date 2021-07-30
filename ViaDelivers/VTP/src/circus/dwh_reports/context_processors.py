from django.conf import settings
from django_comments.models import Comment


def messages_unread_count_all(request):
    message_count_all = notification_count = 0
    if request.user.is_authenticated():
        message_count_all = Comment.objects.filter(comment_to=request.user.id, is_removed=False, comment_read_check=False, notification_type=settings.NOTIFICATION_TYPE_MESSAGE).count()
        notification_count = Comment.objects.filter(comment_to=request.user.id, is_removed=False, comment_read_check=False, notification_type=settings.NOTIFICATION_TYPE_NOTIFICATION).count()
    return {'client_message_unread_count_all': message_count_all, 'client_notification_unread_count': notification_count}