# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('people', '0001_initial'),
        ('services', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='VendorLanguagePair',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('source', models.ForeignKey(related_name=b'source_vendors', to='services.Locale')),
                ('target', models.ForeignKey(related_name=b'target_vendors', to='services.Locale')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VendorManifest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VendorTranslationTaskFileType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_deleted', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True, null=True)),
                ('modified', models.DateTimeField(auto_now=True, null=True)),
                ('code', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(unique=True, max_length=400)),
                ('extension', models.CharField(max_length=40)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='vendormanifest',
            name='vendortranslationtaskfiletype',
            field=models.ForeignKey(verbose_name=b'Assign Filetypes', blank=True, to='vendors.VendorTranslationTaskFileType', null=True),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='Vendor',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('people.account',),
        ),
        migrations.AddField(
            model_name='vendorlanguagepair',
            name='vendor',
            field=models.ForeignKey(to='vendors.Vendor'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='vendormanifest',
            name='vendor',
            field=models.OneToOneField(related_name=b'vendor_manifest', to='vendors.Vendor'),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='VendorContact',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('accounts.circususer',),
        ),
    ]
