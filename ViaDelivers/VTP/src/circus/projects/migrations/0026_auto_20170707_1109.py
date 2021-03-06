# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-07-07 18:09
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0025_auto_20170207_1545'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='access_request',
            field=models.ManyToManyField(blank=True, related_name='access_project', through='projects.ProjectAccess', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='project',
            name='assigned_to',
            field=models.ManyToManyField(blank=True, related_name='_project_assigned_to_+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='project',
            name='restricted_locations',
            field=models.ManyToManyField(blank=True, related_name='_project_restricted_locations_+', to='services.Country'),
        ),
        migrations.AlterField(
            model_name='project',
            name='target_locales',
            field=models.ManyToManyField(blank=True, related_name='_project_target_locales_+', to='services.Locale'),
        ),
        migrations.AlterField(
            model_name='projectteamrole',
            name='role',
            field=models.CharField(blank=True, choices=[(b'pm', b'Project Manager'), (b'ae', b'Account Executive'), (b'tsg_eng', b'TSG Engineer'), (b'vle_eng', b'VLE Engineer'), (b'qa_eng', b'QA Engineer'), (b'sjt_member', b'Secure Job Team Member'), (b'psj_team', b'PHI Secure Job Team Member')], max_length=10, null=True),
        ),
    ]
