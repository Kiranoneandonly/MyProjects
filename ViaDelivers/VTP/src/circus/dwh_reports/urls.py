from django.conf.urls import url, include

urlpatterns = [
    # Customer Reporting
    url(r'^customer/', include('dwh_reports.urls_cust_reports')),

    # OPS Reporting
    url(r'^ops/', include('dwh_reports.urls_ops_reports')),

    # Supplier Reporting
    url(r'^supplier/', include('dwh_reports.urls_supplier_reports')),
]
