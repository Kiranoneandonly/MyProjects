from django.conf.urls import url
from preferred_vendors.views import PreferredVendorsView, update_preferred_vendor

urlpatterns = [
    url(r'^$', PreferredVendorsView.as_view(), name='preferred_vendors_edit'),

    #ajax
    url(r'^ajax/update/$', update_preferred_vendor, name='update_preferred_vendor')
]