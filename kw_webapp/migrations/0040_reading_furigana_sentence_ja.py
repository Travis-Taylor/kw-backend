# -*- coding: utf-8 -*-
# Generated by Django 1.11.11 on 2018-06-03 15:02
from __future__ import unicode_literals

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("kw_webapp", "0039_profile_order_reviews_by_level")]

    operations = [
        migrations.AddField(
            model_name="reading",
            name="furigana_sentence_ja",
            field=django.contrib.postgres.fields.jsonb.JSONField(
                default={}, max_length=1000
            ),
        )
    ]