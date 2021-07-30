# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='InvoiceTemplate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(max_length=40)),
            ],
            options={
                'verbose_name': 'attribute: Invoice Template',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectPayment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('payment_method', models.CharField(default='ca', max_length=10, choices=[('ca', 'Corporate/Invoice'), ('cc', 'Credit Card')])),
                ('cc_response_auth_code', models.CharField(max_length=255, null=True, verbose_name='Credit Card Authorization Code', blank=True)),
                ('ca_invoice_number', models.CharField(help_text='Corporate Account Reference Number. 100 characters max.', max_length=100, null=True, verbose_name='Purchase Order', blank=True)),
                ('note', models.TextField(null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
