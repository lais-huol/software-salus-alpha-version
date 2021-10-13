# Generated by Django 3.0.7 on 2020-07-09 00:18

from django.db import migrations

from notificacoes.models import Notificacao


def processar_notificacoes_similares(apps, schema_editor):
    Notificacao.processar_notificacoes_similares()

class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0047_auto_20200708_2036'),
    ]

    operations = [
        migrations.RunPython(processar_notificacoes_similares)
    ]
