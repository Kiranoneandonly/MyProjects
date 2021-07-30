from django import forms
from django.conf import settings
from people.models import AccountType
from clients.models import Client, ClientManifest
from django.contrib.auth.models import Group
from accounts.models import CircusUser
from django.db.models import Q
from shared.group_permissions import CLIENT_DEFAULT_LEVEL_GROUP


class ClientForm(forms.ModelForm):
    minimum = forms.DecimalField(label='Minimum project cost', max_digits=15, decimal_places=3, required=False)

    def __init__(self, *args, **kwargs):
        super(ClientForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Client
        exclude = ['is_deleted', 'account_type', 'owner', 'admin', 'is_person_account', 'vendor_type']

    def save(self, commit=True):
        client = super(ClientForm, self).save(commit=False)
        client.account_type = AccountType.objects.get(code=settings.CLIENT_USER_TYPE)
        if commit:
            client.save()

        return client


class ClientManifestForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(ClientManifestForm, self).__init__(*args, **kwargs)

        self.get_client_users = CircusUser.objects.filter(account_id=self.instance.client.id)
        if not self.instance.default_client_user_level.all():
            self.initial['default_client_user_level'] = [g.id for g in Group.objects.filter(name=CLIENT_DEFAULT_LEVEL_GROUP)]

    def save(self, commit=True):
        if 'default_client_user_level' in self.changed_data:
            client_user_level_groups = self.cleaned_data.get('default_client_user_level', None)
            grp_obj = Group.objects
            remove_groups = grp_obj.filter(~Q(id__in=client_user_level_groups))
            #Removing the previous roles for the users of this client.
            for user in self.get_client_users:
                for rem_group in remove_groups:
                    user.remove_from_group(rem_group.name)
            #Assigning the default client level role for the users of this client.
            for user in self.get_client_users:
                for group in client_user_level_groups:
                    user.add_to_group(group.name)

        return super(ClientManifestForm, self).save(commit=commit)

    class Meta:
        model = ClientManifest
        exclude = ['client']
        exclude = ['is_deleted']


class NoteForm(forms.Form):
    note = forms.CharField(label="Notes", required=False, widget=forms.Textarea(attrs={'class': 'input-block-level'}))
    parent_note = forms.CharField(label="Parent Company Notes", required=False, widget=forms.Textarea(attrs={'class': 'input-block-level'}))
    client_id = forms.IntegerField(widget=forms.HiddenInput)

    @classmethod
    def for_client(cls, client):
        data = {
            'client_id': client.id,
            'note': client.manifest.note,
        }
        if client.parent:
            parent_manifest = ClientManifest.objects.get(client=client.parent)
            data['parent_note'] = parent_manifest.note
        return cls(data)
