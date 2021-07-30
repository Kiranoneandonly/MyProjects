from django.conf import settings
from people.models import AccountManager


class ViaManager(AccountManager):
    def for_filter(self, filters):
        try:
            return self.get(id=filters[settings.VIA_USER_TYPE])
        except:
            return None