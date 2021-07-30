from __future__ import unicode_literals
import hashlib
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, ReadOnlyPasswordHashField, PasswordChangeForm, SetPasswordForm, \
    PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import mail_admins
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import ugettext_lazy as _
from notifications.notifications import confirm_account, send_email, get_notify_email_subject
from django.utils import timezone
from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404
from django.db.models import Q
from clients.models import Client
from people.models import Account


class CircusAuthenticationForm(AuthenticationForm):
    error_messages = {
        'invalid_login': _("Please enter a valid %(username)s and password. "
                           "Note that both fields are be case-sensitive."),
        'no_cookies': _("Your Web browser doesn't appear to have cookies "
                        "enabled. Cookies are required to log in."),
        'inactive': _("This account is inactive."),
    }

    def __init__(self, *args, **kwargs):
        super(CircusAuthenticationForm, self).__init__(*args, **kwargs)
        self.fields['username'].label = None
        self.fields['username'].widget.attrs['placeholder'] = _("Email address")
        self.fields['username'].widget.attrs['class'] = "form-control"
        self.fields['password'].widget.attrs['placeholder'] = _("Password")
        self.fields['password'].widget.attrs['class'] = "form-control"

    def full_clean(self):
        stripped_data = {}
        for k, v in self.data.items():
            stripped_data[k] = v.strip()
            self.data = stripped_data
        super(CircusAuthenticationForm, self).full_clean()


class CircusUserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(label=_("Password"),
                                         help_text=_("Raw passwords are not stored, so there is no way to see "
                                                     "this user's password, but you can change the password "
                                                     "using <a href=\"../password/\">this form</a>."))

    class Meta:
        model = get_user_model()
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(CircusUserChangeForm, self).__init__(*args, **kwargs)
        f = self.fields.get('user_permissions', None)
        if f is not None:
            f.queryset = f.queryset.select_related('content_type')

    def clean_password(self):
        # Regardless of what the user provides, return the initial value.
        # This is done here, rather than on the field, because the
        # field does not have access to the initial value
        return self.initial["password"]


# used in admin to create user
class CircusUserCreationForm(forms.ModelForm):
    error_messages = {
        'duplicate_email': _("A user with that email already exists."),
        'password_mismatch': _("The two password fields didn't match."),
        }
    password1 = forms.CharField(label=_("Password"),
                                widget=forms.PasswordInput)
    password2 = forms.CharField(label=_("Password confirmation"),
                                widget=forms.PasswordInput,
                                help_text=_("Enter the same password as above, for verification."))

    class Meta:
        model = get_user_model()
        fields = ("email",)

    def __init__(self, *args, **kwargs):
        user = None
        if 'current_user' in kwargs:
            user = kwargs.pop('current_user')

        super(CircusUserCreationForm, self).__init__(*args, **kwargs)

        if user:
            client = get_object_or_404(Client, id=user.account.id)
            if client.manifest.enforce_customer_hierarchy and user.is_client_organization_administrator:
                if user.has_perm('clients.client_admin_access_child_departments'):
                    user_list = get_user_model().objects.filter(Q(account=user.account) | Q(account__in=user.account.children.all()))
                else:
                    user_list = get_user_model().objects.filter(account=user.account)

                departments_list = []
                for u in user_list:
                    departments_list.append(u.account.id)
                departments = Account.objects.filter(id__in=departments_list)

                self.fields['account'] = forms.ModelChoiceField(queryset=departments, empty_label="Select a Department...")

    def clean_email(self):
        # Since email is unique, this check is redundant,
        # but it sets a nicer error message than the ORM. See #13147.
        email = self.cleaned_data["email"]
        try:
            self._meta.model._default_manager.get(email=email)
        except self._meta.model.DoesNotExist:
            return email
        raise forms.ValidationError(self.error_messages['duplicate_email'])

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages['password_mismatch'])
        return password2

    def save(self, commit=True):
        user = super(CircusUserCreationForm, self).save(commit=False)
        user.account_type = settings.CLIENT_USER_TYPE
        user.set_password(self.cleaned_data["password1"])
        user.last_login = timezone.now()
        if commit:
            user.save()
        return user


class ProfileForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email', 'title', 'department', 'phone', 'user_timezone']


def validate_password(password):
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        raise forms.ValidationError(_("Your password must be at least %d characters long.") % settings.MIN_PASSWORD_LENGTH)


class ClientProfileForm(forms.ModelForm):
    new_password1 = forms.CharField(label=_("New password"), widget=forms.PasswordInput(), required=False)
    new_password2 = forms.CharField(label=_("New password confirmation"), widget=forms.PasswordInput(), required=False)

    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'title', 'department', 'phone', 'user_timezone', 'is_active']

    def clean_new_password1(self):
        password1 = self.cleaned_data.get('new_password1')
        if password1:
            validate_password(self.cleaned_data['new_password1'])
        return password1

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 or password2:
            if password1 != password2:
                raise forms.ValidationError(_("The two password fields didn't match."))
        return password2

    def save(self, commit=True):
        if self.cleaned_data['new_password1']:
            self.instance.set_password(self.cleaned_data['new_password1'])
        return super(ClientProfileForm, self).save(commit)


