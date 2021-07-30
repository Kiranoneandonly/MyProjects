# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='QualityDefect',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('quality_defect', models.CharField(blank=True, max_length=10, null=True, choices=[(b'no', b'No'), (b'eqd', b'EQD'), (b'iqd', b'IQD')])),
                ('title', models.CharField(max_length=300, null=True, verbose_name=b'title', blank=True)),
                ('due_date', models.DateTimeField(null=True, verbose_name='Due Date', blank=True)),
                ('due_created', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Date Created')),
                ('due_modified', models.DateTimeField(null=True, verbose_name='Date Created', blank=True)),
                ('status', models.CharField(blank=True, max_length=50, null=True, choices=[(b'open', b'Open'), (b'closed', b'Closed')])),
                ('priority', models.CharField(blank=True, max_length=20, null=True, choices=[(b'1', b'(1) High'), (b'2', b'(2) Normal'), (b'3', b'(3) Low')])),
                ('closed_date', models.DateTimeField(null=True, verbose_name='Closed Date', blank=True)),
                ('root_cause', models.CharField(blank=True, max_length=50, null=True, choices=[(b'PM', b'PM'), (b'SM', b'SM'), (b'DTP', b'DTP'), (b'Linguistic', b'Linguistic'), (b'Billing', b'Billing'), (b'Technical', b'Technical'), (b'client_source', b'Client Source'), (b'Sales', b'Sales'), (b'Other', b'Other')])),
                ('root_cause_analysis', models.TextField(null=True, verbose_name='Root Cause Analysis', blank=True)),
                ('resolution', models.TextField(null=True, verbose_name='Resolution', blank=True)),
                ('client_consulted', models.CharField(blank=True, max_length=10, null=True, choices=[(b'satisfied', b'Satisfied'), (b'not_satisfied', b'Not Satisfied')])),
                ('client_consulted_notes', models.TextField(null=True, verbose_name='Client consulted notes', blank=True)),
                ('client_informed', models.BooleanField(default=False, verbose_name='client informed')),
                ('assigned_to', models.ForeignKey(related_name=b'+', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('client', models.ForeignKey(blank=True, to='clients.Client', null=True)),
                ('project', models.ForeignKey(blank=True, to='projects.Project', null=True)),
                ('related_qd', models.ForeignKey(blank=True, to='quality_defects.QualityDefect', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='QualityDefectComment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('comment', models.TextField(null=True, verbose_name='Comment', blank=True)),
                ('date_created', models.DateTimeField(default=django.utils.timezone.now, verbose_name='Date Created')),
                ('date_modified', models.DateTimeField(null=True, verbose_name='Date Created', blank=True)),
                ('comment_by', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('quality_defect', models.ForeignKey(to='quality_defects.QualityDefect')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
