from django.contrib import admin
from dwh_reports.models import TasksReporting, ClientsReporting, ProjectsReporting, ClientManager, EqdReporting, \
    VendorsReporting, VendorUserReporting, ViaReporting, ViaUserReporting, ClientReport, ClientReportAccess, \
    RefreshTracking


class ClientReportAccessInline(admin.TabularInline):
    model = ClientReportAccess
    fields = ('client_report', 'access')
    extra = 0


class ClientsReportingAdmin(admin.ModelAdmin):
    list_display = ['client_id', 'name', 'parent_id', 'account_type']
    search_fields = ('client_id', 'name', )
    ordering = ('name', )

    inlines = [
        ClientReportAccessInline,
    ]


class ClientManagerAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'user_type', 'account', 'department']
    search_fields = ('first_name', 'last_name',)
    ordering = ('first_name', 'last_name',)


class VendorsReportingAdmin(admin.ModelAdmin):
    list_display = ['client_id', 'name', 'parent_id', 'account_type']
    search_fields = ('client_id', 'name', )
    ordering = ('name', )


class VendorUserAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'user_type', 'account', 'department']
    search_fields = ('first_name', 'last_name',)
    ordering = ('first_name', 'last_name',)


class ViaReportingAdmin(admin.ModelAdmin):
    list_display = ['client_id', 'name', 'parent_id', 'account_type']
    search_fields = ('client_id', 'name', )
    ordering = ('name', )


class ViaUserAdmin(admin.ModelAdmin):
    list_display = ['id', 'first_name', 'last_name', 'user_type', 'account', 'department']
    search_fields = ('first_name', 'last_name',)
    ordering = ('first_name', 'last_name',)


class ProjectsReportingAdmin(admin.ModelAdmin):
    list_display = ['project_id', 'job_number', 'name', 'customer', 'project_status', 'estimate_type', 'price', 'gross_margin']
    search_fields = ('job_number', 'name',)
    ordering = ('job_number', )


class TasksReportingAdmin(admin.ModelAdmin):
    list_display = ['task_id', 'project', 'target', 'source_file', 'service_type', 'status', 'word_count', 'memory_bank_discount', 'price', 'gross_margin']
    search_fields = ('project__name', 'project__job_number', 'service_type',)
    ordering = ('project__job_number', 'project__name', 'target', 'source_file', 'service_type', 'task_id', )


class EqdReportingAdmin(admin.ModelAdmin):
    list_display = ['id', 'quality_defect', 'title']
    search_fields = ('quality_defect', 'title',)
    ordering = ('id', )


class ClientReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'report_name', 'report_url_reverse']
    search_fields = ('id', 'report_name', )
    ordering = ('id',)


class ClientReportAccessAdmin(admin.ModelAdmin):
    list_display = ['client', 'client_report', 'access']
    search_fields = ('client__name', 'client_report__report_name', 'access',)
    ordering = ('client', 'client_report',)


class RefreshTrackingAdmin(admin.ModelAdmin):
    list_display = ['last_refreshed_timestamp']


admin.site.register(ClientsReporting, ClientsReportingAdmin)
admin.site.register(ClientManager, ClientManagerAdmin)
admin.site.register(VendorsReporting, VendorsReportingAdmin)
admin.site.register(VendorUserReporting, VendorUserAdmin)
admin.site.register(ViaReporting, VendorsReportingAdmin)
admin.site.register(ViaUserReporting, VendorUserAdmin)
admin.site.register(ProjectsReporting, ProjectsReportingAdmin)
admin.site.register(TasksReporting, TasksReportingAdmin)
admin.site.register(EqdReporting, EqdReportingAdmin)
admin.site.register(ClientReport, ClientReportAdmin)
admin.site.register(ClientReportAccess, ClientReportAccessAdmin)
admin.site.register(RefreshTracking, RefreshTrackingAdmin)

