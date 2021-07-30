from __future__ import unicode_literals

import logging

import pygeoip
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.utils.translation import ugettext as _
from django.contrib import messages
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext
from django.views.generic import FormView, TemplateView
from ipware.ip import get_ip

from accounts.forms import ProfileForm, CircusPasswordChangeForm, CircusSignupForm
from circus.settings.base import GEOIP_PATH
from shared.mixins import HideSearchMixin
from ipware.ip import get_ip
from clients.models import Client

import logging

logger = logging.getLogger('circus.' + __name__)


@login_required
def edit_profile(request, template='clients/accounts/profile.html'):
    if request.method == 'POST':

        if 'update_password' in request.POST:
            password_form = CircusPasswordChangeForm(user=request.user, data=request.POST, prefix='password')
            profile_form = ProfileForm(instance=request.user, prefix='profile')
            if password_form.is_valid():
                password_form.save()
                messages.add_message(request, messages.SUCCESS, _('Your password has been updated.'))

        else:
            # This is not explicitly checking for the 'update_profile' button
            # name so that there's a default case for when the button name
            # is left out. Which browsers *shouldn't* do, but the Tinfoil
            # scan generated hundreds of errors here.
            profile_form = ProfileForm(request.POST, instance=request.user, prefix='profile')
            password_form = CircusPasswordChangeForm(user=request.user, prefix='password')
            if profile_form.is_valid():
                profile_form.save()
                messages.add_message(request, messages.SUCCESS, _('Your profile has beenwww updated.'))

    else:
        profile_form = ProfileForm(instance=request.user, prefix='profile')
        password_form = CircusPasswordChangeForm(user=request.user, prefix='password')
    # context = RequestContext(request)
    context = {
        'hide_search': True,
        'password_form': password_form,
        'profile_form': profile_form,
    }
    if request.user.user_type == settings.CLIENT_USER_TYPE:
        context['current_user_id'] = request.user.pk
        client = request.user.account.cast(Client)
        context['show_client_messenger'] = client.manifest.show_client_messenger
        context['secure_hierarchy'] = client.manifest.enforce_customer_hierarchy
        context['secure_jobs'] = client.manifest.secure_jobs
        context['phi_warning'] = client.manifest.phi_warning() and not client.manifest.baa_agreement_for_phi
        context['can_access_users_groups_options'] = request.user.can_access_users_groups_options()
        context['can_manage_users'] = request.user.can_manage_users()

    return render(request=request, template_name=template, context=context)


def user_country(request):
    gi = pygeoip.GeoIP(GEOIP_PATH+'/GeoIP.dat')
    return gi.country_code_by_addr(get_client_ip(request))


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[-1].strip()
    else:
        ip = get_ip(request)

    if settings.DEBUG:
        if ip == '127.0.0.1':
            ip = '103.254.188.0'  # CN
            # ip = '1.23.255.255'  # IN
    return ip


class SignupView(HideSearchMixin, FormView):
    template_name = 'shared/auth/signup.html'
    form_class = CircusSignupForm

    def form_valid(self, form):
        # try:
        obj = form.save()  # NOQA
        # except:
        #     return self.form_invalid(form)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('signup_complete')


class SignupCompleteView(HideSearchMixin, TemplateView):
    template_name = 'shared/auth/signup_complete.html'

    def get_context_data(self, **kwargs):
        context = super(SignupCompleteView, self).get_context_data(**kwargs)
        context['support_email'] = settings.VIA_SUPPORT_EMAIL
        context['contactus_form'] = settings.VIA_SUPPORT_CONTACT_US_FORM
        return context


def activate_account(request, pk=None, activation_key=None):
    if request.user.is_authenticated():
        logger.info(u'User activate_account : {0} {1} at {2}.'.format(request.user, request.user.email, request.META['REMOTE_ADDR']))
    else:
        logger.info(u'Anonymous activate_account : {0} : {1} at {2}.'.format(pk, activation_key, request.META['REMOTE_ADDR']))

    try:
        user = get_user_model().objects.get(pk=pk, activation_code=activation_key)
    except:
        user = None
    if not user:
        return redirect('unknown_activation')

    is_via, email_name, via_company = user.is_via_signup()

    if is_via:
        logger.info(u"activate_account is_via = TRUE")
        user.user_type = settings.VIA_USER_TYPE
        user.is_staff = True
        user.jams_username = email_name
        user.account = via_company
    else:
        logger.info(u"activate_account is_via = FALSE")
        if not user.user_type:
            user.user_type = settings.CLIENT_USER_TYPE

    user.is_active = True
    user.activation_code = None
    user.save()
    user.backend = 'django.contrib.auth.backends.ModelBackend'
    login(request, user)

    messages.success(request, _('Your account has been activated and you have been signed in.'))

    if is_via:
        return redirect('edit_profile')
    else:
        return redirect('register_redirect')


class UnknownActivationView(HideSearchMixin, TemplateView):
    template_name = 'shared/auth/unknown_activation.html'

    def get_context_data(self, **kwargs):
        context = super(UnknownActivationView, self).get_context_data(**kwargs)
        context['support_email'] = settings.VIA_SUPPORT_EMAIL
        context['contactus_form'] = settings.VIA_SUPPORT_CONTACT_US_FORM
        return context
