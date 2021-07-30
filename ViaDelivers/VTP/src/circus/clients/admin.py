from django.contrib import admin
from django.conf import settings
from django.db.models import Q
from accounts.admin import CircusUserAdmin
from accounts.models import CircusUser
from matches.models import ANALYSIS_FIELD_NAMES
from people.admin import AccountAdmin, AccountContactRoleInline
from clients.models import Client, ClientContact, ClientTeamRole, ClientEmailDomain, ClientService, ClientManifest, ClientReferenceFiles, ClientDiscount
from services.models import ServiceType
from people.models import Account
from clients.forms import ClientManifestForm


class ClientEmailDomainInline(admin.TabularInline):
    model = ClientEmailDomain
    extra = 1


class ClientTeamRoleInline(admin.TabularInline):
    model = ClientTeamRole
    extra = 1

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'contact':
            kwargs['queryset'] = CircusUser.objects.filter(Q(user_type=settings.VIA_USER_TYPE) & Q(is_active=True)).order_by('first_name')
        return super(ClientTeamRoleInline, self).formfield_for_foreignkey(db_field, request, **kwargs)


class ClientServiceInline(admin.TabularInline):
    model = ClientService
    extra = 1

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        if db_field.name == 'service':
            kwargs['queryset'] = ServiceType.objects.filter(Q(available=True)).order_by('code')
        return super(ClientServiceInline, self).formfield_for_foreignkey(db_field, request, **kwargs)


class ClientDiscountAdmin(admin.ModelAdmin):
    list_display = ['client', 'start_date', 'end_date', 'discount']


class ClientDiscountInline(admin.TabularInline):
    model = ClientDiscount
    can_delete = True
    exclude = ['is_deleted']
    extra = 1


class ClientManifestInline(admin.TabularInline):
    model = ClientManifest
    can_delete = False
    exclude = ['is_deleted']

    fieldsets = (
        ("Pricing", {
            'fields': [
                'vertical',
                'pricing_scheme',
                'pricing_basis',
                'minimum_price',
                'express_factor',
                'expansion_rate_floor_override',
                'standard_translation_words_per_day',
            ]
        }),
        ("TEAMServer", {
            'fields': [
                'word_count_breakdown_flag',
                'pricing_memory_bank_discount',
                'teamserver_tm_enabled',
                'teamserver_client_subject',
                'teamserver_client_code',
                'update_tm',
            ]
        }),
        ("Workflow", {
            'fields': [
                'auto_estimate_jobs',
                'auto_start_workflow',
                'ignore_holiday_flag',
                'is_hourly_schedule',
            ]
        }),
        ("Portal", {
            'fields': [
                'is_sow_available',
                'is_reports_menu_available',
                'show_client_messenger',
                'client_notification_group',
            ]
        }),
        ("Secure", {
            'fields': [
                'enforce_customer_hierarchy',
                'baa_agreement_for_phi',
                'secure_jobs',
                'restricted_pricing',
                'state_secrets_validation',
            ]
        }),
    )


