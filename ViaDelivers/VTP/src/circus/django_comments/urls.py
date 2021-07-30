from django.conf.urls import url
from django_comments.views import comments as c, moderation as m
from django.contrib.contenttypes.views import shortcut


urlpatterns = [
    url(r'^post/$', c.post_comment, name='comments-post-comment'),
    url(r'^delete/(\d+)/(\d+)/(\w+)/$', m.delete, name='comments-delete'),
    url(r'^edit/(\d+)/$', m.edit, name='comments-edit'),

    url(r'^cr/(\d+)/(.+)/$', shortcut, name='comments-url-redirect'),
]
