from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth import get_user_model
from django.forms.widgets import CheckboxSelectMultiple, RadioSelect
from django.utils.translation import ugettext_lazy as _
from django import forms
from accounts.models import CircusUser
from localization_kits.models import FileAnalysis, FileAsset

from clients.models import Client
from finance.models import PAYMENT_CHOICES
from people.models import JoinAccountRequest, Account
from projects.models import Project
from services.managers import DEFAULT_INDUSTRY_CODE
from services.models import ServiceType
from tinymce import TinyMCE
from projects.forms import RESTRICTED_CHOICES, SECURE_JOB_CHOICES
#from shared.fields import CreditCardField, ExpiryDateField


class ClientOrderForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        super(ClientOrderForm, self).__init__(*args, **kwargs)
        self.fields['source_locale'].queryset = self.fields['source_locale'].queryset.filter(available=True)
        self.fields['source_locale'].required = True
        self.fields['target_locales'].help_text = ''
        self.fields['target_locales'].required = True
        self.fields['target_locales'].queryset = self.fields['target_locales'].queryset.filter(available=True)

        self.fields['assigned_to'].label = 'Assign to'
        self.fields['assigned_to'].help_text = ''
        self.fields['assigned_to'].required = False
        self.fields['assigned_to'].queryset = CircusUser.objects.filter(user_type=settings.CLIENT_USER_TYPE , account=self.user.account ).order_by('first_name')

        self.fields['services'].label = ''
        self.fields['services'].help_text = ''
        self.fields['services'].required = True

        self.fields['is_restricted_job'].label = _('Access')
        self.fields['is_restricted_job'].help_text = ''
        self.fields['is_restricted_job'].initial = False

        self.fields['is_secure_job'].label = _('Secure Job')
        self.fields['is_secure_job'].help_text = ''
        self.fields['is_secure_job'].initial = False

        self.fields['services'].queryset = ServiceType.objects.filter(
            clientservice__client=self.instance.client,
            clientservice__available=True,
            available=True
        ).order_by('-description')

        self.fields['industry'].queryset = self.fields['industry'].queryset.exclude(code=DEFAULT_INDUSTRY_CODE)

    class Meta:
        model = Project
        fields = [
            'industry',
            'source_locale',
            'target_locales',
            'services',
            'is_restricted_job',
            'assigned_to',
            'is_secure_job'
        ]
        widgets = {
            'services': CheckboxSelectMultiple(),
            'is_restricted_job': RadioSelect(choices=RESTRICTED_CHOICES),
            'is_secure_job': RadioSelect(choices=SECURE_JOB_CHOICES),
        }

    def clean(self):
        cleaned_data = super(ClientOrderForm, self).clean()
        if not self.instance.kit.file_count():
            raise forms.ValidationError("Please upload at least one file for translation.")
        return cleaned_data


class ClientApproveQuoteForm(forms.ModelForm):

    payment_method = forms.ChoiceField(choices=PAYMENT_CHOICES, initial='ca', widget=forms.RadioSelect())
    ca_invoice_number = forms.CharField(required=False, max_length=100)
    instructions = forms.CharField(widget=TinyMCE(attrs={'cols': settings.TINYMCE_COLS, 'rows': settings.TINYMCE_ROWS}), required=False)
    accept_terms_and_conditions = forms.BooleanField(required=True, initial=False, label='', error_messages={'required': 'Required.'})
    project_reference_name = forms.CharField(required=False, max_length=100)

    def __init__(self, *args, **kwargs):
        super(ClientApproveQuoteForm, self).__init__(*args, **kwargs)
        self.fields['project_speed'].widget = forms.RadioSelect(choices=self.fields['project_speed'].choices)
        self.fields['ca_invoice_number'].label = 'Purchase Order'
        self.fields['project_reference_name'].label = 'Job Reference'
        if self.instance.payment_details:
            self.fields['payment_method'].initial = self.instance.payment_details.payment_method
            self.fields['ca_invoice_number'].initial = self.instance.payment_details.ca_invoice_number

    class Meta:
        model = Project
        fields = [
            'accept_terms_and_conditions',
            'project_speed',
            'instructions',
            'ca_invoice_number',
            'project_reference_name',
        ]


