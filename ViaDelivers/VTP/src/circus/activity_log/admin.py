from django.contrib import admin
from activity_log.models import Actions


class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'action_content_type', 'verb', 'actor', 'job_id', 'task_id', 'file_type',
                    'trans_file_name', 'support_file_name', 'description', 'data']
    readonly_fields = ('job_id', 'task_id', 'trans_file_name', 'support_file_name', 'action_content_type',
                       'action_object_id', 'action_object_name')
    search_fields = ('timestamp', 'description', 'data', )
    ordering = ('-timestamp', )

admin.site.register(Actions, ActivityLogAdmin)
