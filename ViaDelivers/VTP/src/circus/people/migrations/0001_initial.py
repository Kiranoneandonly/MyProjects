# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import shared.fields
import nullablecharfield.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('is_person_account', models.BooleanField(default=False)),
                ('account_number', models.CharField(max_length=40, null=True, verbose_name='JAMS ID', blank=True)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(null=True, blank=True)),
                ('website', models.CharField(max_length=255, null=True, blank=True)),
                ('site', models.CharField(help_text=b"the account's location, e.g. London or Headquarters", max_length=80, null=True, verbose_name=b'Account Site', blank=True)),
                ('phone', shared.fields.PhoneField(max_length=30, null=True, blank=True)),
                ('fax', shared.fields.PhoneField(max_length=30, null=True, blank=True)),
                ('billing_city', models.CharField(max_length=40, null=True, blank=True)),
                ('billing_country', models.CharField(max_length=40, null=True, blank=True)),
                ('billing_postal_code', models.CharField(max_length=20, null=True, blank=True)),
                ('billing_state', models.CharField(max_length=20, null=True, blank=True)),
                ('billing_street', models.TextField(null=True, blank=True)),
                ('jobs_email', models.EmailField(max_length=254, null=True)),
                ('via_team_jobs_email', models.EmailField(max_length=254, null=True)),
                ('salesforce_account_id', nullablecharfield.db.models.fields.CharNullField(db_index=True, max_length=18, null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AccountContactRole',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_primary', models.BooleanField(default=False)),
                ('account', models.ForeignKey(related_name=b'contact_roles', to='people.Account')),
                ('contact', models.ForeignKey(related_name=b'role', to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AccountEmailDomain',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email_domain', models.CharField(max_length=255)),
                ('account', models.ForeignKey(to='people.Account')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AccountType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(max_length=40)),
            ],
            options={
                'verbose_name': 'attribute: Account Type',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ContactRole',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(max_length=40)),
            ],
            options={
                'verbose_name': 'attribute: Contact Role',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='GenericEmailDomain',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('email_domain', models.CharField(max_length=255)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='JoinAccountRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('account', models.ForeignKey(to='people.Account')),
                ('approver', models.ForeignKey(related_name=b'+', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('user', models.ForeignKey(related_name=b'+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Salutation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(max_length=40)),
            ],
            options={
                'verbose_name': 'attribute: Salutation',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VendorType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(max_length=40)),
            ],
            options={
                'verbose_name': 'attribute: Vendor Type',
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='accountcontactrole',
            name='role',
            field=models.ForeignKey(blank=True, to='people.ContactRole', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='account',
            name='account_type',
            field=models.ForeignKey(to='people.AccountType'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='account',
            name='owner',
            field=models.ForeignKey(related_name=b'owned_accounts', blank=True, to=settings.AUTH_USER_MODEL, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='account',
            name='parent',
            field=models.ForeignKey(related_name=b'children', blank=True, to='people.Account', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='account',
            name='vendor_type',
            field=models.ForeignKey(blank=True, to='people.VendorType', null=True),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='SalesforceAccount',
            fields=[
            ],
            options={
                'db_table': 'Account',
                'managed': False,
            },
            bases=(models.Model,),
        ),
    ]
