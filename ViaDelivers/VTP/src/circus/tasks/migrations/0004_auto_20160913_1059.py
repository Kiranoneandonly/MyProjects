# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-09-13 05:29
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0003_auto_20160902_1718'),
    ]

    operations = [
        migrations.AlterField(
            model_name='taskquote',
            name='gm',
            field=models.DecimalField(blank=True, decimal_places=4, default=0.0, max_digits=15, null=True),
        ),
        migrations.AlterField(
            model_name='taskquote',
            name='mbd',
            field=models.DecimalField(blank=True, decimal_places=4, default=0.0, max_digits=15, null=True),
        ),
        migrations.AlterField(
            model_name='taskquote',
            name='net_price',
            field=models.DecimalField(blank=True, decimal_places=4, default=0.0, max_digits=15, null=True),
        ),
        migrations.AlterField(
            model_name='taskquote',
            name='raw_price',
            field=models.DecimalField(blank=True, decimal_places=4, default=0.0, max_digits=15, null=True),
        ),
        migrations.AlterField(
            model_name='taskquote',
            name='total_cost',
            field=models.DecimalField(blank=True, decimal_places=4, default=0, max_digits=15, null=True),
        ),
    ]
