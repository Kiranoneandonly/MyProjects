from django.contrib import admin
from preferred_vendors.models import PreferredVendor


class PreferredVendorAdmin(admin.ModelAdmin):
    list_display = ['id', 'source', 'target', 'service_type', 'vertical', 'client', 'vendor', 'priority']
    search_fields = ('source__description', 'target__description', 'vertical__description', 'service_type__description', 'client__name', 'vendor__name', )
    ordering = ('source', 'target', 'vertical', 'service_type', 'client', 'priority', )

admin.site.register(PreferredVendor, PreferredVendorAdmin)