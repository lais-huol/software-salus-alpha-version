# Generated by Django 3.0.7 on 2020-07-08 14:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0025_unidadefederativa_sigla'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='estabelecimentosaude',
            name='cpf_operador',
        ),
    ]