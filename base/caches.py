import zlib

import json
import logging
import pickle
from django.core.cache import cache
from datetime import datetime, date
from enum import Enum

from base.utils import DateTimeDecoder, normalize_str
import pandas as pd

logger = logging.getLogger(__name__)


class StatusProcessamento(Enum):
    INICIALIZADO = 0
    CONCLUIDO = 1
    INTERROMPIDO = 2


class _cacheBase():
    # NOME_CACHE = ''
    # CACHE_VAZIO = None

    def clear(self):
        cache.delete(self._nome_cache)

    def reset(self):
        self.clear()
        self.set_status(StatusProcessamento.INICIALIZADO)
        logger.debug('Reset cache {}'.format(self._nome_cache))

    @property
    def _nome_cache(self):
        return self.NOME_CACHE

    def get(self, class_encode=None):
        if self.exists():
            _dados = self._prepare_content_to_get(cache.get(self._nome_cache))
            if class_encode is not None:
                _dados = json.dumps(_dados, cls=class_encode)
            return _dados
        return self.CACHE_VAZIO

    def _prepare_content_to_get(self, acache):
        raise NotImplemented()

    def remove(self, chaves):
        acache = self.get()
        for chave in chaves:
            if self._get_method_to_remove() == 'remove':
                acache.remove(chave)
            elif self._get_method_to_remove() == 'pop':
                acache.pop(chave)
            else:
                raise ValueError('_get_method_to_remove not valid.')
        self.set(acache)

    def _get_method_to_remove(self):
        raise NotImplemented()

    def set(self, valor):
        cache.set(self._nome_cache, self._prepare_content_to_set(valor), None)

    def _prepare_content_to_set(self, valor):
        raise NotImplemented()

    def _delete(self):
        cache.delete(self._nome_cache)

    def has_content(self):
        dados = self.get()
        return dados != self._nome_cache

    def exists(self):
        return cache.keys(self._nome_cache) != []

    def status(self):
        return cache.get('{}_status'.format(self.__class__.__name__).lower())

    def set_status(self, status):
        cache.set('{}_status'.format(self.__class__.__name__).lower(), status, None)


class _CacheAssociarNomesEstabelecimento(_cacheBase):
    '''
    Armazena uma lista de nomes de estabelecimentos que precisam ser associados.
    formato dos dadados do cache: []
    Exemplo: ['UPA 24h Potengi', 'UPA 24h Pajussara']
    '''
    NOME_CACHE = 'censo_imd_nomes_estabelecimento_pendentes'
    CACHE_VAZIO = []

    def _prepare_content_to_get(self, acache):
        return json.loads(acache)

    @classmethod
    def _prepare_content_to_set(self, valor):
        nomes_pendentes = list(valor)
        return json.dumps(nomes_pendentes)

    def _get_method_to_remove(self):
        return 'remove'


class _CacheFiltrosNotificacao(_cacheBase):
    '''
    Armazena um dicionário de valores para filtros de notificação.
    formato dos dadados do cache: {'chave_filtro': [valor1, valor2, ...], ...}
    Exemplo: ['UPA 24h Potengi', 'UPA 24h Pajussara']
    '''
    NOME_CACHE = 'filtros_notificacao'
    CACHE_VAZIO = {}

    def _prepare_content_to_get(self, acache):
        return json.loads(acache)

    def reset(self):
        self.clear()

    def _prepare_content_to_set(self, valor):
        return json.dumps(valor)

    def _get_method_to_remove(self):
        return 'remove'


