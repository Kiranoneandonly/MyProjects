# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import shared.fields


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0001_initial'),
        ('clients', '0001_initial'),
        ('services', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientNonTranslationPrice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('unit_price', shared.fields.CurrencyField(default=0.0, max_digits=15, decimal_places=4)),
                ('client', models.ForeignKey(blank=True, to='clients.Client', null=True)),
                ('pricing_scheme', models.ForeignKey(related_name='+', blank=True, to='services.PricingScheme', null=True)),
                ('service', models.ForeignKey(related_name='+', to='services.Service')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ClientTranslationPrice',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('guaranteed', shared.fields.CurrencyField(default=0.0, verbose_name='Prfect', max_digits=15, decimal_places=4)),
                ('exact', shared.fields.CurrencyField(default=0.5, verbose_name='Exact', max_digits=15, decimal_places=4)),
                ('duplicate', shared.fields.CurrencyField(default=0.5, verbose_name='Reps', max_digits=15, decimal_places=4)),
                ('fuzzy9599', shared.fields.CurrencyField(default=1.0, verbose_name='95-99', max_digits=15, decimal_places=4)),
                ('fuzzy8594', shared.fields.CurrencyField(default=1.0, verbose_name='85-94', max_digits=15, decimal_places=4)),
                ('fuzzy7584', shared.fields.CurrencyField(default=1.0, verbose_name='75-84', max_digits=15, decimal_places=4)),
                ('fuzzy5074', shared.fields.CurrencyField(default=1.0, verbose_name='50-74', max_digits=15, decimal_places=4)),
                ('no_match', shared.fields.CurrencyField(default=1.0, verbose_name='NoMch', max_digits=15, decimal_places=4)),
                ('minimum_price', shared.fields.CurrencyField(default=0.0, max_digits=15, decimal_places=4)),
                ('word_rate', shared.fields.CurrencyField(default=0.0, max_digits=15, decimal_places=4)),
                ('notes', models.TextField(null=True, blank=True)),
                ('basis', models.ForeignKey(related_name='+', blank=True, to='services.PricingBasis', null=True)),
                ('client', models.ForeignKey(blank=True, to='clients.Client', null=True)),
                ('pricing_scheme', models.ForeignKey(related_name='+', blank=True, to='services.PricingScheme', null=True)),
                ('service', models.ForeignKey(related_name='+', to='services.Service')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VendorNonTranslationRate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('minimum', shared.fields.CurrencyField(default=0.0, max_digits=15, decimal_places=4)),
                ('unit_cost', shared.fields.CurrencyField(default=0.0, max_digits=15, decimal_places=4)),
                ('client', models.ForeignKey(related_name='+', blank=True, to='clients.Client', null=True)),
                ('service', models.ForeignKey(related_name='+', to='services.Service')),
                ('vendor', models.ForeignKey(blank=True, to='vendors.Vendor', null=True)),
                ('vertical', models.ForeignKey(related_name='+', blank=True, to='services.Vertical', null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VendorTranslationRate',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('guaranteed', shared.fields.CurrencyField(default=0.0, verbose_name='Prfect', max_digits=15, decimal_places=4)),
                ('exact', shared.fields.CurrencyField(default=0.5, verbose_name='Exact', max_digits=15, decimal_places=4)),
                ('duplicate', shared.fields.CurrencyField(default=0.5, verbose_name='Reps', max_digits=15, decimal_places=4)),
                ('fuzzy9599', shared.fields.CurrencyField(default=1.0, verbose_name='95-99', max_digits=15, decimal_places=4)),
                ('fuzzy8594', shared.fields.CurrencyField(default=1.0, verbose_name='85-94', max_digits=15, decimal_places=4)),
                ('fuzzy7584', shared.fields.CurrencyField(default=1.0, verbose_name='75-84', max_digits=15, decimal_places=4)),
                ('fuzzy5074', shared.fields.CurrencyField(default=1.0, verbose_name='50-74', max_digits=15, decimal_places=4)),
                ('no_match', shared.fields.CurrencyField(default=1.0, verbose_name='NoMch', max_digits=15, decimal_places=4)),
                ('minimum', shared.fields.CurrencyField(default=0.0, max_digits=15, decimal_places=4)),
                ('word_rate', shared.fields.CurrencyField(default=0.0, max_digits=15, decimal_places=4)),
                ('basis', models.ForeignKey(related_name='+', blank=True, to='services.PricingBasis', null=True)),
                ('client', models.ForeignKey(related_name='+', blank=True, to='clients.Client', null=True)),
                ('service', models.ForeignKey(related_name='+', to='services.Service')),
                ('vendor', models.ForeignKey(blank=True, to='vendors.Vendor', null=True)),
                ('vertical', models.ForeignKey(related_name='+', blank=True, to='services.Vertical', null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='vendortranslationrate',
            unique_together=set([('vendor', 'service', 'vertical', 'client')]),
        ),
        migrations.AlterUniqueTogether(
            name='vendornontranslationrate',
            unique_together=set([('vendor', 'service', 'vertical', 'client')]),
        ),
        migrations.AlterUniqueTogether(
            name='clienttranslationprice',
            unique_together=set([('client', 'service', 'pricing_scheme')]),
        ),
        migrations.AlterUniqueTogether(
            name='clientnontranslationprice',
            unique_together=set([('client', 'service', 'pricing_scheme')]),
        ),
    ]