class ClientAdmin(AccountAdmin):
    list_display = ['name', 'account_number', 'billing_city', 'site', 'get_parent_link', 'is_top_organization', 'is_deleted']
    fieldsets = (
        (None, {
            'fields': (
                ('name', 'account_number'),
                'description',
                ('account_type', 'parent', 'is_top_organization', 'owner'),
                ('website', 'site'),
                ('via_team_jobs_email'),
                ('salesforce_account_id'),
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
    search_fields = ('name', 'account_number', 'parent__name', 'manifest__vertical__description', 'manifest__pricing_scheme__description', 'site', 'billing_city', )
    ordering = ('name', )

    inlines = [ClientManifestInline, ClientEmailDomainInline, AccountContactRoleInline, ClientTeamRoleInline, ClientServiceInline, ClientDiscountInline]

    def save_model(self, request, obj, form, change):
        if change and 'parent' in form.changed_data:
            if obj.parent is not None:
                obj.is_top_organization = False
        obj.save()


class ClientManifestAdmin(admin.ModelAdmin):
    form = ClientManifestForm
    list_display = ['client_name', 'parent_name', 'client_jams_id']
    list_select_related = ['client']

    ordering = ['client__name']

    search_fields = ['client__name', 'client__parent__name']

    readonly_fields = ['client']

    def client_name(self, manifest):
        return manifest.client.name

    client_name.admin_order_field = 'client__name'

    def parent_name(self, manifest):
        return manifest.client.parent.name if manifest.client.parent else None

    parent_name.admin_order_field = 'client__parent__name'

    def client_jams_id(self, manifest):
        return manifest.client.account_number

    client_jams_id.admin_order_field = 'client__account_number'

    fieldsets = [
        (None, {
            'fields': ['client'],
        }),
        ("Pricing", {
            'fields': [
                'vertical',
                'pricing_scheme',
                'pricing_basis',
                'minimum_price',
                'express_factor',
                'expansion_rate_floor_override',
                'standard_translation_words_per_day',
            ]
        }),
        ("Pricing: Matching", {
            'fields': ANALYSIS_FIELD_NAMES,
            'description': "Values are multipliers, i.e. 1.0 for 100%."
        }),
        ("TEAMServer", {
            'fields': [
                'word_count_breakdown_flag',
                'pricing_memory_bank_discount',
                'teamserver_tm_enabled',
                'teamserver_client_subject',
                'teamserver_client_code',
                'update_tm',
            ]
        }),
        ("Workflow", {
            'fields': [
                'auto_estimate_jobs',
                'auto_start_workflow',
                'ignore_holiday_flag',
                'is_hourly_schedule',
            ]
        }),
        ("Portal", {
            'fields': [
                'is_sow_available',
                'is_reports_menu_available',
                'show_client_messenger',
                'client_notification_group',
                'note',
            ]
        }),
        ("Secure", {
            'fields': [
                'enforce_customer_hierarchy',
                'baa_agreement_for_phi',
                'secure_jobs',
                'restricted_pricing',
                'state_secrets_validation',
            ]
        }),
        ("Default Client User Level", {
            'fields': ['default_client_user_level'],
        }),
    ]

    def has_add_permission(self, request):
        # A Client's Manifest should be created when the Client is.
        return False

    def get_all_client_hierarchy(self, client_id=None, parent_id=None, include_self=True):
        children_list = []
        parent_list = []
        if client_id:
            if include_self:
                children_list.append(client_id)

            for child in Account.objects.filter(parent=client_id):
                if child.id:
                    _child = self.get_all_client_hierarchy(client_id=child.id, include_self=True)
                    if 0 < len(_child):
                        children_list.extend(_child)
        if parent_id:
            if include_self:
                parent_list.append(parent_id)

            for parent in Account.objects.filter(id=parent_id):
                if parent.parent_id:
                    _parent = self.get_all_client_hierarchy(parent_id=parent.parent_id, include_self=True)
                    if 0 < len(_parent):
                        parent_list.extend(_parent)

        return children_list + parent_list

    def save_model(self, request, obj, form, change):
        obj.save()
        all_client_hierarchy = self.get_all_client_hierarchy(client_id=obj.client_id, parent_id=obj.client.parent_id)
        client_manifest_list = ClientManifest.objects.filter(client_id__in=all_client_hierarchy)
        for cm in client_manifest_list:
            cm.enforce_customer_hierarchy = obj.enforce_customer_hierarchy
            cm.save()

class ClientContactAdmin(CircusUserAdmin):
    pass


class ClientReferenceFilesAdmin(admin.ModelAdmin):
    list_display = ['orig_name', 'orig_file', 'client', 'reference_file_type', 'source', 'target']

    search_fields = ('orig_name', 'orig_file', 'client', 'project__source_locale__description')
    ordering = ('orig_name', )

admin.site.register(Client, ClientAdmin)
admin.site.register(ClientDiscount, ClientDiscountAdmin)
admin.site.register(ClientManifest, ClientManifestAdmin)
admin.site.register(ClientContact, ClientContactAdmin)
admin.site.register(ClientReferenceFiles, ClientReferenceFilesAdmin)
