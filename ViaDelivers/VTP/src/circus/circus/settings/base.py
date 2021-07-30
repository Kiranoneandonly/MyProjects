"""Common settings and globals."""
from decimal import Decimal
import os
import platform

from os.path import abspath, basename, dirname, join, normpath
from sys import path


def bool_env(name, default=None):
    """Return a boolean value from an environment variable.

    False is any of '', '0', 'f', 'false', 'n', 'no', 'off'.

    Anything else is True.

    :rtype: bool
    """
    if name in os.environ:
        value = os.environ[name]
        if value.lower() in ['', '0', 'false', 'n', 'no', 'off']:
            return False
        else:
            return True
    else:
        if default is not None:
            return default
        else:
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured("Environment has no %s" % (name,))


APP_NAME = os.environ.get('APP_NAME', 'Translation')
APP_FULL_NAME = os.environ.get('APP_FULL_NAME', 'VIA Translation Platform')
APP_SLUG_INSTANCE = os.environ.get('APP_SLUG_INSTANCE', 'VTP')
APP_SLUG_VTP = os.environ.get('APP_SLUG_VTP', 'VTP')

########## PATH CONFIGURATION
# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = dirname(dirname(abspath(__file__)))

PROJECT_DIR = DJANGO_ROOT

# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(DJANGO_ROOT)

# Site name:
SITE_NAME = basename(DJANGO_ROOT)

# Add our project to our pythonpath, this way we don't need to type our project
# name in our dotted import paths:
path.append(DJANGO_ROOT)

APPEND_SLASH = True
########## END PATH CONFIGURATION


########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = False
DEBUG_DB_SQL = DEBUG
########## END DEBUG CONFIGURATION

########## SSL CONFIGURATION
# When generating links, use http or https? (not a standard django setting)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
LINKS_USE_HTTPS = bool_env('LINKS_USE_HTTPS', False)
# https://docs.djangoproject.com/en/1.8/ref/settings/#secure-ssl-redirect
SECURE_SSL_REDIRECT = LINKS_USE_HTTPS
########## END SSL CONFIGURATION

########## MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
    ('VIA Translation Platform', 'no-reply@viadelivers.com'),
    ('VIA Developer', 'developer@viadelivers.com'),
    ('Kevin B', 'kbruner@viadelivers.com'),
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
########## END MANAGER CONFIGURATION

AUTH_USER_MODEL = 'accounts.CircusUser'

########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/1.6/ref/settings/#conn-max-age
# The lifetime of a database connection, in seconds. Use 0 to close database connections at the end of each request
# - Djangos historical behavior - and None for unlimited persistent connections.
CONN_MAX_AGE = int(os.environ.get('CONN_MAX_AGE', 500))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.',
        'NAME': '',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
        'CONN_MAX_AGE': CONN_MAX_AGE,
    }
}

SALESFORCE_ENABLED = bool_env('SALESFORCE_ENABLED', False)

if SALESFORCE_ENABLED:
    DATABASES['salesforce'] = {
        'ENGINE': 'salesforce.backend',
        'CONSUMER_KEY': os.environ['SALESFORCE_CONSUMER_KEY'],
        'CONSUMER_SECRET': os.environ['SALESFORCE_CONSUMER_SECRET'],
        'USER': os.environ['SALESFORCE_USER'],
        # This is user's password + security token
        'PASSWORD': os.environ['SALESFORCE_PASSWORD'],
        'HOST': 'https://login.salesforce.com',
    }

    DATABASE_ROUTERS = [
        "salesforce.router.ModelRouter",
    ]

########## END DATABASE CONFIGURATION

########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHE_COUNT_TIMEOUT = os.environ.get('CACHE_COUNT_TIMEOUT', 60)  # seconds, not too long.
CACHE_EMPTY_QUERYSETS = bool_env('CACHE_EMPTY_QUERYSETS', True)

# Do this here because thanks to django-pylibmc-sasl and pylibmc memcacheify is painful to install on windows.
# memcacheify is what's used in Production
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': ''
    }
}
########## END CACHE CONFIGURATION

########## GENERAL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#time-zone
TIME_ZONE = 'America/Los_Angeles'
PST_TIME_ZONE = 'America/Los_Angeles'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#languages-code
LANGUAGE_CODE = 'en-us'

PLATFORM_LOCALES = {
    'Windows': 'English_United States',
    'Darwin': 'en_US',
    'Linux': 'en_US.utf8',
}

