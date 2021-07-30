# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0001_initial'),
        ('tasks', '0001_initial'),
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='delivery',
            name='tasks',
            field=models.ManyToManyField(to='tasks.Task'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='delivery',
            name='vendor',
            field=models.ForeignKey(to='vendors.Vendor'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='backgroundtask',
            name='project',
            field=models.ForeignKey(to='projects.Project', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='backgroundtask',
            name='task',
            field=models.ForeignKey(to='tasks.Task', null=True),
            preserve_default=True,
        ),
        migrations.CreateModel(
            name='SalesforceOpportunity',
            fields=[
            ],
            options={
                'db_table': 'Opportunity',
                'managed': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SalesforceOpportunityContactRole',
            fields=[
            ],
            options={
                'db_table': 'OpportunityContactRole',
                'managed': False,
            },
            bases=(models.Model,),
        ),
    ]
