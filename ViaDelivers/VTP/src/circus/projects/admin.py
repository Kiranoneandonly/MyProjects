from django.contrib import admin
from projects.models import Project, ProjectTeamRole, BackgroundTask, PriceQuote, PriceQuoteDetails, ProjectJobOptions
from tasks.models import Task


class TaskInline(admin.TabularInline):
    model = Task
    extra = 1


class ProjectTeamRoleInline(admin.TabularInline):
    model = ProjectTeamRole
    extra = 1


class ProjectJobOptionsInline(admin.TabularInline):
    model = ProjectJobOptions
    extra = 0

class ProjectAdmin(admin.ModelAdmin):
    list_display = ['job_number', 'client', 'name', 'approved', 'status', 'estimate_type', 'jams_estimateid']
    inlines = [ProjectTeamRoleInline, ProjectJobOptionsInline]
    fieldsets = (
        ('', {
            'classes': ('grp-collapse grp-open',),
            'fields': (
                ('job_number', 'client', 'name'),
                ('pricing_basis', 'express_factor', 'estimate_type', 'approved', 'status'),
            )
        }),
        ('People', {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                ('client_poc',),
            )
        }),
        ('Instructions', {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                ('instructions',),
                ('instructions_via',),
                ('instructions_vendor',),
            )
        }),
        ('Dates', {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                ('created',),
                ('quote_due', 'quoted'),
                ('started_timestamp', 'due'),
                ('delivered', 'completed'),
            )
        }),
        ('Locales', {
            'classes': ('grp-collapse grp-closed',),
            'fields': ('source_locale', 'target_locales'),
        }),
        ('JAMS API', {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                ('jams_jobid', 'jams_estimateid'),
            )
        }),
        ('Secure', {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                ('is_secure_job', 'is_phi_secure_job'),
                ('is_restricted_job', 'restricted_locations'),
            )
        }),
        ('Misc', {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                ('internal_via_project', 'no_express_option', 'ignore_holiday_flag', 'price_per_document'),
                ('delay_job_po', 'original_invoice_count', 'revenue_recognition_month'),
            )
        }),
        ('Approvals', {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                ('project_manager_approver', 'ops_management_approver', 'sales_management_approver'),
                ('large_job_approval_timestamp', 'large_job_approval_notes'),
            )
        }),
        ('Salesforce', {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                ('salesforce_opportunity_id',)
            )
        }),
        ('System Information', {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                'kit',
                'modified',
                'current_user',
                'is_deleted',
            )
        })
    )
    readonly_fields = ('created', 'modified', 'kit')
    search_fields = ('job_number', 'name', 'status', 'jams_estimateid', )
    ordering = ('-job_number', 'name', )


class PriceQuoteDetailsInline(admin.TabularInline):
    model = PriceQuoteDetails
    extra = 1


class PriceQuoteAdmin(admin.ModelAdmin):
    list_display = ['project', 'price', 'cost', 'gm', 'standard_tat', 'express_price', 'express_cost', 'express_gm',
                    'express_tat', 'wordcount', 'version', 'active']
    inlines = [PriceQuoteDetailsInline]
    search_fields = ('project__job_number', 'project__name')
    readonly_fields = ('id', 'created', 'modified', 'project')
    exclude = ['is_deleted']


class PriceQuoteDetailsAdmin(admin.ModelAdmin):
    list_display = ['pricequote', 'target', 'target_price', 'target_cost', 'target_gross_margin',
                    'target_standard_tat', 'target_express_price', 'target_express_cost', 'target_express_gross_margin',
                    'target_express_tat']
    search_fields = ('pricequote__project__name', 'pricequote__project__job_number', 'target__description')
    readonly_fields = ('id', 'created', 'modified', 'pricequote', 'target')
    exclude = ['is_deleted']


class BackgroundTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'created', 'completed', 'name', 'project']
    readonly_fields = ('created', 'modified', 'project', 'task', 'celery_task_id',
                       'callback_sig', 'errback_sig')
    search_fields = ('name', 'project__name', 'project__job_number', 'celery_task_id', )


admin.site.register(Project, ProjectAdmin)
admin.site.register(PriceQuote, PriceQuoteAdmin)
admin.site.register(PriceQuoteDetails, PriceQuoteDetailsAdmin)
admin.site.register(BackgroundTask, BackgroundTaskAdmin)
