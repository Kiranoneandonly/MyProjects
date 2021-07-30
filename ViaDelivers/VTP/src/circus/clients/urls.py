from django.conf.urls import url
from clients import views as v

urlpatterns = [
    url(r'^$', v.ClientsListView.as_view(), name='clients_list'),
    url(r'^(?P<pk>\d+)/$', v.ClientDetailView.as_view(), name='clients_detail'),
    url(r'^new/$', v.ClientCreateView.as_view(), name='clients_create'),
    url(r'^edit/(?P<client_id>\d+)/$', v.update, name='clients_edit'),
    url(r'^note/(?P<client_id>\d+)/$', v.edit_note, name='clients_note'),
]