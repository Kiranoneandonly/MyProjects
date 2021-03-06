# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2016-07-26 10:15
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('people', '0003_auto_20160620_1827'),
        ('projects', '0023_auto_20160720_1250'),
    ]

    operations = [
        migrations.CreateModel(
            name='SecureJobAccess',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_access_given', models.BooleanField(choices=[(True, 'Access given'), (False, 'No Access')], default=False)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='member_account', to='people.Account')),
            ],
        ),
        migrations.AlterField(
            model_name='project',
            name='restricted_locations',
            field=models.ManyToManyField(blank=True, null=True, related_name='_project_restricted_locations_+', to='services.Country'),
        ),
        migrations.AlterField(
            model_name='project',
            name='target_locales',
            field=models.ManyToManyField(blank=True, null=True, related_name='_project_target_locales_+', to='services.Locale'),
        ),
        migrations.AddField(
            model_name='securejobaccess',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='secure_job', to='projects.Project'),
        ),
        migrations.AddField(
            model_name='securejobaccess',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='secure_job_team', to=settings.AUTH_USER_MODEL),
        ),
    ]
