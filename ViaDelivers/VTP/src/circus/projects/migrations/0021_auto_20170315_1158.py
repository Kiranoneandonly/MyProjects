# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-03-15 06:28
from __future__ import unicode_literals

from django.db import migrations, models
import tinymce.models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0019_merge_20161102_1727'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='instructions',
            field=tinymce.models.HTMLField(blank=True, null=True, verbose_name='Client Instructions'),
        ),
        migrations.AlterField(
            model_name='project',
            name='instructions_vendor',
            field=tinymce.models.HTMLField(blank=True, null=True, verbose_name='Supplier Instructions'),
        ),
        migrations.AlterField(
            model_name='project',
            name='instructions_via',
            field=tinymce.models.HTMLField(blank=True, null=True, verbose_name='VIA Instructions'),
        ),
        migrations.AddField(
            model_name='project',
            name='supplier_reference',
            field=models.NullBooleanField(default=False),
        ),
]