# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-02-07 10:15
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0024_auto_20160726_1545'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='is_phi_secure_job',
            field=models.NullBooleanField(default=False),
        ),
    ]
