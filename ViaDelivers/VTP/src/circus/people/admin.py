from django.contrib import admin
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import Q
from accounts.models import CircusUser

from people.models import AccountType, Account, Salutation, ContactRole, AccountContactRole, VendorType, GenericEmailDomain


class AccountTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'description']
    search_fields = ('code', 'description',)


class SalutationAdmin(admin.ModelAdmin):
    list_display = ['code', 'description']
    search_fields = ('code', 'description',)


class ContactRoleAdmin(admin.ModelAdmin):
    list_display = ['code', 'description']
    search_fields = ('code', 'description',)


class VendorTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'description']
    search_fields = ('code', 'description',)


class GenericEmailDomainAdmin(admin.ModelAdmin):
    list_display = ['email_domain']
    search_fields = ('email_domain',)


class AccountContactRoleInline(admin.TabularInline):
    model = AccountContactRole
    extra = 1

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'contact':
            if len(request.resolver_match.args) > 0:
                parent_account_pk = request.resolver_match.args[0]
                kwargs['queryset'] = CircusUser.objects.filter(Q(user_type=settings.CLIENT_USER_TYPE) & Q(account__pk=parent_account_pk) & Q(is_active=True)).order_by('first_name')
        return super(AccountContactRoleInline, self).formfield_for_foreignkey(db_field, request, **kwargs)


class AccountAdmin(admin.ModelAdmin):
    list_display = ['name', 'account_type', 'account_number', 'site', 'get_parent_link', 'billing_city', 'is_deleted']
    inlines = [AccountContactRoleInline]
    readonly_fields = ('created', 'modified')

    search_fields = ('name', 'account_type__description', 'account_number', )
    ordering = ('name',)

    def get_parent_link(self, obj):
        if not obj.parent:
            return u''
        return u'<a href="{0}">{1}</a>'.format(reverse('admin:people_account_change', args=(obj.parent.id,)), obj.parent.name)
    get_parent_link.allow_tags=True
    get_parent_link.short_description = 'Parent'


admin.site.register(GenericEmailDomain, GenericEmailDomainAdmin)
admin.site.register(AccountType, AccountTypeAdmin)
admin.site.register(Salutation, SalutationAdmin)
admin.site.register(ContactRole, ContactRoleAdmin)
admin.site.register(VendorType, VendorTypeAdmin)
admin.site.register(Account, AccountAdmin)
