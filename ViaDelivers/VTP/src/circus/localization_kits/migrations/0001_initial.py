# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import localization_kits.models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileAnalysis',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('guaranteed', models.IntegerField(default=0, verbose_name='Prfect')),
                ('exact', models.IntegerField(default=0, verbose_name='Exact')),
                ('duplicate', models.IntegerField(default=0, verbose_name='Reps')),
                ('fuzzy9599', models.IntegerField(default=0, verbose_name='95-99')),
                ('fuzzy8594', models.IntegerField(default=0, verbose_name='85-94')),
                ('fuzzy7584', models.IntegerField(default=0, verbose_name='75-84')),
                ('fuzzy5074', models.IntegerField(default=0, verbose_name='50-74')),
                ('no_match', models.IntegerField(default=0, verbose_name='NoMch')),
                ('page_count', models.IntegerField(default=0)),
                ('image_count', models.IntegerField(default=0)),
                ('message', models.CharField(max_length=255, null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FileAsset',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('asset_type', models.CharField(default=b'placeholder', max_length=20, choices=[(b'source', b'Source'), (b'reference', b'Reference item'), (b'placeholder', b'Placeholder')])),
                ('status', models.CharField(default=b'new', max_length=20, choices=[(b'new', b'New'), (b'queued', b'Queued'), (b'analysis_complete', b'Analysis Complete'), (b'analysis_error', b'Analysis Error')])),
                ('orig_name', models.CharField(max_length=255, verbose_name=b'Original Name')),
                ('orig_file', models.FileField(max_length=500, upload_to=localization_kits.models.get_project_asset_path, null=True, verbose_name=b'Original File', blank=True)),
                ('prepared_name', models.CharField(max_length=255, null=True, verbose_name=b'Prepared Name', blank=True)),
                ('prepared_file', models.FileField(max_length=500, upload_to=localization_kits.models.get_project_prepared_asset_path, null=True, verbose_name=b'Prepared File', blank=True)),
                ('queued_timestamp', models.DateTimeField(null=True, blank=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LocaleTranslationKit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('translation_file', models.FileField(max_length=500, null=True, upload_to=localization_kits.models.get_translation_file_path, blank=True)),
                ('reference_file', models.FileField(max_length=500, null=True, upload_to=localization_kits.models.get_reference_file_path, blank=True)),
                ('analysis_code', models.CharField(max_length=24, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LocalizationKit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('notes', models.TextField(null=True, blank=True)),
                ('analysis_code', models.CharField(max_length=24, null=True, blank=True)),
                ('analysis_started', models.DateTimeField(null=True, blank=True)),
                ('analysis_completed', models.DateTimeField(null=True, blank=True)),
                ('tm_update_started', models.DateTimeField(null=True, blank=True)),
                ('tm_update_completed', models.DateTimeField(null=True, blank=True)),
                ('is_manually_updated', models.BooleanField(default=False, verbose_name='staff status')),
                ('obsolete_analyzing', models.BooleanField(default=False, db_column=b'analyzing')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='localetranslationkit',
            name='kit',
            field=models.ForeignKey(to='localization_kits.LocalizationKit'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='localetranslationkit',
            name='target_locale',
            field=models.ForeignKey(to='services.Locale'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='localetranslationkit',
            unique_together=set([('kit', 'target_locale')]),
        ),
        migrations.AddField(
            model_name='fileasset',
            name='kit',
            field=models.ForeignKey(related_name=b'files', to='localization_kits.LocalizationKit'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='fileasset',
            name='source_locale',
            field=models.ForeignKey(blank=True, to='services.Locale', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='fileanalysis',
            name='asset',
            field=models.ForeignKey(to='localization_kits.FileAsset', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='fileanalysis',
            name='source_locale',
            field=models.ForeignKey(related_name=b'+', to='services.Locale', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='fileanalysis',
            name='target_locale',
            field=models.ForeignKey(related_name=b'+', to='services.Locale', null=True),
            preserve_default=True,
        ),
    ]
