# FIXME XXX TODO: Módulo deprecated! REMOVER!

from multiprocessing import cpu_count

import geocoder
import logging
from concurrent.futures.thread import ThreadPoolExecutor
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

def get_max_jobs():
    return (cpu_count() * 2) + 1

def obter_coordenada(endereco):
    g = geocoder.google(endereco, key=settings.GOOGLE_API_KEY, components="country:BR")

    if not g:
        return None

    latitude = g.latlng[0]
    longitude = g.latlng[1]

    return latitude, longitude

def _salvar_coordenada(dados):
    from notificacoes.models import Notificacao
    numero, endereco = dados
    # logger.debug('Thread {} - obtendo coordenada de {} ({})'.format(threading.get_ident(), numero, endereco))
    try:
        coordendadas = obter_coordenada(endereco)
        if coordendadas is not None:
            longitude, latitude = coordendadas
            Notificacao.objects.filter(numero=numero).update(longitude=longitude,
                                                          latitude=latitude,
                                                          coordendas_atualizadas_em=timezone.now())
            return numero, longitude, latitude
        else:
            Notificacao.objects.filter(numero=numero).update(coordendas_atualizadas_em=timezone.now())
    except:
        # logger.debug('Erro ao obter coordenada de {} ({})'.format(numero, endereco))
        return numero, 0, 0

def _obter_notificacoes():
    from notificacoes.models import Notificacao
    qs = Notificacao.ativas.filter(coordendas_atualizadas_em__isnull=True).order_by('-data')
    qs = qs.values_list('numero', 'dados__logradouro',
              'dados__numero_res',
              'dados__complemento',
              'bairro__nome',
              'dados__municipio_de_residencia',
              'dados__estado_de_residencia')
    dados = []
    for valores in qs:
        numero = valores[0]
        aendereco = []
        for valor in valores[1:]:
            if valor is not None:
                aendereco.append(valor)
        endereco = ', '.join(aendereco)
        dados.append((numero, endereco))
    return dados


def processar_coordenadas():
    dados = _obter_notificacoes()
    logger.debug('Coordenadas a serem obtidas: {}'.format(len(dados)))

    pool = ThreadPoolExecutor(max_workers=get_max_jobs())
    results = pool.map(_salvar_coordenada, dados)

    return results
