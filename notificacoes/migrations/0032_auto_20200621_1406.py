# Generated by Django 3.0.7 on 2020-06-21 17:06
import logging
import os
from django.conf import settings

from django.db import migrations

from notificacoes.management.commands.processar_coordenadas import importar_coordendas_from_csv

logger = logging.getLogger(__name__)

def import_notificacoes(a, b):
    path_dir_fixtures = os.path.join(settings.BASE_DIR, 'base/fixtures')
    filenamepath = os.path.join(path_dir_fixtures,  'coordendas.csv')

    if os.path.exists(filenamepath):
        logger.debug('CSV de coordenadas encontrado, processando dados do arquivo')
        importar_coordendas_from_csv(filenamepath)
    else:
        raise FileNotFoundError('Arquivo {}. Execute o comando processar_coordenadas.'.format(filenamepath))


class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0031_auto_20200621_1158'),
    ]

    operations = [
        migrations.RunPython(import_notificacoes)
    ]