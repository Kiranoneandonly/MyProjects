from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from finance.views import vendor_po, vendor_po_preview

urlpatterns = [
   url(r'^po/(?P<pk>\d+)/?$', login_required(vendor_po), name='finance_vendor_po'),
   url(r'^po/(?P<pk>\d+)/html/?$', login_required(vendor_po_preview), name='finance_vendor_po_preview'),
]