CURRENCY_LOCALE = PLATFORM_LOCALES[platform.system()]

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
########## END GENERAL CONFIGURATION


########## MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = normpath(join(SITE_ROOT, 'media'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = '/media/'
########## END MEDIA CONFIGURATION

########## STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
# STATIC_ROOT = normpath(join(SITE_ROOT, 'assets'))
STATIC_ROOT = ''

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = '/static/'

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (
    # normpath(join(SITE_ROOT, 'static')),
    normpath(join(PROJECT_DIR, 'static')),
    # os.path.join(PROJECT_DIR, "static"),
)

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
########## END STATIC FILE CONFIGURATION

########## SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = 'uzi#&amp;o*9*zlv@qr)1kl68l8xi8dy2_85rd4!s$a0jw14#0@^@f'
########## END SECRET CONFIGURATION

########## FIXTURE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    normpath(join(SITE_ROOT, 'fixtures')),
)
########## END FIXTURE CONFIGURATION

########## TEMPLATE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [normpath(join(PROJECT_DIR, 'templates'))],
        # 'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG,
            # ...
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ],
            # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.request',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                # Your stuff: custom template context processors go here
                'shared.context_processors.get_app_name',
                'shared.context_processors.get_app_full_name',
                'dwh_reports.context_processors.messages_unread_count_all',
            ],
        },
    },
]
########## END TEMPLATE CONFIGURATION

########## MIDDLEWARE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#middleware-classes
MIDDLEWARE_CLASSES = (
    'tasks.middleware.GCMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'accounts.middleware.ProfileRequiredMiddleware',
    'accounts.middleware.UserCountryMiddleware',
    'breadcrumbs.middleware.BreadcrumbsMiddleware',
    'impersonate.middleware.ImpersonateMiddleware',
    'shared.middleware.TimezoneMiddleware',
    'tasks.middleware.ThreadLocalMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)
########## END MIDDLEWARE CONFIGURATION

########## URL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = '%s.urls' % SITE_NAME
# ROOT_URLCONF = 'circus.urls'
########## END URL CONFIGURATION

########## APP CONFIGURATION
DJANGO_APPS = (
    # Default Django apps:
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.flatpages',
    'django.contrib.messages',
    # For Django 1.7+, 'collectfast' should come before 'django.contrib.staticfiles'.
    # Please note, that failure to do so will cause Django to use django.contrib.staticfiles's collectstatic.
    'collectfast',
    'django.contrib.staticfiles',

    # Useful template tags:
    'django.contrib.humanize',
    'django_extensions',

    # Admin panel and documentation:
    'grappelli',
    'django.contrib.admin',
    # 'django.contrib.admindocs',
)

THIRD_PARTY_APPS = (
    'djcelery',
    # 'kombu.transport.django',
    'storages',
    'mathfilters',
    'menus',
    'breadcrumbs',
    'bootstrapform',
    'nullablecharfield',
    'widget_tweaks',
    'django_tables2',
    'bootstrap_pagination',
    'salesforce',
    'impersonate',
    'rest_framework',
    'rest_framework.authtoken',
    'rest_framework_docs',
    'django_nvd3',
    'pygeoip',
    'ipware',
    'tinymce',
)

# Apps specific for this project go here.
LOCAL_APPS = (
    'shared',
    'accounts',
    'services',
    'people',
    'clients',
    'vendors',
    'prices',
    'localization_kits',
    'projects',
    'tasks',
    'preferred_vendors',
    'vendor_portal',
    'notifications',
    'finance',
    'invoices',
    'jams_api',
    'via_staff',
    'holidays',
    'dwh_reports',
    'quality_defects',
    'activity_log',
    'avatar',
    'django_comments',
    'after_response',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

########## END APP CONFIGURATION

########## LOGGING CONFIGURATION
# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'with_name': {
            'format': '%(levelname)s %(name)s %(funcName)s: %(message)s'
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'shared.loghandler.AdminEmailHandler',
            'include_html': True,
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'with_name',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': normpath(join(PROJECT_DIR, 'file.log')),
        },
    },
    'loggers': {
        'circus': {
            'handlers': ['console', 'mail_admins'],
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['console', 'mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        }
    }
}

if DEBUG:
    # make all loggers use the console.
    for logger in LOGGING['loggers']:
        LOGGING['loggers'][logger]['handlers'] = ['console']

########## END LOGGING CONFIGURATION

########## WSGI CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'circus.wsgi.application'
########## END WSGI CONFIGURATION


########## CELERY
# http://docs.celeryproject.org/en/latest/getting-started/brokers/django.html
# has synch problems above a couple workers, update to better message broker to scale
BROKER_URL = 'django://'
import djcelery
djcelery.setup_loader()

CELERY_IMPORTS = [
    'client_portal.views',
    'localization_kits.engine',
    'projects.models',
    'projects.start_tasks',
]

# causes immediate execution of tasks, remove for production
# http://docs.celeryproject.org/en/latest/django/unit-testing.html#testing-with-django
# CELERY_ALWAYS_EAGER = False

# We haven't figured out how to make DejaVu reliable when we give it concurrent tasks, so limit concurrency to 1.
CELERYD_CONCURRENCY = 1

# Send exceptions to ADMINS
CELERY_SEND_TASK_ERROR_EMAILS = True
CELERY_TRACK_STARTED = True

# Explicitly say we accept pickle content (suppresses a warning message).
# This means the worker is only as secure as the database is, but that seems fine.
CELERY_ACCEPT_CONTENT = ['pickle', 'json', 'msgpack']
########## END CELERY

########## CONSTANTS
BREADCRUMBS_AUTO_HOME = True

BASE_URL = os.environ.get('BASE_URL', 'https://translation.viadelivers.com')
VENDOR_URL = os.environ.get('VENDOR_URL', BASE_URL)
CLIENT_URL = os.environ.get('CLIENT_URL', BASE_URL)

LOGIN_URL = "/accounts/login"
LOGIN_REDIRECT_URL = "/"

MIN_PASSWORD_LENGTH = os.environ.get('MIN_PASSWORD_LENGTH', 4)

########## AMAZON S3 CONFIGURATION
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', 'DO-NOT-SEND-CONFIG-VARIABLE-NEEDED')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', 'DO-NOT-SEND-CONFIG-VARIABLE-NEEDED')
# real production is vtp_prod, but for translation-dev.viadelivers.com, its production but we want circus_dev
AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_BUCKET', 'circus_dev')
AWS_BUCKET_URL_TEMPLATE = os.environ.get('AWS_BUCKET_URL_TEMPLATE', '//s3.amazonaws.com/%s')
AWS_BUCKET_URL = AWS_BUCKET_URL_TEMPLATE % AWS_STORAGE_BUCKET_NAME
AWS_DEFAULT_ACL = 'private'   # Any canned S3 ACL
AWS_QUERYSTRING_EXPIRE = 31536000
AWS_PRELOAD_METADATA = True