class ClientManualQuoteForm(forms.ModelForm):
    instructions = forms.CharField(widget=TinyMCE(attrs={'cols': settings.TINYMCE_COLS, 'rows': settings.TINYMCE_ROWS}), required=False)
    auto_approved = forms.BooleanField(required=False)
    ca_invoice_number = forms.CharField(required=False)
    project_reference_name = forms.CharField(required=False)
    editable_source = forms.BooleanField(required=False)
    recreation_source = forms.BooleanField(required=False)
    translation_unformatted = forms.BooleanField(required=False)
    translation_billingual = forms.BooleanField(required=False)

    def __init__(self, pk=None, *args, **kwargs):
        super(ClientManualQuoteForm, self).__init__(*args, **kwargs)
        self.fields['auto_approved'].label = 'Automatically approve Manual Estimate'
        self.fields['auto_approved'].initial = self.instance.approved

        self.fields['ca_invoice_number'].label = None
        self.fields['ca_invoice_number'].widget.attrs['placeholder'] = _("Purchase Order")
        self.fields['ca_invoice_number'].widget.attrs['class'] = "form-control"

        self.fields['instructions'].label = None
        self.fields['instructions'].widget.attrs['placeholder'] = _("Special Instructions")
        self.fields['instructions'].widget.attrs['class'] = "form-control"

        self.fields['project_reference_name'].label = None
        self.fields['project_reference_name'].widget.attrs['placeholder'] = _("Job Reference")
        self.fields['project_reference_name'].widget.attrs['class'] = "form-control"

        self.fields['editable_source'].label = 'Editable Source on Approval (MS Office, InDesign, etc.)'
        self.fields['recreation_source'].label = 'Full Recreation of Source from PDFs (MS Office) '
        self.fields['translation_unformatted'].label = 'Translation Only as an Unformatted MS Word document'
        self.fields['translation_billingual'].label = 'Translation Only as a Bilingual MS Word document (two columns)'

        if self.instance.payment_details:
            self.fields['ca_invoice_number'].initial = self.instance.payment_details.ca_invoice_number

    def clean(self):
        cleaned_data = self.cleaned_data
        ca_invoice_number = cleaned_data.get("ca_invoice_number")
        auto_approved = cleaned_data.get("auto_approved")

        # require CA when auto_approved selected
        if auto_approved:
            if not ca_invoice_number:
                msg = u"Please enter if you select Automatically Approve Manual Estimate."
                self._errors["ca_invoice_number"] = self.error_class([msg])

                # These fields are no longer valid. Remove them from the cleaned data.
                del cleaned_data["ca_invoice_number"]

        # Always return the full collection of cleaned data.
        return cleaned_data

    class Meta:
        model = Project
        fields = [
            'instructions',
            'auto_approved',
            'ca_invoice_number',
            'project_reference_name'
        ]


class ClientRegisterForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ClientRegisterForm, self).__init__(*args, **kwargs)
        for field in ['first_name', 'last_name', 'mailing_street', 'mailing_city', 'mailing_state', 'mailing_postal_code']:
            self.fields[field].required = True

        self.fields['mailing_street'].label = 'Street'
        self.fields['mailing_city'].label = 'City'
        self.fields['mailing_state'].label = 'State'
        self.fields['mailing_postal_code'].label = 'Postal Code'
        self.fields['mailing_country'].label = 'Country'

    class Meta:
        model = get_user_model()
        fields = [
            'email',
            'first_name',
            'last_name',
            'title',
            'department',
            'phone',
            'mailing_street',
            'mailing_city',
            'mailing_state',
            'mailing_postal_code',
            'mailing_country'
        ]

    def save(self, commit=True):
        user = super(ClientRegisterForm, self).save(False)
        user.profile_complete = True
        user.save()


class ClientAccountForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ClientAccountForm, self).__init__(*args, **kwargs)
        self.fields['name'].label = self.instance.client_type.title() + " Name"

    class Meta:
        model = Client
        fields = [
            'name',
            'website',
            'phone',
            'fax',
            'billing_street',
            'billing_city',
            'billing_state',
            'billing_postal_code',
            'billing_country'
        ]


class JoinClientForm(forms.ModelForm):
    account = forms.ModelChoiceField(
        Account.objects.none(),
        label=_('Select your organization/department'),
        empty_label=None
    )

    def __init__(self, *args, **kwargs):
        clients = kwargs.pop('clients')
        super(JoinClientForm, self).__init__(*args, **kwargs)
        self.fields['account'].queryset = clients

    class Meta:
        model = JoinAccountRequest
        fields = ['account']
