from django.conf.urls import url
import dwh_reports.views as v


urlpatterns = [

    url(r'^total_spend_by_customer/?$', v.total_spend_by_customer, name='total_spend_by_customer'),
    url(r'^total_price_per_word/?$', v.total_price_per_word, name='total_price_per_word'),
    url(r'^total_price_per_word_language/(?P<userid>\d+)/(?P<start>(\d{4})-(\d{2})-(\d+))/(?P<end>(\d{4})-(\d{2})-(\d+))/?$', v.total_price_per_word_language, name='total_price_per_word_language'),
    url(r'^total_spend_by_tasks/?$', v.total_spend_by_tasks, name='total_spend_by_tasks'),
    url(r'^total_spend_by_manager/?$', v.total_spend_by_manager, name='total_spend_by_manager'),
    url(r'^eqd_report/?$', v.eqd_report, name='eqd_report'),
    url(r'^customer_tm_savings/?$', v.customer_tm_savings, name='customer_tm_savings'),
    url(r'^customer_tm_savings/(?P<client_id>\d+)/(?P<start>(\d{4})-(\d{2})-(\d+))/(?P<end>(\d{4})-(\d{2})-(\d+))/?$', v.CustomerJobsTmSavings.as_view(), name='customer_jobs_tm_savings'),

    url(r'^customers_activity/(?P<client_id>\d+)/?$', v.client_activity_report, name='client_activity_report'),
    url(r'^customers_activity/(?P<client_id>\d+)/(?P<status>[A-Za-z]\w*)/?$', v.client_activity_report, name='client_activity_report'),

    url(r'^customers_filter_form/(?P<view_id>\d+)/?$', v.client_form_view, name='client_filter_form'),
    url(r'^customers_activity_report/(?P<client_id>\d+)/(?P<status>[A-Za-z]\w*)/(?P<days>\d+)/?$', v.ClientActivityReportView.as_view(), name='client_activity_report_view'),
    url(r'^customers_activity_report/(?P<client_id>\d+)/(?P<status>[A-Za-z]\w*)/(?P<from_days>\d+)/(?P<to_days>-?\d+)/?$', v.ClientActivityReportView.as_view(), name='client_activity_report_view'),
    url(r'^customers_activity_report_csv_export/(?P<client_id>\d+)/(?P<status>[A-Za-z]\w*)/(?P<from_days>\d+)/(?P<to_days>-?\d+)/?$', v.client_activity_report, name='client_activity_csv_export'),
    url(r'^customers-activity-pricing-by-documents/(?P<client_id>\d+)/(?P<from_days>\d+)/(?P<to_days>-?\d+)/?$', v.ClientActivityReportPricingBreakdownByDocumentView.as_view(), name='client_activity_pricing_breakdown_by_document_report'),
    url(r'^customers-activity-pricing-by-documents-csv_export/(?P<client_id>\d+)/(?P<from_days>\d+)/(?P<to_days>-?\d+)/?$', v.ClientActivityPricingByDocumentCsvExport.as_view(), name='client_activity_pricing_by_document_csv_export'),

    url(r'^customers_gross_margin_report/?$', v.clients_gross_margin_report, name='clients_gross_margin_report'),
    url(r'^client-poc-lookup-departments/?$', v.client_poc_lookup_department, name='via_client_poc_lookup_department'),
    url(r'^client-poc-lookup-managers/?$', v.client_poc_lookup_managers, name='via_client_poc_lookup_managers'),

]


