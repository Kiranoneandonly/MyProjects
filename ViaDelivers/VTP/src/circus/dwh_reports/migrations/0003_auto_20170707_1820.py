# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-07-08 01:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dwh_reports', '0002_projectsreporting_is_secure_job'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clientreport',
            name='code',
            field=models.CharField(db_index=True, max_length=40, unique=True),
        ),
    ]
