from django.contrib import admin
from accounts.admin import CircusUserAdmin
from people.admin import AccountAdmin
from via_staff.models import ViaContact, Via, ViaEmailDomain


class ViaEmailDomainInline(admin.TabularInline):
    model = ViaEmailDomain
    extra = 1


class ViaContactInline(admin.TabularInline):
    model = ViaContact
    extra = 1
    fieldsets = (
        (None, {
            'fields': ['email', 'user_type', 'first_name', 'last_name', 'jams_username', 'is_staff']
        }),
    )


class ViaAdmin(AccountAdmin):
    list_display = ['name', 'site', 'get_parent_link', 'is_deleted']
    fieldsets = (
        (None, {
            'fields': (
                'name',
                'description',
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
    search_fields = ('name', 'billing_city', 'site', 'parent__name')
    ordering = ('name', )
    inlines = [ViaEmailDomainInline]


class ViaContactAdmin(CircusUserAdmin):
    pass


admin.site.register(Via, ViaAdmin)
admin.site.register(ViaContact, ViaContactAdmin)
