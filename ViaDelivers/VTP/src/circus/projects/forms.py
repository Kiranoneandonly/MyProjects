from django import forms
from django.conf import settings
from django.forms import TextInput, RadioSelect, modelformset_factory
from django.utils.translation import ugettext_lazy as _

from accounts.models import CircusUser
from clients.models import Client
from finance.models import PAYMENT_CHOICES
from projects.models import Project, ProjectJobOptions
from services.managers import DEFAULT_INDUSTRY_CODE
from shared.widgets import DateTimeWidget
from django.forms.widgets import HiddenInput

from services.models import ServiceType
from django.forms.widgets import CheckboxSelectMultiple
from tinymce import TinyMCE
from shared.group_permissions import PROTECTED_HEALTH_INFORMATION_GROUP


RESTRICTED_CHOICES = (
        (True, _(u'Restricted Access')),
        (False, _(u'Unrestricted Access')),
    )

SECURE_JOB_CHOICES= (
        (True, _(u'Limit Team')),
        (False, _(u'Full Team')),
    )


class ProjectNewAutoJobForm(forms.ModelForm):
    project_reference_name = forms.CharField(required=False, max_length=100)

    def __init__(self, *args, **kwargs):
        super(ProjectNewAutoJobForm, self).__init__(*args, **kwargs)
        self.fields['name'].label = _('Job Name')
        self.fields['name'].help_text = ''
        self.fields['name'].required = True

        self.fields['job_number'].required = False

        self.fields['client_poc'].queryset = CircusUser.objects.none()

        self.fields['project_reference_name'].label = _('Client Job Reference')
        self.fields['internal_via_project'].label = _('No Client View')

        clients = Client.objects.filter(is_deleted=False).order_by('name')
        self.fields['client'].queryset = clients
        if len(clients) == 1:
            self.fields['client'].initial = clients[0].pk

        from shared.forms import form_get_client_id
        client_id = form_get_client_id(self)

        if client_id:
            # client is known. Now I can display the matching children.
            from shared.forms import form_get_client_poc
            client_poc =  form_get_client_poc(client_id)
            self.fields['client_poc'].queryset = client_poc
            if len(client_poc) == 1:
                self.fields['client_poc'].initial = client_poc[0].pk

    class Meta:
        model = Project
        exclude = ['kit', 'status', 'estimate_type']
        fields = [
            'job_number',
            'name',
            'client',
            'client_poc',
            'project_reference_name',
            'internal_via_project',
        ]
        widgets = {
            'job_number': TextInput(attrs={'placeholder': '(Leave this to auto-generate)'}),
        }


class ProjectAutoJobContinueForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ProjectAutoJobContinueForm, self).__init__(*args, **kwargs)
        self.fields['source_locale'].queryset = self.fields['source_locale'].queryset.filter(available=True)
        self.fields['source_locale'].required = True
        self.fields['target_locales'].help_text = ''
        self.fields['target_locales'].required = True
        self.fields['target_locales'].queryset = self.fields['target_locales'].queryset.filter(available=True)
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
            'is_secure_job'
        ]
        widgets = {
            'services': CheckboxSelectMultiple(),
            'is_restricted_job': RadioSelect(choices=RESTRICTED_CHOICES),
            'is_secure_job': RadioSelect(choices=SECURE_JOB_CHOICES),
        }

    def clean(self):
        cleaned_data = super(ProjectAutoJobContinueForm, self).clean()
        if not self.instance.kit.file_count():
            raise forms.ValidationError("Please upload at least one file for translation.")
        return cleaned_data


