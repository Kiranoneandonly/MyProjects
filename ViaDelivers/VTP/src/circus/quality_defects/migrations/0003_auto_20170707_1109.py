# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-07-07 18:09
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('quality_defects', '0002_auto_20160427_1402'),
    ]

    operations = [
        migrations.AlterField(
            model_name='qualitydefect',
            name='client',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='client', to='clients.Client'),
        ),
        migrations.AlterField(
            model_name='qualitydefect',
            name='vendor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='vendor', to='vendors.Vendor'),
        ),
    ]