# Generated by Django 3.0.7 on 2020-06-09 02:53

import django.contrib.postgres.fields.jsonb
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0014_auto_20200608_2353'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pessoafisica',
            name='dados',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict),
        ),
    ]