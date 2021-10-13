# Generated by Django 3.0.7 on 2020-07-03 00:49

from django.db import migrations

from indicadores.models import ModeloAplicacao

def modelo_copy(apps, schema_editor):
    Boletim = apps.get_model('indicadores', 'Boletim')
    for boletim in Boletim.objects.all():
        ModeloAplicacao.objects.create(
            nome = boletim.nome,
            modelo = boletim.modelo,
            data = boletim.data,
            criado_em = boletim.criado_em,
            dados = boletim.dados,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('indicadores', '0008_modeloaplicacao'),
    ]

    operations = [
        migrations.RunPython(modelo_copy)
    ]