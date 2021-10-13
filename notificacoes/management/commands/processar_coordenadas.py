# FIXME XXX TODO: Módulo deprecated! REMOVER!

import logging
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from base.model_csv import qs_to_local_csv
from notificacoes.google_geocoding_parse import processar_coordenadas
import pandas as pd
from notificacoes.models import Notificacao

logger = logging.getLogger(__name__)

def exportar_coordenadas_to_csv(filepath, filename):
    from notificacoes.models import Notificacao
    qs = Notificacao.ativas.filter(coordendas_atualizadas_em__isnull=False)

    qs_to_local_csv(qs,
                    fields=['numero', 'longitude', 'latitude'],
                    path=filepath,
                    filename=filename)

def importar_coordendas_from_csv(filename):
    df = pd.read_csv(filename, delimiter=',')
    logger.debug('Coordenadas a serem obtidas: {}'.format(df.numero.count()))
    dados = {}
    contador = 0
    for index, row in df.iterrows():
        numero = int(row['numero'])
        longitude = row['longitude']
        latitude = row['latitude']
        Notificacao.objects.filter(numero=numero).update(longitude=longitude,
                                                         latitude=latitude,
                                                         coordenadas_atualizadas_em=timezone.now())
    return dados


class Command(BaseCommand):
    help = 'Carrega dados iniciais'

    def handle(self, *args, **kwargs):
        # test()
        path_dir_fixtures = os.path.join(settings.BASE_DIR, 'base/fixtures')
        filename = 'coordendas.csv'
        if not os.path.exists(os.path.join(path_dir_fixtures, filename)):
            logger.debug('CSV de coordenadas não encontrados, obtendo dados externo')
            processar_coordenadas()
            exportar_coordenadas_to_csv(path_dir_fixtures, filename)
        else:
            logger.debug('CSV de coordenadas encontrado, processando dados do arquivo')
            importar_coordendas_from_csv(os.path.join(path_dir_fixtures, filename))
