import json
from django.core.files.base import ContentFile, File
from django.core.management.base import BaseCommand
from django.utils import timezone
from zipfile import ZipFile, BadZipFile

from base.caches import ControleCache
from base.utils import normalize_str
from indicadores.indicadores import *
import pandas as pd
from elasticsearch import Elasticsearch
import elasticsearch.helpers

from notificacoes.models import UploadImportacao
from notificacoes.processar_notificacoes import ObterNotificacaoEsusveAPI, ObterNotificacaoEsusveCSV

logger = logging.getLogger(__name__)
import os
import datetime
import glob


def processar_csv(filename, column_map, column_index):
    df = None
    try:
        with ZipFile(filename) as myzip:
            with myzip.open(myzip.namelist()[0]) as myfile:
                df = pd.read_csv(myfile, delimiter=';', index_col=column_index)
    except BadZipFile:
        pass

    if df is None:
        df = pd.read_csv(filename, delimiter=';', index_col=column_index)

    df.rename(columns=column_map, inplace=True)
    return df

def get_last_file_name(director):
    list_of_files = glob.glob('{}/esusve-uf_*'.format(director))  # * means all if need specific format then *.csv
    return max(list_of_files, key=os.path.getctime)

COLUNAS_EXTRA_API = ['@timestamp', '_created_at', '_p_usuarioAlteracao', '_p_usuario',
                     '_updated_at', 'descricaoRacaCor', 'desnormalizarNome',
                     'nomeCompletoDesnormalizado', 'estadoIBGE', 'estadoNotificacaoIBGE',
                     'idade', 'municipioCapital', 'municipioIBGE', 'municipioNotificacaoCapital',
                     'municipioNotificacaoIBGE', 'source_id', 'outros_paciente_assintomatico'
                    ]
COLUNAS_EXTRA_CSV = [ 'notificante_cnpj', 'operador_cpf', 'operador_email',
                      'operador_nome_completo', 'pais_de_origem', 'tem_cpf'
                    ]

def download_dados(dir_media):
    user = 'municipio-esusve-rn-natal'
    pwd = 'cumugoqunu'
    index = user

    url = 'https://' + user + ':' + pwd + '@elasticsearch-saps.saude.gov.br'

    # https://elasticsearch-saps.saude.gov.br/notificacoes-esusve*/_search?pretty
    print(url)
    es = Elasticsearch([url], send_get_body_as='POST')
    body = {"query": {"match_all": {}}}
    results = elasticsearch.helpers.scan(es, query=body, index=index)
    df_api = pd.DataFrame.from_dict([document['_source'] for document in results])

    print("numero de casos:", df_api.shape[0], "de", es.count(index=index)['count'])
    print("coluns:", df_api.columns)
    filename_esusve = os.path.join(dir_media,
                                   'esusve-uf_{}.csv'.format(datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")))
    df_api.to_csv(filename_esusve, sep=';', encoding='utf-8-sig', index=False)




class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--download_dados', action='store_true', help='Se true, refaz as notificações desativadas')

    def __obter_dados(self):
        user = 'municipio-esusve-rn-natal'
        pwd = 'cumugoqunu'
        index = user

        url = 'https://' + user + ':' + pwd + '@elasticsearch-saps.saude.gov.br'

        # https://elasticsearch-saps.saude.gov.br/notificacoes-esusve*/_search?pretty
        print(url)
        es = Elasticsearch([url], send_get_body_as='POST')
        body = {"query": {"match_all": {}}}
        results = elasticsearch.helpers.scan(es, query=body, index=index)

        dados_originais = [document['_source'] for document in results]

        dir_media = os.path.join(settings.BASE_DIR, 'media')
        filename_esusve = os.path.join(dir_media, 'esusve-uf_{}.json'.format(
            datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")))
        with open(filename_esusve, 'w') as fp:
            json.dump(dados_originais, fp)
            upload_importacao = UploadImportacao.objects.create(arquivo=os.path.basename(fp.name), datahora=timezone.now())

        return dados_originais


    def handle(self, *args, **options):
        ControleCache.processamento_notificacoes().reset()

        dir_media = os.path.join(settings.BASE_DIR, 'media')

        obter_notificacao = ObterNotificacaoEsusveAPI()

        obter_dados = options['download_dados']
        if obter_dados:
            obter_notificacao.__obter_dados()
        dados, df_api = obter_notificacao._obter_dados()

        column_map_api = {}
        for c in df_api.columns.to_list():
            column_map_api[c] = '{}__'.format(c)

        for c in COLUNAS_EXTRA_API:
            column_map_api[c] = 'api_{}'.format(column_map_api[c])
        df_api.rename(columns=column_map_api, inplace=True)


        filename_csv = os.path.join(dir_media, '00364af1ded6d891963b0f60d27c81c8.csv')

        df_csv = processar_csv(filename_csv,
                               ObterNotificacaoEsusveCSV.PARSE_COLUNAS,
                               'Número da Notificação')

        column_map_api = {}
        for c in COLUNAS_EXTRA_CSV:
            column_map_api[c] = 'csv_{}'.format(c)
        df_csv.rename(columns=column_map_api, inplace=True)
        df_api.rename(columns=column_map_api, inplace=True)


        # #ler arquivo json com os dados originais da api
        # filename_esusve = get_last_file_name(dir_media)
        # with open(filename_esusve, 'r') as f:
        #     dados_originais = json.loads(f.read())
        #
        #
        #
        # df_api = pd.DataFrame.from_dict(dados_originais)
        # df_api.rename(columns=PARSE_COLUNAS, inplace=True)
        #
        df_csv.index = df_csv.index.astype(str)

        #Concatenando os dos arquivos csv
        df = pd.concat([df_api, df_csv], axis=1)

        #ordenando os dados pelas colunas
        df.sort_index(axis=1, inplace=True)

        df.reset_index(inplace=True)

        filename_esusve = os.path.join(dir_media,'esusve-compare.csv')
        df.to_csv(filename_esusve, sep=';', encoding='utf-8-sig', index=False)
        print('arquivo salvo em: ', filename_esusve)




