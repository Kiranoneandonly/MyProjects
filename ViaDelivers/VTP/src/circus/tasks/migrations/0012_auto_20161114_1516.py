# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-11-14 23:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0011_taskassetquote_asset_wordcount'),
    ]

    operations = [
        migrations.AddField(
            model_name='taskquote',
            name='express_tat',
            field=models.DecimalField(blank=True, decimal_places=2, default=0.0, max_digits=15, null=True),
        ),
        migrations.AddField(
            model_name='taskquote',
            name='standard_tat',
            field=models.DecimalField(blank=True, decimal_places=2, default=0.0, max_digits=15, null=True),
        ),
    ]