class ProjectForm(forms.ModelForm):

    payment_method = forms.ChoiceField(choices=PAYMENT_CHOICES, initial='ca', widget=forms.RadioSelect())
    ca_invoice_number = forms.CharField(required=False, max_length=100)
    rush_estimate = forms.BooleanField(required=False)
    project_reference_name = forms.CharField(required=False, max_length=100)
    reschedule_all_due_dates = forms.BooleanField(required=False, widget=forms.HiddenInput())

    instructions = forms.CharField(widget=TinyMCE(attrs={'cols': settings.TINYMCE_COLS, 'rows': settings.TINYMCE_ROWS}), required=False)
    instructions_via = forms.CharField(widget=TinyMCE(attrs={'cols': settings.TINYMCE_COLS, 'rows': settings.TINYMCE_ROWS}), required=False)
    instructions_vendor = forms.CharField(widget=TinyMCE(attrs={'cols': settings.TINYMCE_COLS, 'rows': settings.TINYMCE_ROWS}), required=False)

    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        self.fields['name'].label = _('Job Name')
        self.fields['name'].help_text = ''
        self.fields['name'].required = True

        self.fields['source_locale'].help_text = ''
        self.fields['source_locale'].required = True
        self.fields['source_locale'].queryset = self.fields['source_locale'].queryset.filter(available=True)

        self.fields['target_locales'].help_text = ''
        self.fields['target_locales'].required = True
        self.fields['target_locales'].queryset = self.fields['target_locales'].queryset.filter(available=True)
        if self.instance.id:
            target_count = u" (%s)" % (self.instance.target_locales_count(),)
            self.fields['target_locales'].label += target_count

        if self.instance.is_phi_secure_job:
            via_users = CircusUser.objects.filter(user_type=settings.VIA_USER_TYPE, groups__name=PROTECTED_HEALTH_INFORMATION_GROUP).order_by('first_name')
        else:
            via_users = CircusUser.objects.filter(user_type=settings.VIA_USER_TYPE).order_by('first_name')

        self.fields['project_manager'].queryset = via_users
        self.fields['account_executive'].queryset = via_users
        self.fields['estimator'].queryset = via_users
        self.fields['industry'].queryset = self.fields['industry'].queryset.exclude(code=DEFAULT_INDUSTRY_CODE)

        self.fields['is_restricted_job'].label = _('Access')
        self.fields['is_restricted_job'].help_text = ''
        self.fields['is_restricted_job'].initial = False

        self.fields['is_secure_job'].label = _('Secure Job')
        self.fields['is_secure_job'].help_text = ''
        self.fields['is_secure_job'].initial = False

        self.fields['is_phi_secure_job'].label = _('PHI Job')
        self.fields['is_phi_secure_job'].help_text = ''
        self.fields['is_phi_secure_job'].initial = False

        self.fields['delay_job_po'].label = _('PO Basis')
        self.fields['delay_job_po'].help_text = ''
        self.fields['delay_job_po'].initial = False

        self.fields['restricted_locations'].help_text = ''
        self.fields['restricted_locations'].label = _('Restricted Region')
        self.fields['restricted_locations'].required = False
        if self.instance.id:
            restricted_locations_count = u" (%s)" % (self.instance.restricted_locations.count(),)
            self.fields['restricted_locations'].label += restricted_locations_count

        self.fields['completed'].label = _('Downloaded Date')

        self.fields['job_number'].required = False

        self.fields['project_reference_name'].label = _('Client Job Reference')
        self.fields['internal_via_project'].label = _('No Client Access')
        self.fields['no_express_option'].label = _('No Client Express')
        self.fields['ignore_holiday_flag'].label = _('Holidays Ignored')

        if not self.instance.can_edit_locales():
            # select widgets don't necessarily have a readonly attribute, but
            # we can use this to get select2.js to use read-only mode.
            self.fields['source_locale'].widget.attrs['readonly'] = True
            self.fields['target_locales'].widget.attrs['readonly'] = True
            # if select2 isn't working, we can discourage editing by limiting
            # the querysets to the current values. Not entirely bulletproof
            # against removing current targets, but will discourage other changes.
            self.fields['source_locale'].queryset = self.fields['source_locale'].queryset.filter(id=self.instance.source_locale_id)
            self.fields['target_locales'].queryset = self.instance.target_locales

        self.fields['ca_invoice_number'].label = 'Purchase Order'
        if self.instance.payment_details:
            self.fields['payment_method'].initial = self.instance.payment_details.payment_method
            self.fields['ca_invoice_number'].initial = self.instance.payment_details.ca_invoice_number

        # chained select filter based upon the chosen Client Company

        self.fields['client_poc'].queryset = CircusUser.objects.none()

        clients = Client.objects.filter(is_deleted=False).order_by('name')
        self.fields['client'].queryset = clients
        if len(clients) == 1:
            self.fields['client'].initial = clients[0].pk

        # client_id = self.fields['client'].initial or \
        #             self.initial.get('client')
        from shared.forms import form_get_client_id
        client_id = form_get_client_id(self)

        if client_id:
            # client is known. Now I can display the matching children.
            from shared.forms import form_get_client_poc
            client_poc =  form_get_client_poc(client_id)
            self.fields['client_poc'].queryset = client_poc
            if len(client_poc) == 1:
                self.fields['client_poc'].initial = client_poc[0].pk

        if self.instance.canceled or self.instance.is_canceled_status():
            self.fields['canceled'].label = _('Canceled')
            self.fields['canceled'].initial = self.instance.canceled
        else:
            self.fields['canceled'].label = ''
            self.fields["canceled"].widget = HiddenInput()

    class Meta:
        model = Project
        exclude = ['kit', 'status', 'estimate_type']
        fields = [
            'job_number',
            'name',
            'project_speed',
            'client',
            'client_poc',
            'industry',
            'project_manager',
            'account_executive',
            'estimator',
            'source_locale',
            'target_locales',
            'quote_due',
            'quoted',
            'started_timestamp',
            'due',
            'delivered',
            'completed',
            'payment_method',
            'ca_invoice_number',
            'rush_estimate',
            'instructions',
            'instructions_via',
            'instructions_vendor',
            'is_restricted_job',
            'delay_job_po',
            'restricted_locations',
            'project_reference_name',
            'internal_via_project',
            'canceled',
            'no_express_option',
            'ignore_holiday_flag',
            'price_per_document',
            'is_secure_job',
            'is_phi_secure_job'
        ]
        widgets = {
            'quote_due': DateTimeWidget(),
            'quoted': DateTimeWidget(),
            'started_timestamp': DateTimeWidget(),
            'due': DateTimeWidget(),
            'delivered': DateTimeWidget(),
            'completed': DateTimeWidget(),
            'job_number': TextInput(attrs={'placeholder': '(Leave this to auto-generate)'}),
            'is_restricted_job': RadioSelect(choices=RESTRICTED_CHOICES),
            'is_secure_job': RadioSelect(choices=SECURE_JOB_CHOICES),
            'delay_job_po': RadioSelect(),
            'canceled': DateTimeWidget(),
        }


