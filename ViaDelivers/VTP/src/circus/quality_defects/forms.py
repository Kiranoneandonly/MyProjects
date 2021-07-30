from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from accounts.models import CircusUser
from clients.models import Client
from quality_defects.models import QualityDefect, QualityDefectComment
from shared.widgets import DateTimeWidget
from projects.models import Project
from tasks.models import Task
from vendors.models import Vendor


class QualityDefectForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(QualityDefectForm, self).__init__(*args, **kwargs)

        self.fields['title'].required = True
        self.fields['status'].required = True
        self.fields['priority'].required = True
        self.fields['quality_defect'].required = True

        self.fields['vendor'].label = _('Supplier')
        self.fields['vendor'].queryset = Vendor.objects.filter(is_deleted=False).order_by('name')

        self.fields['status'].initial = 'open'
        self.fields['priority'].initial = '2'
        self.fields['quality_defect'].initial = 'no'

        self.fields['assigned_to'].queryset = CircusUser.objects.filter(is_active=True, user_type=settings.VIA_USER_TYPE).order_by('first_name')
        self.fields['project'].queryset = Project.objects.none()
        self.fields['task'].queryset = Task.objects.none()


        clients = Client.objects.filter(is_deleted=False).order_by('name')
        self.fields['client'].queryset = clients
        if len(clients) == 1:
            self.fields['client'].initial = clients[0].pk

        from shared.forms import form_get_client_id
        client_id = form_get_client_id(self)

        if client_id:
            # client is known. Now I can display the matching children.
            from shared.forms import form_get_client_project
            project = form_get_client_project(client_id)
            self.fields['project'].queryset = project
            if len(project) == 1:
                self.fields['project'].initial = project[0].pk

        from shared.forms import form_get_project_id
        project_id = form_get_project_id(self)

        if project_id:
            from shared.forms import form_get_client_project_task
            task = form_get_client_project_task(project_id)
            self.fields['task'].queryset = task
            if len(task) == 1:
                self.fields['task'].initial = task[0].pk

    class Meta:
        model = QualityDefect
        exclude = []
        fields = [
            'quality_defect',
            'title',
            'due_date',
            'status',
            'assigned_to',
            'priority',
            'vertical',
            'client',
            'project',
            'task',
            'vendor',
            'root_cause',
            'root_cause_analysis',
            'resolution',
            'client_consulted',
            'client_consulted_notes',
            'related_qd',
            'client_informed',
            'closed_date'
        ]
        widgets = {
            'due_date': DateTimeWidget(),
            'closed_date': DateTimeWidget(),
        }


class QualityDefectCommentForm(forms.Form):
    comment = forms.CharField()
    #quality_defect = forms.ForeignKey(QualityDefect)