from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from shared.group_permissions import DEPARTMENT_ADMINISTRATOR_GROUP, CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP


def client_login_required(function=None):
    actual_decorator = user_passes_test(
        lambda u: u.id and u.is_client(),
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


def client_administrator_login_required(function=None):
    actual_decorator = user_passes_test(
        # lambda u: u.id and u.groups.filter(name=DEPARTMENT_ADMINISTRATOR_GROUP).count()
        lambda u: u.id and u.groups.filter(name__in=[DEPARTMENT_ADMINISTRATOR_GROUP, CLIENT_ORGANIZATION_ADMINISTRATOR_GROUP]).count()
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