DEFAULT_FILE_STORAGE = 'circus.s3utils.MediaRootS3BotoStorage'
STATICFILES_STORAGE = 'circus.s3utils.StaticRootS3BotoStorage'
STATIC_DIRECTORY = STATIC_URL   # '/static/'
MEDIA_DIRECTORY = '/media/'
SERVE_FILE_BACKEND = 'lib.filetransfers.backends.url.serve_file'
PUBLIC_DOWNLOAD_URL_BACKEND = 'lib.filetransfers.backends.url.public_download_url'
FULL_FILEPATH_LENGTH = 500
########## END AMAZON S3 CONFIGURATION

#### Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        # CSRF makes we wary of adding SessionAuthentication here.
    )
}

REST_FRAMEWORK_DOCS = {
    'HIDE_DOCS': os.environ.get('HIDE_DRFDOCS', False)
}

#### END Django REST Framework

# How long a post to VIA_DVX_BASE_URL should wait before timing out.
try:
    VIA_API_CALL_TIMEOUT_SECONDS = float(os.environ.get('VIA_API_CALL_TIMEOUT_SECONDS', 1800.0))
except:
    VIA_API_CALL_TIMEOUT_SECONDS = 1800.0

# DVX API
VIA_DVX_API_KEY = os.environ.get('VIA_DVX_API_KEY', '918704ec-4811-45b6-a169-16bae3df69a8')
VIA_DVX_BASE_URL = os.environ.get('VIA_DVX_BASE_URL', 'http://teamserver.viadelivers.com/dvx_vtp_prod')
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

DVX_EXTERNAL_FORMAT_RTF = os.environ.get('DVX_EXTERNAL_FORMAT_RTF', '0')

