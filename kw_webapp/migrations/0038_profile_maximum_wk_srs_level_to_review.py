# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-07-27 21:38
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kw_webapp', '0037_auto_20180321_1551'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='maximum_wk_srs_level_to_review',
            field=models.CharField(choices=[('APPRENTICE', 'Apprentice'), ('GURU', 'Guru'), ('MASTER', 'Master'), ('ENLIGHTENED', 'Enlightened'), ('BURNED', 'Burned')], default='BURNED', max_length=20),
        ),
    ]