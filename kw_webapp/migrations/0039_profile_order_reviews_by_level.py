# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-07-29 00:11
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('kw_webapp', '0038_profile_maximum_wk_srs_level_to_review'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='order_reviews_by_level',
            field=models.BooleanField(default=False),
        ),
    ]