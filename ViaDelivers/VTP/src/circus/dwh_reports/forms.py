from __future__ import unicode_literals
from django import forms
from django.conf import settings
from dwh_reports.models import ClientsReporting, ClientManager, ViaUserReporting, VendorUserReporting, ProjectsReporting, \
    VendorsReporting
from people.models import AccountType


class ClientsReportingClientManagerFilterForm(forms.ModelForm):
    client_poc_department = forms.ModelChoiceField(ClientsReporting.objects.none())

    def __init__(self, *args, **kwargs):
        super(ClientsReportingClientManagerFilterForm, self).__init__(*args, **kwargs)

        self.fields['client_poc'].queryset = ClientManager.objects.none()

        clients = ClientsReporting.objects.exclude(name='').order_by('name')
        self.fields['customer'].queryset = clients
        if len(clients) == 1:
            self.fields['customer'].initial = clients[0].pk

        # client_id = self._raw_value('customer') or \
        #             self.fields['customer'].initial or \
        #             self.initial.get('customer')
        client_id = self.fields['customer'].initial or \
                    self.initial.get('customer')

        if client_id:
            #Department
            client_poc_department = clients.filter(parent_id=client_id).order_by('name')
            self.fields['client_poc_department'].queryset = client_poc_department
            if len(client_poc_department) == 1:
                self.fields['client_poc_department'].initial = client_poc_department[0].pk

            # department_id = self._raw_value('client_poc_department') or \
            #         self.fields['client_poc_department'].initial or \
            #         self.initial.get('client_poc_department')

            department_id = self.fields['client_poc_department'].initial or \
                    self.initial.get('client_poc_department')

            if department_id:
                client_id = department_id

            client_list = []
            is_parent = False
            parents = clients.filter(parent_id=client_id)
            for parent in parents:
                client_list.append(parent.client_id)
                is_parent = True

            # client is known. Now I can display the matching children.
            if is_parent:
                client_poc = ClientManager.objects.filter(account__client_id__in=client_list).order_by('first_name')
            else:
                client_poc = ClientManager.objects.filter(account__client_id=client_id).order_by('first_name')

            self.fields['client_poc'].queryset = client_poc
            if len(client_poc) == 1:
                self.fields['client_poc'].initial = client_poc[0].pk



    class Meta:
        model = ProjectsReporting
        fields = [
            'customer',
            'client_poc'
        ]


class ClientsActivityReportingFilterForm(forms.ModelForm):
    name = forms.ModelChoiceField(ClientsReporting.objects.exclude(name='').order_by('name'))

    def __init__(self, *args, **kwargs):
        super(ClientsActivityReportingFilterForm, self).__init__(*args, **kwargs)

    class Meta:
        model = ClientsReporting
        fields = [
            'name',
        ]


class ClientsReportingFilterForm(forms.ModelForm):
    name = forms.ModelChoiceField(ClientsReporting.objects.exclude(name='').order_by('name'))
    client_poc_department = forms.ModelChoiceField(ClientsReporting.objects.none())
    user = None

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(ClientsReportingFilterForm, self).__init__(*args, **kwargs)
        clients = ClientsReporting.objects.exclude(name='').order_by('name')
        client_id = self.user
        if client_id:
            # client is known. Now I can display the matching children.
            client_poc_department = clients.filter(parent_id=client_id).order_by('name')
            self.fields['client_poc_department'].queryset = client_poc_department
            if len(client_poc_department) == 1:
                self.fields['client_poc_department'].initial = client_poc_department[0].pk

    class Meta:
        model = ClientsReporting
        fields = [
            'name',
        ]


class ClientManagerFilterForm(forms.ModelForm):
    user = None
    client_manager = forms.ModelChoiceField(ClientManager.objects.order_by('first_name'))
    client_poc_department = forms.ModelChoiceField(ClientsReporting.objects.none())

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(ClientManagerFilterForm, self).__init__(*args, **kwargs)
        client_id = self.user
        clients = ClientsReporting.objects.exclude(name='').order_by('name')

        client_poc_department = clients.filter(parent_id=self.user).order_by('name')
        self.fields['client_poc_department'].queryset = client_poc_department
        if len(client_poc_department) == 1:
            self.fields['client_poc_department'].initial = client_poc_department[0].pk

        # department_id = self._raw_value('client_poc_department') or \
        #                 self.fields['client_poc_department'].initial or \
        #                 self.initial.get('client_poc_department')

        department_id = self.fields['client_poc_department'].initial or \
                        self.initial.get('client_poc_department')

        if department_id:
            client_id = department_id

        client_list = []
        is_parent = False
        parents = clients.filter(parent_id=client_id)
        for parent in parents:
            client_list.append(parent.client_id)
            is_parent = True

        # client is known. Now I can display the matching children.
        if is_parent:
            client_manager = ClientManager.objects.filter(account__client_id__in=client_list).order_by('first_name')
        else:
            client_manager = ClientManager.objects.filter(account__client_id=client_id).order_by('first_name')

        self.fields['client_manager'].queryset = client_manager
        if len(client_manager) == 1:
            self.fields['client_manager'].initial = client_manager[0].pk

    class Meta:
        model = ClientManager
        fields = []


class ViaUserReportingFilterForm(forms.ModelForm):
    project_manager = forms.ModelChoiceField(ViaUserReporting.objects.all().order_by('first_name'))

    def __init__(self, *args, **kwargs):
        super(ViaUserReportingFilterForm, self).__init__(*args, **kwargs)
        self.fields['project_manager'].required = True

    class Meta:
        model = ViaUserReporting
        fields = [
            'project_manager'
        ]


class VendorUserReportingFilterForm(forms.ModelForm):
    project_manager = forms.ModelChoiceField(VendorsReporting.objects.all().select_related().order_by('name'))

    def __init__(self, *args, **kwargs):
        super(VendorUserReportingFilterForm, self).__init__(*args, **kwargs)
        self.fields['project_manager'].required = True

    class Meta:
        model = VendorUserReporting
        fields = [
            'project_manager'
        ]
