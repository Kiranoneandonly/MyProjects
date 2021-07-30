"""Development settings and globals."""

import urlparse
import sys
from sys import path
import os
from os.path import abspath, basename, dirname, join, normpath
from decimal import Decimal

from base import *  # NOQA

########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
########## END DEBUG CONFIGURATION

########## TEMPLATE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
TEMPLATES[0]['OPTIONS']['debug'] = DEBUG
########## END TEMPLATE CONFIGURATION

########## MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
    ('VIA Developer', 'developer@viadelivers.com'),
)
########## END MANAGER CONFIGURATION

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
########## END EMAIL CONFIGURATION

########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases

DATABASES['default'] = {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'circus',
    'USER': 'django_login',
    'PASSWORD': 'django',
    'HOST': 'localhost',
    'PORT': '5432',
    'CONN_MAX_AGE': CONN_MAX_AGE,
}

# try:
#     if 'DATABASE_URL' in os.environ:
#         url = urlparse.urlparse(os.environ['DATABASE_URL'])
#
#         DATABASES['default'].update({
#             'NAME': url.path[1:],
#             'USER': url.username,
#             'PASSWORD': url.password,
#             'HOST': url.hostname,
#             'PORT': url.port,
#             'CONN_MAX_AGE': CONN_MAX_AGE,
#             })
#         if url.scheme == 'postgres':
#             DATABASES['default']['ENGINE'] = 'django.db.backends.postgresql'
# except:
#     print 'Unexpected error configuring database:', sys.exc_info()
########## END DATABASE CONFIGURATION

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]']

DEBUG_DB_SQL = bool_env('DEBUG_DB_SQL', False)

if DEBUG_DB_SQL:
    ########## TOOLBAR CONFIGURATION
    # See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
    INSTALLED_APPS += (
        'debug_toolbar',
    )

    # See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
    INTERNAL_IPS = ('localhost', '127.0.0.1', '[::1]',)

    # See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
    MIDDLEWARE_CLASSES += (
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    )

    CONFIG_DEFAULTS = {
        # Toolbar options
        'RESULTS_CACHE_SIZE': 3,
        'SHOW_COLLAPSED': True,
        # Panel options
        'SQL_WARNING_THRESHOLD': 100,   # milliseconds
    }
    ########## END TOOLBAR CONFIGURATION

# See: https://github.com/lavi06/django-profile-middleware
DEBUG_PROFILER = bool_env('DEBUG_PROFILER', False)

if DEBUG_PROFILER:
    INSTALLED_APPS += (
        'django_profile_middleware',
    )

    # See: https://github.com/django-debug-toolbar/django-debug-toolbar#installation
    MIDDLEWARE_CLASSES += (
        'django_profile_middleware.middleware.ProfilerMiddleware',
    )

    PROFILER = {
        'enable': True,

        # optional fields
        'sort': 'time',
        'count': None,
        'output': ['console', 'file'],
        'file_location': '_profiling_results.log'
    }

if 'VTP_IPYTHON_PROFILE' in os.environ:
    IPYTHON_ARGUMENTS = [
        '--ext', 'django_extensions.management.notebook_extension',
        '--profile', os.environ['VTP_IPYTHON_PROFILE']
    ]


########## LOGGING
def skip_djkombu(record):
    """Celery polls with this about every five seconds, so skip it."""
    if record.sql.startswith('SELECT') and 'djkombu_' in record.sql:
        return False
    return True

LOGGING['filters']['skip_djkombu'] = {
    '()': 'django.utils.log.CallbackFilter',
    'callback': skip_djkombu
}

if 'debug_toolbar' in INSTALLED_APPS:
    # For some reason when debug_toolbar is installed, it makes the celery
    # log noisy even when the django console isn't.
    LOGGING['loggers']['django.db.backends'] = {
        'filters': ['skip_djkombu']
    }

if DEBUG_DB_SQL:
    # devserver's SQL logging would probably be prettier, but it doesn't work atm.
    # https://github.com/dcramer/django-devserver/issues/92
    LOGGING['loggers']['django.db.backends'] = {
        'handlers': ['console'],
        'level': 'DEBUG',
        'filters': ['skip_djkombu']
    }


LOGGING['loggers']['shared.protection'] = {
    'handlers': ['console'],
    'level': 'DEBUG'
}
LOGGING['loggers']['circus'] = {
    'handlers': ['console'],
    'level': 'DEBUG'
}

########## END LOGGING

########## CELERY
# causes immediate execution of tasks, remove for production
# http://docs.celeryproject.org/en/latest/django/unit-testing.html#testing-with-django
CELERY_ALWAYS_EAGER = False
########## END CELERY

########## CONSTANTS
LINKS_USE_HTTPS = bool_env('LINKS_USE_HTTPS', False)
SECURE_SSL_REDIRECT = LINKS_USE_HTTPS


