from django.contrib.auth.decorators import user_passes_test


def vendor_login_required(function=None):
    actual_decorator = user_passes_test(
        lambda u: hasattr(u, 'user_type') and u.is_vendor(),
    )
    if function:
        return actual_decorator(function)
    return actual_decorator
