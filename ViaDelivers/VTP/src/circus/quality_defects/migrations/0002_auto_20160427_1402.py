# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0001_initial'),
        ('tasks', '0001_initial'),
        ('quality_defects', '0001_initial'),
        ('services', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='qualitydefect',
            name='task',
            field=models.ForeignKey(default=False, blank=True, to='tasks.Task', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='qualitydefect',
            name='vendor',
            field=models.ForeignKey(blank=True, to='vendors.Vendor', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='qualitydefect',
            name='vertical',
            field=models.ForeignKey(blank=True, to='services.Vertical', null=True),
            preserve_default=True,
        ),
    ]
