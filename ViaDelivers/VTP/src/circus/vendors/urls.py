from django.conf.urls import url
from vendors.views import VendorsListView, VendorDetailView, VendorCreateView, VendorUpdateView, VendorTranslationRatesView, VendorNonTranslationRatesView


urlpatterns = [
    url(r'^$', VendorsListView.as_view(), name='vendors_list'),
    url(r'^(?P<pk>\d+)/$', VendorDetailView.as_view(), name='vendors_detail'),
    url(r'^new/$', VendorCreateView.as_view(), name='vendors_create'),
    url(r'^edit/(?P<pk>\d+)/$', VendorUpdateView.as_view(), name='vendors_edit'),
    url(r'^edit/(?P<pk>\d+)/transrates$', VendorTranslationRatesView.as_view(), name='vendors_edit_trans_rates'),
    url(r'^edit/(?P<pk>\d+)/servicerates$', VendorNonTranslationRatesView.as_view(), name='vendors_edit_service_rates'),
]
