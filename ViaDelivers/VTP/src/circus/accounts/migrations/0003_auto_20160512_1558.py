# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_auto_20160427_1402'),
    ]

    operations = [
        migrations.AlterField(
            model_name='circususer',
            name='groups',
            field=models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', verbose_name='groups'),
        ),
        migrations.AlterField(
            model_name='circususer',
            name='last_login',
            field=models.DateTimeField(null=True, verbose_name='last login', blank=True),
        ),
        migrations.AlterField(
            model_name='circususer',
            name='user_type',
            field=models.CharField(max_length=6, choices=[(b'client', 'Client'), (b'via', 'VIA Staff'), (b'vendor', 'Vendor')]),
        ),
    ]
