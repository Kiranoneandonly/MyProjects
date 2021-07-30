from django.contrib import admin
from prices.models import VendorTranslationRate, VendorNonTranslationRate, ClientTranslationPrice, ClientNonTranslationPrice
from services.models import Service, get_translation_task_service_types
import copy
import logging

logger = logging.getLogger('circus.' + __name__)


def copy_record(modeladmin=None, request=None, queryset=None):
    try:
        for cp in queryset:
            cp_copy = copy.copy(cp)
            cp_copy.id = None
            cp_copy.pricing_scheme = None
            cp_copy.vertical = None
            cp_copy.save()
    except Exception, error:
        import traceback
        tb = traceback.format_exc()  # NOQA
        print tb
        logger.error("price admin copy_price error", exc_info=True)

    copy_record.short_description = "Make a copy of the Record"


class VendorTranslationRateAdmin(admin.ModelAdmin):
    actions = [copy_record]
    list_display = ['id', 'vendor', 'service', 'vertical', 'client', 'basis', 'word_rate', 'guaranteed', 'exact', 'duplicate', 'fuzzy9599', 'fuzzy8594', 'fuzzy7584', 'fuzzy5074', 'no_match', 'minimum']
    readonly_fields = ('id',)
    search_fields = ('id', 'vendor__name', 'vertical__description', 'service__service_type__description', 'service__target__description', 'basis__description', 'client__name', )
    ordering = ('vendor', 'vertical', 'client', 'basis', )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'service':
            kwargs['queryset'] = (
                Service.objects
                .filter(service_type__available=True,
                        service_type_id__in=get_translation_task_service_types())
                .order_by('service_type__description', 'source', 'target')
                .prefetch_related('source', 'target')
            )
        return super(VendorTranslationRateAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class VendorNonTranslationRateAdmin(admin.ModelAdmin):
    actions = [copy_record]
    list_display = ['id', 'vendor', 'service', 'vertical', 'client', 'unit_cost']
    list_filter = ['vendor', 'service__service_type']
    readonly_fields = ('id',)
    search_fields = ('id', 'vendor__name', 'vertical__description', 'service__service_type__description', 'service__target__description', 'client__name', )
    ordering = ('vendor', 'vertical', 'client', )

    def get_queryset(self, request):
        qs = super(VendorNonTranslationRateAdmin, self).get_queryset(request)
        return qs.prefetch_related('vendor')

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'service':
            kwargs['queryset'] = (
                Service.objects
                .exclude(service_type_id__in=get_translation_task_service_types())
                .filter(service_type__available=True)
                .order_by('service_type__description', 'source', 'target')
                .prefetch_related('source', 'target')
            )
        return super(VendorNonTranslationRateAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class ClientTranslationPriceAdmin(admin.ModelAdmin):
    actions = [copy_record]
    list_display = ['id', 'client', 'pricing_scheme', 'service', 'basis', 'word_rate', 'guaranteed', 'exact', 'duplicate', 'fuzzy9599', 'fuzzy8594', 'fuzzy7584', 'fuzzy5074', 'no_match', 'minimum_price']
    readonly_fields = ('id',)
    search_fields = ('id', 'client__name', 'pricing_scheme__description', 'service__service_type__description', 'service__target__description', 'basis__description', )
    ordering = ('client', 'pricing_scheme', 'basis',)

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'service':
            kwargs['queryset'] = (
                Service.objects
                .filter(service_type__available=True,
                        service_type_id__in=get_translation_task_service_types())
                .order_by('service_type__description', 'source', 'target')
                .prefetch_related('source', 'target')
            )
        return super(ClientTranslationPriceAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class ClientNonTranslationPriceAdmin(admin.ModelAdmin):
    actions = [copy_record]
    list_display = ['id', 'client', 'pricing_scheme', 'service', 'unit_price']
    list_filter = ['service__service_type']
    readonly_fields = ('id',)
    search_fields = ('id', 'client__name', 'pricing_scheme__description', 'service__service_type__description', 'service__target__description', )
    ordering = ('client', 'pricing_scheme', )

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'service':
            kwargs['queryset'] = (
                Service.objects
                .exclude(service_type_id__in=get_translation_task_service_types())
                .filter(service_type__available=True)
                .order_by('service_type__description', 'source', 'target')
                .prefetch_related('source', 'target')
            )
        return super(ClientNonTranslationPriceAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(ClientTranslationPrice, ClientTranslationPriceAdmin)
admin.site.register(ClientNonTranslationPrice, ClientNonTranslationPriceAdmin)
admin.site.register(VendorNonTranslationRate, VendorNonTranslationRateAdmin)
admin.site.register(VendorTranslationRate, VendorTranslationRateAdmin)
