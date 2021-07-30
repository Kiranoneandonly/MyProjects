# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        ('accounts', '0001_initial'),
        ('people', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='circususer',
            name='account',
            field=models.ForeignKey(related_name='contacts', blank=True, to='people.Account', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='circususer',
            name='groups',
            field=models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Group', blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of his/her group.', verbose_name='groups'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='circususer',
            name='reports_to',
            field=models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='circususer',
            name='salutation',
            field=models.ForeignKey(blank=True, to='people.Salutation', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='circususer',
            name='user_permissions',
            field=models.ManyToManyField(related_query_name='user', related_name='user_set', to='auth.Permission', blank=True, help_text='Specific permissions for this user.', verbose_name='user permissions'),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='SalesforceContact',
            fields=[
            ],
            options={
                'db_table': 'Contact',
                'managed': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SalesforceUser',
            fields=[
            ],
            options={
                'db_table': 'User',
                'managed': False,
            },
            bases=(models.Model,),
        ),
    ]