# JAMS API
VIA_JAMS_INTEGRATION = bool_env('VIA_JAMS_INTEGRATION', False)
VIA_JAMS_API_KEY = os.environ.get('VIA_JAMS_API_KEY', '918704ec-4811-45b6-a169-16bae3df69a8')
VIA_JAMS_BASE_URL = os.environ.get('VIA_JAMS_BASE_URL', 'http://65.100.53.45')  # http://webjamsapi.viadelivers.com
VIA_JAMS_JOB_URL_V1 = VIA_JAMS_BASE_URL + '/api/v1/jobs'
VIA_JAMS_ESTIMATE_URL_V1 = VIA_JAMS_BASE_URL + '/api/v1/estimates'
VIA_JAMS_TASK_URL_V1 = VIA_JAMS_BASE_URL + '/api/v1/tasks'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#server-email
SERVER_EMAIL = os.environ.get('FROM_SERVER_EMAIL', 'no-reply@viadelivers.com')
FROM_EMAIL_ADDRESS = SERVER_EMAIL
VIA_SUPPORT_EMAIL = os.environ.get('VIA_SUPPORT_EMAIL', 'info@viadelivers.com')
VIA_SUPPORT_CONTACT_US_FORM = os.environ.get('VIA_SUPPORT_CONTACT_US_FORM', 'http://www.viadelivers.com/contact-us')

VIA_ESTIMATES_EMAIL_ALIAS = os.environ.get('VIA_ESTIMATES_EMAIL_ALIAS', 'estimates@viadelivers.com')
VIA_TSG_GROUP_EMAIL_ALIAS = os.environ.get('VIA_TSG_GROUP_EMAIL_ALIAS', 'TSG@viadelivers.com')
VIA_PM_GROUP_EMAIL_ALIAS = os.environ.get('VIA_PM_GROUP_EMAIL_ALIAS', 'TranslationCoordinators@viadelivers.com')
VIA_SALES_GROUP_EMAIL_ALIAS = os.environ.get('VIA_SALES_GROUP_EMAIL_ALIAS', 'SalesEnablement@viadelivers.com')
VIA_SUPPLIER_MANAGEMENT_EMAIL_ALIAS = os.environ.get('VIA_SUPPLIER_MANAGEMENT_EMAIL_ALIAS', 'SupplierManagement@viadelivers.com')

VIA_LOGO_IMAGE_URL = os.environ.get('VIA_LOGO_IMAGE_URL', 'https://s3.amazonaws.com/vtp_prod/static/shared/img/via.png')

# Default to using the payflow pilot testing URL. Set PAYFLOW_LIVE_MODE to
# use the production URL.
PAYFLOW_LIVE_MODE = bool_env('PAYFLOW_LIVE_MODE', False)
PAYFLOW_PARTNER_NAME = os.environ.get('PAYFLOW_PARTNER_NAME', 'verisign')
PAYFLOW_LOGIN = os.environ.get('PAYFLOW_LOGIN', 'viaLanguage')

CLIENT_USER_TYPE = 'client'
VIA_USER_TYPE = 'via'
VENDOR_USER_TYPE = 'vendor'
COMPETITOR_USER_TYPE = 'competitor'
PARTNER_USER_TYPE = 'partner'

NOTIFICATION_TYPE_NOTIFICATION = 'notification'
NOTIFICATION_TYPE_MESSAGE = 'message'

# The TEAMServerSubject.code new clients use
DEFAULT_TEAMSERVER_SUBJECT = os.environ.get('DEFAULT_TEAMSERVER_SUBJECT', 'corporate')

RESPOND_BY_TIMEDELTA = int(os.environ.get('RESPOND_BY_TIMEDELTA', 18))
MINIMUM_TRANSLATION_WORDS_STANDARD = float(os.environ.get('MINIMUM_TRANSLATION_WORDS_STANDARD', 2000.0))
MINIMUM_TRANSLATION_WORDS_EXPRESS = float(os.environ.get('MINIMUM_TRANSLATION_WORDS_EXPRESS', 800.0))
BASIC_TRANSLATION_WORDS_PER_DAY_STANDARD = float(os.environ.get('BASIC_TRANSLATION_WORDS_PER_DAY_STANDARD', 2000.0))
BASIC_TRANSLATION_WORDS_PER_DAY_EXPRESS = float(os.environ.get('BASIC_TRANSLATION_WORDS_PER_DAY_EXPRESS', 3000.0))
TAT_DAYS_STANDARD = int(os.environ.get('TAT_DAYS_STANDARD', 2))
TAT_DAYS_EXPRESS = int(os.environ.get('TAT_DAYS_EXPRESS', 1))
EXPRESS_FACTOR = float(os.environ.get('EXPRESS_FACTOR', 1.5))
MBD_TAT_FACTOR = float(os.environ.get('MBD_TAT_FACTOR', 0.5))

