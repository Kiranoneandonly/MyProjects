# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-08-26 07:25
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dwh_reports', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectsreporting',
            name='is_secure_job',
            field=models.NullBooleanField(default=False),
        ),
    ]
