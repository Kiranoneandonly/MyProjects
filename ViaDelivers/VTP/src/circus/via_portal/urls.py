from django.conf.urls import url, include
from projects import sow
import via_portal.accounting_views as av
import via_portal.views as v
import via_portal.authorization as authz


urlpatterns = [
    url(r'^jobs/?$', v.ProjectListView.as_view(), name='via_jobs_list'),
    url(r'^jobs/search/?$', v.ProjectSearchView.as_view(), name='via_jobs_search'),
    url(r'^jobs/(?P<pk>\d+)/?$', v.ProjectOverviewView.as_view(), name='via_job_detail_overview'),
    url(r'^jobs/(?P<pk>\d+)/estimate/?$', v.ProjectEstimateView.as_view(), name='via_job_detail_estimate'),

    url(r'^jobs/(?P<pk>\d+)/estimate/price_per_document/$', v.project_price_per_document, name='price_per_document'),

    url(r'^jobs/(?P<pk>\d+)/files/?$', v.ProjectFilesView.as_view(), name='via_job_detail_files'),
    url(r'^jobs/(?P<pk>\d+)/estimate/sow/$', sow.download_statement, name='download_sow'),
    url(r'^jobs/(?P<pk>\d+)/tasks/tasks_view/(?P<service_id>[\d]+)/$', v.ProjectTasksNewView.as_view(), name='via_job_detail_tasks_view'),
    url(r'^jobs/(?P<pk>\d+)/tasks/?$', v.ProjectTasksView.as_view(), name='via_job_detail_tasks'),
    url(r'^jobs/(?P<pk>\d+)/accounting/summary/?$', av.ProjectAccountingSummaryView.as_view(), name='via_job_accounting_summary'),
    url(r'^jobs/(?P<pk>\d+)/accounting/invoices/?$', av.ProjectAccountingInvoiceListView.as_view(), name='via_job_accounting_invoice_list'),
    url(r'^jobs/(?P<pk>\d+)/accounting/purchase-orders/?$', av.ProjectAccountingPurchaseOrderListView.as_view(), name='via_job_accounting_purchase_order_list'),
    url(r'^jobs/(?P<pk>\d+)/invoice/new/?$', av.InvoiceCreateView.as_view(), name='via_job_invoice_create'),
    url(r'^jobs/(?P<pk>\d+)/invoice/(?P<invoice_pk>\d+)/?$', av.InvoiceEditView.as_view(), name='via_job_invoice_edit'),
    url(r'^jobs/(?P<pk>\d+)/invoice/(?P<invoice_pk>\d+)/delete/?$', av.InvoiceDeleteView.as_view(), name='via_job_invoice_delete'),
    # url(r'^jobs/(?P<pk>\d+)/purchase-orders/new?$', av.PurchaseOrderCreateView.as_view(), name='via_job_purchase_order_create'),
    # url(r'^jobs/(?P<pk>\d+)/purchase-order/(?P<pk>\d+)/?$', av.PurchaseOrderView.as_view(), name='via_job_purchase_order'),
    url(r'^jobs/(?P<pk>\d+)/team/?$', v.ProjectTeamView.as_view(), name='via_job_detail_team'),
    url(r'^jobs/(?P<pk>\d+)/activitylog/?$', v.ActivityLogView.as_view(), name='via_job_detail_activelog'),
    url(r'^jobs/(?P<pk>\d+)/tm/?$', v.ProjectDvxView.as_view(), name='via_job_detail_dvx'),

    url(r'^jobs/(?P<status>[\w]+)/?$', v.ProjectListView.as_view(), name='via_jobs_status_list'),
    url(r'^jobs/(?P<status>[\w]+)/csv$', v.ProjectListViewExport.as_view(), name='via_jobs_status_list_export'),

    url(r'^jobs/(?P<pk>\d+)/log/?$', v.ProjectLogView.as_view(), name='via_job_detail_log'),
    url(r'^jobs/start/new/?$', v.ProjectCreateView.as_view(), name='via_job_create'),
    url(r'^jobs/start/new_auto_job/?$', v.ProjectAutoJobCreateView.as_view(), name='via_auto_job_create'),
    url(r'^jobs/start/new_workflow_job/?$', v.WorkflowJobCreateView.as_view(), name='via_workflow_job_create'),
    url(r'^jobs/start/new_auto_job_create/(?P<pk>\d+)/(?P<client>\d+)?$', v.ProjectAutoJobContinueView.as_view(), name='via_continue_auto_job'),
    url(r'^quotes/waiting/(?P<pk>[\d]+)/$', v.WaitingQuoteView.as_view(), name='via_waiting_for_quote'),
    url(r'^jobs/start/manual_estimate_job_create/(?P<pk>[\d]+)/$', v.manual_estimate_job, name='manual_estimate_job'),

    url(r'^quality_defects/(?P<pk>\d+)/?$', v.QualityDefectEditView.as_view(), name='via_quality_defect_edit'),
    url(r'^quality_defects/new/?$', v.QualityDefectCreateView.as_view(), name='via_quality_defect_create'),
    url(r'^quality_defects/?$', v.QualityDefectListView.as_view(), name='via_quality_defect_list'),

    url(r'^client-project-lookup/?$', v.client_project_lookup, name='via_client_project_lookup'),

    url(r'^project-task-lookup/?$', v.project_task_lookup, name='via_project_task_lookup'),

    url(r'^client-poc-lookup/?$', v.client_poc_lookup, name='via_client_poc_lookup'),

    url(r'^tasks/(?P<pk>\d+)/approve/?$', v.ApproveTask.as_view(), name='via_approve_task'),
    url(r'^tasks/(?P<pk>\d+)/(?P<locale_id>\d+)/accept/?$', v.accept_task, name='via_accept_task'),
    url(r'^tasks/(?P<pk>\d+)/reject/?$', v.reject_task, name='via_reject_task'),
    url(r'^tasks/(?P<pk>\d+)/replace-delivery/?$', v.final_approval_replace_delivery_redirect, name='via_final_approval_replace_delivery'),
    url(r'^tasks/(?P<pk>\d+)/replace-post_delivery/?$', v.post_delivery_replace_redirect, name='via_post_delivery_replace_delivery'),

    #Client reference files downloading
    url(r'^download/p_(?P<proj_id>\d+)/client-ref-files/(?P<asset_id>\d+)/?$', v.client_reference_file_download_handler, name='download_client_reference_file'),
    url(r'^price-per-document/(?P<project>\d+)/csv/?$', v.DocumentPriceExport.as_view(), name='price_per_document_export'),
]

