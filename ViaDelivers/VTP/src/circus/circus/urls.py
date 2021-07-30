from django.conf import settings
from django.conf.urls import include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin
from django.views.generic.base import RedirectView
from circus.views import ContactView, TermsView, permission_denied
import circus.views as c

admin.autodiscover()

urlpatterns = [
    url(r'^grappelli/', include('grappelli.urls')),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^impersonate/', include('impersonate.urls')),
    url(r'^admin/', include(admin.site.urls)),

    url(r'^$', c.home, name='home_redirect'),
    url(r'^register/?$', c.register, name='register_redirect'),
    url(r'^contact/?$', ContactView.as_view(), name='contact_via'),
    url(r'^terms/?$', TermsView.as_view(), name='terms_via'),

    url(r'^accounts/', include('accounts.urls')),
    url(r'^client/', include('client_portal.urls')),
    url(r'^vendor/', include('vendor_portal.urls')),
    url(r'^via/', include('via_portal.urls')),
    url(r'^finance/', include('finance.urls')),
    url(r'^projects/', include('projects.urls')),
    url(r'^tasks/', include('tasks.urls')),
    url(r'^kits/', include('localization_kits.shared_urls')),
    url(r'^email/', include('notifications.urls')),

    url(r'^internal_api/', include('localization_kits.api_urls')),
    url(r'^internal_api/docs/', include('rest_framework_docs.urls')),

    url(r'^avatar/', include('avatar.urls')),
    url(r'^messenger/', include('django_comments.urls')),
    url(r'^tinymce/', include('tinymce.urls')),


    url(r'^favicon\.ico$', RedirectView.as_view(url='/static/shared/img/via_favi_V-16.png', permanent=True)),
]

urlpatterns += staticfiles_urlpatterns()

if settings.DEBUG_DB_SQL:
    import debug_toolbar

    urlpatterns = [
                      url(r'^__debug__/', include(debug_toolbar.urls)),
                  ] + urlpatterns

handler403 = permission_denied
