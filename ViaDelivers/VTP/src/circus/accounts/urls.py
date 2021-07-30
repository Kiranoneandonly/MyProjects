from django.conf import settings
from django.conf.urls import url
from accounts.forms import CircusAuthenticationForm, CircusPasswordResetForm
from accounts.views import SignupView, SignupCompleteView, UnknownActivationView, edit_profile, activate_account
from django.contrib.auth import views as v

urlpatterns = [
    url(r'^login$', v.login,
        {
            'template_name': 'shared/auth/login.html',
            'authentication_form': CircusAuthenticationForm,
            'extra_context':
                {
                    'support_email': settings.VIA_SUPPORT_EMAIL,
                    'contactus_form': settings.VIA_SUPPORT_CONTACT_US_FORM,
                    'new_client_setup': settings.NEW_CLIENT_SETUP_ENABLED
                },
        },
        name='login'),
    url(r'^signup/?$', SignupView.as_view(), name="signup"),
    url(r'^signup_complete/?$', SignupCompleteView.as_view(), name="signup_complete"),
    url(r'^activate/(?P<pk>\d+)/(?P<activation_key>\w+)/?$', activate_account, name="activate_account"),
    url(r'^unknown_activation/?$', UnknownActivationView.as_view(), name="unknown_activation"),

    url(r'^password/reset/$', v.password_reset,
        {'template_name': 'shared/auth/password_reset_form.html',
         'email_template_name': 'notifications/password_reset_email.html',
         'from_email': settings.FROM_EMAIL_ADDRESS,
         'post_reset_redirect': '/accounts/password/reset/done/',
         'password_reset_form': CircusPasswordResetForm,
        },
        name="password_reset"),
    url(r'^password/reset/done/$', v.password_reset_done,
        {'template_name': 'shared/auth/password_reset_done.html'
        },
        name="password_reset_done"),
    url(r'^password/reset/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$', v.password_reset_confirm,
        {'template_name': 'shared/auth/password_reset_confirm.html',
         'post_reset_redirect': '/accounts/password/done/'
        },
        name="password_reset_confirm"),
    url(r'^password/done/$', v.password_reset_complete,
        {'template_name': 'shared/auth/password_reset_complete.html'
        },
        name="password_reset_complete"),

    url(r'^profile/$', edit_profile, name='edit_profile'),
    url(r'^logout/$', v.logout, {'next_page': '/accounts/login'}, name='logout'),

    # todo do we really need this, if so, re-add. accounts\views.py manage_accounts has been commented out as well.
    # url(r'^manage/$', 'accounts.views.manage_accounts', name='manage_accounts')

    # reset password
]
