from django.conf import settings
from people.models import AccountManager


class VendorManager(AccountManager):
    def for_filter(self, filters):
        try:
            return self.get(id=filters[settings.VENDOR_USER_TYPE])
        except:
            return None
