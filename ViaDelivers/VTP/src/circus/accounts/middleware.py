# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.shortcuts import redirect

import logging

from accounts.views import user_country

logger = logging.getLogger('circus.' + __name__)


class ProfileRequiredMiddleware(object):

    def process_request(self, request):
        # todo there's got to be a better way
        if '/internal_api/' in str(request.path) or '/api/' in str(request.path):
            logger.info(u"Api call: %s at %s" % (request.user, request.META['REMOTE_ADDR']))
            return

        if '/logout' in str(request.path):
            logger.info(u"User logged out: %s at %s" % (request.user, request.META['REMOTE_ADDR']))
            return

        if request.user.is_authenticated():
            logger.info(u"User %s at %s from %s" % (request.user, request.path, request.META['REMOTE_ADDR']))
            if request.user.is_client():
                if not request.user.has_usable_password():
                    # todo something here when this becomes a possibility
                    return
                else:
                    if not request.user.profile_complete:
                        target_url = str(request.path)
                        if 'register' not in target_url:
                            return redirect('register_redirect')
                    if not request.user.registration_complete:
                        target_url = str(request.path)
                        if not any(view in target_url for view in ['static', 'account', 'register', 'contact']):
                            return redirect('register_redirect')


class UserCountryMiddleware(object):

    def process_request(self, request):
        if request.user.is_authenticated():
            request.user.country = user_country(request)
            return
