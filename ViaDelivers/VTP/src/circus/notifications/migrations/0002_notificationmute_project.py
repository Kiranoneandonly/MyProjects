# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
        ('notifications', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificationmute',
            name='project',
            field=models.OneToOneField(related_name=b'notification_mute', to='projects.Project'),
            preserve_default=True,
        ),
    ]
