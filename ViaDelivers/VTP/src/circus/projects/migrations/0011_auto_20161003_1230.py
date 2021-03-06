# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-10-03 07:00
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0010_auto_20160913_1059'),
    ]

    operations = [
        migrations.CreateModel(
            name='PriceQuoteDetails',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('target_id', models.IntegerField(blank=True, null=True)),
                ('target_price', models.DecimalField(blank=True, decimal_places=4, default=0.0, max_digits=15, null=True)),
                ('target_cost', models.DecimalField(blank=True, decimal_places=4, default=0.0, max_digits=15, null=True)),
                ('target_gross_margin', models.DecimalField(blank=True, decimal_places=4, default=0.0, max_digits=15, null=True)),
                ('target_standard_tat', models.DecimalField(blank=True, decimal_places=2, default=0.0, max_digits=15, null=True)),
                ('target_express_tat', models.DecimalField(blank=True, decimal_places=2, default=0.0, max_digits=15, null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RemoveField(
            model_name='pricequote',
            name='target_cost',
        ),
        migrations.RemoveField(
            model_name='pricequote',
            name='target_express_tat',
        ),
        migrations.RemoveField(
            model_name='pricequote',
            name='target_gross_margin',
        ),
        migrations.RemoveField(
            model_name='pricequote',
            name='target_id',
        ),
        migrations.RemoveField(
            model_name='pricequote',
            name='target_price',
        ),
        migrations.RemoveField(
            model_name='pricequote',
            name='target_standard_tat',
        ),
        migrations.AddField(
            model_name='pricequotedetails',
            name='pricequote',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='projects.PriceQuote'),
        ),
    ]
