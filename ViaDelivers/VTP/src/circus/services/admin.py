from django.contrib import admin
from services.models import ServiceType, Locale, PricingFormula, Service, ScopeUnit, Industry, DocumentType, PricingBasis, Vertical, PricingScheme, \
    ServiceCategory , Country


class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ['code', 'rank', 'description']
    list_editable = ['rank', 'description']
    search_fields = ['code', 'description']
    exclude = ['is_deleted']


class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'description', 'abbreviation', 'icon', 'category', 'available', 'translation_task', 'billable', 'workflow']
    list_filter = ['available', 'billable', 'translation_task', 'workflow', 'category']
    search_fields = ['code', 'description']
    list_editable = ['category']
    list_select_related = ['category']


class LocaleAdmin(admin.ModelAdmin):
    list_display = ['code', 'description', 'lcid', 'jams_lcid', 'dvx_lcid', 'available', 'dvx_log_name', 'if_source_no_auto_estimate', 'if_target_no_auto_estimate']
    search_fields = ('code', 'description', 'lcid', 'jams_lcid', 'dvx_lcid', 'dvx_log_name')


class CountryAdmin(admin.ModelAdmin):
    list_display = ['country_code', 'country_name']
    search_fields = ('country_code', 'country_name')


class PricingFormulaAdmin(admin.ModelAdmin):
    list_display = ['code', 'description', 'percent_calculation']
    search_fields = ('code', 'description',)


class PricingBasisAdmin(admin.ModelAdmin):
    list_display = ['code', 'description']
    search_fields = ('code', 'description',)


class ScopeUnitAdmin(admin.ModelAdmin):
    list_display = ['code', 'description']
    search_fields = ('code', 'description',)


class IndustryAdmin(admin.ModelAdmin):
    list_display = ['code', 'description']
    search_fields = ('code', 'description',)


class VerticalAdmin(admin.ModelAdmin):
    list_display = ['code', 'description']
    search_fields = ('code', 'description',)


class PricingSchemeAdmin(admin.ModelAdmin):
    list_display = ['code', 'description']
    search_fields = ('code', 'description')


class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'description', 'can_auto_estimate', 'can_semiauto_estimate']
    search_fields = ('code', 'description',)


class ServiceAdmin(admin.ModelAdmin):
    list_display = ['service_type', 'source', 'target', 'unit_of_measure', 'expansion_rate']
    list_filter = ['service_type', 'source', 'target']
    search_fields = ('service_type__description', 'source__description', 'target__description', 'unit_of_measure__description', )
    fieldsets = (
        (None, {
            'fields': (
                'service_type',
                ('unit_of_measure', 'formula'),
                ('source', 'target'),
                'expansion_rate',
                'is_deleted'
            )
        }),
    )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'service_type':
            kwargs['queryset'] = (
                ServiceType.objects
                .filter(available=True)
                .order_by('description')
            )
        return super(ServiceAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.register(ServiceCategory, ServiceCategoryAdmin)
admin.site.register(ServiceType, ServiceTypeAdmin)
admin.site.register(Locale, LocaleAdmin)
admin.site.register(PricingBasis, PricingBasisAdmin)
admin.site.register(PricingFormula, PricingFormulaAdmin)
admin.site.register(Service, ServiceAdmin)
admin.site.register(ScopeUnit, ScopeUnitAdmin)
admin.site.register(Industry, IndustryAdmin)
admin.site.register(Vertical, VerticalAdmin)
admin.site.register(PricingScheme, PricingSchemeAdmin)
admin.site.register(Country, CountryAdmin)
admin.site.register(DocumentType, DocumentTypeAdmin)
