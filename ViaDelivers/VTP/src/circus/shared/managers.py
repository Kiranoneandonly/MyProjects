from django.db import models
from django.db.models import Q
from django.utils import timezone
from projects.states import STARTED_STATUS, CREATED_STATUS, COMPLETED_STATUS, CLOSED_STATUS


class GetOrNoneMixin(object):
    def get_or_none(self, **kwargs):
        try:
            return self.get(**kwargs)
        except self.model.DoesNotExist:
            return None


class CircusManager(models.Manager, GetOrNoneMixin):
    def default(self):
        return None


class CircusLookupManager(CircusManager):
    def default_id(self):
        try:
            return self.default().id
        except:
            return None

    def get_not_applicable(self):
        obj, created = self.get_or_create(code='na', description='N/A')
        return obj


def get_default_kwargs(source_dict):
    return {
        'code': source_dict[0][0],
        'description': source_dict[0][1],
    }


def manager_with_queryset_methods(mixin):
    class qs(models.query.QuerySet, mixin):
        pass

    class manager(CircusManager, mixin):
        use_for_related_fields = True

        # def get_query_set(self):
        def get_queryset(self):
            return qs(self.model)
    return manager

"""
class SomeMixin(object):
    def manager_function_you_want(self):
        pass

MyManager = manager_with_query_set_methods(SomeMixin)
"""


class ManagerWithDefaultVertical(CircusManager):
    _default_vertical_obj = None

    def default_vertical_obj(self):
        if not self._default_vertical_obj:
            from services.managers import DEFAULT_VERTICAL_CODE
            from services.models import Vertical
            self._default_vertical_obj = Vertical.objects.get(code=DEFAULT_VERTICAL_CODE)
        return self._default_vertical_obj


class ManagerWithDefaultPricingScheme(CircusManager):
    _default_pricing_scheme_obj = None

    def default_pricing_scheme_obj(self):
        if not self._default_pricing_scheme_obj:
            from services.managers import PRICING_SCHEMES_STANDARD
            from services.models import PricingScheme
            self._default_pricing_scheme_obj = PricingScheme.objects.get(code=PRICING_SCHEMES_STANDARD)
        return self._default_pricing_scheme_obj


def get_overdue_projects_filter():
    now = timezone.now()
    return [
            # Job Overdue
            Q(status=STARTED_STATUS, due__lt=now) |
            # Estimate Overdue
            Q(quoted__isnull=True, status=CREATED_STATUS, quote_due__lt=now)
        ]


def get_delivered_projects_filter():
    return [Q(status=COMPLETED_STATUS) & Q(delivered__isnull=False) & Q(completed__isnull=True)]


def get_completed_projects_filter():
    return [Q(status=COMPLETED_STATUS) | Q(status=CLOSED_STATUS) & Q(completed__isnull=False)]


def get_inestimate_projects_filter():
    return [Q(status=CREATED_STATUS)]
