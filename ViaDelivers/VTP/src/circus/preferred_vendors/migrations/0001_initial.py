# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0001_initial'),
        ('clients', '0001_initial'),
        ('services', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PreferredVendor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('priority', models.IntegerField(default=1)),
                ('client', models.ForeignKey(related_name=b'preferred_vendors', blank=True, to='clients.Client', null=True)),
                ('service_type', models.ForeignKey(blank=True, to='services.ServiceType', null=True)),
                ('source', models.ForeignKey(related_name=b'preferred_vendors_as_source', blank=True, to='services.Locale', null=True)),
                ('target', models.ForeignKey(related_name=b'preferred_vendors_as_target', blank=True, to='services.Locale', null=True)),
                ('vendor', models.ForeignKey(to='vendors.Vendor')),
                ('vertical', models.ForeignKey(related_name=b'preferred_vendors', blank=True, to='services.Vertical', null=True)),
            ],
            options={
                'ordering': ['priority'],
            },
            bases=(models.Model,),
        ),
    ]
