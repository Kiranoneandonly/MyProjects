# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-06-07 08:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='is_top_organization',
            field=models.BooleanField(default=False),
        ),
    ]
