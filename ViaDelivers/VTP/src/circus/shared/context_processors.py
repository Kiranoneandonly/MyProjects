from django.conf import settings


def get_app_name(request):
    return {'APP_NAME': settings.APP_NAME}


def get_app_full_name(request):
    return {'APP_FULL_NAME': settings.APP_FULL_NAME}