# DVX API
VIA_API_DVX_TEAMSERVER_DVX_TS_DEV = bool_env('VIA_API_DVX_TEAMSERVER_DVX_TS_DEV', True)
VIA_DVX_BASE_URL = 'http://teamserver.viadelivers.com/dvx_ts_dev' if VIA_API_DVX_TEAMSERVER_DVX_TS_DEV else VIA_DVX_BASE_URL

VIA_API_DVX_TEAMSERVER_VS_DEBUG = bool_env('VIA_API_DVX_TEAMSERVER_VS_DEBUG', False)
VIA_DVX_BASE_URL = 'http://localhost:9335' if VIA_API_DVX_TEAMSERVER_VS_DEBUG else VIA_DVX_BASE_URL

VIA_DVX_API_VERSION = int(os.environ.get('VIA_DVX_API_VERSION', 2))
_VIA_DVX_BASE_PATH = '/api/v%s/' % (VIA_DVX_API_VERSION,)

# DVI APIs
# Analyze, Delivery, Lockit, Machinetranslate, Memorydb, Pretranslate, PseudoTranslate, Qualityassurance, Settings, Terminologydb, Translation

VIA_DVX_SETTINGS_URL = VIA_DVX_BASE_URL + _VIA_DVX_BASE_PATH + 'Settings/Get'
VIA_ANALYSIS_URL = VIA_DVX_BASE_URL + _VIA_DVX_BASE_PATH + 'Analyze'
VIA_MT_TRANS_URL = VIA_DVX_BASE_URL + _VIA_DVX_BASE_PATH + 'Machinetranslate/Get'
VIA_PRE_TRANS_URL = VIA_DVX_BASE_URL + _VIA_DVX_BASE_PATH + 'Pretranslate/Get'
VIA_PSUEDO_TRANS_URL = VIA_DVX_BASE_URL + _VIA_DVX_BASE_PATH + 'Psuedotranslate/Get'
VIA_PREP_KIT_URL = VIA_DVX_BASE_URL + _VIA_DVX_BASE_PATH + 'Lockit/Get'
VIA_IMPORT_URL = VIA_DVX_BASE_URL + _VIA_DVX_BASE_PATH + 'Translation'
VIA_QA_URL = VIA_DVX_BASE_URL + _VIA_DVX_BASE_PATH + 'Qualityassurance/Get'
VIA_DELIVERY_URL = VIA_DVX_BASE_URL + _VIA_DVX_BASE_PATH + 'Delivery'
VIA_MEMORYDB_URL = VIA_DVX_BASE_URL + _VIA_DVX_BASE_PATH + 'Memorydb/Get'
VIA_TERMINOLOGYDB_URL = VIA_DVX_BASE_URL + _VIA_DVX_BASE_PATH + 'Terminologydb/Get'

VIA_API_DVX_TEAMSERVER_USE_MT = bool_env('VIA_API_DVX_TEAMSERVER_USE_MT', False)
VIA_API_DVX_TEAMSERVER_USE_TM = bool_env('VIA_API_DVX_TEAMSERVER_USE_TM', False)

# JAMS API
VIA_JAMS_INTEGRATION = bool_env('VIA_JAMS_INTEGRATION', True)
VIA_JAMS_BASE_URL = 'http://webjamsapi.viadelivers.com'
VIA_API_JAMS_WEBAPITEST = bool_env('VIA_API_JAMS_WEBAPITEST', True)
VIA_JAMS_BASE_URL = 'http://webjamsapitest.viadelivers.com' if VIA_API_JAMS_WEBAPITEST else VIA_JAMS_BASE_URL
VIA_API_JAMS_VS_DEBUG = bool_env('VIA_API_JAMS_VS_DEBUG', False)
VIA_JAMS_BASE_URL = 'http://localhost:52759' if VIA_API_JAMS_VS_DEBUG else VIA_JAMS_BASE_URL
VIA_JAMS_JOB_URL_V1 = VIA_JAMS_BASE_URL + '/api/v1/jobs'
VIA_JAMS_ESTIMATE_URL_V1 = VIA_JAMS_BASE_URL + '/api/v1/estimates'
VIA_JAMS_TASK_URL_V1 = VIA_JAMS_BASE_URL + '/api/v1/tasks'

VIA_ESTIMATES_EMAIL_ALIAS = os.environ.get('VIA_ESTIMATES_EMAIL_ALIAS', 'developer@viadelivers.com')
VIA_TSG_GROUP_EMAIL_ALIAS = os.environ.get('VIA_TSG_GROUP_EMAIL_ALIAS', 'developer@viadelivers.com')
VIA_PM_GROUP_EMAIL_ALIAS = os.environ.get('VIA_PM_GROUP_EMAIL_ALIAS', 'developer@viadelivers.com')
VIA_SALES_GROUP_EMAIL_ALIAS = os.environ.get('VIA_SALES_GROUP_EMAIL_ALIAS', 'developer@viadelivers.com')

########## END CONSTANTS