# Actually, *all* the via/ views fall under the "any via user" authorization
# rule, but the ones above already have their mixins and decorators and whatnot
# and I'm not going to retrofit them all just yet.
urlpatterns.extend(authz.any_via_user.protect_patterns(
                                                       url(r'^$', v.ViaDashboardView.as_view(), name='via_dashboard'),
                                                       url(r'^dashboard/(?P<is_user_type>[A-Za-z]\w*)/(?P<userid>\d+)/?$', v.ViaDashboardView.as_view(), name='team_dashboard'),
                                                       url(r'^dashboard/(?P<is_user_type>[A-Za-z]\w*)/(?P<userid>\d+)/?$', v.ViaDashboardView.as_view(), name='my_dashboard'),
                                                       url(r'^tasks/(?P<is_user_type>[A-Za-z]\w*)/(?P<status>[A-Za-z]\w*)/?$', v.ViaMyTasksStatusView.as_view(), name='my_tasks_status'),

                                                       url(r'^source_file_upload_complete/(?P<pk>\d+)/?$', v.source_file_upload_redirect, name='source_file_upload_complete'),
                                                       url(r'^auto_job_source_file_upload_complete/(?P<pk>\d+)/?$', v.auto_job_source_file_upload_redirect, name='auto_job_source_file_upload_complete'),
                                                       url(r'^reference_file_upload_complete/(?P<pk>\d+)/?$', v.reference_file_upload_redirect, name='reference_file_upload_complete'),
                                                       url(r'^reference_file_replace_complete/(?P<pk>\d+)/?$', v.reference_file_replace_redirect, name='reference_file_replace_complete'),
                                                       url(r'^prepared_file_upload_complete/(?P<file_asset_id>\d+)/?$', v.prepared_file_upload_redirect, name='prepared_file_upload_complete'),
                                                       url(r'^kit_translation_file_upload_complete/(?P<pk>\d+)/?$', v.kit_translation_file_upload_complete, name='kit_translation_file_upload_complete'),
                                                       url(r'^ltk_reference_upload_complete/(?P<ltk_id>\d+)/?', v.ltk_reference_upload_redirect, name='ltk_reference_upload_complete'),
                                                       url(r'^via_upload_tltk/(?P<pk>\d+)/?$', v.via_tltk_delivery_redirect, name='via_tltk_delivery_complete'),
                                                       url(r'^via_upload_tla/(?P<pk>\d+)/?$', v.via_tla_delivery_redirect, name='via_tla_delivery_complete'),
                                                       url(r'^tasks/(?P<pk>\d+)/upload_tlsf/(?P<tltk_id>\d+)/?$', v.via_tlsf_delivery_redirect, name='via_tlsf_delivery_complete'),
                                                       url(r'^upload_tm_file/(?P<tltk_id>\d+)/?$', v.via_tm_file_delivery_redirect, name='via_tm_file_delivery_complete'),
                                                       url(r'^via_upload_tlasf/(?P<pk>\d+)/?$', v.via_tlasf_delivery_redirect, name='via_tlasf_delivery_complete'),
                                                       url(r'^via_upload_tla_input/(?P<pk>\d+)/?$', v.via_tla_input_delivery_redirect, name='via_tla_input_delivery_complete'),
                                                       url(r'^prepared_file_remove/(?P<file_asset_id>\d+)/?$', v.prepared_file_remove, name='prepared_file_remove'),

                                                       url(r'^kits/', include('localization_kits.urls')),
                                                       url(r'^customers/', include('clients.urls')),
                                                       url(r'^suppliers/', include('vendors.urls')),
                                                       url(r'^preferred_suppliers/', include('preferred_vendors.urls')),

                                                       url(r'^reports/background_tasks/?$', v.current_background_tasks, name='background_tasks'),
                                                       url(r'^reports/background_tasks/complete/(?P<bgtask_id>\d+)/?$', v.complete_background_task, name='complete_background_task'),

                                                       url(r'^reports/', include('dwh_reports.urls')),

                                                       url(r'^messenger/(?P<project_id>\d+)/?$', v.ProjectClientCommentsView.as_view(), name='project_comments'),
                                                       url(r'^messages/?$', v.ProjectCommentsListView.as_view(), name='job_messages_list_page'),
                                                       url(r'^notifications/?$', v.ProjectNotificationsListView.as_view(), name='job_notifications_list_page'),

                                                       ))