class _CacheAssociarNomesPaciente(_cacheBase):
    '''
        Armazena no cache o dicinários com os dados de nomes de pacientes que precisam ser associados com notificações
        chave:  tupla com os dados do paciente interancao, formato: (id_paciente_interanacao, nome, idade)
        valor: dicionário com as tuplas de possíveis nomes, formato:
        {
            'dados_internacao': ['id','nome_do_paciente','leitos__idade','municipio','tipo_de_leito','data_de_admissao','data_de_liberacao','ti'],
            'dados_notificacao': (nome do notificado, data de nascimento, idade, número da notificacao)
        }
        Exemplo
        {
            (982, 'JOSE MARIA DE AQUINO', '82'): {
                    'dados_internacao': [982, 'JOSE MARIA DE AQUINO', '82', 'Natal', 'Enfermaria', '', '', '6'],
                    'dados_notificacao': [('JOSE MARIA DE AQUINO', '02/12/1937', 82, '242002490929')]
                    }
        }
    '''
    NOME_CACHE = 'censo_imd_dados_nomes_a_associar'
    CACHE_VAZIO = {}

    def reset(self):
        super(_CacheAssociarNomesPaciente, self).reset()

        hoje = datetime.now().date()
        if cache.get('censo_imd_controle_alerta') is None or cache.get('censo_imd_controle_alerta').get(hoje, None) is None:
            #Recria o cache todos os dias
            cache.delete('censo_imd_controle_alerta')
            cache.set('censo_imd_controle_alerta', {hoje: 0}, None)

        contador = cache.get('censo_imd_controle_alerta')[hoje]
        contador += 1
        cache.set('censo_imd_controle_alerta', {hoje: contador}, None)
        logger.debug('censo_imd_controle_alerta[{}] = {}'.format(hoje, contador))

    def _prepare_content_to_get(self, acache):
        return acache

    def _prepare_content_to_set(self, valor):
        return valor

    def _get_method_to_remove(self):
        return 'pop'

    def get_contador_controle_envio_alerta(self):
        hoje = datetime.now().date()
        return cache.get('censo_imd_controle_alerta')[hoje]

    def pode_enviar_alerta_hoje(self):
        hoje = datetime.now().date()
        if self.has_content() > 0:
            if cache.keys('censo_imd_controle_alerta') == []:
                return False
            #envia alerta uma única vez ao dia.
            return cache.get('censo_imd_controle_alerta').get(hoje, 0) == 1
        return False

    def processamento_foi_concluido(self):
        return self.status() == StatusProcessamento.CONCLUIDO


class _CacheCeps(_cacheBase):
    '''
    Armazena um dicionário com os ceps processados do arquivos vbase/fixtures/ceps.csv
    Formato: chave do dicionário é o número do CEP e valor são os dados.
    Exemplo:
        {
        '01133010': {
              'cep': '01133010',
              'logradouro': 'Baronesa de Porto Carreiro',
              'tipo_logradouro': 'Rua',
              'complemento': '',
              'local': '',
              'bairro_id': 25247,
              'bairro': 'Bom Retiro',
              'cidade_id': 9668,
              'localidade': 'São Paulo',
              'uf': 'SP',
              'cidade_cep': '0',
              'ibge': '3550308',
              'area': 1521.11,
              'id_municipio_subordinado': 0.0}
        }
    '''

    NOME_CACHE = 'esusve_processamento_ceps'
    CACHE_VAZIO = {}

    def _prepare_content_to_get(self, acache):
        return acache

    def _prepare_content_to_set(self, valor):
        return valor

    def _get_method_to_remove(self):
        return 'pop'


