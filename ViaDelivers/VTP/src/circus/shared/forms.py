from __future__ import unicode_literals
import base64
import datetime
import hmac
import json
from hashlib import sha1

from django import forms
from django.conf import settings
from django.utils.safestring import mark_safe


class S3UploadForm(forms.Form):
    """
    http://developer.amazonwebservices.com/connect/entry.jspa?externalID=1434

    <input type="hidden" name="key" value="uploads/${filename}">
    <input type="hidden" name="AWSAccessKeyId" value="YOUR_AWS_ACCESS_KEY">
    <input type="hidden" name="acl" value="private">
    <input type="hidden" name="success_action_redirect" value="http://localhost/">
    <input type="hidden" name="policy" value="YOUR_POLICY_DOCUMENT_BASE64_ENCODED">
    <input type="hidden" name="signature" value="YOUR_CALCULATED_SIGNATURE">
    <input type="hidden" name="content_type" value="image/jpeg">
    """
    key = forms.CharField(widget=forms.HiddenInput)
    AWSAccessKeyId = forms.CharField(widget=forms.HiddenInput)
    acl = forms.CharField(widget=forms.HiddenInput)
    success_action_redirect = forms.CharField(widget=forms.HiddenInput)
    policy = forms.CharField(widget=forms.HiddenInput)
    signature = forms.CharField(widget=forms.HiddenInput)
    content_type = forms.CharField(widget=forms.HiddenInput)
    file = forms.FileField()

    def __init__(self, key, success_action_redirect=None,
                 expires_after=datetime.timedelta(days=1), acl=settings.AWS_DEFAULT_ACL,
                 content_type=''):

        self.aws_access_key = settings.AWS_ACCESS_KEY_ID
        self.aws_secret_key = settings.AWS_SECRET_ACCESS_KEY
        self.bucket = settings.AWS_STORAGE_BUCKET_NAME
        self.key = key
        self.expires_after = expires_after
        self.acl = acl
        self.success_action_redirect = success_action_redirect
        self.content_type = content_type

        policy = base64.b64encode(self.calculate_policy())
        signature = self.sign_policy(policy)

        initial = {
            'key': self.key,
            'AWSAccessKeyId': self.aws_access_key,
            'acl': self.acl,
            'policy': policy,
            'signature': signature,
            'content_type': self.content_type,
        }
        if self.success_action_redirect:
            initial['success_action_redirect'] = self.success_action_redirect

        super(S3UploadForm, self).__init__(initial=initial)

        self.fields['content_type'].widget.attrs.update({'name': 'Content-Type'})

        # Don't include success_action_redirect if it's not being used
        if not self.success_action_redirect:
            del self.fields['success_action_redirect']

    def add_prefix(self, field_name):
        # Hack to use the S3 required field name
        if field_name == 'content_type':
            field_name = 'Content-Type'
        return super(S3UploadForm, self).add_prefix(field_name)

    def as_html(self):
        """
        Use this instead of as_table etc, because S3 requires the file field
        come AFTER the hidden fields, but Django's normal form display methods
        position the visible fields BEFORE the hidden fields.
        """
        html = '\n'.join(map(unicode, self.hidden_fields()))
        html += unicode(self['file'])
        return mark_safe(html)

    def as_form_html(self, prefix='', suffix=''):
        html = """
        <form action="%s" method="post" enctype="multipart/form-data">
        <p>%s</p>
        <button id="delivery_kit" type="submit" class="btn btn-primary pull-right">Upload</button>
        <a id="cancel" class="close opaque btn pull-right" href="#">Cancel</a>
        </form>
        """.strip() % (self.action(), self.as_html())
        return mark_safe(html)

    def as_support_form_html(self, prefix='', suffix=''):
        html = """
        <form action="%s" method="post" enctype="multipart/form-data">
        <p>%s</p>
        <button id="delivery_support_kit" type="submit" class="btn btn-primary pull-right">Upload</button>
        <a id="cancel" class="close opaque btn pull-right" href="#">Cancel</a>
        </form>
        """.strip() % (self.action(), self.as_html())
        return mark_safe(html)

    def is_multipart(self):
        return True

    def action(self):
        return 'https://%s.s3.amazonaws.com/' % self.bucket

    def calculate_policy(self):
        conditions = [
            {'bucket': self.bucket},
            {'acl': self.acl},
            ['starts-with', '$key', self.key.replace('${filename}', '')],
            ['starts-with', '$Content-Type', ''],
        ]
        if self.success_action_redirect:
            conditions.append(
                {'success_action_redirect': self.success_action_redirect},
                )

        policy_document = {
            "expiration": (datetime.datetime.now() + self.expires_after).isoformat().split('.')[0] + 'Z',
            "conditions": conditions,
            }
        return json.dumps(policy_document, indent=2)

    def sign_policy(self, policy):
        return base64.b64encode(hmac.new(self.aws_secret_key, policy, sha1).digest())


def form_get_client_id(form):
    try:
        client_id = form.data.get('client') or \
                    form.fields['client'].initial or \
                    form.initial.get('client')
        return client_id
    except:
        return None


def form_get_client_poc(client_id):
    try:
        # client is known. Now I can display the matching children.
        from clients.models import ClientContact
        return ClientContact.objects.filter(account__id=client_id, is_active=True).order_by('first_name')
    except:
        return None


def form_get_project_id(form):
    try:
        project_id = form.data.get('project') or \
                     form.fields['project'].initial or \
                     form.initial.get('project')
        return project_id
    except:
        return None


def form_get_client_project(client_id):
    try:
        # client is known. Now I can display the matching children.
        from projects.models import Project
        return Project.objects.select_related().filter(client_id=client_id).order_by('job_number')
    except:
        return None


def form_get_client_project_task(project_id):
    try:
        # client is known. Now I can display the matching children.
        from tasks.models import Task
        return Task.objects.select_related().filter(project_id=project_id)
    except:
        return None