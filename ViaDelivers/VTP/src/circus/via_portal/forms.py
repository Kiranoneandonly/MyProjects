# -*- coding: utf-8 -*-
from itertools import groupby
from django import forms
from django.db.models import Q
from django.forms.models import ModelChoiceIterator
from django.forms.widgets import CheckboxSelectMultiple, CheckboxFieldRenderer
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _
from clients.models import Client

from services.managers import FINAL_APPROVAL_SERVICE_TYPE
from services.models import ServiceType

from shared.widgets import DateTimeWidget
from projects.models import Project
from invoices.models import Invoice
from clients.models import ClientService

from django.conf import settings
from accounts.models import CircusUser


class ProjectAccountingSummaryForm(forms.ModelForm):
    ca_invoice_number = forms.CharField(required=False, max_length=100)
    original_price = forms.DecimalField(required=False)
    number_of_invoices = forms.IntegerField(required=False)

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        if instance:
            ca_invoice_number = instance.payment_details.ca_invoice_number
            #number_of_invoices = instance.number_of_invoices
            #import ipdb; ipdb.set_trace()
            initial = kwargs.get('initial', {})
            initial['ca_invoice_number'] = ca_invoice_number
            initial['original_price'] = instance.original_order_amount()
            kwargs['initial'] = initial

        super(ProjectAccountingSummaryForm, self).__init__(*args, **kwargs)
        self.fields['original_price'].label = 'Original Price'
        self.fields['original_invoice_count'].label = 'Original Invoice Count'
        self.fields['ca_invoice_number'].label = 'Purchase Order'
        self.fields['revenue_recognition_month'].label = 'Revenue Recognized'

    class Meta:
        model = Project
        fields = [
            'ca_invoice_number',
            'original_price',
            'revenue_recognition_month',
            'original_invoice_count'
        ]
        widgets = {
            'revenue_recognition_month': DateTimeWidget(),
        }

    def is_valid(self):
        return super(ProjectAccountingSummaryForm, self).is_valid()

    def clean(self):
        cleaned_data = super(ProjectAccountingSummaryForm, self).clean()
        #if not self.instance.kit.file_count():
        #    raise forms.ValidationError("Please upload at least one file for translation.")
        return cleaned_data



class GroupedChoiceFieldRenderer(CheckboxFieldRenderer):

    def render(self):
        """
        Outputs a <ul> for this set of choice fields.
        If an id was given to the field, it is applied to the <ul> (each
        item in the list will get an id of `$id_$i`).
        """
        # backported from Django 1.7
        # https://code.djangoproject.com/ticket/20931#comment:7
        id_ = self.attrs.get('id', None)
        start_tag = format_html('<ul id="{0}">', id_) if id_ else '<ul>'
        output = [start_tag]
        for i, choice in enumerate(self.choices):
            choice_value, choice_label = choice
            if isinstance(choice_label, (tuple, list)):
                attrs_plus = self.attrs.copy()
                if id_:
                    attrs_plus['id'] += '_{0}'.format(i)
                sub_ul_renderer = GroupedChoiceFieldRenderer(
                    name=self.name, value=self.value, attrs=attrs_plus,
                    choices=choice_label)
                sub_ul_renderer.choice_input_class = self.choice_input_class
                output.append(format_html('<li>{0}{1}</li>', choice_value,
                                          sub_ul_renderer.render()))
            else:
                w = self.choice_input_class(self.name, self.value,
                                            self.attrs.copy(), choice, i)
                output.append(format_html('<li>{0}</li>', force_text(w)))
        output.append('</ul>')
        return mark_safe('\n'.join(output))


class GroupedCheckboxSelectMultiple(CheckboxSelectMultiple):
    renderer = GroupedChoiceFieldRenderer


