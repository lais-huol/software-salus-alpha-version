import unicodedata

import logging
import os
import pandas as pd
import re
from django.conf import settings
from django.core.management.base import BaseCommand
from base.caches import ControleCache
from base.signals import fonte_de_dados_indicadores_alterados
from base.utils import to_date

logger = logging.getLogger(__name__)

def convert_date(datestr):
    try:
        return to_date(datestr)
    except:
        return None

def convert_sexo(sexostr):
    try:
        if sexostr.upper().strip() == 'FEMININO':
            return 'MULHERES'
        elif sexostr.upper().strip() == 'MASCULINO':
            return 'HOMENS'
    except:
        return None

replacements = {
    'Name': ['FirstName','First Name','Nombre','NameFirst', 'Name', 'Given name', 'given name', 'Name'],
    'Address': ['Residence','Primary Address', 'primary address' ],
    #...
}

# df.rename(columns={el:k for k,v in replacements.iteritems() for el in v}, inplace=True)

def normalize_columns(keys):
    normalized_keys = {}
    for key in keys:
        new_key = re.sub('[^A-Za-z0-9_]+', '', unicodedata.normalize('NFKD', key.replace(' ', '_').lower()))
        normalized_keys[key] = new_key
    return normalized_keys

def processar_obitos(filename_municipios):
    #SEXO;
    # IDADE;
    # INICIO DOS SINTOMAS;
    # UNIDADE NOTIFICADORA;
    # LOGRADOURO;
    # NUMERO;
    # BAIRRO;
    # TELEFONE;
    # INTERNAÇÃO;
    # SINAIS/SINTOMAS;
    # MEDIDAS ADOTADAS;
    # CONTATOS INVESTIGADOS;
    # OCUPAÇÃO;
    # DETECÇÃO VIRAL/SORO;
    # ( AMOSTRA);
    # RESULTADO;
    # ENCERRAMENTO;
    # RELATÓRIO;
    # STATUS;
    # INFORMAÇÕES;
    # FIM DE QUARENTENA;
    # DESFECHO;
    # PERÍODO ENTRE A DATA DOS PRIMEIROS SINTOMAS E A ATUAL;
    # SEMANA EPIDEMIOLÓGICA;
    # DATA DO ÓBITO
    df = pd.read_csv(filename_municipios, delimiter=';')
    df.rename(columns=normalize_columns(df.columns), inplace=True)

    df['data_do_obito'] = df['data_do_obito'].apply(convert_date)
    df['sexo'] = df['sexo'].apply(convert_sexo)
    # df['idade'] = df['idade'].astype(int)
    pd.to_numeric(df['idade'], downcast='integer', errors='ignore')


    # if df['idade'].apply(lambda x: str(x).isnumeric()==False).sum() > 0:
    #     # df.dropna(subset=['data_do_obito'], inplace=True)
    #     raise Exception('Há idades que não puderam ser convertidos, corrija na planilha',
    #                     df[df['idade'].apply(lambda x: str(x).isnumeric()==False)])

    # if df['data_do_obito'].isnull().sum() > 0:
    #     # df.dropna(subset=['data_do_obito'], inplace=True)
    #     raise Exception('Há data de óbtios vazia, corrija na planilha', df[df['data_do_obito'].isnull()])

    # if df['data_do_obito'].apply(lambda x: isinstance(x, str)).sum() > 0:
    #     raise Exception('Há datas que não puderam ser convertidas, corrija na planilha',
    #         df[df['data_do_obito'].apply(lambda x: isinstance(x, str))])

    df.sort_values(by=['data_do_obito'], inplace=True)

    ControleCache.obitos_planilha().set(df)
    fonte_de_dados_indicadores_alterados.send(sender=None)


class Command(BaseCommand):
    help = 'Processar arquivos auxiliares'

    def handle(self, *args, **kwargs):
        path_dir_fixtures = os.path.join(settings.BASE_DIR, 'indicadores/fixtures')

        filename = os.path.join(path_dir_fixtures, 'nan_obitos_20200709.csv')
        processar_obitos(filename)

