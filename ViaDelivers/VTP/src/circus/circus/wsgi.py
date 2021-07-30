"""
WSGI config for circus project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/howto/deployment/wsgi/

----------------------------------

WSGI config for circus project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""

import os
from os.path import abspath, dirname
from sys import path
import logging

from django.conf import settings

logger = logging.getLogger('circus.' + __name__)

SITE_ROOT = dirname(dirname(abspath(__file__)))
path.append(SITE_ROOT)

logger.info("SITE_ROOT: %s", SITE_ROOT)
logger.info("sys.path: %s", path)

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks if running multiple sites in the
# same mod_wsgi process. To fix this, use mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "circus.settings.production")

deploy_env = "production"

if 'VTP_SETTINGS_ENV' in os.environ:
    deploy_env = os.environ['VTP_SETTINGS_ENV']

if deploy_env == "production":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "circus.settings.production")
elif deploy_env == "test":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "circus.settings.test")
elif deploy_env == "local":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "circus.settings.local")
else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "circus.settings.production")

logger.info("deploy_env: %s", deploy_env)
logger.info("DJANGO_SETTINGS_MODULE: %s", os.environ.get('DJANGO_SETTINGS_MODULE', 'DJANGO_SETTINGS_MODULE not found'))

# Fix django closing connection to MemCachier after every request (#11331)
from django.core.cache.backends.memcached import BaseMemcachedCache
BaseMemcachedCache.close = lambda self, **kwargs: None

# This application object is used by any WSGI server configured to use this file.
# This includes Django's development server, if the WSGI_APPLICATION setting points here.
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

if settings.GARBAGE_COLLECTION_DISABLED:
    logger.info("GARBAGE_COLLECTION_DISABLED: %s", settings.GARBAGE_COLLECTION_DISABLED)
    # gc.disable() doesn't work, because some random 3rd-party library will enable it back implicitly.
    import gc
    gc.disable()
    gc.set_threshold(0)
    # Suicide immediately after other atexit functions finishes.
    # CPython will do a bunch of cleanups in Py_Finalize which will again cause Copy-on-Write, including a final GC
    import atexit
    atexit.register(os._exit, 0)