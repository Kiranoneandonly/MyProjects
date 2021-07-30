# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import projects.models
from django.conf import settings
import nullablecharfield.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0001_initial'),
        ('localization_kits', '0001_initial'),
        ('finance', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('services', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='BackgroundTask',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('celery_task_id', models.CharField(max_length=36, unique=True, null=True, blank=True)),
                ('callback_sig', models.TextField(null=True, blank=True)),
                ('errback_sig', models.TextField(null=True, blank=True)),
                ('remote_id', models.CharField(max_length=36, unique=True, null=True, blank=True)),
                ('name', models.CharField(db_index=True, max_length=200, choices=[('ANALYSIS', 'Analysis'), ('PRE_TRANSLATE', 'Pretranslate'), ('PSEUDO_TRANSLATE', 'Pseudotranslate'), ('MACHINE_TRANSLATE', 'Machine Translate (MT)'), ('PREP_KIT', 'Prepare Loc. Kit'), ('IMPORT_TRANSLATION', 'Import Translation'), ('GENERATE_DELIVERY', 'Generate Delivery Files'), ('MEMORY_DB_TM', 'Add to Translation Memory'), ('TERMINOLOGY_DB', 'Add to Terminology Database')])),
                ('completed', models.DateTimeField(null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Delivery',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('file', models.FileField(max_length=500, upload_to=projects.models.get_project_delivery_path)),
                ('notes', models.TextField(null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('job_number', models.CharField(max_length=50)),
                ('name', models.CharField(max_length=1000, null=True, blank=True)),
                ('status', models.CharField(default=b'queued', max_length=40, choices=[(b'quoted', 'Estimated'), (b'created', 'In Estimate'), (b'started', 'Active'), (b'completed', 'Delivered'), (b'canceled', 'Canceled'), (b'closed', 'Closed'), (b'hold', 'Hold'), (b'queued', 'Queued')])),
                ('is_secure_job', models.BooleanField(default=False, choices=[(True, 'Restricted Access'), (False, 'Unrestricted Access')])),
                ('delay_job_po', models.BooleanField(default=False, choices=[(False, 'Estimate Hours'), (True, 'Actual Hours')])),
                ('estimate_type', models.CharField(default='auto', max_length=10, choices=[('auto', 'Automatic'), ('manual', 'Manual')])),
                ('revenue_recognition_month', models.DateTimeField(null=True, verbose_name='Revenue Recognition Month', blank=True)),
                ('original_invoice_count', models.IntegerField(null=True, verbose_name='Original Invoice Count', blank=True)),
                ('salesforce_opportunity_id', nullablecharfield.db.models.fields.CharNullField(db_index=True, max_length=18, null=True, blank=True)),
                ('approved', models.BooleanField(default=False)),
                ('instructions', models.TextField(null=True, verbose_name='Client Instructions', blank=True)),
                ('instructions_via', models.TextField(null=True, verbose_name='VIA Instructions', blank=True)),
                ('instructions_vendor', models.TextField(null=True, verbose_name='Supplier Instructions', blank=True)),
                ('project_speed', models.CharField(default='standard', max_length=10, choices=[('standard', 'Standard'), ('express', 'Express')])),
                ('quote_due', models.DateTimeField(null=True, verbose_name='Quote Due Date', blank=True)),
                ('quoted', models.DateTimeField(null=True, verbose_name='Quote Delivered Date', blank=True)),
                ('started_timestamp', models.DateTimeField(null=True, verbose_name='Started Date', blank=True)),
                ('due', models.DateTimeField(null=True, verbose_name='Due Date', blank=True)),
                ('delivered', models.DateTimeField(null=True, verbose_name='Delivered Date', blank=True)),
                ('completed', models.DateTimeField(null=True, verbose_name='Complete Date', blank=True)),
                ('canceled', models.DateTimeField(null=True, verbose_name='Canceled Date', blank=True)),
                ('express_factor', models.DecimalField(default=1.5, max_digits=15, decimal_places=4)),
                ('jams_jobid', models.IntegerField(null=True, verbose_name='JAMS JobID', blank=True)),
                ('jams_estimateid', models.IntegerField(null=True, verbose_name='JAMS EstimateID', blank=True)),
                ('project_reference_name', models.CharField(max_length=1000, null=True, blank=True)),
                ('current_user', models.IntegerField(null=True, blank=True)),
                ('internal_via_project', models.BooleanField(default=False)),
                ('no_express_option', models.BooleanField(default=False)),
                ('large_job_approval_timestamp', models.DateTimeField(null=True, verbose_name='Large Jobs Approval Date', blank=True)),
                ('large_job_approval_notes', models.TextField(null=True, verbose_name='Large Jobs Approval Instructions', blank=True)),
                ('ignore_holiday_flag', models.BooleanField(default=False)),
                ('price_per_document', models.BooleanField(default=True)),
                ('account_executive', models.ForeignKey(related_name='+', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('client', models.ForeignKey(to='clients.Client')),
                ('client_poc', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('estimator', models.ForeignKey(related_name='+', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('industry', models.ForeignKey(to='services.Industry', null=True)),
                ('invoice_template', models.ForeignKey(related_name='invoice_template', to='finance.InvoiceTemplate', null=True)),
                ('kit', models.OneToOneField(related_name='project', null=True, blank=True, to='localization_kits.LocalizationKit')),
                ('ops_management_approver', models.ForeignKey(related_name='+', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('payment_details', models.OneToOneField(related_name='payment_detail', null=True, blank=True, to='finance.ProjectPayment')),
                ('pricing_basis', models.ForeignKey(related_name='+', blank=True, to='services.PricingBasis', null=True)),
                ('project_manager', models.ForeignKey(related_name='+', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('project_manager_approver', models.ForeignKey(related_name='+', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('restricted_locations', models.ManyToManyField(related_name='+', null=True, to='services.Country', blank=True)),
                ('sales_management_approver', models.ForeignKey(related_name='+', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('services', models.ManyToManyField(related_name='+', null=True, to='services.ServiceType', blank=True)),
                ('source_locale', models.ForeignKey(related_name='+', blank=True, to='services.Locale', null=True)),
                ('target_locales', models.ManyToManyField(related_name='+', null=True, to='services.Locale', blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ProjectTeamRole',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('role', models.CharField(blank=True, max_length=10, null=True, choices=[(b'pm', b'Project Manager'), (b'ae', b'Account Executive'), (b'tsg_eng', b'TSG Engineer'), (b'vle_eng', b'VLE Engineer'), (b'qa_eng', b'QA Engineer')])),
                ('contact', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
                ('project', models.ForeignKey(related_name='team', to='projects.Project')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='delivery',
            name='project',
            field=models.ForeignKey(to='projects.Project'),
            preserve_default=True,
        ),
    ]
