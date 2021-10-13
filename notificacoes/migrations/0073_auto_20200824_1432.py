# Generated by Django 3.0.7 on 2020-08-24 17:32

from django.db import migrations

from notificacoes.management.commands.migracao_dados_obitos import atualizar_bairro_do_obito


def atualizar_bairro_do_obitos(apps, schema_editor):
    atualizar_bairro_do_obito()


class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0072_obito_bairro'),
    ]

    operations = [
        migrations.RunPython(atualizar_bairro_do_obitos)
    ]