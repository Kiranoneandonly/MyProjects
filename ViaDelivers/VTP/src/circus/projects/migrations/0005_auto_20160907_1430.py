# -*- coding: utf-8 -*-
# Generated by Django 1.9.9 on 2016-09-07 21:30
from __future__ import unicode_literals
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0004_auto_20160621_1213'),
    ]

    operations = [
        migrations.CreateModel(
            name='PriceQuote',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('price', models.DecimalField(decimal_places=2, default=0.0, max_digits=15)),
                ('cost', models.DecimalField(decimal_places=2, default=0.0, max_digits=15)),
                ('gm', models.DecimalField(decimal_places=2, default=0.0, max_digits=15)),
                ('target_id', models.IntegerField(unique=True)),
                ('target_price', models.DecimalField(decimal_places=4, default=0.0, max_digits=15)),
                ('target_cost', models.DecimalField(decimal_places=4, default=0.0, max_digits=15)),
                ('target_gross_margin', models.DecimalField(decimal_places=4, default=0.0, max_digits=15)),
                ('target_standard_tat', models.IntegerField(unique=True)),
                ('target_express_tat', models.IntegerField(unique=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='projects.Project')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AlterField(
            model_name='projectservicesglobal',
            name='express_days',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
        migrations.AlterField(
            model_name='projectservicesglobal',
            name='standard_days',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
    ]