class _CacheNotificacoesSimilares(_cacheBase):
    '''
    Formato do cache:
        O cache é um dicionário onde a chave é uma tupla e o valor é um dicionário com as colunas diferente das notificações similares

        Exemplo:
        {
            "esusve_notificacoes_similares_('2020-06-06T03:00:00.000Z', 'JULIO CESAR FRANCA DE MEDEIROS SILVA', '1998-05-26T03:00:00.000Z')":
                [{'descricao_do_sintoma': 'cefaleia',
                  'numero_da_notificacao': '242002941077',
                  'data_do_inicio_dos_sintomas': '2020-06-02T03:00:00.000Z',
                  'telefone_de_contato': '(84) 8744-2149',
                  'data_da_notificacao': '2020-06-06T03:00:00.000Z',
                  'nome_completo': 'JULIO CESAR FRANCA DE MEDEIROS SILVA',
                  'data_de_nascimento': '1998-05-26T03:00:00.000Z'},
                 {'descricao_do_sintoma': 'coriza',
                  'numero_da_notificacao': '242002940149',
                  'data_do_inicio_dos_sintomas': '2020-06-03T03:00:00.000Z',
                  'telefone_de_contato': '(84) 8137-5204',
                  'data_da_notificacao': '2020-06-06T03:00:00.000Z',
                  'nome_completo': 'JULIO CESAR FRANCA DE MEDEIROS SILVA',
                  'data_de_nascimento': '1998-05-26T03:00:00.000Z'}],
            "esusve_notificacoes_similares_('2020-05-26T12:41:28.091Z', 'MARCELO GLAUBER DA SILVA PEREIRA', '1985-03-24T03:00:00.000Z')":
                [{'classificacao_final': None,
                  'numero_da_notificacao': '242001914238',
                  'data_da_notificacao': '2020-05-26T12:41:28.091Z',
                  'nome_completo': 'MARCELO GLAUBER DA SILVA PEREIRA',
                  'data_de_nascimento': '1985-03-24T03:00:00.000Z'},
                 {'classificacao_final': 'Confirmado Laboratorial',
                  'numero_da_notificacao': '242001914498',
                  'data_da_notificacao': '2020-05-26T12:41:28.091Z',
                  'nome_completo': 'MARCELO GLAUBER DA SILVA PEREIRA',
                  'data_de_nascimento': '1985-03-24T03:00:00.000Z'}]

        }
    '''
    NOME_CACHE = 'esusve_notificacoes_similares'
    CACHE_VAZIO = {}

    def clear(self):
        for chave in cache.keys('{}*'.format(self.NOME_CACHE)):
            cache.delete(chave)

    def remove(self, chaves):
        for chave in chaves:
            cache.delete(chave)

    def exists(self):
        return cache.keys('{}*'.format(self.NOME_CACHE)) != []

    def _prepare_content_to_get(self, acache):
        return cache.get_many(cache.keys('{}*'.format(self.NOME_CACHE)))

    def _prepare_content_to_set(self, valor):
        # cache.set('esusve_similaridade_processamento_concluido', True, None)
        return valor

    def _get_method_to_remove(self):
        return 'pop'

    def processamento_foi_concluido(self):
        return self.status() == StatusProcessamento.CONCLUIDO

    def add(self, chave, valor):
        cache.set('{}_{}'.format(self.NOME_CACHE, chave), valor, None)


