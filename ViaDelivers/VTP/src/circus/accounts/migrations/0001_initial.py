# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import shared.fields
import nullablecharfield.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CircusUser',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(default=django.utils.timezone.now, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('user_type', models.CharField(max_length='6', choices=[(b'client', 'Client'), (b'via', 'VIA Staff'), (b'vendor', 'Vendor')])),
                ('email', models.EmailField(unique=True, max_length=254, db_index=True)),
                ('is_staff', models.BooleanField(default=False, verbose_name='staff status')),
                ('is_active', models.BooleanField(default=False, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('approved_buyer', models.BooleanField(default=False)),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('salesforce_contact_id', nullablecharfield.db.models.fields.CharNullField(max_length=18, unique=True, null=True, blank=True)),
                ('salesforce_user_id', nullablecharfield.db.models.fields.CharNullField(db_index=True, max_length=18, null=True, blank=True)),
                ('first_name', models.CharField(max_length=40, null=True, blank=True)),
                ('last_name', models.CharField(max_length=80, null=True, blank=True)),
                ('description', models.TextField(null=True, blank=True)),
                ('title', models.CharField(max_length=80, null=True, blank=True)),
                ('department', models.CharField(max_length=255, null=True, blank=True)),
                ('phone', shared.fields.PhoneField(max_length=30, null=True, verbose_name='Business Phone', blank=True)),
                ('mobile_phone', shared.fields.PhoneField(max_length=30, null=True, blank=True)),
                ('home_phone', shared.fields.PhoneField(max_length=30, null=True, blank=True)),
                ('fax', shared.fields.PhoneField(max_length=30, null=True, blank=True)),
                ('do_not_call', models.BooleanField(default=False)),
                ('mailing_city', models.CharField(max_length=40, null=True, blank=True)),
                ('mailing_country', models.CharField(max_length=40, null=True, blank=True)),
                ('mailing_postal_code', models.CharField(max_length=20, null=True, blank=True)),
                ('mailing_state', models.CharField(max_length=20, null=True, blank=True)),
                ('mailing_street', models.TextField(null=True, blank=True)),
                ('activation_code', models.CharField(max_length=255, null=True, blank=True)),
                ('profile_complete', models.BooleanField(default=False)),
                ('registration_complete', models.BooleanField(default=False)),
                ('jams_username', models.CharField(max_length=50, null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