class EstimateForm(forms.ModelForm):
    analysis_csv = forms.FileField(required=False, label='Select file')
    # quantity = forms.DecimalField(required=False)

    def __init__(self, *args, **kwargs):
        super(EstimateForm, self).__init__(*args, **kwargs)
        services_field = self.fields['services']
        services_field.label = ''
        services_field.help_text = ''
        services_field.required = True
        services_field.queryset = ServiceType.objects.filter(available=True)\
            .filter(~Q(code=FINAL_APPROVAL_SERVICE_TYPE)).order_by('category').prefetch_related('category')

        if self.instance.internal_via_project:
            self.fields['services'].queryset = ServiceType.objects.filter(category=5)
        else:
            services_field.widget.choices = self._service_choices_by_category(services_field)
        if self.instance.id:
            if not self.instance.services.exists():
                client = self.instance.client_id
                client_service_list = ClientService.objects.filter(client_id=client, job_default=True)
                service_list = []
                for service in client_service_list:
                    service_list.append(service.service_id)

                self.initial['services'] = service_list

        large_jobs_approvers = CircusUser.objects.filter(user_type=settings.VIA_USER_TYPE, is_active=True).order_by('first_name')

        self.fields['project_manager_approver'].queryset = large_jobs_approvers
        self.fields['project_manager_approver'].label = ''
        self.fields['ops_management_approver'].queryset = large_jobs_approvers
        self.fields['ops_management_approver'].label = ''
        self.fields['sales_management_approver'].queryset = large_jobs_approvers
        self.fields['sales_management_approver'].label = ''
        # self.fields['quantity'].initial = ""

        self.fields['large_job_approval_notes'].widget.attrs['style'] = 'width: 99%;'
        self.fields['large_job_approval_notes'].label = 'Approval Notes'

        self.fields['large_job_approval_timestamp'].label = 'Approved Date'

    def _service_choices_by_category(self, services_field):

        def sortkey(item):
            return item[1]

        grouped_services = []
        # How to turn a ServiceType instance from the queryset into a choice
        # element? The built-in widgets do that with ModelChoiceIterator.
        # We don't actually iterate with it because we have multiple
        # sub-groups, but we can use its choice() method.
        choice_factory = ModelChoiceIterator(services_field).choice

        for category, services in groupby(services_field.queryset,
                                          lambda s: s.category):
            group_choices = sorted([choice_factory(service) for service in services], key=sortkey)
            group_label = category.description if category else u"Uncategorized"
            grouped_services.append((group_label, group_choices))

        return grouped_services

    class Meta:
        model = Project
        fields = [
            'analysis_csv',
            'services',
            'project_manager_approver',
            'ops_management_approver',
            'sales_management_approver',
            'large_job_approval_timestamp',
            'large_job_approval_notes',
        ]
        widgets = {"services": GroupedCheckboxSelectMultiple(),
                   'large_job_approval_timestamp': DateTimeWidget(), }


class InvoiceForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        if instance:
            project = instance.project
            initial = kwargs.get('initial', {})
            initial['project'] = project
            kwargs['initial'] = initial

        super(InvoiceForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Invoice
        fields = [
            'due_date', 'order_amount', 'invoice_amount', 'ok_to_invoice',
            'internal_notes', 'external_notes', 'billing_refnumber',
            'billing_txnnumber', 'billing_sync_date', 'billing_sent_date', 'billing_paid',
            'billing_paid_date'
        ]


def primary_client_account(account_number):
    if account_number is None:
        return None
    # Pick the parent Client with this account number.
    clients = Client.objects.filter(account_number=account_number).order_by("parent")
    return clients.last()


class DashboardFilterForm(forms.Form):

    def __init__(self, *args, **kwargs):
        super(DashboardFilterForm, self).__init__(*args, **kwargs)
        # the account_number field is not unique, so it doesn't work with the
        # default ModelChoiceField implementation.
        self.fields['client'].to_python = primary_client_account

    client = forms.ModelChoiceField(
        label=_(u"Client"),
        empty_label=_(u"(All)"),
        queryset=Client.objects.filter(project__isnull=False).distinct().order_by("name"),
        to_field_name="account_number"
    )
