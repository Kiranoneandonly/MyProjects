# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from nullablecharfield.db.models.fields import CharNullField
from salesforce import models as sfmodels

from people.models import Account, Salutation, AccountType, GenericEmailDomain, SalesforceAccount
from shared.fields import PhoneField
from shared.group_permissions import DEPARTMENT_ADMINISTRATOR_GROUP, CLIENT_NOTIFICATION_GROUP, \
    CLIENT_PROJECT_APPROVER_GROUP, CLIENT_MANAGER_GROUP, \
    CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP, CLIENT_CONTRIBUTOR_GROUP
from shared.managers import CircusManager
import pytz
from django.contrib.auth.models import Group, Permission
from django.shortcuts import get_object_or_404

import logging

logger = logging.getLogger('circus.' + __name__)


class CircusUserManager(BaseUserManager, CircusManager):
    def create_user(self, email, password=None):
        if not email:
            raise ValueError('Users must have an email address')

        user = self.model(email=CircusUserManager.normalize_email(email))

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        user = self.create_user(email, password=password)
        user.is_admin = True
        user.save(using=self._db)
        return user

    # def get_query_set(self):
    def get_queryset(self):
        # qs = super(CircusUserManager, self).get_query_set()
        qs = super(CircusUserManager, self).get_queryset()
        if self.model.USER_TYPE:
            qs = qs.filter(user_type=self.model.USER_TYPE)
        return qs

    def get_by_natural_key(self, username):
        return self.get(email__iexact=username)