class ViaInstructionsForm(forms.Form):
    via_instructions = forms.CharField()


class ProjectJobOptionsForm(forms.ModelForm):
    editable_source = forms.BooleanField(required=False)
    recreation_source = forms.BooleanField(required=False)
    translation_unformatted = forms.BooleanField(required=False)
    translation_billingual = forms.BooleanField(required=False)

    class Meta:
        model = ProjectJobOptions
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ProjectJobOptionsForm, self).__init__(*args, **kwargs)
        self.fields['editable_source'].label = 'Editable Source on Approval (MS Office, InDesign, etc.)'
        self.fields['recreation_source'].label = 'Full Recreation of Source from PDFs (MS Office) '
        self.fields['translation_unformatted'].label = 'Translation Only as an Unformatted MS Word document'
        self.fields['translation_billingual'].label = 'Translation Only as a Bilingual MS Word document (two columns)'

ProjectJobOptionsSet = modelformset_factory(ProjectJobOptions, fields='__all__', exclude=None, can_delete=True)


class ViaWorkflowForm(forms.ModelForm):
    cost = forms.DecimalField(required=False)
    price = forms.DecimalField(required=False)
    express_cost = forms.DecimalField(required=False)
    express_price = forms.DecimalField(required=False)

    def __init__(self, *args, **kwargs):
        super(ViaWorkflowForm, self).__init__(*args, **kwargs)
        self.fields['name'].label = _('Job Name')
        self.fields['name'].help_text = ''
        self.fields['name'].required = True

        self.fields['source_locale'].help_text = ''
        self.fields['source_locale'].required = True
        self.fields['source_locale'].queryset = self.fields['source_locale'].queryset.filter(available=True)

        self.fields['target_locales'].help_text = ''
        self.fields['target_locales'].required = True
        self.fields['target_locales'].queryset = self.fields['target_locales'].queryset.filter(available=True)
        if self.instance.id:
            target_count = u" (%s)" % (self.instance.target_locales.count(),)
            self.fields['target_locales'].label += target_count

        self.fields['services'].label = ''
        self.fields['services'].help_text = ''
        self.fields['services'].required = True
        self.fields['services'].queryset = ServiceType.objects.filter(available=True, workflow=True).order_by('category', 'description')

        self.fields['job_number'].required = True
        self.fields['industry'].queryset = self.fields['industry'].queryset.exclude(code=DEFAULT_INDUSTRY_CODE)

        self.fields['client_poc'].queryset = CircusUser.objects.none()

        clients = Client.objects.filter(is_deleted=False).order_by('name')
        self.fields['client'].queryset = clients
        if len(clients) == 1:
            self.fields['client'].initial = clients[0].pk

        from shared.forms import form_get_client_id
        client_id = form_get_client_id(self)

        if client_id:
            # client is known. Now I can display the matching children.
            from shared.forms import form_get_client_poc
            client_poc = form_get_client_poc(client_id)
            self.fields['client_poc'].queryset = client_poc
            if len(client_poc) == 1:
                self.fields['client_poc'].initial = client_poc[0].pk

    class Meta:
        model = Project
        fields = [
            'job_number',
            'client',
            'client_poc',
            'name',
            'source_locale',
            'target_locales',
            'industry',
            'services',
            'cost',
            'price',
            'express_cost',
            'express_price',
        ]
        widgets = {
            'services': CheckboxSelectMultiple(),
        }

