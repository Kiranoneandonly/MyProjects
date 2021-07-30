"""Production settings and globals."""
from configurations import values
from os import environ
import os
import urlparse
import sys

from base import *

# ALLOWED_HOSTS = [".herokussl.com", ".herokuapp.com", ".viadelivers.com", ".viadelivers.net", ".viadelivers.net.", ".viadelivers.com."]
# Allow all host hosts/domain names for this site
ALLOWED_HOSTS = ['*']

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.sendgrid.net')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-user
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'app4576961@heroku.com')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-host-password
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'k8irpmd9')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-port
EMAIL_PORT = os.environ.get('EMAIL_PORT', 587)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-use-tls
EMAIL_USE_TLS = bool_env('EMAIL_USE_TLS', True)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-subject-prefix
EMAIL_SUBJECT_PREFIX = '[%s] ' % APP_SLUG_INSTANCE
########## END EMAIL CONFIGURATION

########## DATABASE CONFIGURATION
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

########## CACHE CONFIGURATION
# Only do this here because thanks to django-pylibmc-sasl and pylibmc memcacheify is painful to install on windows.
try:
    # See: https://github.com/rdegges/django-heroku-memcacheify
    from memcacheify import memcacheify

    CACHES = memcacheify()
except ImportError:
    CACHES = values.CacheURLValue(default="memcached://127.0.0.1:11211")
########## END CACHE CONFIGURATION

########## AMAZON S3 CONFIGURATION
# real production is vtp_prod, but for translation-dev.viadelivers.com, its production but we want circus_dev
STATIC_URL = AWS_BUCKET_URL + STATIC_URL

ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'
########## END AMAZON S3 CONFIGURATION
