from django.conf.urls import url
import dwh_reports.views as v

urlpatterns = [

    #Client reports
    url(r'^total_spend_by_customer/?$', v.total_spend_by_customer, name='total_spend_by_customer_client_portal'),
    url(r'^total_spend_by_manager/?$', v.total_spend_by_manager, name='total_spend_by_manager_client_portal'),
    url(r'^total_spend_by_tasks/?$', v.total_spend_by_tasks, name='total_spend_by_tasks_client_portal'),
    url(r'^total_price_per_word/?$', v.total_price_per_word, name='total_price_per_word_client_portal'),
    url(r'^total_price_per_word_language/(?P<userid>\d+)/(?P<start>(\d{4})-(\d{2})-(\d+))/(?P<end>(\d{4})-(\d{2})-(\d+))/?$', v.total_price_per_word_language, name='total_price_per_word_language_client_portal'),
    url(r'^customer_tm_savings/?$', v.customer_tm_savings, name='customer_tm_savings_client_portal'),
    url(r'^customer_tm_savings/(?P<client_id>\d+)/(?P<start>(\d{4})-(\d{2})-(\d+))/(?P<end>(\d{4})-(\d{2})-(\d+))/?$', v.CustomerJobsTmSavings.as_view(), name='customer_jobs_tm_savings_client_portal'),
    url(r'^customers_filter_form/?$', v.client_form_view, name='client_filter_form_client_portal'),
    url(r'^customers_filter_form/(?P<view_id>\d+)/?$', v.client_form_view, name='client_filter_form_client_portal'),
    url(r'^customers_activity_report/(?P<client_id>\d+)/(?P<status>[A-Za-z]\w*)/(?P<from_days>\d+)/(?P<to_days>-?\d+)/?$', v.ClientActivityReportView.as_view(), name='client_activity_report_view_client_portal'),
    url(r'^customers_activity_report_csv_export/(?P<client_id>\d+)/(?P<status>[A-Za-z]\w*)/(?P<from_days>\d+)/(?P<to_days>-?\d+)/?$', v.client_activity_report, name='client_activity_csv_export_client_portal'),
    url(r'^customers_activity_report/(?P<client_id>\d+)/(?P<status>[A-Za-z]\w*)/(?P<days>\d+)/?$', v.ClientActivityReportView.as_view(), name='client_activity_report_view_client_portal'),
    url(r'^client-poc-lookup-managers/?$', v.client_poc_lookup_managers, name='via_client_poc_lookup_managers_client_portal'),
]
