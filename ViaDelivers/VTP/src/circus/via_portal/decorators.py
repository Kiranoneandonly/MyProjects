from django.contrib.auth.decorators import user_passes_test


def via_login_required(function=None):
    actual_decorator = user_passes_test(
        # AnonymousUsers have no user_type attribute
        lambda u: hasattr(u, 'user_type') and u.is_via(),
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