class _CacheProcessamentoNotificacao(_cacheBase):
    NOME_CACHE = 'esusve_processamento_resumo'
    CACHE_VAZIO = 0

    def __init__(self, nome_arquivo):
        super().__init__()
        self._nome_arquivo = normalize_str(nome_arquivo)

    def clear(self):
        for chave in cache.keys('{}*'.format(self._nome_cache)):
            cache.delete(chave)

    def reset(self):
        super(_CacheProcessamentoNotificacao, self).reset()

        self.clear()

        cache.set('{}__timestamp_inicio'.format(self._nome_cache), datetime.now(), None)
        cache.set('{}__timestamp_fim'.format(self._nome_cache), None, None)
        cache.set('{}__percentual_execucao'.format(self._nome_cache), 0, None)
        cache.set('{}__stack_trace'.format(self._nome_cache), None, None)

        cache.set(self._nome_cache, {}, None)

        self.set_status(StatusProcessamento.INICIALIZADO)

    def _prepare_content_to_get(self, acache):
        return acache

    def _prepare_content_to_set(self, valor):
        return valor

    def processamento_foi_concluido(self):
        if self._nome_arquivo:
            for chave in cache.keys('{}_*'.format(self.NOME_CACHE)):
                if cache.get('{}_status'.format(chave)) != StatusProcessamento.INICIALIZADO:
                    return False
            return True
        return self.status() != StatusProcessamento.INICIALIZADO

    def status(self):
        return cache.get('{}_status'.format(self._nome_cache))

    def add(self, adict):
        dresumo = self.get()
        dresumo.update(adict)
        self.set(dresumo)

    def set_percentual(self, valor):
        cache.set('{}__percentual_execucao'.format(self._nome_cache), valor, None)

    def set_status(self, status):
        cache.set('{}_status'.format(self._nome_cache), status, None)
        if status == StatusProcessamento.CONCLUIDO:
            cache.set('{}__timestamp_fim'.format(self._nome_cache), datetime.now(), None)
            cache.set('{}__percentual_execucao'.format(self._nome_cache), 100.0, None)
        elif status == StatusProcessamento.INTERROMPIDO:
            cache.set('{}__timestamp_fim'.format(self._nome_cache), datetime.now(), None)

    def get_status_detalhe(self):
        cache.get('{}__timestamp_inicio'.format(self._nome_cache))
        cache.get('{}__timestamp_fim'.format(self._nome_cache))
        cache.get('{}__percentual_execucao'.format(self._nome_cache))
        cache.get('{}__stack_trace'.format(self._nome_cache))

        return {'timestamp_inicio': cache.get('{}__timestamp_inicio'.format(self._nome_cache)),
                'timestamp_fim': cache.get('{}__timestamp_fim'.format(self._nome_cache)),
                'percentual_execucao': cache.get('{}__percentual_execucao'.format(self._nome_cache)),
                'stack_trace': cache.get('{}__stack_trace'.format(self._nome_cache))
        }

    def set_nome_arquivo(self, nome):
        self._nome_arquivo = normalize_str(nome)

    @property
    def _nome_cache(self):
        return '{}_{}'.format(self.NOME_CACHE, self._nome_arquivo)


class _CacheIndicadoresBoletim(_cacheBase):
    '''
    '''
    NOME_CACHE = 'indicadores_boletim'
    CACHE_VAZIO = []

    def __init__(self):
        pass

    def _prepare_content_to_get(self, acache):
        return acache

    @classmethod
    def _prepare_content_to_set(self, valor):
        return valor

    def _get_method_to_remove(self):
        return 'pop'


class _CacheIndicadores(_cacheBase):
    '''
    '''
    NOME_CACHE = 'indicadores_catalogo'
    CACHE_VAZIO = {}

    def __init__(self, class_nome):
        self.class_nome = class_nome

    @property
    def _nome_cache(self):
        return self.class_nome

    def _prepare_content_to_get(self, acache):
        return acache

    @classmethod
    def _prepare_content_to_set(self, valor):
        return valor

    def _get_method_to_remove(self):
        return 'pop'

    def add(self, pk, dados):
        # logger.debug('Adicionando dados do indicador {} no cache {}'.format(pk, self._nome_cache))
        adict = {}
        adict[pk] = dados
        indicadores = self.get()
        indicadores.update(adict)
        self.set(indicadores)


class _CachePlanilhaObitos(_cacheBase):
    '''
    Armazena um dicionário com os dados da planilha de óbitos fornecido pelo CIEVS/Natal
    Exemplo:
        {
            {
              "sexo": "MULHERES",
              "idade": 71,
              "inicio_dos_sintomas": "09\\/06\\/2020",
              "unidade_notificadora": "HOSPITAL DE CAMPANHA",
              "logradouro": "RUA CANTOR CARLOS ALEXANDRE",
              "numero": "139",
              "bairro": "LAGOA AZUL",
              "telefone": "98834-7779",
              "internacao": "SIM",
              "sinaissintomas": "TOSSE, DISPNEIA E ADINAMIA",
              "medidas_adotadas": null,
              "contatos_investigados": null,
              "ocupacao": null,
              "deteccao_viralsoro": "15\\/06\\/2020",
              "__amostra": "RT-PCR",
              "resultado": "DETECTAVEL PARA COVID 22",
              "encerramento": "CONFIRMADO",
              "relatorio": null,
              "status": "CONFIRMADO",
              "informacoes": null,
              "fim_de_quarentena": null,
              "desfecho": "\\u00d3BITO ",
              "periodo_entre_a_data_dos_primeiros_sintomas_e_a_atual": null,
              "semana_epidemiologica": null,
              "data_do_obito": "2020-06-22T00:00:00.000Z",
              "telefone1": "98834-7779"
            }
    '''

    NOME_CACHE = 'esusve_indicadores_obitos'
    CACHE_VAZIO = None

    def get(self, class_encode=None):
        if self.exists():
            return pickle.loads(zlib.decompress(cache.get(self._nome_cache)))
        return self.CACHE_VAZIO

    def set(self, df):
        cache.set(self._nome_cache, self._prepare_content_to_set(zlib.compress(pickle.dumps(df))), None)

    def _prepare_content_to_get(self, acache):
        return acache

    def _prepare_content_to_set(self, valor):
        return valor

    def _get_method_to_remove(self):
        return 'pop'