FORCE_MANUAL_ESTIMATE_IF_STANDARD_TAT_IS_OVER = int(os.environ.get('FORCE_MANUAL_ESTIMATE_IF_STANDARD_TAT_IS_OVER', 15))
LARGE_JOB_PRICE = int(os.environ.get('LARGE_JOB_PRICE', 10000))

NON_TRANSLATION_DEFAULT_COST = Decimal(os.environ.get('NON_TRANSLATION_DEFAULT_COST', 25.0))

PM_PERCENT_UNIT_COST_CALC = Decimal(os.environ.get('PM_PERCENT_UNIT_COST_CALC', 0.05))
PM_PRICE_MIN = Decimal(os.environ.get('PM_PRICE_MIN', 65.0))
PM_COST_MIN = Decimal(os.environ.get('PM_COST_MIN', 35.0))
PM_HOURS_MIN_HOURS = float(os.environ.get('PM_HOURS_MIN_HOURS', 1.0))
FILE_PREP_WORDS_PER_HOUR = int(os.environ.get('FILE_PREP_WORDS_PER_HOUR', 20000))
FILE_PREP_MIN_HOURS = float(os.environ.get('FILE_PREP_MIN_HOURS', 0.5))
FEEDBACK_MANAGEMENT_WORDS_PER_HOUR = int(os.environ.get('FEEDBACK_MANAGEMENT_WORDS_PER_HOUR', 20000))
FEEDBACK_MANAGEMENT_MIN_HOURS = float(os.environ.get('FEEDBACK_MANAGEMENT_MIN_HOURS', 0.5))
RECREATE_SOURCE_FROM_PDF_WORDS_PER_HOUR = int(os.environ.get('RECREATE_SOURCE_FROM_PDF_WORDS_PER_HOUR', 3500))
DTP_WORDS_PER_HOUR = int(os.environ.get('DTP_WORDS_PER_HOUR', 3750))
POST_DTP_REVIEW_WORDS_PER_HOUR = int(os.environ.get('POST_DTP_REVIEW_WORDS_PER_HOUR', 4000))
PROOFREADING_THIRD_PARTY_REVIEW_WORDS_PER_HOUR = int(os.environ.get('PROOFREADING_THIRD_PARTY_REVIEW_WORDS_PER_HOUR', 750))
ATTORNEY_REVIEW_WORDS_PER_HOUR = int(os.environ.get('ATTORNEY_REVIEW_WORDS_PER_HOUR', 2500))
PROOFREADING_WORDS_PER_HOUR = int(os.environ.get('PROOFREADING_WORDS_PER_HOUR', 750))
DTP_THIRD_PARTY_REVIEW_REQUIRED = bool_env('DTP_THIRD_PARTY_REVIEW_REQUIRED', True)
DTP_LSO_REQUIRED = bool_env('DTP_LSO_REQUIRED', False)
DTP_LSO_WORDS_PER_HOUR = int(os.environ.get('DTP_LSO_WORDS_PER_HOUR', POST_DTP_REVIEW_WORDS_PER_HOUR))

HOURS_PER_DAY = Decimal(os.environ.get('HOURS_PER_DAY', 8.0))
HOURS_PER_DAY_STANDARD = Decimal(os.environ.get('HOURS_PER_DAY_STANDARD', 5.0))
HOURS_PER_DAY_EXPRESS = Decimal(os.environ.get('HOURS_PER_DAY_EXPRESS', 7.0))
ONE_HOUR_MIN_HOURS = Decimal(os.environ.get('ONE_HOUR_MIN_HOURS', 1.0))
HALF_HOUR_MIN_HOURS = Decimal(os.environ.get('HALF_HOUR_MIN_HOURS', 0.5))
HALF_HOUR_INCREMENT_VALUE = Decimal(os.environ.get('HALF_HOUR_INCREMENT_VALUE', 2))
QUARTER_HOUR_INCREMENT_VALUE = Decimal(os.environ.get('QUARTER_HOUR_INCREMENT_VALUE', 4))

