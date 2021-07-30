#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    # os.environ.setdefault("DJANGO_SETTINGS_MODULE", "circus.settings")

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

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