class _CacheBairro(_cacheBase):
    '''
    Armazena um dicionário com os bairros
    Formato: chave do dicionário é o nome do bairro e o valor é um dicionário no formato
        { 'pk':
          'nome':
          'municipio': { 'pk' }
        }
    '''

    NOME_CACHE = 'bairros'
    CACHE_VAZIO = {}

    def _prepare_content_to_get(self, acache):
        return acache

    def _prepare_content_to_set(self, valor):
        return valor

    def _get_method_to_remove(self):
        return 'pop'


class _CacheHabitacoesBairro(_cacheBase):
    '''
    Armazena um dicionário com as habitações de bairros
    Formato: chave do dicionário é o nome da habitação e o valor é um dicionário no formato
        { 'pk':
          'nome':
          'municipio': { 'pk' }
        }
    '''

    NOME_CACHE = 'habitacoes_bairros'
    CACHE_VAZIO = {}

    def _prepare_content_to_get(self, acache):
        return acache

    def _prepare_content_to_set(self, valor):
        return valor

    def _get_method_to_remove(self):
        return 'pop'


class _CacheAssociacoesBairro(_cacheBase):
    '''
    Armazena um dicionário com as associações de bairros
    Formato: chave do dicionário é o nome da associação e o valor é um dicionário no formato
        { 'pk':
          'nome':
          'municipio': { 'pk' }
        }
    '''

    NOME_CACHE = 'associacoes_bairros'
    CACHE_VAZIO = {}

    def _prepare_content_to_get(self, acache):
        return acache

    def _prepare_content_to_set(self, valor):
        return valor

    def _get_method_to_remove(self):
        return 'pop'


class ControleCache():
    @staticmethod
    def filtros_de_notificacao():
        obj = _CacheFiltrosNotificacao()
        return obj

    @staticmethod
    def nomes_estabelecimento_a_associar():
        obj = _CacheAssociarNomesEstabelecimento()
        return obj

    @staticmethod
    def nomes_paciente_a_associar():
        obj = _CacheAssociarNomesPaciente()
        return obj

    @staticmethod
    def ceps():
        obj = _CacheCeps()
        return obj

    @staticmethod
    def notificacoes_similares():
        obj = _CacheNotificacoesSimilares()
        return obj

    @staticmethod
    def processamento_notificacoes(upload_importacao=None):
        if upload_importacao:
            return _CacheProcessamentoNotificacao(upload_importacao.arquivo.name)
        return _CacheProcessamentoNotificacao('')

    @staticmethod
    def indicadores(class_nome):
        obj = _CacheIndicadores(class_nome)
        return obj

    @staticmethod
    def decode(dados, class_decode=DateTimeDecoder):
        return json.loads(dados, cls=class_decode)

    @staticmethod
    def obitos_planilha():
        obj = _CachePlanilhaObitos()
        return obj

    @staticmethod
    def bairros():
        obj = _CacheBairro()
        return obj

    @staticmethod
    def habitacoes_bairros():
        obj = _CacheHabitacoesBairro()
        return obj

    @staticmethod
    def associacoes_bairros():
        obj = _CacheAssociacoesBairro()
        return obj



