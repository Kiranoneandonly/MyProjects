"""Development settings and globals."""

from base import *  # NOQA

########## IN-MEMORY TEST DATABASE
DATABASES['default'] = {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
    "USER": "",
    "PASSWORD": "",
    "HOST": "",
    "PORT": "",
}

# You can, and maybe should, use a LocMemCache backend for tests, but
# django.test.TestCase's automatic rollbacks and django-cache-machine's
# cache get out of sync.
# https://github.com/jbalogh/django-cache-machine/issues/64
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
    }
}

######### Don't use S3 storage
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
STATICFILES_STORAGE = 'django.core.files.storage.FileSystemStorage'

# Unit test passwords prefer speed over security.
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)


# Don't use live Payflow URL.
PAYFLOW_LIVE_MODE = False


########## CELERY
# causes immediate execution of tasks, remove for production
# http://docs.celeryproject.org/en/latest/django/unit-testing.html#testing-with-django
CELERY_ALWAYS_EAGER = False
########## END CELERY

########## CONSTANTS
LINKS_USE_HTTPS = bool_env('LINKS_USE_HTTPS', False)
SECURE_SSL_REDIRECT = LINKS_USE_HTTPS

# DVX API
VIA_API_DVX_TEAMSERVER_DVX_TS_DEV = bool_env('VIA_API_DVX_TEAMSERVER_DVX_TS_DEV', False)
VIA_DVX_BASE_URL = 'http://teamserver.viadelivers.com/dvx_ts_dev' if VIA_API_DVX_TEAMSERVER_DVX_TS_DEV else VIA_DVX_BASE_URL

VIA_API_DVX_TEAMSERVER_VS_DEBUG = bool_env('VIA_API_DVX_TEAMSERVER_VS_DEBUG', True)
VIA_DVX_BASE_URL = 'http://localhost:9335' if VIA_API_DVX_TEAMSERVER_VS_DEBUG else VIA_DVX_BASE_URL

VIA_DVX_API_VERSION = 2
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
VIA_API_JAMS_VS_DEBUG = bool_env('VIA_API_JAMS_VS_DEBUG', True)
VIA_JAMS_BASE_URL = 'http://localhost:52759' if VIA_API_JAMS_VS_DEBUG else VIA_JAMS_BASE_URL
VIA_JAMS_JOB_URL_V1 = VIA_JAMS_BASE_URL + '/api/v1/jobs'
VIA_JAMS_ESTIMATE_URL_V1 = VIA_JAMS_BASE_URL + '/api/v1/estimates'
VIA_JAMS_TASK_URL_V1 = VIA_JAMS_BASE_URL + '/api/v1/tasks'

VIA_ESTIMATES_EMAIL_ALIAS = os.environ.get('VIA_ESTIMATES_EMAIL_ALIAS', 'developer@viadelivers.com')
VIA_TSG_GROUP_EMAIL_ALIAS = os.environ.get('VIA_TSG_GROUP_EMAIL_ALIAS', 'developer@viadelivers.com')
VIA_PM_GROUP_EMAIL_ALIAS = os.environ.get('VIA_PM_GROUP_EMAIL_ALIAS', 'developer@viadelivers.com')
VIA_SALES_GROUP_EMAIL_ALIAS = os.environ.get('VIA_SALES_GROUP_EMAIL_ALIAS', 'developer@viadelivers.com')

########## END CONSTANTS
