# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2017-05-08 13:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0013_task_overdue_email_last_sent'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='qa_approved',
            field=models.NullBooleanField(default=False),
        ),
    ]
