from django import forms
from django.forms.models import modelformset_factory
from clients.models import Client
from preferred_vendors.models import PreferredVendor
from services.managers import DEFAULT_VERTICAL_CODE
from services.models import Locale, ServiceType, Vertical


class PreferredVendorFilterForm(forms.Form):
    source = forms.ModelChoiceField(queryset=Locale.objects.all().order_by('description'))
    target = forms.ModelChoiceField(queryset=Locale.objects.all().order_by('description'))
    vertical = forms.ModelChoiceField(queryset=Vertical.objects.all().order_by('description'), required=False)
    client = forms.ModelChoiceField(queryset=Client.objects.all().order_by('name'), required=False)
    service_type = forms.ModelChoiceField(queryset=ServiceType.objects.filter(available=True).order_by('description'))

    def __init__(self, *args, **kwargs):
        super(PreferredVendorFilterForm, self).__init__(*args, **kwargs)


PreferredVendorFormSet = modelformset_factory(PreferredVendor, fields='__all__', exclude=None, can_delete=True)
