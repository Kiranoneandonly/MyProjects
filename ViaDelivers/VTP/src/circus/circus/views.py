from urlparse import urlparse, urlunparse
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, QueryDict
from django.shortcuts import resolve_url, render
from django.utils.encoding import force_str
from django.views.generic import TemplateView
from accounts.views import user_country

@login_required
def home(request):
    request.user.country = user_country(request)
    request.session['user_country'] = user_country(request)
    return HttpResponseRedirect(reverse('%s_dashboard' % request.user.user_type))

@login_required
def register(request):
    return HttpResponseRedirect(reverse('%s_register' % request.user.user_type))


class ContactView(TemplateView):
    template_name = "shared/contact.html"


class TermsView(TemplateView):
    template_name = "shared/terms.html"


def permission_denied(request):
    # this is lifted from the auth.decorators.user_passes_test implementation
    path = request.build_absolute_uri()
    # urlparse chokes on lazy objects in Python 3, force to str
    resolved_login_url = force_str(resolve_url(settings.LOGIN_URL))
    # If the login url is the same scheme and net location then just
    # use the path as the "next" url.
    login_scheme, login_netloc = urlparse(resolved_login_url)[:2]
    current_scheme, current_netloc = urlparse(path)[:2]
    if ((not login_scheme or login_scheme == current_scheme) and
        (not login_netloc or login_netloc == current_netloc)):
        path = request.get_full_path()

    if request.user and request.user.is_authenticated():
        # lifted from redirect_to_login, but we want to put that url in the
        # context instead of redirecting to it immediately.
        login_url_parts = list(urlparse(resolved_login_url))
        querystring = QueryDict(login_url_parts[4], mutable=True)
        querystring[REDIRECT_FIELD_NAME] = path
        login_url_parts[4] = querystring.urlencode(safe='/')

        context = {
            'user': request.user,
            'login_url': urlunparse(login_url_parts),
            'support_email': settings.VIA_SUPPORT_EMAIL,
            'contactus_form': settings.VIA_SUPPORT_CONTACT_US_FORM,
        }
        return render(request=request, template_name='403.html', context=context)

    else:
        return redirect_to_login(
            path, resolved_login_url, REDIRECT_FIELD_NAME)
