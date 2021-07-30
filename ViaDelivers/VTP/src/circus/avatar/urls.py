try:
    from django.conf.urls import url
except ImportError:
    # Django < 1.4
    from django.conf.urls.defaults import url
from avatar.views import add, change, delete, render_primary

urlpatterns = [
    url(r'^add/$', add, name='avatar_add'),
    url(r'^change/$', change, name='avatar_change'),
    url(r'^delete/$', delete, name='avatar_delete'),
    url(r'^render_primary/(?P<user>[\w\d\@\.\-_]{3,30})/(?P<size>[\d]+)/$', render_primary, name='avatar_render_primary'),
]
