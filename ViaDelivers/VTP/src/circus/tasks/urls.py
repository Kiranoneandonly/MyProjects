from django.conf.urls import url
from tasks import views as v

from tasks.authorization import via_or_assignee
from via_portal.authorization import any_via_user

urlpatterns = any_via_user.protect_patterns(
    url(r'^(?P<pk>[\d]+)/tasks/new/$', v.TaskCreateView.as_view(), name='projects_tasks_create'),
    url(r'^edit/(?P<pk>\d+)/$', v.TaskUpdateView.as_view(), name='projects_tasks_edit'),
    url(r'^(?P<task_id>\d+)/remove_reference/$', v.remove_reference_file, name='task_remove_reference'),
    url(r'^(?P<pk>\d+)/delete/$', v.delete_task, name='projects_tasks_delete'),
    url(r'^(?P<pk>\d+)/copy_to_tla_output_file/(?P<tla_id>\d+)$', v.copy_to_tla_output_file, name='copy_to_tla_output_file'),
    url(r'^(?P<task_id>\d+)/supplier_ref_uploaded/?$', v.supplier_reference_redirect, name='task_supplier_ref_uploaded'),
)


urlpatterns += via_or_assignee.protect_patterns(
    url(r'^(?P<pk>\d+)/input/zip/?$', v.task_input_files_zip, name='task_input_files_zip'),
    url(r'^(?P<pk>\d+)/output/zip/?$', v.task_output_files_zip, name='task_output_files_zip'),
)
