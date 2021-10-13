from collections import OrderedDict

import requests
from django.conf import settings


def get_estabelecimentosproximos(lat=None, lng=None, endereco_completo=None):
    if lat and lng:
        params = dict(lat=lat, lng=lng)
    elif endereco_completo:
        params = dict(endereco=endereco_completo)
    else:
        raise ValueError()
    url = '{}/api/estabelecimentos_proximos'.format(settings.LOCALIZA_SUS['url'])
    res = requests.get(
        url=url,
        headers={'Authorization': 'Token {}'.format(settings.LOCALIZA_SUS['token'])},
        params=params)
    # Nota: OrderedDict é importante porque os registros vêm ordenados por proximidade
    return res.json(object_pairs_hook=OrderedDict)


def get_estabelecimento_referencia(lat=None, lng=None, endereco_completo=None):
    """Retorna o estabelecimento mais próximo dos argumentos informados e também retorna dados da origem, o que é
    útil para obter as coordanadas do endereco_completo."""
    if not lat and not lng and not endereco_completo:
        return dict()
    response = get_estabelecimentosproximos(lat=lat, lng=lng, endereco_completo=endereco_completo)
    lista_cnes = response.get('data', {})
    if lista_cnes:
        codigo_cnes = list(lista_cnes.keys())[0]
        estabelecimento = lista_cnes[codigo_cnes]
        estabelecimento['codigo_cnes'] = codigo_cnes
        return dict(
            estabelecimento=estabelecimento,
            origem=response['origem'],
        )
    return dict()
