from django.contrib import admin
from vendors.models import Vendor, VendorContact, VendorManifest, VendorTranslationTaskFileType
from people.admin import AccountAdmin
from accounts.admin import CircusUserAdmin


class VendorContactInline(admin.TabularInline):
    model = VendorContact
    extra = 1
    fieldsets = (
        (None, {
            'fields': ['email', 'user_type', 'first_name', 'last_name']
        }),
    )


class VendorManifestInline(admin.TabularInline):
    model = VendorManifest
    can_delete = False
    exclude = ['is_deleted']
    extra = 1
    
    
class VendorAdmin(AccountAdmin):
    list_display = ['name', 'account_number', 'billing_city', 'site', 'vendor_type', 'get_parent_link', 'is_deleted']
    fieldsets = (
        (None, {
            'fields': (
                ('name', 'account_number', 'vendor_type'),
                'description',
                'jobs_email',
                'website',
                'site',
                ('account_type', 'parent', 'owner'),
            )
        }),
        ('Billing', {
            'fields': (
                'phone',
                'fax',
                'billing_street',
                ('billing_city', 'billing_state'),
                ('billing_postal_code', 'billing_country'),
            )
        }),
        ('System Data', {
            'classes': ('collapse',),
            'fields': (
                ('created', 'modified'),
                ('is_deleted', 'is_person_account')
            )
        }),
    )
    search_fields = ('name', 'account_number', 'billing_city', 'site', 'vendor_type__description', 'parent__name')
    ordering = ('name', )
    inlines = [VendorContactInline, VendorManifestInline]


class VendorManifestAdmin(admin.ModelAdmin):
    list_display = ['vendor_name', 'vendor_jams_id', 'vendor_type', 'vendortranslationtaskfiletype']
    list_select_related = ['vendor']
    ordering = ['vendor__name']
    search_fields = ['vendor__name', 'vendor__account_number', 'vendor__vendor_type__description', 'vendortranslationtaskfiletype__description']
    readonly_fields = ['vendor']

    def vendor_name(self, vendor_manifest):
        return vendor_manifest.vendor.name

    vendor_name.admin_order_field = 'vendor__name'

    def vendor_jams_id(self, vendor_manifest):
        return vendor_manifest.vendor.account_number

    vendor_jams_id.admin_order_field = 'vendor__account_number'

    def vendor_type(self, vendor_manifest):
        return vendor_manifest.vendor.vendor_type

    fieldsets = [
        (None, {
            'fields': ['vendor'],
        }),
        ("Assigned Files", {
            'fields': [
                'vendortranslationtaskfiletype',
            ]
        }),
        ("PHI Secure Job Options", {
            'fields': [
                'is_phi_approved',
                'baa_agreement_for_phi_signed',
            ]
        }),
        ]

    def has_add_permission(self, request):
        # A Client's Manifest should be created when the Client is.
        return False
    
    
class FileTypesAdmin(admin.ModelAdmin):
    list_display = ['code','extension','description']


class VendorContactAdmin(CircusUserAdmin):
    pass


admin.site.register(Vendor, VendorAdmin)
admin.site.register(VendorManifest, VendorManifestAdmin)
admin.site.register(VendorTranslationTaskFileType, FileTypesAdmin)
admin.site.register(VendorContact, VendorContactAdmin)
