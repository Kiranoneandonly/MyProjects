from django.conf.urls import url

from projects import views as v, authorization as authz, sow


urlpatterns = authz.any_via_user.protect_patterns(
    url(r'^(?P<pk>[\d]+)/perform_action/(?P<action_slug>[\w_]+)/$', v.perform_action, name='projects_perform_project_action'),
    url(r'^(?P<pk>[\d]+)/perform_transition/(?P<transition_slug>[\w_]+)/$', v.perform_transition, name='projects_perform_transition'),
)

urlpatterns.extend(authz.project_viewers.protect_patterns(
    # compare with loc kit 'download_asset'
    url(r'^download/job/(?P<proj_id>[\d]*)/source/zip/?$', v.project_source_files_zip, name='project_source_files_zip'),
    url(r'^download/job/(?P<proj_id>[\d]*)/reference/zip/?$', v.project_reference_files_zip, name='project_reference_files_zip'),
    url(r'^download/job/(?P<proj_id>[\d]*)/client-reference/zip/?$', v.glossary_styleguide_files_zip, name='glossary_styleguide_files_zip')
))

urlpatterns.extend(authz.project_clients.protect_patterns(
    # used by clients
    url(r'(?P<proj_id>\d+)/cancel', v.cancel, name="projects_cancel"),
    # compare with loc kit 'download_tasklocalizedasset_out_file'
    url(r'^download/job/(?P<proj_id>[\d]*)/delivery/(?P<lcid>[\d]*)/zip/?$', v.project_target_delivery_zip, name='project_target_delivery_zip'),
))


