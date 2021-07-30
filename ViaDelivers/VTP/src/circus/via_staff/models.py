from django.conf import settings
from django.db.models import permalink
from accounts.models import CircusUser
from people.models import Account, AccountEmailDomain
from via_staff.managers import ViaManager


class Via(Account):
    USER_TYPE = settings.VIA_USER_TYPE
    objects = ViaManager()

    class Meta:
        proxy = True
        verbose_name = 'VIA'
        verbose_name_plural = 'VIA'

    @permalink
    def get_absolute_url(self):
        return 'via_detail', (self.id,), {}


class ViaContact(CircusUser):
    USER_TYPE = settings.VIA_USER_TYPE

    class Meta:
        proxy = True


class ViaEmailDomain(AccountEmailDomain):

    class Meta:
        proxy = True

    def __unicode__(self):
        return unicode(self.account.name)
