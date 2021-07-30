# -*- coding: utf-8 -*-
from via_portal import authorization as via_authz
from django.conf.urls import url
from . import views as v


urlpatterns = via_authz.any_via_user.protect_patterns(
    # url(r'^new_job_ordered/(?P<project_id>\d+)/?$', v.new_job_ordered),
    # url(r'^project_quote_ready/(?P<project_id>\d+)/?$', v.project_quote_ready),
    url(r'^via_new_client_user/(?P<user_id>\d+)/?$', v.via_new_client_user),
    url(r'^via_new_client_account/(?P<account_id>\d+)/?$', v.via_new_client_account),

    url(r'^manual_quote_needed/(?P<project_id>\d+)/?$', v.project_manual_quote_needed),
    url(r'^via_manual_quote_needed/(?P<project_id>\d+)/?$', v.project_manual_quote_needed_via),

    url(r'^mute/(?P<project_id>\d+)/?$', v.mute, name='mute'),
)
