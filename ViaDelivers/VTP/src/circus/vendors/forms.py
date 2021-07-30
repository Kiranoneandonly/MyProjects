from django import forms
from django.conf import settings
from people.models import AccountType
from vendors.models import Vendor


class VendorForm(forms.ModelForm):
    minimum = forms.DecimalField(label='Minimum translation charge per language', max_digits=15, decimal_places=3, required=False)

    class Meta:
        model = Vendor
        exclude = ['via_team_jobs_email', 'admin', 'is_person_account', 'is_deleted', 'account_type', 'vertical',
                   'pricing_scheme', 'parent', 'owner', 'express_factor', 'auto_estimate_jobs', 'auto_start_workflow',
                   'salesforce_account_id', ]

    def save(self, commit=True):
        vendor = super(VendorForm, self).save(commit=False)
        vendor_account = AccountType.objects.get(code=settings.VENDOR_USER_TYPE)
        vendor.account_type = vendor_account
        if commit:
            vendor.save()
        return vendor
