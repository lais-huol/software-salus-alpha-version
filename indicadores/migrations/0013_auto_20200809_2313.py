# Generated by Django 3.0.7 on 2020-08-10 02:13

from django.db import migrations
from django.core.cache import cache

def limpar_cache(apps, schema_editor):
    cache.clear()


class Migration(migrations.Migration):

    dependencies = [
        ('indicadores', '0012_auto_20200809_2258'),
    ]

    operations = [
        migrations.RunPython(limpar_cache)
    ]