LANGUAGE_COUNT_NUMBER_OF_LANGUAGES = int(os.environ.get('LANGUAGE_COUNT_NUMBER_OF_LANGUAGES', 5))
# If we get too many languages (> 24) it becomes not just a larger workload, but DejaVu project will corrupt.
LANGUAGE_COUNT_MAX_TO_AUTO_ESTIMATE = int(os.environ.get('LANGUAGE_COUNT_MAX_TO_AUTO_ESTIMATE', 24))
JOB_UPLOAD_TIME_FIRST_RECEIVED_TIME_PUSH_HOUR = int(os.environ.get('JOB_UPLOAD_TIME_FIRST_RECEIVED_TIME_PUSH_HOUR', 9))
JOB_UPLOAD_TIME_FIRST_RECEIVED_TIME_PUSH_MINUTE = int(os.environ.get('JOB_UPLOAD_TIME_FIRST_RECEIVED_TIME_PUSH_MINUTE', 30))
JOB_UPLOAD_TIME_FIRST_RECEIVED_TIME = int(os.environ.get('JOB_UPLOAD_TIME_FIRST_RECEIVED_TIME', 9))
JOB_UPLOAD_TIME_LAST_RECEIVED_TIME = int(os.environ.get('JOB_UPLOAD_TIME_LAST_RECEIVED_TIME', 17))
QUOTE_DUE_HOUR = int(os.environ.get('QUOTE_DUE_HOUR', 14))

# TIMEZONE_BLURB_TEXT = os.environ.get('TIMEZONE_BLURB_TEXT', '*All Pacific Time')

SALESFORCE_DEFAULT_OPPORTUNITY_OWNER = os.environ.get('SALESFORCE_DEFAULT_OPPORTUNITY_OWNER', '00540000001SqTA')
HEALTHCARE_CONTACT = os.environ.get('HEALTHCARE_CONTACT', 'KDonovan@viadelivers.com')

VIA_PANAMA_VENDOR_JAMS_ID = os.environ.get('VIA_PANAMA_VENDOR_JAMS_ID', '453054985')
VIA_PANAMA_NO_AUTO_GENERATE_TEP_PO_JAMS = bool_env('VIA_PANAMA_NO_AUTO_GENERATE_TEP_PO_JAMS', False)

NEW_CLIENT_SETUP_ENABLED = bool_env('NEW_CLIENT_SETUP_ENABLED', True)


REPORT_DEFAULT_DAYS_FROM = int(os.environ.get('REPORT_DEFAULT_DAYS_FROM', 120))

SOW_TEMPLATE_DOCX = os.environ.get('SOW_TEMPLATE_DOCX', 'sow_template_via_short_2013.docx')

UPDATE_TM_CALL_DELAY = int(os.environ.get('UPDATE_TM_CALL_DELAY', 10))

FUTURE_DATE_RANGE = int(os.environ.get('FUTURE_DATE_RANGE', 180))
HISTORY_DATE_RANGE = int(os.environ.get('HISTORY_DATE_RANGE', 180))
HISTORY_DATE_RANGE_MONTH = int(os.environ.get('HISTORY_DATE_RANGE_MONTH', 30))

GEOIP_PATH = normpath(join(PROJECT_DIR, 'GEO_DB'))

PAGINATE_BY_STANDARD = int(os.environ.get('PAGINATE_BY_STANDARD', 15))
PAGINATE_BY_LARGE = int(os.environ.get('PAGINATE_BY_LARGE', 1000))
PAGINATE_BY_RANGE_DISPLAY = int(os.environ.get('PAGINATE_BY_RANGE_DISPLAY', 10))
TASKS_PAGINATE_BY_STANDARD = int(os.environ.get('TASKS_PAGINATE_BY_STANDARD', 10))

BACKGROUND_PAGE_REFRESH_COUNTER = int(os.environ.get('BACKGROUND_PAGE_REFRESH_COUNTER', 31))

########## END CONSTANTS

####Avatar settings
AVATAR_STORAGE_DIR = 'avatars/'
AVATAR_DEFAULT_SIZE = int(os.environ.get('AVATAR_DEFAULT_SIZE', 30))

####tinymce settings
TINYMCE_COLS = int(os.environ.get('TINYMCE_COLS', 80))
TINYMCE_ROWS = int(os.environ.get('TINYMCE_ROWS', 10))

TINYMCE_DEFAULT_CONFIG = {
    'selector': 'textarea',
    'theme': 'modern',
    'plugins': 'advlist lists hr preview codesample contextmenu textcolor colorpicker charmap table code',
    'toolbar1': 'formatselect fontselect fontsizeselect | bold italic underline | removeformat | forecolor backcolor | bullist numlist | alignleft alignright | outdent indent | table | hr | charmap | preview | code ',
    'contextmenu': 'formats | link image',
    'menubar': False,
    'inline': False,
    'statusbar': True,
    'height': 360,
}

GARBAGE_COLLECTION_DISABLED = bool_env('GARBAGE_COLLECTION_DISABLED', True)
