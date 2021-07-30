# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Actions',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('action_object_id', models.PositiveIntegerField()),
                ('action_object_name', models.CharField(max_length=500, db_index=True)),
                ('verb', models.CharField(max_length=255)),
                ('actor', models.CharField(max_length=500)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('trans_file_name', models.CharField(default='', max_length=500, null=True, blank=True)),
                ('support_file_name', models.CharField(default='', max_length=500, null=True, blank=True)),
                ('supplier_reference_file', models.CharField(default='', max_length=500, null=True, blank=True)),
                ('ntt_input_file_name', models.CharField(default='', max_length=500, null=True, blank=True)),
                ('ntt_output_file_name', models.CharField(default='', max_length=500, null=True, blank=True)),
                ('ntt_support_file_name', models.CharField(default='', max_length=500, null=True, blank=True)),
                ('task_service_type', models.CharField(default='', max_length=500, null=True, blank=True)),
                ('file_type', models.CharField(default='', max_length=500, null=True, blank=True)),
                ('job_id', models.IntegerField(default=0, null=True, blank=True)),
                ('task_id', models.IntegerField(default=0, null=True, blank=True)),
                ('user', models.CharField(default='', max_length=500, null=True, blank=True)),
                ('status', models.CharField(default='', max_length=500, null=True, blank=True)),
                ('description', models.TextField(null=True, blank=True)),
                ('data', models.CharField(default='', max_length=500, null=True, blank=True)),
                ('project_manager_approver', models.IntegerField(default=0, null=True, blank=True)),
                ('ops_management_approver', models.IntegerField(default=0, null=True, blank=True)),
                ('sales_management_approver', models.IntegerField(default=0, null=True, blank=True)),
                ('action_content_type', models.ForeignKey(related_name='action', to='contenttypes.ContentType')),
            ],
            options={
                'ordering': ('-timestamp',),
            },
            bases=(models.Model,),
        ),
    ]
