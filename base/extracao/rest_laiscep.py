import json
import os

import logging
import re
import csv
import numpy as np
import pandas as pd
from django.conf import settings
from django.core.cache import cache

from base.caches import ControleCache

logger = logging.getLogger(__name__)

token = None
URL = 'https://viacep.com.br/ws'
REQUEST_CONNECTION_TIMEOUT = 5
REQUEST_READ_TIMEOUT = 30

#abdo do huol, cpf 24609455072

def recuperar_ceps():
    if ControleCache.ceps().exists():
        logger.debug('Usando cache de CEP')
        return ControleCache.ceps().get()

    dir_cep = settings.CEPS_PATH

    # cep|logradouro|tipo_logradouro|complemento|local|id_cidade|id_bairro
    ##59153900|Alameda dos Bosques 680||||7229|44056
    filename_cep_endereco = os.path.join(dir_cep, 'qualocep_endereco.csv')
    logger.debug('Processando arquivo {}...'.format(filename_cep_endereco))
    ceps_enderecos = []
    csv.register_dialect('piper', delimiter='|', quoting=csv.QUOTE_NONE)
    with open(filename_cep_endereco, 'r', encoding='iso-8859-1') as csvfile:
        for row in csv.DictReader(csvfile, dialect='piper'):
            ceps_enderecos.append(row)
    df_endereco = pd.DataFrame(ceps_enderecos, columns=ceps_enderecos[0].keys())
    df_endereco['id_cidade'] = pd.to_numeric(df_endereco['id_cidade'], errors='coerce').fillna(0).astype(int)
    df_endereco['id_bairro'] = df_endereco['id_bairro'].fillna(0).astype(int)

    # id_cidade|cidade|uf|cep|cod_ibge|area|id_municipio_subordinado
    # 7229 | Parnamirim | RN | | 2403251 | 123.471 | 0
    filename_cep_cidade = os.path.join(dir_cep, 'qualocep_cidade.csv')
    logger.debug('Processando arquivo {}...'.format(filename_cep_cidade))
    df_cidade = pd.read_csv(filename_cep_cidade, delimiter='|', encoding='iso-8859-1')
    df_cidade.rename(columns={'id_cidade': 'cidade_id',
                              'cep': 'cidade_cep',
                              'cod_ibge': 'ibge',
                              'cidade': 'localidade'
                              }
                     , inplace=True)
    df_cidade['ibge'] = df_cidade['ibge'].fillna(0).astype(int).astype(str)
    df_cidade['cidade_cep'] = df_cidade['cidade_cep'].fillna(0).astype(int).astype(str)

    # id_bairro|bairro|id_cidade
    # 44056|Parque do Jiqui|7229
    filename_cep_bairro = os.path.join(dir_cep, 'qualocep_bairro.csv')
    logger.debug('Processando arquivo {}...'.format(filename_cep_bairro))
    df_bairro = pd.read_csv(filename_cep_bairro, delimiter='|', encoding='iso-8859-1')
    df_bairro.rename(columns={'id_bairro': 'bairro_id',
                              'id_cidade': 'bairro_id_cidade',
                              }
                     , inplace=True)
    df_bairro['bairro_id'] = df_bairro['bairro_id'].astype(int)

    df_endereco = pd.merge(left=df_endereco, right=df_bairro, left_on='id_bairro', right_on='bairro_id')
    df_endereco = pd.merge(left=df_endereco, right=df_cidade, left_on='id_cidade', right_on='cidade_id')
    df_endereco.drop('bairro_id_cidade', axis=1, inplace=True)
    df_endereco.drop('id_bairro', axis=1, inplace=True)
    df_endereco.drop('id_cidade', axis=1, inplace=True)

    #Tratamento para incluir as geolocalização dos ceps
    filename_cep_geo = os.path.join(dir_cep, 'qualocep_geo2.csv')
    logger.debug('Processando arquivo {}...'.format(filename_cep_geo))
    df_ceps_geo = pd.read_csv(filename_cep_geo, delimiter='|', encoding='iso-8859-1')
    df_ceps_geo['cep'] = df_ceps_geo['cep'].fillna(0).astype(int).astype(str)
    df_endereco = pd.merge(left=df_endereco, right=df_ceps_geo, left_on='cep', right_on='cep')


    df_endereco['cep_index'] = df_endereco['cep']
    df_endereco.set_index('cep_index', inplace=True)
    ceps = json.loads(df_endereco.to_json(orient='index'))

    #Tratamento para incluir os ceps de cidade
    df_cidade['cep'] = df_cidade['cidade_cep']
    df_cidade['cep_index'] = df_cidade['cidade_cep']
    df_cidade.set_index('cep_index', inplace=True)
    for column in df_endereco.columns:
        if df_cidade.get(column) is None:
            df_cidade[column] = ''
    #remove ceps duplicados
    df_cidade = df_cidade.groupby(df_cidade.index).first()

    #Atualiza ceps com os ceps de cidade.
    ceps.update(json.loads(df_cidade.to_json(orient='index')))
    ControleCache.ceps().set(ceps)
    return ceps


def get_cep(cep):
    cep = re.sub('[.-]', '', cep)
    return recuperar_ceps()[cep]
