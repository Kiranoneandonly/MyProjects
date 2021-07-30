from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from nullablecharfield.db.models.fields import CharNullField
from salesforce import models as sfmodels

from shared.fields import PhoneField
from shared.managers import CircusManager
from shared.models import CircusModel, CircusLookup


# salesforce api docs
# http://www.salesforce.com/us/developer/docs/api/index_Left.htm

# saleforce default picklist values
# http://help.salesforce.com/apex/HTViewSolution?id=000004221&language=en_US

class AccountType(CircusLookup):
    class Meta:
        verbose_name = 'attribute: Account Type'


class AccountManager(CircusManager):
    # def get_query_set(self):
    def get_queryset(self):
        account_type = self.model.__name__.lower()
        # qs = super(AccountManager, self).get_query_set()
        qs = super(AccountManager, self).get_queryset()
        if not account_type == 'account':
            qs = qs.filter(account_type__code=account_type)
        return qs


class VendorType(CircusLookup):
    class Meta:
        verbose_name = 'attribute: Vendor Type'


class Account(CircusModel):
    objects = AccountManager()
    # http://www.salesforce.com/us/developer/docs/api/Content/sforce_api_objects_account.htm
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')
    # account exec type
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, related_name='owned_accounts')

    # record type is used to filter sets of data, so people can set up views
    # should we add this? need to check via salesforce config

    # account type
    account_type = models.ForeignKey(AccountType)
    is_person_account = models.BooleanField(default=False)

    # basic metadata
    account_number = models.CharField(_('JAMS ID'), blank=True, null=True, max_length=40)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    website = models.CharField(max_length=255, blank=True, null=True)
    site = models.CharField('Account Site', max_length=80, help_text="the account's location, e.g. London or Headquarters", blank=True, null=True)

    # marketing info

    # account_source - 40 chars, configurable picklist
    # industry - 40 characters, configurable picklist
    # annual_revenue - currency
    # naics_code - 8 characters, string
    # naics_desc - 120 characters
    # number_of_employees - 8 digits
    # ownership - picklist (private, public, subsidiary)
    # rating - (hot, warm, cold)
    # duns number and sic code omitted
    # ticker symbol - 20 characters
    # year started

    # main contact info
    phone = PhoneField(blank=True, null=True)
    fax = PhoneField(blank=True, null=True)

    billing_city = models.CharField(blank=True, null=True, max_length=40)
    billing_country = models.CharField(blank=True, null=True, max_length=40)
    billing_postal_code = models.CharField(blank=True, null=True, max_length=20)
    billing_state = models.CharField(blank=True, null=True, max_length=20)
    billing_street = models.TextField(blank=True, null=True)

    # used for vendor accounts when notifying about assignments
    # this is temp, probably replace with role based approach later
    jobs_email = models.EmailField(max_length=254, null=True)

    # used for client accounts when notifying about new jobs so VIA team can pickup
    # this is temp, probably replace with role based approach later
    via_team_jobs_email = models.EmailField(max_length=254, null=True)

    # omitted: shipping info

    # used for vendors
    vendor_type = models.ForeignKey(VendorType, blank=True, null=True)

    salesforce_account_id = CharNullField(max_length=18, blank=True,
                                          null=True, db_index=True)

    is_top_organization = models.NullBooleanField(default=False, blank=True, null=True)

    def cast(self, klass):
        self.__class__ = klass
        return self

    def contact_mail(self):
        return self.jobs_email

    def via_team_mail(self):
        return self.via_team_jobs_email

    def get_absolute_url(self):
        try:
            route_name = {
                'vendor': 'vendors_detail',
            }[self.account_type.code]
            return reverse(route_name, args=(self.id,))
        except:
            return None

    @property
    def client_type(self):
        if self.parent:
            return _("department")
        else:
            return _("organization")


    @cached_property
    def salesforce_account(self):
        if not self.salesforce_account_id:
            return SalesforceAccount.objects.get(pk=self.salesforce_account_id)


    def __unicode__(self):
        return unicode(self.name)



class SalesforceAccount(sfmodels.SalesforceModel):
    name = models.CharField(db_column='Name', max_length=255)
    parent = models.ForeignKey('self', blank=True, null=True,
                               db_column='ParentId', on_delete=models.PROTECT,
                               related_name='children')
    owner = models.ForeignKey('accounts.SalesforceUser',
                              db_column='OwnerId',
                              on_delete=models.DO_NOTHING,
                              null=True, related_name='accounts')

    class Meta:
        db_table = 'Account'
        managed = False


    @cached_property
    def account(self):
        return Account.objects.get(salesforce_account_id=self.pk)


    def __repr__(self):
        return '<%s %s %r>' % (self.__class__.__name__, self.pk, self.name)


class Salutation(CircusLookup):
    class Meta:
        verbose_name = 'attribute: Salutation'


class ContactRole(CircusLookup):
    class Meta:
        verbose_name = 'attribute: Contact Role'


class AccountContactRole(models.Model):
    account = models.ForeignKey(Account, related_name='contact_roles')
    contact = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='role')
    role = models.ForeignKey(ContactRole, blank=True, null=True)
    is_primary = models.BooleanField(default=False)

    unique_together = ("account", "contact", "role")


class JoinAccountRequest(CircusModel):
    account = models.ForeignKey(Account)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+')
    approver = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='+', blank=True, null=True)


class AccountEmailDomain(models.Model):
    account = models.ForeignKey(Account)
    email_domain = models.CharField(max_length=255, db_index=True)

    def __unicode__(self):
        return u'{0} ({1})'.format(self.account.name, self.email_domain)


class GenericEmailDomain(CircusModel):
    email_domain = models.CharField(max_length=255)

    def __unicode__(self):
        return u'{0}'.format(self.email_domain)
