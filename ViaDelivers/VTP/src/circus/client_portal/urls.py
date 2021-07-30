from django.conf.urls import url, include
from client_portal.views import (NewProjectView, QuoteView, new_project_redirect, WaitingQuoteView,
                                 ProjectListView, ProjectSearchView, DashboardView, ProjectDetailView,
                                 ClientRegisterView, JoinClientAccountView, ProjectStatusOverdueView,
                                 AccountApprovalNeededView, EditUserView, UpdateClientAccountView,
                                 ProjectDeliveryView, ProjectListViewExport,
                                 UserListView, disable_user, CreateUserView, delete_asset_ajax,
                                 ManualQuoteUpdateView, check_analysis_status,
                                 account_setup_view, new_payment_view, client_post_delivery_replace_redirect, new_clone_job_redirect, ProjectCommentsView,
                                 ClientProjectCommentsListView, ClientProjectNotificationsListView, RequestedJobsView, no_access_job_redirect, GroupsListView, CreateGroupView, edit_delete_group)
from projects import sow

urlpatterns = [
    # ClientLoginRequiredMixin
    url(r'^$', DashboardView.as_view(), name='client_dashboard'),

    # ClientLoginRequiredMixin, @client_login_required
    url(r'^register/?$', ClientRegisterView.as_view(), name='client_register'),
    url(r'^account_setup/?$', account_setup_view, name='account_setup'),
    url(r'^join_account/?$', JoinClientAccountView.as_view(), name='join_client_organization'),
    url(r'^account_approval_needed/(?P<pk>[\d]+)/?$', AccountApprovalNeededView.as_view(), name='account_approval_needed'),

    # ClientLoginRequiredMixin, @client_login_required
    url(r'^jobs/?$', ProjectListView.as_view(), name='client_project_list'),
    url(r'^jobs/(?P<pk>[\d]+)/?$', ProjectDetailView.as_view(), name='client_project_detail'),
    url(r'^jobs/(?P<pk>[\d]+)/delivery/(?P<lcid>[\d]+)/?$', ProjectDeliveryView.as_view(), name='client_project_delivery'),
    url(r'^jobs/new/?$', new_project_redirect, name='client_new_project_start'),
    url(r'^jobs/new/phi/?$', new_project_redirect, name='client_new_phi_project_start'),
    url(r'^jobs/new/(?P<pk>[\d]+)/?$',  NewProjectView.as_view(), name='client_new_project'),
    url(r'^jobs/search/?$', ProjectSearchView.as_view(), name='client_project_search'),
    url(r'^jobs/overdue/?$', ProjectStatusOverdueView.as_view(), name='client_project_status_overdue'),
    # url(r'^jobs/requested/?$', RequestedJobsView.as_view(), name='requested'),
    url(r'^jobs/requested/?$', RequestedJobsView.as_view(), name='requested_job_access'),
    url(r'^jobs/no-access/?$', no_access_job_redirect, name='client_no_access'),
    url(r'^jobs/(?P<status>[\w]+)/?$', ProjectListView.as_view(), name='client_project_status_list'),
    url(r'^jobs/(?P<status>[\w]+)/csv$', ProjectListViewExport.as_view(), name='client_project_list_export'),
    url(r'^jobs/clone-new/(?P<id>[\d]+)/?$', new_clone_job_redirect, name='client_clone_new_job'),


    # ClientLoginRequiredMixin, @client_login_required
    url(r'^quotes/(?P<pk>[\d]+)/?$', QuoteView.as_view(), name='client_quote'),
    url(r'^quotes/waiting/(?P<pk>[\d]+)/$', WaitingQuoteView.as_view(), name='client_waiting_for_quote'),
    url(r'^quotes/manual/(?P<pk>[\d]+)/?$', ManualQuoteUpdateView.as_view(), name='client_manual_quote_message'),
    url(r'^quotes/(?P<proj_id>\d+)/pay/?$', new_payment_view, name='client_pay'),

    # ClientAdministratorLoginRequired
    url(r'^accounts/(?P<pk>[\d]+)/new/?$', UpdateClientAccountView.as_view(template_name='clients/accounts/new_organization.html', after='client_dashboard'), name='new_client_organization'),
    url(r'^accounts/(?P<pk>[\d]+)/edit/?$', UpdateClientAccountView.as_view(template_name='clients/accounts/update_organization.html'), name='update_client_organization'),

    # ClientAdministratorLoginRequired, @client_administrator_login_required
    url(r'^users/manage/?$', UserListView.as_view(), name='client_manage_users'),
    url(r'^users/(?P<pk>[\d]+)/edit/?$', EditUserView.as_view(), name='client_edit_user'),
    url(r'^users/new/?$', CreateUserView.as_view(), name='client_create_user'),
    url(r'^users/(?P<pk>[\d]+)/delete/?$', disable_user, name='client_delete_user'),
    url(r'^groups/manage/?$', GroupsListView.as_view(), name='client_manage_groups'),
    url(r'^group/new/?$', CreateGroupView.as_view(), name='client_create_group'),
    url(r'^groups/(?P<pk>[\d]+)/(?P<action>[\w]+)/edit/?$', edit_delete_group, name='client_edit_delete_group'),

    # @csrf_exempt, @login_required
    url(r'^assets/(?P<pk>[\d]+)/delete/?$', delete_asset_ajax, name='client_delete_asset'),

    # @login_required
    url(r'^analysis_status/?$', check_analysis_status, name='check_analysis_status'),
    url(r'^jobs/(?P<pk>\d+)/estimate/sow/$', sow.download_statement, name='download_client_sow'),

    #Client reports
    url(r'^reports/', include('client_portal.urls_cust_reports')),

    url(r'^tasks/(?P<pk>\d+)/replace-post_delivery/?$', client_post_delivery_replace_redirect, name='client_post_delivery_replace_delivery'),
    url(r'^messenger/(?P<project_id>\d+)/?$', ProjectCommentsView.as_view(), name='client_project_comments'),
    url(r'^messages/?$', ClientProjectCommentsListView.as_view(), name='job_messages_list_page_client'),
    url(r'^notifications/?$', ClientProjectNotificationsListView.as_view(), name='job_notification_list_page_client'),

                       ]
