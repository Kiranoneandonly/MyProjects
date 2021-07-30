from django.conf.urls import url
from vendor_portal.views import (VendorTasksStatusView,
                                 VendorDashboardView, accept_task, reject_task, vendor_tla_delivery_redirect, vendor_tlasf_delivery_redirect,
                                 vendor_tltk_delivery_redirect, vendor_tlsf_delivery_redirect, VendorTaskDetailView, VendorTaskSearchView, ProjectCommentsView,
                                  VendorProjectNotificationsListView, vendor_tltk_input_delivery_redirect)
from vendor_portal.authorization import protected_task
from accounts.views import edit_profile


urlpatterns = [
                       url(r'^$', VendorDashboardView.as_view(), name='vendor_dashboard'),
                       url(r'^profile/$', edit_profile, {'template': 'vendors/accounts/profile.html'}, name='vendor_edit_profile'),
                       url(r'^tasks/search/?$', VendorTaskSearchView.as_view(), name='vendor_task_search'),
                       # make sure status does not start with a digit, to tell it apart from vendor_task_detail.
                       url(r'^tasks/(?P<status>[A-Za-z]\w*)/?$', VendorTasksStatusView.as_view(), name='vendor_tasks_status'),
                       url(r'^messenger/(?P<project_id>\d+)/?$', ProjectCommentsView.as_view(), name='vendor_project_comments'),
                       # todo when we figure out how to filter messages by Vendor
                       url(r'^notifications/?$', VendorProjectNotificationsListView.as_view(), name='vendor_notification_unread_count'),
                       ]


protected_patterns = protected_task.protect_patterns(
    url(r'^tasks/(?P<pk>\d+)/?$', VendorTaskDetailView.as_view(), name='vendor_task_detail'),
    url(r'^tasks/(?P<pk>\d+)/accept/?$', accept_task, name='vendor_accept_task'),
    url(r'^tasks/(?P<pk>\d+)/reject/?$', reject_task, name='vendor_reject_task'),
    url(r'^tasks/(?P<pk>\d+)/upload_tltk/(?P<tltk_id>\d+)/?$',
        vendor_tltk_delivery_redirect, name='vendor_tltk_delivery_complete'),
    url(r'^tasks/(?P<pk>\d+)/upload_tltk/(?P<tltk_id>\d+)/input/?$',
        vendor_tltk_input_delivery_redirect, name='vendor_tltk_input_delivery_complete'),
    url(r'^tasks/(?P<pk>\d+)/upload_tlsf/(?P<tltk_id>\d+)/?$',
        vendor_tlsf_delivery_redirect, name='vendor_tlsf_delivery_complete'),
    url(r'^tasks/(?P<pk>\d+)/upload_tlasf/(?P<tla_id>\d+)/?$', vendor_tlasf_delivery_redirect, name='vendor_tlasf_delivery_complete'),
    url(r'^tasks/(?P<pk>\d+)/upload_tla/(?P<tla_id>\d+)/?$',
        vendor_tla_delivery_redirect, name='vendor_tla_delivery_complete'),
)

urlpatterns.extend(protected_patterns)
