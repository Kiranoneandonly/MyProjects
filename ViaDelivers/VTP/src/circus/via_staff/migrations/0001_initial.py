# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('people', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Via',
            fields=[
            ],
            options={
                'verbose_name': 'VIA',
                'proxy': True,
                'verbose_name_plural': 'VIA',
            },
            bases=('people.account',),
        ),
        migrations.CreateModel(
            name='ViaContact',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('accounts.circususer',),
        ),
        migrations.CreateModel(
            name='ViaEmailDomain',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('people.accountemaildomain',),
        ),
    ]