class CircusPasswordChangeForm(PasswordChangeForm):
    error_messages = dict(SetPasswordForm.error_messages, **{
        'password_incorrect': _("Your old password was entered incorrectly."),
    })

    old_password = forms.CharField(label=_("Old password"), widget=forms.PasswordInput())
    new_password1 = forms.CharField(label=_("New password"), widget=forms.PasswordInput())
    new_password2 = forms.CharField(label=_("New password confirmation"), widget=forms.PasswordInput())

    def clean(self):
        super(CircusPasswordChangeForm, self).clean()
        if 'new_password1' in self.cleaned_data:
            validate_password(self.cleaned_data['new_password1'])
        return self.cleaned_data


class CircusPasswordResetForm(PasswordResetForm):
    # derived from an older version of django's PasswordResetForm which was
    # more generous about what information it divulged to unknown parties;
    # https://code.djangoproject.com/ticket/19758
    # https://github.com/django/django/blob/7acabbb9800de4492c0ee612a8a0aa784eb07f49/django/contrib/auth/forms.py#L208

    error_messages = {
        'unknown': _("That email address doesn't have an associated "
                     "user account. See the new account instructions below."),
        'unusable': _("The user account associated with this email "
                      "address cannot reset the password."),
    }

    def clean_email(self):
        """
        Validates that an active user exists with the given email address.
        """
        UserModel = get_user_model()
        email = self.cleaned_data["email"]
        try:
            # django's original implementation of this gets all users that
            # match the given email address, but CircusUser uses email for
            # username so at most one user object can match.
            user = UserModel.objects.get(email__iexact=email)
        except UserModel.DoesNotExist:
            raise forms.ValidationError(self.error_messages['unknown'])

        if not user.is_active:
            raise forms.ValidationError(self.error_messages['unknown'])
        if not user.has_usable_password():
            raise forms.ValidationError(self.error_messages['unusable'])
        return email

    def save(self, domain_override=None, request=None, use_https=False,
             token_generator=default_token_generator, from_email=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             html_email_template_name='registration/password_reset_email.html',
             extra_email_context=None):
        """
        Generates a one-use only link for resetting password and sends to the user.
        """
        email_template_name = 'notifications/new_user_password_reset_email'

        UserModel = get_user_model()
        email = self.cleaned_data["email"]
        active_users = UserModel._default_manager.filter(email__iexact=email, is_active=True)
        for user in active_users:
            # Make sure that no email is sent to a user that actually has a password marked as unusable
            if not user.has_usable_password():
                continue

            if user.email:
                try:
                    if not domain_override:
                        # current_site = Site.objects.get_current()
                        current_site = get_current_site(request)
                        site_name = current_site.name
                        domain = current_site.domain
                    else:
                        site_name = domain = domain_override

                    email_subject = get_notify_email_subject(project=None, subject=_("Password reset on {0}").format(site_name))

                    context = {
                        'email': user.email,
                        'domain': domain,
                        'site_name': site_name,
                        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                        'user': user,
                        'token': token_generator.make_token(user),
                        'protocol': 'https' if use_https else 'http',
                        'via_logo_image_url': settings.VIA_LOGO_IMAGE_URL,
                    }

                    send_email.after_response(
                        subject=email_subject,
                        from_email=from_email,
                        to_list=[user.email],
                        template_name=email_template_name,
                        context=context
                    )
                    return
                except:
                    import traceback
                    tb = traceback.format_exc()  # NOQA
                    mail_admins('[CircusPasswordResetForm]: notification failed', '(Email = {0}. Error = {1}. '.format(user.email, tb))


class CircusSignupForm(forms.Form):
    email = forms.EmailField(required=True, widget=forms.TextInput(attrs=dict(maxlength=75)), label=_("Email (will be verified)"))
    password1 = forms.CharField(required=True, widget=forms.PasswordInput(render_value=False), label=_("Password"))
    password2 = forms.CharField(required=True, widget=forms.PasswordInput(render_value=False), label=_("Repeat Password"))

    def clean_email(self):
        """ Validate that the e-mail address is unique. """
        if get_user_model().objects.filter(email__iexact=self.cleaned_data['email']):
            raise forms.ValidationError(_('This email is already in use. Please supply a different email.'))
        return self.cleaned_data['email']

    def clean(self):
        if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
            if self.cleaned_data['password1'] != self.cleaned_data['password2']:
                raise forms.ValidationError(_("The two password fields didn't match."))
        return self.cleaned_data

    def save(self, commit=True):
        user = get_user_model().objects.create_user(self.cleaned_data['email'], self.cleaned_data['password1'])
        user.activation_code = hashlib.sha224(user.email).hexdigest()
        user.save()
        confirm_account(user)
        return user


class GroupCreationForm(forms.ModelForm):
    name = forms.CharField(label=_("Group Name"))

    class Meta:
        model = Group
        fields = ("name",)
