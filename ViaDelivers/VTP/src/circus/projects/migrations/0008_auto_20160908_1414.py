# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-09-08 08:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0007_auto_20160908_1225'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pricequote',
            name='target_express_tat',
            field=models.DecimalField(decimal_places=4, default=0.0, max_digits=15),
        ),
        migrations.AlterField(
            model_name='pricequote',
            name='target_standard_tat',
            field=models.DecimalField(decimal_places=4, default=0.0, max_digits=15),
        ),
    ]