class CircusUser(AbstractBaseUser, PermissionsMixin):
    USER_TYPE = None

    USER_TYPES = (
        (settings.CLIENT_USER_TYPE, _("Client")),
        (settings.VIA_USER_TYPE, _("VIA Staff")),
        (settings.VENDOR_USER_TYPE, _("Vendor")),
    )
    user_type = models.CharField(max_length=6, choices=USER_TYPES, db_index=True)

    # case-insensitive unique constraint created by SQL migration
    # CREATE INDEX ON accounts_circususer ((upper(email)))
    email = models.EmailField(max_length=254, unique=True, db_index=True)
    is_staff = models.BooleanField(_('staff status'), default=False)
    is_active = models.BooleanField(_('active'), default=False,
                                    help_text=_('Designates whether this user should be treated as '
                                                'active. Unselect this instead of deleting accounts.'))

    # allowed to use company invoicing if supported
    approved_buyer = models.BooleanField(default=False)

    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    timezone_list = pytz.common_timezones
    user_timezone = models.CharField(_('Time Zone'), max_length=40, choices=zip(timezone_list, timezone_list), default='UTC')

    # salesforce contact fields
    salesforce_contact_id = CharNullField(max_length=18, blank=True,
                                          null=True, unique=True)
    salesforce_user_id = CharNullField(max_length=18, blank=True,
                                       null=True, db_index=True)

    account = models.ForeignKey(Account, blank=True, null=True, related_name='contacts')

    # basic metadata
    salutation = models.ForeignKey(Salutation, blank=True, null=True)
    first_name = models.CharField(max_length=40, blank=True, null=True)
    last_name = models.CharField(max_length=80, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    title = models.CharField(max_length=80, blank=True, null=True)
    department = models.CharField(max_length=255, blank=True, null=True)
    reports_to = models.ForeignKey('self', blank=True, null=True)

    # contact info
    phone = PhoneField('Business Phone', blank=True, null=True)
    mobile_phone = PhoneField(blank=True, null=True)
    home_phone = PhoneField(blank=True, null=True)
    fax = PhoneField(blank=True, null=True)

    do_not_call = models.BooleanField(default=False)

    mailing_city = models.CharField(blank=True, null=True, max_length=40)
    mailing_country = models.CharField(blank=True, null=True, max_length=40)
    mailing_postal_code = models.CharField(blank=True, null=True, max_length=20)
    mailing_state = models.CharField(blank=True, null=True, max_length=20)
    mailing_street = models.TextField(blank=True, null=True)

    activation_code = models.CharField(blank=True, null=True, max_length=255)
    # user model data provided
    profile_complete = models.BooleanField(default=False)
    # account data provided
    registration_complete = models.BooleanField(default=False)

    # omitted other_* address fields

    # omitted - email bounced data and reason
    # last_activity_date = models.DateTimeField(blank=True, null=True)
    # lead_source

    # JAMS API Integration to be able to match to user
    jams_username = models.CharField(blank=True, null=True, max_length=50)

    is_client_organization_administrator = models.NullBooleanField(default=False, blank=True, null=True)

    objects = CircusUserManager()

    USERNAME_FIELD = 'email'

    def save(self, *args, **kwargs):
        super(CircusUser, self).save(*args, **kwargs)

    def get_full_name(self):
        if self.first_name and self.last_name:
            return u'{0} {1}'.format(self.first_name, self.last_name)
        else:
            return self.email

    def get_short_name(self):
        return self.get_full_name()

    def add_to_group(self, name):
        from django.contrib.auth.models import Group
        self.groups.add(Group.objects.get(name=name))
        if name == CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP:
            self.is_client_organization_administrator = True
            if self.account.parent_id is None:
                self.account.is_top_organization = True
            else:
                self.account.is_top_organization = False
            self.account.save()
            self.save()
        return True

    def remove_from_group(self, name):
        from django.contrib.auth.models import Group
        self.groups.remove(Group.objects.get(name=name))
        if name == CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP:
            self.is_client_organization_administrator = False
            self.save()
            # TO make the top organizatio, is_top_organization = False, all the users is_client_organization_administrators should be False
            client_org_admins_count = CircusUser.objects.filter(account=self.account, is_client_organization_administrator=True).count()
            if self.account.parent_id is None and client_org_admins_count:
                self.account.is_top_organization = True
            else:
                self.account.is_top_organization = False
            self.account.save()

        return True

    def add_user_permission(self, group_id=None, permission=None, user_id=None):
        from django.contrib.auth.models import Permission, Group
        if permission:
            self.user_permissions.add(Permission.objects.get(id=permission.id))
        else:
            instance = get_object_or_404(Group, id=group_id)
            grp_permissions = instance.permissions.get_queryset()
            for prm in grp_permissions:
                self.user_permissions.add(Permission.objects.get(id=prm.id))
            # Adding permissions form GroupOwnerPermissions
            grp_perm_list = GroupOwnerPermissions.objects.filter(group_id=group_id, user_id=user_id)
            specific_group_permissions = []
            for gpl in grp_perm_list:
                specific_group_permissions.append(gpl.permission_id)

            for perm in specific_group_permissions:
                self.user_permissions.add(Permission.objects.get(id=perm))

        return True

    def remove_user_permission(self, group_id=None, permission=None, user_id=None):
        from django.contrib.auth.models import Permission, Group
        if permission:
            self.user_permissions.remove(Permission.objects.get(id=permission.id))
        else:
            instance = get_object_or_404(Group, id=group_id)
            grp_permissions = instance.permissions.get_queryset()
            for prm in grp_permissions:
                self.user_permissions.remove(Permission.objects.get(id=prm.id))

            # Removing permissions form GroupOwnerPermissions
            grp_perm_list = GroupOwnerPermissions.objects.filter(group_id=group_id, user_id=user_id)
            specific_group_permissions = []
            for gpl in grp_perm_list:
                specific_group_permissions.append(gpl.permission_id)

            for perm in specific_group_permissions:
                self.user_permissions.remove(Permission.objects.get(id=perm))

        return True

    def add_user_permission(self, group_id=None, permission=None, user_id=None):
        from django.contrib.auth.models import Permission, Group
        if permission:
            self.user_permissions.add(Permission.objects.get(id=permission.id))
        else:
            instance = get_object_or_404(Group, id=group_id)
            grp_permissions = instance.permissions.get_queryset()
            for prm in grp_permissions:
                self.user_permissions.add(Permission.objects.get(id=prm.id))
            # Adding permissions form GroupOwnerPermissions
            grp_perm_list = GroupOwnerPermissions.objects.filter(group_id=group_id, user_id=user_id)
            specific_group_permissions = []
            for gpl in grp_perm_list:
                specific_group_permissions.append(gpl.permission_id)

            for perm in specific_group_permissions:
                self.user_permissions.add(Permission.objects.get(id=perm))

        return True

    def remove_user_permission(self, group_id=None, permission=None, user_id=None):
        from django.contrib.auth.models import Permission, Group
        if permission:
            self.user_permissions.remove(Permission.objects.get(id=permission.id))
        else:
            instance = get_object_or_404(Group, id=group_id)
            grp_permissions = instance.permissions.get_queryset()
            for prm in grp_permissions:
                self.user_permissions.remove(Permission.objects.get(id=prm.id))

            # Removing permissions form GroupOwnerPermissions
            grp_perm_list = GroupOwnerPermissions.objects.filter(group_id=group_id, user_id=user_id)
            specific_group_permissions = []
            for gpl in grp_perm_list:
                specific_group_permissions.append(gpl.permission_id)

            for perm in specific_group_permissions:
                self.user_permissions.remove(Permission.objects.get(id=perm))

        return True

    def __unicode__(self):
        # return self.get_full_name()
        return unicode(self.get_full_name())

    def contact_mail(self):
        return self.email

    def get_absolute_url(self):
        return None

    def is_via(self):
        return self.user_type == settings.VIA_USER_TYPE

    def is_via_signup(self):
        logger.info(u'Email: {0}.'.format(self.email))

        try:
            email_name, email_domain = self.email.split('@')
            logger.info(u'Name: {0}, Domain: {1}'.format(email_name, email_domain))
            via_account_type = AccountType.objects.get(code=settings.VIA_USER_TYPE)
            via_account = Account.objects.get_or_none(account_type=via_account_type, parent=None)
            from via_staff.models import ViaEmailDomain
            via = ViaEmailDomain.objects.filter(account=via_account, email_domain__iexact=email_domain)
            if via:
                logger.info(u'VIA Account: {0}'.format(self.email))
                return True, email_name, via_account
            else:
                logger.info(u'NOT VIA Account: {0}'.format(self.email))
                return False, "", None
        except Exception, error:
            logger.info(u"ERROR is_via_signup")
            import traceback
            tb = traceback.format_exc()  # NOQA
            print tb
            logger.error("is_via_signup error", exc_info=True)
            return False, "", None

    def is_client(self):
        return self.user_type == settings.CLIENT_USER_TYPE

    def is_client_organization_administrator_group(self):
        return self.is_client() and self.groups.filter(name=CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP).count() > 0

    def is_client_administrator_group(self):
        return self.is_client() and self.groups.filter(name=DEPARTMENT_ADMINISTRATOR_GROUP).count() > 0

    def is_client_notification_group(self):
        return self.is_client() and self.groups.filter(name=CLIENT_NOTIFICATION_GROUP).count() > 0

    def is_approver_group(self):
        return self.is_client() and self.groups.filter(name=CLIENT_PROJECT_APPROVER_GROUP).count() > 0

    def is_client_contributor_group(self):
        return self.is_client() and self.groups.filter(name=CLIENT_CONTRIBUTOR_GROUP).count() > 0

    def is_manager_group(self):
        return self.is_client() and self.groups.filter(name=CLIENT_MANAGER_GROUP).count() > 0

    def can_manage_users(self):
        return self.is_client_administrator_group() or self.is_client_organization_administrator_group() or self.is_client_organization_administrator

    def can_access_users_groups_options(self):
        return self.is_client_organization_administrator_group() or self.is_client_organization_administrator

    def is_approver_admin_groups(self):
        return self.is_client_organization_administrator_group() or self.is_client_administrator_group() or self.is_manager_group() or self.is_approver_group()

    def can_access_client_job_order(self):
        return self.is_approver_admin_groups() or self.is_client_contributor_group()

    def has_permission(self, permission=None):
        perms_list = []
        permisssions = self.is_client() and self.user_permissions.all().order_by('name')
        for permission in permisssions:
            perms_list.append(permission.id)
        return perms_list

    def has_group(self, group=None):
        group_ids = []
        group_names = []
        groups = self.is_client() and self.groups.all().order_by('name')
        for group in groups:
            group_ids.append(group.id)
            group_names.append(group.name)
        return group_ids, group_names

    def is_vendor(self):
        return self.user_type == settings.VENDOR_USER_TYPE

    def is_public_email_domain(self):
        email_name, email_domain = self.email.split('@')
        try:
            generic_email = GenericEmailDomain.objects.filter(email_domain__iexact=email_domain)
            if generic_email:
                return True
            else:
                return False
        except:
            return False

    def mail_link(self):
        return u'<a href="mailto:{0}" target="_blank">{1}</a>'.format(self.email, self.get_full_name())


    @cached_property
    def salesforce_contact(self):
        if not self.salesforce_contact_id:
            return None
        return SalesforceContact.objects.get(pk=self.salesforce_contact_id)


    @cached_property
    def salesforce_user(self):
        if not self.salesforce_user_id:
            return None
        return SalesforceUser.objects.get(pk=self.salesforce_user_id)



class SalesforceContact(sfmodels.SalesforceModel):
    email = models.EmailField(db_column='Email', max_length=80)
    first_name = models.CharField(db_column='FirstName', max_length=40)
    last_name = models.CharField(db_column='LastName', max_length=80)
    salutation = models.CharField(db_column='Salutation', max_length=40)
    account = models.ForeignKey(SalesforceAccount, db_column='AccountId',
                                on_delete=models.DO_NOTHING,
                                related_name='contacts')

    class Meta:
        db_table = 'Contact'
        managed = False


    @cached_property
    def circus_user(self):
        return CircusUser.objects.get(salesforce_contact_id=self.pk)


    def __repr__(self):
        return '<%s %s %r>' % (self.__class__.__name__, self.pk, self.email)



class SalesforceUser(sfmodels.SalesforceModel):
    email = models.EmailField(db_column='Email', max_length=128)
    username = models.EmailField(db_column='Username', max_length=80, unique=True)
    first_name = models.CharField(db_column='FirstName', max_length=40)
    last_name = models.CharField(db_column='LastName', max_length=80)
    alias = models.CharField(db_column='Alias', max_length=8)
    is_active = models.BooleanField(db_column='IsActive')

    class Meta:
        db_table = 'User'
        managed = False


    @cached_property
    def circus_user(self):
        return CircusUser.objects.get(salesforce_user_id=self.pk)


    def __repr__(self):
        return '<%s %s %r>' % (self.__class__.__name__, self.pk, self.username)


# Creating a child class for Group to have custom functions has_permissions() and has_users().
class ViaGroup(Group):

    class Meta:
        proxy = True

    # Fetching the permissions of a group and provide in JSON serialization
    def has_permissions(self, user):
        perms_list = []
        permisssions = self.permissions.all()
        group = GroupOwnerPermissions.objects.filter(group=self, user=user)
        for grp in group:
            perms_list.append(grp.permission_id)
        for permission in permisssions:
            perms_list.append(permission.id)
        return perms_list

    # Know the number of users assigned to a group
    def has_users(self):
        return self.user_set.all().count()


class GroupOwner(models.Model):

    group = models.ForeignKey(Group, blank=True, null=True, related_name='specific_group')
    user = models.ForeignKey(CircusUser, blank=True, null=True, related_name='group_owner')

    def __unicode__(self):
        return self.group.name


class GroupOwnerPermissions(models.Model):

    group = models.ForeignKey(Group, blank=True, null=True, related_name='specific_group_permission')
    permission = models.ForeignKey(Permission, blank=True, null=True, related_name='group_owner_permission')
    user = models.ForeignKey(CircusUser, blank=True, null=True, related_name='group_permission_owner')
    parent_account = models.ForeignKey(Account, blank=True, null=True, related_name='parent_account')

    class Meta:
        unique_together = [('group', 'permission', 'user')]

    def __unicode__(self):
        return self.group.name
