from django import forms
from projects.models import Delivery
from tasks.models import Task


class DeliveryForm(forms.ModelForm):

    class Meta:
        model = Delivery
        exclude = ['is_deleted', 'project', 'vendor']

    def __init__(self, project, vendor, *args, **kwargs):
        super(DeliveryForm, self).__init__(*args, **kwargs)
        self.fields['tasks'].help_text = u'Select all tasks that are completed by this delivery.'
        self.fields['tasks'].queryset = Task.objects.pending_completion().filter(project=project, vendor=vendor)
        self.fields['tasks'].widget = forms.CheckboxSelectMultiple(choices=self.fields['tasks'].choices)
