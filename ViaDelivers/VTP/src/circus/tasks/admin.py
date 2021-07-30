from django.contrib import admin
from tasks.forms import VendorPurchaseOrderAdminForm
from tasks.models import TaskLocaleTranslationKit, VendorPurchaseOrder, TranslationTask, NonTranslationTask, \
    TranslationTaskClientPrice, TranslationTaskVendorRates, TranslationTaskAnalysis, TaskLocalizedAsset, TaskQuote, \
    TaskAssetQuote


class TaskLocalizedAssetAdmin(admin.ModelAdmin):
    list_display = ['task', 'name', 'input_file', 'output_file', 'source_asset', 'downloaded']
    search_fields = ('task__project__job_number', 'task__project__name', 'task__service__service_type__description',
                     'task__service__source__description', 'task__service__target__description', 'name', 'input_file',
                     'output_file', )
    readonly_fields = ('id', 'created', 'modified', 'task', 'source_asset')


class TaskLocaleTranslationKitAdmin(admin.ModelAdmin):
    list_display = ['task', 'input_file', 'output_file']
    search_fields = ('task__project__job_number', 'task__project__name', 'task__service__service_type__description',
                     'task__service__source__description', 'task__service__target__description', )


class VendorPurchaseOrderAdmin(admin.ModelAdmin):
    form = VendorPurchaseOrderAdminForm
    list_display = ['vendor', 'get_tasks_list', 'po_number']
    readonly_fields = ('number',)
    search_fields = ('vendor__name','task__project__job_number', 'task__project__name',
                     'task__service__service_type__description', 'task__service__source__description',
                     'task__service__target__description', 'po_number')

    def get_tasks_list(self, obj):
        return obj.task
    get_tasks_list.short_description = 'Tasks'


class NonTranslationTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'project', 'service', 'status', 'unit_cost', 'quantity']
    search_fields = ('id', 'status', 'project__job_number', 'project__name', 'service__service_type__description',
                     'service__source__description', 'service__target__description', )
    fieldsets = (
        ('', {
            'classes': ('grp-collapse grp-open',),
            'fields': (
                ('project',),
                ('service',),
                ('predecessor',),
            )
        }),
        ('Misc', {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                ('billable',),
                ('status',),
                ('standard_days',),
                ('express_days',),
                ('scheduled_start_timestamp',),
                ('started_timestamp',),
                ('accepted_timestamp',),
                ('due',),
                ('overdue_email_last_sent',),
                ('completed_timestamp',),
                ('notes',),
                ('via_notes',),
                ('vendor_notes',),
                ('reference_file',),
                ('create_po_needed',),
                ('po_created_date',),
                ('jams_taskid',),
                ('assignee_content_type',),
                ('assignee_object_id',),
                ('rating',),
            )
        }),
        ('Non Translation Fields', {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                ('formula',),
                ('quantity',),
                ('actual_hours',),
                ('unit_cost',),
                ('unit_price',),
                ('price_is_percentage',),
                ('vendor_minimum',),
            )
        }),
        ('System Info', {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                'created',
                'modified',
                'is_deleted',
            )
        })
    )
    readonly_fields = ('id', 'created', 'modified', 'project', 'predecessor', 'service')


class TranslationTaskAdmin(admin.ModelAdmin):
    list_display = ['id', 'project', 'service', 'status']
    search_fields = ('id', 'status', 'project__job_number', 'project__name', 'service__service_type__description',
                     'service__source__description', 'service__target__description', )
    inlines = []
    fieldsets = (
        ('', {
            'classes': ('grp-collapse grp-open',),
            'fields': (
                ('project',),
                ('service',),
                ('predecessor',),
            )
        }),
        ('Misc', {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                ('billable',),
                ('status',),
                ('standard_days',),
                ('express_days',),
                ('scheduled_start_timestamp',),
                ('started_timestamp',),
                ('accepted_timestamp',),
                ('due',),
                ('overdue_email_last_sent',),
                ('completed_timestamp',),
                ('notes',),
                ('via_notes',),
                ('vendor_notes',),
                ('reference_file',),
                ('jams_taskid',),
                ('assignee_content_type',),
                ('assignee_object_id',),
                ('rating',),
            )
        }),
        ('Translation Fields', {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                ('analysis',),
                ('vendor_rates',),
                ('client_price',),
            )
        }),
        ('System Info', {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                'created',
                'modified',
                'is_deleted',
            )
        })
    )
    readonly_fields = ('id', 'created', 'modified', 'project', 'predecessor', 'service', 'analysis', 'vendor_rates', 'client_price')


class TranslationTaskClientPriceAdmin(admin.ModelAdmin):
    list_display = ['id', 'source_of_client_prices', 'basis', 'word_rate', 'expansion_rate', 'minimum_price']
    search_fields = ('id', 'source_of_client_prices', 'basis__description', 'word_rate', 'expansion_rate',
                     'minimum_price',)


class TranslationTaskVendorRatesAdmin(admin.ModelAdmin):
    list_display = ['id', 'source_of_vendor_rates', 'basis', 'word_rate', 'minimum']
    search_fields = ('id', 'source_of_vendor_rates', 'basis__description', 'word_rate', 'minimum',)


class TranslationTaskAnalysisAdmin(admin.ModelAdmin):
    list_display = ['id', 'source_of_analysis', 'source', 'target']
    search_fields = ('id', 'source_of_analysis', 'source__description', 'target__description',)


class TaskQuoteAdmin(admin.ModelAdmin):
    list_display = ['task', 'wordcount', 'raw_price', 'mbd', 'net_price', 'total_cost', 'gm',
                    'total_express_cost', 'express_raw_price', 'express_mbd', 'express_net_price', 'express_gm']
    search_fields = ('project__job_number', 'project__name', 'task__service__service_type__description',
                     'task__service__source__description', 'task__service__target__description')
    readonly_fields = ('id', 'created', 'modified', 'project', 'task')


class TaskAssetQuoteAdmin(admin.ModelAdmin):
    list_display = ['task', 'target', 'asset', 'asset_is_minimum_price', 'asset_raw_price', 'asset_mbd', 'asset_net_price',
                    'asset_total_cost', 'asset_gm']
    search_fields = ('task__project__job_number', 'task__project__name', 'task__service__service_type__description',
                     'task__service__source__description', 'task__service__target__description', 'asset__orig_name')
    readonly_fields = ('id', 'created', 'modified', 'task', 'target', 'asset')


admin.site.register(TaskQuote, TaskQuoteAdmin)
admin.site.register(TaskAssetQuote, TaskAssetQuoteAdmin)
admin.site.register(TranslationTask, TranslationTaskAdmin)
admin.site.register(TaskLocaleTranslationKit, TaskLocaleTranslationKitAdmin)
admin.site.register(TaskLocalizedAsset, TaskLocalizedAssetAdmin)
admin.site.register(TranslationTaskAnalysis, TranslationTaskAnalysisAdmin)
admin.site.register(TranslationTaskClientPrice, TranslationTaskClientPriceAdmin)
admin.site.register(TranslationTaskVendorRates, TranslationTaskVendorRatesAdmin)
admin.site.register(NonTranslationTask, NonTranslationTaskAdmin)
admin.site.register(VendorPurchaseOrder, VendorPurchaseOrderAdmin)
