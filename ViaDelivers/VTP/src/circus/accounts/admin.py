from __future__ import unicode_literals
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin, GroupAdmin
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from accounts.forms import CircusUserChangeForm, CircusUserCreationForm
from accounts.models import CircusUser
from people.admin import AccountContactRoleInline
from django.contrib.auth.models import Permission, Group
from accounts.models import GroupOwner
from shared.group_permissions import CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP


class CircusUserAdmin(UserAdmin):
    add_form_template = 'admin/auth/user/add_form.html'
    inlines = [AccountContactRoleInline]
    fieldsets = (
        (None, {
            'classes': ('grp-collapse grp-open',),
            'fields': (
                'email',
                'password',
                'user_type',
                ('registration_complete', 'profile_complete'),
                'activation_code'
            )
        }),
        (_('Permissions'), {
            'classes': ('grp-collapse grp-open',),
            'fields': (
                ('is_active', 'is_superuser'),
                ('is_staff', 'jams_username')
            )
        }),
        (_('Personal Info'), {
            'classes': ('grp-collapse grp-open',),
            'fields': (
                'account',
                'salutation',
                ('first_name', 'last_name'),
                ('title', 'department', 'reports_to'),
                'description',
            )
        }),
        (_('Phone'), {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                'do_not_call',
                ('phone', 'mobile_phone'),
                ('home_phone', 'fax'),
            )
        }),
        (_('Address'), {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                'mailing_street',
                ('mailing_city', 'mailing_state'),
                ('mailing_postal_code', 'mailing_country'),
            )
        }),
        (_('Groups'), {
            'classes': ('grp-collapse grp-closed',),
            'fields': (
                'groups',
                'user_permissions',
                'is_client_organization_administrator',
            )
        }),
        (_('Salesforce'), {
            'fields': (
                # for ClientContacts
                'salesforce_contact_id',
                # for VIA Staff
                'salesforce_user_id',
            )}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    # for new user form only
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'user_type')}
        ),
    )
    form = CircusUserChangeForm
    add_form = CircusUserCreationForm

    list_display = ('email', 'user_type', 'first_name', 'last_name', 'get_account_link', 'is_active', 'is_staff', 'is_superuser', 'get_impersonate_link')
    # list_filter = ('user_type', 'is_staff', 'is_superuser', 'is_active', 'groups', 'account')
    search_fields = ('email', 'user_type', 'first_name', 'last_name', 'account__name')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions',)

    def get_account_link(self, obj):
        if not obj.account:
            return u''
        return u'<a href="{0}">{1}</a>'.format(reverse('admin:people_account_change', args=(obj.account.id,)), obj.account.name)
    get_account_link.allow_tags = True
    get_account_link.short_description = 'Account'

    # IMPERSONATE LINK
    def get_impersonate_link(self, obj):
        if not obj.account:
            return u''
        return u'<a href="/impersonate/{0}">Debug</a>'.format(obj.id)
    get_impersonate_link.allow_tags = True
    get_impersonate_link.short_description = 'Impersonate'

    def save_model(self, request, obj, form, change):
        obj.save()
        if change and 'groups' in form.changed_data:
            for group in form.cleaned_data['groups']:
                if group.name == CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP:
                    obj.is_client_organization_administrator = True
                    if obj.account.parent_id is None:
                        obj.account.is_top_organization = True
                    else:
                        obj.account.is_top_organization = False
                    obj.account.save()
                    obj.save()
                    break
                else:
                    obj.is_client_organization_administrator = False
                    obj.save()
                    client_org_admins_count = CircusUser.objects.filter(account=obj.account, is_client_organization_administrator=True).count()
                    if obj.account.parent_id is None and client_org_admins_count:
                        obj.account.is_top_organization = True
                    else:
                        obj.account.is_top_organization = False
                    obj.account.save()


class ViaGroupAdmin(GroupAdmin):

    def save_model(self, request, obj, form, change):
        obj.save()
        if not change:
            group_owner = GroupOwner(
                group_id=obj.id,
            )
            group_owner.save()

    def delete_model(self, request, obj):
        obj.save()
        GroupOwner.objects.get(group_id=obj.id).delete()


class PermissionAdmin(admin.ModelAdmin):
    model = Permission
    fields = ['name', 'content_type', 'codename']
    search_fields = ('name', 'codename')

class ViaGroupAdmin(GroupAdmin):

    def save_model(self, request, obj, form, change):
        obj.save()
        if not change:
            group_owner = GroupOwner(
                group_id=obj.id,
            )
            group_owner.save()

    def delete_model(self, request, obj):
        obj.save()
        GroupOwner.objects.get(group_id=obj.id).delete()


class PermissionAdmin(admin.ModelAdmin):
    model = Permission
    fields = ['name', 'content_type', 'codename']
    search_fields = ('name', 'codename')

admin.site.register(CircusUser, CircusUserAdmin)
admin.site.register(Permission, PermissionAdmin)
admin.site.unregister(Group)
admin.site.register(Group, ViaGroupAdmin)

