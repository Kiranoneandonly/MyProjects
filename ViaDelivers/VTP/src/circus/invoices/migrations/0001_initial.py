# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings
import shared.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Invoice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('due_date', models.DateTimeField(default=django.utils.timezone.now, null=True, verbose_name='Due Date', blank=True)),
                ('order_amount', shared.fields.CurrencyField(default=0.0, max_digits=15, decimal_places=4)),
                ('invoice_amount', shared.fields.CurrencyField(default=0.0, max_digits=15, decimal_places=4)),
                ('ok_to_invoice', models.BooleanField(default=False)),
                ('internal_notes', models.TextField(null=True, blank=True)),
                ('external_notes', models.TextField(null=True, blank=True)),
                ('billing_refnumber', models.CharField(max_length=50, null=True, verbose_name='RefNumber', blank=True)),
                ('billing_txnnumber', models.CharField(max_length=50, null=True, verbose_name='TxnNumber', blank=True)),
                ('billing_sync_date', models.DateTimeField(null=True, verbose_name='Sync Date', blank=True)),
                ('billing_sent_date', models.DateTimeField(null=True, verbose_name='Sent Date', blank=True)),
                ('billing_paid', models.BooleanField(default=False, verbose_name='Paid')),
                ('billing_paid_date', models.DateTimeField(null=True, verbose_name='Paid Date', blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InvoiceNotes',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('note', models.TextField(null=True, blank=True)),
                ('invoice', models.ForeignKey(to='invoices.Invoice')),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'invoice notes',
            },
            bases=(models.Model,),
        ),
    ]
