# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-09-08 06:55
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0006_auto_20160908_1148'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pricequote',
            name='project',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='projects.Project'),
        ),
    ]
