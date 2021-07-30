# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from decimal import Decimal
import clients.models
import django.db.models.deletion
from django.conf import settings
import shared.fields


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('people', '0001_initial'),
        ('services', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ClientManifest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('express_factor', models.DecimalField(default=Decimal('1.5'), max_digits=15, decimal_places=4)),
                ('auto_estimate_jobs', models.BooleanField(default=True)),
                ('auto_start_workflow', models.BooleanField(default=True)),
                ('is_hourly_schedule', models.BooleanField(default=False)),
                ('secure_jobs', models.BooleanField(default=False)),
                ('state_secrets_validation', models.BooleanField(default=False)),
                ('restricted_pricing', models.DecimalField(decimal_places=4, default=Decimal('16'), max_digits=6, blank=True, null=True, verbose_name='Restricted Pricing %')),
                ('pricing_memory_bank_discount', models.BooleanField(default=False, verbose_name='Memory Bank Discount')),
                ('teamserver_tm_enabled', models.BooleanField(default=False, verbose_name='TEAMServer TM Enabled')),
                ('note', models.TextField(blank=True)),
                ('guaranteed', models.DecimalField(null=True, verbose_name='Prfect', max_digits=6, decimal_places=4, blank=True)),
                ('exact', models.DecimalField(null=True, verbose_name='Exact', max_digits=6, decimal_places=4, blank=True)),
                ('duplicate', models.DecimalField(null=True, verbose_name='Reps', max_digits=6, decimal_places=4, blank=True)),
                ('fuzzy9599', models.DecimalField(null=True, verbose_name='95-99', max_digits=6, decimal_places=4, blank=True)),
                ('fuzzy8594', models.DecimalField(null=True, verbose_name='85-94', max_digits=6, decimal_places=4, blank=True)),
                ('fuzzy7584', models.DecimalField(null=True, verbose_name='75-84', max_digits=6, decimal_places=4, blank=True)),
                ('fuzzy5074', models.DecimalField(null=True, verbose_name='50-74', max_digits=6, decimal_places=4, blank=True)),
                ('no_match', models.DecimalField(null=True, verbose_name='NoMch', max_digits=6, decimal_places=4, blank=True)),
                ('minimum_price', shared.fields.CurrencyField(null=True, max_digits=15, decimal_places=4, blank=True)),
                ('teamserver_client_code', models.CharField(max_length=40, null=True, verbose_name='TEAMServer Client Code')),
                ('is_sow_available', models.BooleanField(default=False)),
                ('is_reports_menu_available', models.BooleanField(default=False)),
                ('update_tm', models.CharField(default=b'immediately', max_length=256, choices=[(b'immediately', b'immediately'), (b'weekly', b'weekly'), (b'monthly', b'monthly')])),
                ('show_client_messenger', models.BooleanField(default=False)),
                ('ignore_holiday_flag', models.BooleanField(default=False)),
                ('client_notification_group', models.BooleanField(default=True)),
                ('word_count_breakdown_flag', models.BooleanField(default=False)),
                ('pricing_basis', models.ForeignKey(related_name=b'+', to='services.PricingBasis', null=True)),
                ('pricing_scheme', models.ForeignKey(to='services.PricingScheme', null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ClientReferenceFiles',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('orig_name', models.CharField(max_length=255, verbose_name=b'Original Name')),
                ('orig_file', models.FileField(max_length=500, null=True, upload_to=clients.models.get_reference_file_path, blank=True)),
                ('reference_file_type', models.CharField(blank=True, max_length=50, null=True, choices=[(b'glossary', b'Glossary'), (b'style_guide', b'StyleGuide')])),
                ('source', models.ForeignKey(related_name=b'+', blank=True, to='services.Locale', null=True)),
                ('target', models.ForeignKey(related_name=b'+', blank=True, to='services.Locale', null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ClientService',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('available', models.BooleanField(default=False)),
                ('job_default', models.BooleanField(default=False)),
                ('service', models.ForeignKey(to='services.ServiceType')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ClientTeamRole',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('role', models.CharField(blank=True, max_length=10, null=True, choices=[(b'pm', b'Project Manager'), (b'ae', b'Account Executive'), (b'tsg_eng', b'TSG Engineer'), (b'vle_eng', b'VLE Engineer'), (b'qa_eng', b'QA Engineer')])),
                ('contact', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TEAMServerSubject',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(max_length=40)),
                ('dvx_subject_code', models.CharField(max_length=40, verbose_name='TEAMServer Subject Code')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='clientmanifest',
            name='teamserver_client_subject',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, default=clients.models.default_subject, verbose_name='TEAMServer Subject Code', to='clients.TEAMServerSubject'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='clientmanifest',
            name='vertical',
            field=models.ForeignKey(to='services.Vertical', null=True),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='Client',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('people.account',),
        ),
        migrations.AddField(
            model_name='clientmanifest',
            name='client',
            field=models.OneToOneField(related_name=b'manifest', to='clients.Client'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='clientreferencefiles',
            name='client',
            field=models.ForeignKey(to='clients.Client'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='clientservice',
            name='client',
            field=models.ForeignKey(to='clients.Client'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='clientteamrole',
            name='client',
            field=models.ForeignKey(to='clients.Client'),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='ClientContact',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('accounts.circususer',),
        ),
        migrations.CreateModel(
            name='ClientEmailDomain',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('people.accountemaildomain',),
        ),
    ]
