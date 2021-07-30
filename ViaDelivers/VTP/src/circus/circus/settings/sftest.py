# -*- coding: utf-8 -*-
# Settings for salesforce tests.
# Run with manage.py test --settings circus.settings.sftest --pattern 'sftest_*.py'

from .test import *

# uses the remote salesforce DB!
DATABASES['salesforce'] = {
    'ENGINE': 'salesforce.backend',
    'CONSUMER_KEY': os.environ.get('SALESFORCE_CONSUMER_KEY'),
    'CONSUMER_SECRET': os.environ.get('SALESFORCE_CONSUMER_SECRET'),
    'USER': os.environ.get('SALESFORCE_USER'),
    # This is user's password + security token
    'PASSWORD': os.environ.get('SALESFORCE_PASSWORD'),
    'HOST': 'https://login.salesforce.com',
}

# LOGGING['loggers']['salesforce'] = {
#     'handlers': ['console'],
#     'level': 'DEBUG'
# }
