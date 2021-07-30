from django.db.models import Q
from accounts.models import CircusUser
from people.models import Account
from prices.search_by_basis import search_by_basis_client, search_by_basis_vendor
from services.managers import TARGET_BASIS
from services.models import PricingBasis
from shared.managers import ManagerWithDefaultVertical, ManagerWithDefaultPricingScheme
from vendors.models import Vendor


class VendorRateManager(ManagerWithDefaultVertical):
    def for_task(self, task):
        vendor = None
        assignee = task.assigned_to
        if isinstance(assignee, Account):
            vendor = assignee.cast(Vendor)
        elif isinstance(assignee, CircusUser):
            vendor = assignee.account

        client = task.project.client
        rates = self.filter(
            *task.service_filters()
        ).filter(
            Q(vertical=client.manifest.vertical) |
            Q(vertical=self.default_vertical_obj()) |
            Q(vertical_id=None)
        ).filter(
            Q(client=client) |
            Q(client=client.parent) |
            Q(client_id=None)
        ).filter(
            Q(vendor=vendor)
        )
        return search_by_basis_vendor(rates, client, task)


class ClientPriceManager(ManagerWithDefaultPricingScheme):
    def for_task(self, task):

        client = task.project.client
        prices = self.filter(
            *task.service_filters()
        ).filter(
            Q(pricing_scheme=client.manifest.pricing_scheme) |
            Q(pricing_scheme=self.default_pricing_scheme_obj()) |
            Q(pricing_scheme_id=None)
        ).filter(
            Q(client=client) |
            Q(client=client.parent) |
            Q(client_id=None)
        )

        if task.is_translation():
            # only return target basis prices unless client is specifically setup for source basis prices
            target_pricing_basis = PricingBasis.objects.get(code=TARGET_BASIS)
            prices.filter(
                Q(basis=client.manifest.pricing_basis) |
                Q(basis=target_pricing_basis) |
                Q(basis_id=None)
            )

        return search_by_basis_client(
            prices,
            client=client,
            task=task)
