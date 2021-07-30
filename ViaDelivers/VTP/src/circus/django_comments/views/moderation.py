from __future__ import absolute_import
from django.utils import timezone

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.core.urlresolvers import reverse, resolve
from django.http import HttpResponseRedirect

import django_comments
from django_comments import signals


@csrf_protect
def delete(request, comment_id, task_id, redirect_url, next=None):
    comment = get_object_or_404(django_comments.get_model(), pk=comment_id, site__pk=settings.SITE_ID)

    comment.is_removed = True
    comment.save()
    redirect_url = redirect_url
    if request.user.is_client():
        kw_args = {'pk': comment.object_pk}
    elif request.user.is_vendor():
        task_id = task_id
        kw_args = {'pk': task_id}
    else:
        kw_args = {'project_id': comment.object_pk}

    ###Creating a session variable to stay back on same message page when user submits comments.
    request.session['tab_session_name'] = 'message_tab'
    return HttpResponseRedirect(reverse(redirect_url, kwargs=kw_args))


@csrf_protect
def edit(request, comment_id, next=None):
    comment = get_object_or_404(django_comments.get_model(), pk=comment_id, site__pk=settings.SITE_ID)

    # Delete on POST
    if request.method == 'POST':
        # Flag the comment as deleted instead of actually deleting it.
        # perform_edit(request, comment)
        comment.comment = request.POST.get('comment_list')
        comment.submit_date = timezone.now()
        comment.comment_read_check = False
        comment.save()

    redirect_url = resolve(request.POST['redirect_url']).url_name
    if request.user.is_client():
        kw_args = {'pk': comment.object_pk}
    elif request.user.is_vendor():
        task_id = request.POST['vendor_task']
        kw_args = {'pk': task_id}
    else:
        kw_args = {'project_id': comment.object_pk}

    ###Creating a session variable to stay back on same message page when user submits comments.
    request.session['tab_session_name'] = 'message_tab'
    return HttpResponseRedirect(reverse(redirect_url, kwargs=kw_args))


def perform_delete(request, comment):
    flag, created = django_comments.models.CommentFlag.objects.get_or_create(
        comment=comment,
        user=request.user,
        flag=django_comments.models.CommentFlag.MODERATOR_DELETION
    )
    comment.is_removed = True
    comment.save()
    signals.comment_was_flagged.send(
        sender=comment.__class__,
        comment=comment,
        flag=flag,
        created=created,
        request=request,
    )