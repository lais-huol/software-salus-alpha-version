import elasticsearch.helpers
import hashlib
import json
import logging
import os
import pandas as pd
import numpy as np
import re
from datetime import datetime
from dbfread import DBF
from django.conf import settings
from django.core.mail import mail_admins
from django.db.models import Subquery, Count
from django.utils import timezone
from elasticsearch import Elasticsearch
from zipfile import ZipFile, BadZipFile

from base.alertas import Alerta
from base.caches import ControleCache, StatusProcessamento
from base.extracao.rest_laiscep import recuperar_ceps
from base.models import AssociacaoBairro, HabitacoesBairro, Bairro, PessoaFisica, EstabelecimentoSaude, \
    AssociacaoOperadorCNES, UnidadeFederativa
from base.models import Municipio, Sexo
from base.signals import fonte_de_dados_indicadores_alterados
from base.utils import levenshtein_distance, dict_compare, digits, to_date, get_size, normalize_str
from notificacoes.models import TipoArquivo, Notificacao, HistoricoNotificacaoAssociacaoBairroOutros, UploadImportacao, \
    TipoNotificacaoMotivoCancelamento, HistoricoNotificacaoAtualizacao, Obito, TipoFonteDados

logger = logging.getLogger(__name__)


def convert_date(datestr):
    try:
        return to_date(datestr)
    except:
        return None


class SivepTipoClassificacaoFinalCaso():
    SRAG_POR_INFLUENZA = '1'
    SRAG_POR_OUTRO_VIRUS_RESPIRATORIO = '2'
    SRAG_POR_OUTRO_AGENTE_ETIOLOGICO = '3'
    SRAG_NAO_ESPECIFICACAO = '4'
    SRAG_POR_COVID19 = '5'

    TIPO = {
        SRAG_POR_INFLUENZA: 'SRAG por influenza',
        SRAG_POR_OUTRO_VIRUS_RESPIRATORIO: 'SRAG por outro vírus respiratório',
        SRAG_POR_OUTRO_AGENTE_ETIOLOGICO: 'SRAG por outro agente etiológico,qual',
        SRAG_NAO_ESPECIFICACAO: 'SRAG não especificado',
        SRAG_POR_COVID19: 'SRAG por COVID-19'
    }

    @classmethod
    def parse(cls, valor):
        return cls.TIPO.get(valor, None)


class SivepTipoEvolucaoCaso():
    CURA = '1'
    OBITO = '2'
    OBITO_POR_OUTRAS_CAUSAS = '3'
    IGNORADO = '9'
    TIPO = {
        CURA: 'Cura',
        OBITO: 'Óbito',
        OBITO_POR_OUTRAS_CAUSAS: 'Óbito por outras causas',
        IGNORADO: 'Ignorado'
    }
    @classmethod
    def parse(cls, valor):
        return cls.TIPO.get(valor, None)


class SivepTipoCriterioEncerramento():
    LABORATORIAL = '1'
    CLINICO_EPIDEMIOLÓGICO = '2'
    CLINICO = '3'
    CLINICO_IMAGEM = '4'
    TIPO = {
        LABORATORIAL: 'Confirmado Laboratorial',
        CLINICO_EPIDEMIOLÓGICO: 'Confirmado Clínico-Epidemiológico',
        CLINICO: 'Confirmado Clínico',
        CLINICO_IMAGEM: 'Confirmado Clínico Imagem'
    }
    @classmethod
    def parse(cls, valor):
        return cls.TIPO.get(valor, None)


class SivepTipoTesteAntigenico():
    IMUNOFLUORESCENCIA = '1'
    TESTE_RPAIDO_ANTIGENICO = '2'
    TIPO = {
        IMUNOFLUORESCENCIA: 'Imunofluorescência (IF)',
        TESTE_RPAIDO_ANTIGENICO: 'Teste rápido antigênico',
        '0': ''
    }
    @classmethod
    def parse(cls, valor):
        return cls.TIPO.get(valor, None)


class SivepTipoResultadoTeste():
    POSITIVO = '1'
    NEGATIVO = '2'
    INCONCLUSIVO = '3'
    NAO_REALIZADO = '4'
    AGUARDANDO_RESULTADO = '5'
    IGNORADO = '9'
    TIPO = {
        POSITIVO: 'Positivo',
        NEGATIVO: 'Negativo',
        INCONCLUSIVO: 'Inconclusivo',
        NAO_REALIZADO: 'Não realizado',
        AGUARDANDO_RESULTADO: 'Aguardando resultado',
        IGNORADO: 'Ignorado',
    }
    @classmethod
    def parse(cls, valor):
        return cls.TIPO.get(valor, None)


class SivepTipoResultadoRTPCROutroMetodo():
    DETECTAVEL = '1'
    NAO_DETECTAVEL = '2'
    INCONCLUSIVO = '3'
    NAO_REALIZADO = '4'
    AGUARDANDO_RESULTADO = '5'
    IGNORADO = '9'
    TIPO = {
        DETECTAVEL: 'Detectável',
        NAO_DETECTAVEL: 'Não Detectável',
        INCONCLUSIVO: 'Inconclusivo',
        NAO_REALIZADO: 'Não realizado',
        AGUARDANDO_RESULTADO: 'Aguardando resultado',
        IGNORADO: 'Ignorado',
    }
    @classmethod
    def parse(cls, valor):
        return cls.TIPO.get(valor, None)


class SivepTipoSorologiaSARSCov2():
    TESTE_RAPIDO = '1'
    ELISA = '2'
    QUIMILUMINESCENCIA = '3'
    OUTRO = '4'
    TIPO = {
        TESTE_RAPIDO: 'Teste rápido',
        ELISA: 'Elisa',
        QUIMILUMINESCENCIA: 'Quimiluminescência',
        OUTRO: 'Outro, qual',
        '0': '',
    }
    @classmethod
    def parse(cls, valor):
        return cls.TIPO.get(valor, None)


class SivepTipoSexo():
    MASCULINO = '1'
    FEMININO = '2'
    IGNORADO = '9'
    TIPO = {
        MASCULINO: 'Masculino',
        FEMININO: 'Feminino',
        IGNORADO: 'Indefinido',
        'M': 'Masculino',
        'F': 'Feminino'
    }
    @classmethod
    def parse(cls, valor):
        return cls.TIPO.get(valor, None)


class SivepTipoRacaCor():
    BRANCA = '1'
    PRETA = '2'
    AMARELA = '3'
    PARDA = '4'
    INDIGENA = '5'
    IGNORADO = '9'
    TIPO = {
        BRANCA: 'Branca',
        PRETA: 'Preta',
        AMARELA: 'Amarela',
        PARDA: 'Parda',
        INDIGENA: 'Indígena',
        IGNORADO: 'Ignorado',
    }
    @classmethod
    def parse(cls, valor):
        return cls.TIPO.get(valor, None)


class SivepSimNao():
    SIM = '1'
    NAO = '2'
    IGNORADO = '9'
    TIPO = {
        SIM: 'Sim',
        NAO: 'NÃO',
        IGNORADO: 'Indefinido',
    }

    @classmethod
    def parse(cls, valor):
        return cls.TIPO.get(valor, None)


class TipoArquivo():
    ESUSVE_ARQUIVO_CSV = 0
    ESUSVE_API_JSON = 1
    SIVEP_GRIPE_DBF = 2
    SIVEP_GRIPE_API_JSON = 3
    TIPO = [[ESUSVE_ARQUIVO_CSV, 'ESUS-VE NOTIFICA CSV'],
            [ESUSVE_API_JSON, 'ESUS-VE NOTIFICA API'],
            [SIVEP_GRIPE_DBF, 'SIVEP GRIPE DBF'],
            [SIVEP_GRIPE_API_JSON, 'SIVEP GRIPE API'],
            ]


class PessoaParse():
    SEXO_PARSE = {
        'Feminino': Sexo.FEMININO,
        'Masculino': Sexo.MASCULINO,
        'F': Sexo.FEMININO,
        'M': Sexo.MASCULINO,
        'Indefinido': Sexo.INDEFINIDO,
        '1': Sexo.MASCULINO,
        '2': Sexo.FEMININO,
        '9': Sexo.INDEFINIDO,
    }

    def __init__(self, dados):
        '''

        :param dados:  dicionário com as chaves
            {
                'cpf': '',
                'nome': '',
                'cns': '',
                'sexo': '',
                'data_de_nascimento': '',
                'telefones': '',
                'celulares': '',
                'email': '',
                'cep': '',
                'logradouro': '',
                'numero': '',
                'complemento': '',
                'bairro_nome': '',
                'municipio_nome' : '',
                'municipio_ibge' : '',
                'uf_nome': '',
                'uf_ibge': '',
            }
        '''
        self._dados = dados
        self._obter_notificacao = ObterNotificacao(TipoArquivo.ESUSVE_ARQUIVO_CSV)

    @property
    def pk(self):
        return self._dados['pk']

    @property
    def cpf(self):
        dado = self._dados.get('cpf')
        _cpf = None
        if dado:
            _cpf = digits(dado)
            if len(_cpf) != 11:
                return None
        return _cpf

    @property
    def cns(self):
        dado = self._dados.get('cns')
        _cns = None
        if dado:
            _cns = digits(dado)
            if len(_cns) != 15:
                return None
        return _cns

    @property
    def nome_completo(self):
        dado = self._dados.get('nome')
        if dado:
            return dado[:80]
        return None

    @property
    def sexo(self):
        dado = self._dados.get('sexo')
        if dado:
            return self.SEXO_PARSE[dado]
        return Sexo.NAO_INFORMADO

    @property
    def data_de_nascimento(self):
        try:
            dado = self._dados.get('data_de_nascimento')
        except TypeError:
            return None
        try:
            if dado is not None and isinstance(dado, str) and 'T' in dado:
                return datetime.strptime(dado.split('T')[0], '%Y-%m-%d')
            return datetime.strptime(dado, '%d/%m/%Y')
        except ValueError:
            return datetime.strptime(dado, '%Y-%m-%d')
        except TypeError:
            return None

    @property
    def telefones(self):
        dado = self._dados.get('telefones')
        if dado:
            return dado
        return None

    @property
    def celular(self):
        dado = self._dados.get('celulares')
        if dado:
            return dado
        return None

    @property
    def email(self):
        dado = self._dados.get('email')
        if dado:
            return dado
        return None


    @property
    def cep(self):
        dado = self._dados.get('cep')
        if dado:
            cep = digits(dado)
            return f'{cep[:5]}-{cep[5:8]}'
        return None

    @property
    def logradouro(self):
        dado = self._dados.get('logradouro')
        if dado:
            return dado[:80]
        return None

    @property
    def numero(self):
        dado = self._dados.get('numero')
        if dado:
            return dado[:10]
        return None

    @property
    def complemento(self):
        dado = self._dados.get('complemento')
        return dado

    @property
    def nome_de_bairro(self):
        return self._dados.get('bairro_nome')


    @property
    def municipio (self):
        codigo_ibge = self._dados.get('municipio_ibge', None)
        if codigo_ibge:
            return Municipio(pk=codigo_ibge[:6])

    def _get_dados(self):
        return {
            'nome': self.nome_completo,
            'cns': self.cns,
            'sexo': self.sexo,
            'data_de_nascimento': self.data_de_nascimento,
            'telefones': self.telefones,
            'celulares': self.celular,
            'email': self.email,
            'cep': self.cep,
            'logradouro': self.logradouro,
            'numero': self.numero,
            'complemento': self.complemento,
            'bairro': self.nome_de_bairro,
            'municipio': self.municipio,
        }

    def atualizar_dados(self):
        save_data = self._get_dados()
        pessoa, created = PessoaFisica.objects.update_or_create(
            cpf=self.cpf, defaults=save_data
        )
        return pessoa


class ProcessarNotificacaoCache():
    def __init__(self):
        self._cache_ceps = None
        self._cache_bairros = None
        self._cache_habitacoes_bairros = None
        self._cache_associacoes_bairros = None
        self._cache_associacoes_operadores = None
        self._cache_cnes = None
        self._cache_pessoas_fisica = None
        self._cache_municipios = None
        self._municipio_base = None
        self._cache_ufs = None
        self._cache_notificacoes_ja_processadas = None
        self._cache_historico_notificacao_ass_bairro_outros = None

    def processar(self):
        self._procesar_ceps()
        self._processar_bairros()
        self._processar_habitacoes_bairros()
        self._processar_associacoes_bairros()
        self._processar_associacoes_operadores()
        self._processar_cnes()
        self._processar_pessoas_fisica()
        self._processar_municipio_base()
        self._processar_municipios()
        self._processar_ufs()
        self._processar_notificacoes_ja_processadas()
        self._processar_historico_notificacao_ass_bairro_outros()

    def  _procesar_ceps(self):
        self._cache_ceps = recuperar_ceps()
        return self._cache_ceps

    def _processar_bairros(self):
        if ControleCache.bairros().exists():
            logger.debug('Usando cache de bairros')
            self._cache_bairros = ControleCache.bairros().get()
            return self._cache_bairros

        logger.debug('Criado cache de bairros...')
        self._cache_bairros = {}
        qs = Bairro.objects.select_related('municipio').all().values('nome', 'pk', 'municipio__pk')
        for bairro in qs:
            self._cache_bairros[bairro['nome']] = {'pk': bairro['pk'],
                                                  'nome': bairro['nome'],
                                                  'municipio': {'pk': bairro['municipio__pk']}
            }
        ControleCache.bairros().set(self._cache_bairros)
        return self._cache_bairros

    def _processar_habitacoes_bairros(self):
        if ControleCache.habitacoes_bairros().exists():
            logger.debug('Usando cache de habitações de bairros')
            self._cache_habitacoes_bairros = ControleCache.habitacoes_bairros().get()
            return self._cache_habitacoes_bairros

        logger.debug('Criado cache de habitações de bairros...')
        self._cache_habitacoes_bairros = {}
        qs = HabitacoesBairro.objects.select_related('bairro', 'bairro__municipio').all().values('nome',
                                                                                                 'bairro__pk',
                                                                                                 'bairro__nome',
                                                                                                 'bairro__municipio__pk')
        for habitacao in qs:
            self._cache_habitacoes_bairros[habitacao['nome']] = {
                'pk': habitacao['bairro__pk'],
                'nome': habitacao['bairro__nome'],
                'municipio': {'pk': habitacao['bairro__municipio__pk']},
            }
        ControleCache.habitacoes_bairros().set(self._cache_habitacoes_bairros)
        return self._cache_habitacoes_bairros

    def _processar_associacoes_bairros(self):
        if ControleCache.associacoes_bairros().exists():
            logger.debug('Usando cache de habitações de bairros')
            self._cache_associacoes_bairros = ControleCache.associacoes_bairros().get()
            return self._cache_associacoes_bairros

        logger.debug('Criado cache de associações bairros...')
        self._cache_associacoes_bairros = {}
        qs = AssociacaoBairro.objects.select_related('bairro', 'bairro__municipio').all().values('nome',
                                                                                                 'bairro__pk',
                                                                                                 'bairro__nome',
                                                                                                 'bairro__municipio__pk')
        for associacao_bairro in qs:
            self._cache_associacoes_bairros[associacao_bairro['nome'].upper()] = {
                'pk': associacao_bairro['bairro__pk'],
                'nome': associacao_bairro['bairro__nome'],
                'municipio': {'pk': associacao_bairro['bairro__municipio__pk']},
            }
        ControleCache.associacoes_bairros().set(self._cache_associacoes_bairros)
        return self._cache_associacoes_bairros

    def _processar_associacoes_operadores(self):
        logger.debug('Criado cache de associações de operadores...')
        self._cache_associacoes_operadores = {}
        qs = AssociacaoOperadorCNES.objects.select_related('estabelecimento_saude')
        qs = qs.filter(estabelecimento_saude__isnull=False).values('cpf', 'estabelecimento_saude__pk')
        for associacao_operador in qs:
            self._cache_associacoes_operadores[associacao_operador['cpf']] = {
                'estabelecimento_saude': {'pk': associacao_operador['estabelecimento_saude__pk']}
            }
        return self._cache_associacoes_operadores

    def _processar_cnes(self):
        logger.debug('Criado cache de estabelecimentos de saúde...')
        self._cache_cnes = {}
        qs = EstabelecimentoSaude.objects.all().values('codigo_cnes', 'pk')
        for estabelecimento in qs:
            self._cache_cnes[estabelecimento['codigo_cnes']] = {'pk': estabelecimento['pk']}
            self._cache_cnes[estabelecimento['codigo_cnes'].zfill(7)] = {
                'pk': estabelecimento['pk']}  # NOTA TODO: armazenado no banco local registros sem zeros à esquerda
        return self._cache_cnes

    def _processar_pessoas_fisica(self):
        logger.debug('Criado cache de pessoa física...')
        self._cache_pessoas_fisica = {}
        for p in PessoaFisica.objects.all().values('cpf', 'pk'):
            self._cache_pessoas_fisica[p['cpf']] = {'pk': p['pk']}
        return self._cache_pessoas_fisica

    def _processar_municipio_base(self):
        self._municipio_base = Municipio.objects.get(pk=settings.CODIGO_IBGE_MUNICIPIO_BASE)
        return self._municipio_base

    def _processar_municipios(self):
        logger.debug('Criado cache de municipios...')
        self._cache_municipios = {}
        qs = Municipio.objects.select_related('estado').all().values('pk', 'nome', 'estado__nome')
        for municipio in qs:
            self._cache_municipios[(municipio['nome'].upper(), municipio['estado__nome'].upper())] = {
                'pk': municipio['pk']}
        return self._cache_municipios

    def _processar_ufs(self):
        logger.debug('Criado cache de UFs...')
        self._cache_ufs = {}
        qs = UnidadeFederativa.objects.all().values('nome', 'sigla')
        for uf in qs:
            self._cache_ufs[uf['sigla'].upper()] = uf['nome']
        return self._cache_ufs


    def _processar_notificacoes_ja_processadas(self):
        logger.debug('Criado cache de notificações já processadas ...')
        self._cache_notificacoes_ja_processadas = {}
        qs = Notificacao.objects.select_related('bairro').values('pk',
                                                                 'numero',
                                                                 'fonte_dados',
                                                                 'hash_dados',
                                                                 'notificacao_principal_id',
                                                                 'ativa',
                                                                 'data',
                                                                 'pessoa_id',
                                                                 'estabelecimento_saude_id',
                                                                 'municipio_residencia_id',
                                                                 'municipio_ocorrencia_id',
                                                                 'bairro_id',
                                                                 'tipo_motivo_desativacao',
                                                                 'data_incidencia')
        for dados_da_notificacao in qs:
            chave = (dados_da_notificacao['numero'], dados_da_notificacao['fonte_dados'])
            self._cache_notificacoes_ja_processadas[chave] = {
                'pk': dados_da_notificacao['pk'],
                'numero': dados_da_notificacao['numero'],
                'hash_dados': dados_da_notificacao['hash_dados'],
                'notificacao_principal_id': dados_da_notificacao['notificacao_principal_id'],
                'ativa': dados_da_notificacao['ativa'],
                'pessoa_id': dados_da_notificacao['pessoa_id'],
                'estabelecimento_saude_id': dados_da_notificacao['estabelecimento_saude_id'],
                'municipio_residencia_id': dados_da_notificacao['municipio_residencia_id'],
                'municipio_ocorrencia_id': dados_da_notificacao['municipio_ocorrencia_id'],
                'bairro_id': dados_da_notificacao['bairro_id'],
                'tipo_motivo_desativacao': dados_da_notificacao['tipo_motivo_desativacao'],
                'data_incidencia': dados_da_notificacao['data_incidencia']
            }
        return self._cache_notificacoes_ja_processadas

    def _processar_historico_notificacao_ass_bairro_outros(self):
        logger.debug('Criado cache de Histórico de associação Bairro Outros...')
        self._cache_historico_notificacao_ass_bairro_outros = {}
        qs = HistoricoNotificacaoAssociacaoBairroOutros.objects.all().values('notificacao__numero', 'bairro_id',
                                                                             'confirmado')
        for historico in qs:
            self._cache_historico_notificacao_ass_bairro_outros[
                (historico['notificacao__numero'], historico['bairro_id'])] = {
                'bairro_id': historico['bairro_id'],
                'confirmado': historico['confirmado'],
            }
        return self._cache_historico_notificacao_ass_bairro_outros

    @property
    def ceps(self):
        if self._cache_ceps is None:
            return self._procesar_ceps()
        return self._cache_ceps

    @property
    def bairros(self):
        if self._cache_bairros is None:
            return self._processar_bairros()
        return self._cache_bairros

    @property
    def habitacoes_bairros(self):
        if self._cache_habitacoes_bairros is None:
            return self._processar_habitacoes_bairros()
        return self._cache_habitacoes_bairros

    @property
    def associacoes_bairros(self):
        if self._cache_associacoes_bairros is None:
            return self._processar_associacoes_bairros()
        return self._cache_associacoes_bairros

    @property
    def associacoes_operadores(self):
        if self._cache_associacoes_operadores is None:
            return self._processar_associacoes_operadores()
        return self._cache_associacoes_operadores

    @property
    def cnes(self):
        if self._cache_cnes is None:
            return self._processar_cnes()
        return self._cache_cnes

    @property
    def pessoas_fisica(self):
        if self._cache_pessoas_fisica is None:
            return self._processar_pessoas_fisica()
        return self._cache_pessoas_fisica

    @property
    def municipio_base(self):
        if self._municipio_base is None:
            return self._processar_municipio_base()
        return self._municipio_base

    @property
    def municipios(self):
        if self._cache_municipios is None:
            return self._processar_municipios()
        return self._cache_municipios

    @property
    def ufs(self):
        if self._cache_ufs is None:
            return self._processar_ufs()
        return self._cache_ufs

    @property
    def notificacoes_ja_processadas(self):
        if self._cache_notificacoes_ja_processadas is None:
            return self._processar_notificacoes_ja_processadas()
        return self._cache_notificacoes_ja_processadas

    @property
    def historico_notificacao_ass_bairro_outros(self):
        if self._cache_historico_notificacao_ass_bairro_outros is None:
            return self._processar_historico_notificacao_ass_bairro_outros()
        return self._cache_historico_notificacao_ass_bairro_outros

    def total_memoria_utilizada(self):
        cache_memoria_utilizada = get_size(self)
        cache_memoria_utilizada = round(cache_memoria_utilizada / 1024 / 1024, 2)  # conversão para Mbytes
        logger.debug('Uso de memória do cache : {} Mb'.format(cache_memoria_utilizada))
        return cache_memoria_utilizada

    def limpar(self):
        if self._cache_bairros:
            self._cache_bairros.clear()
        if self._cache_habitacoes_bairros:
            self._cache_habitacoes_bairros.clear()
        if self._cache_associacoes_bairros:
            self._cache_associacoes_bairros.clear()
        if self._cache_associacoes_operadores:
            self._cache_associacoes_operadores.clear()
        if self._cache_cnes:
            self._cache_cnes.clear()
        if self._cache_pessoas_fisica:
            self._cache_pessoas_fisica.clear()
        if self._cache_municipios:
            self._cache_municipios.clear()
        if self._cache_ufs:
            self._cache_ufs.clear()
        if self._cache_notificacoes_ja_processadas:
            self._cache_notificacoes_ja_processadas.clear()
        if self._cache_historico_notificacao_ass_bairro_outros:
            self._cache_historico_notificacao_ass_bairro_outros.clear()


class ObterNotificacao():
    def __init__(self, tipo=None, reprocessar=False, qs_upload_importacao=None):
        self.reprocessar = reprocessar
        if qs_upload_importacao is None:
            qs_upload_importacao = UploadImportacao.objects.filter(tipo=tipo, processado=False).order_by('datahora')

        self._upload_importacao = None
        if qs_upload_importacao.exists():
            self._upload_importacao = qs_upload_importacao[0]

        self._cache_status_processamento = ControleCache.processamento_notificacoes(self._upload_importacao)


        self._cache = None

    def get_pessoas_fields(self):
        dados = Notificacao.get_pessoas_fields()
        dados.update({
            'bairro_nome': 'bairro',
            'municipio_nome': 'municipio_de_residencia',
            'municipio_ibge': 'codigo_municipio_de_residencia',
            'uf_sigla': None,
            'uf_nome': 'estado_de_residencia',
            'uf_ibge': 'estadoIBGE',
        })
        return dados

    @property
    def cache(self):
        if self._cache is None:
            self._cache = ProcessarNotificacaoCache()
        return self._cache

    @classmethod
    def get_bairro(cls, nome):
        obter_notificacao = cls()
        dbairro = obter_notificacao.tratar_bairro(nome)
        if dbairro:
            municipio = Municipio(pk =dbairro['municipio']['pk'] )
            return Bairro(pk = dbairro['pk'],
                          nome = dbairro['nome'],
                          municipio = municipio)

    def _get_bairro(self, nome, dados_bairro, dados_habitacoes_bairro, dados_associacoes_bairro):
        '''
        Recupera o registro de bairro, dado um nome de bairro.
        Fluxo:
        1. Busca um nome similar ao nome fornecido
        2. Com base no nome similar, localiza primeiro se já existe um bairro, se sim, retorna o bairo
        3. Não encontrando o bairro, busca em habitações o bairro relacionado
        4. Não encontrando a habitação, localiza se já existe uma associação de bairro
        :param nome:
        :param dados_bairro:
        :param dados_habitacoes_bairro:
        :param dados_associacoes_bairro:
        :return:
        '''

        def get_bairro_encontrado(nome, dados_bairro, dados_associacoes_bairro):
            if 'CONJUNTO' in nome:
                nome = re.sub('CONJUNTO', '', nome).strip()
            if 'CONJ' in nome:
                nome = re.sub('CONJ', '', nome).strip()

            nomes_de_bairro = [*dados_bairro.keys()]
            nome_similar, taxa = levenshtein_distance(nome.upper(), nomes_de_bairro)
            bairro = dados_bairro.get(nome_similar, None)
            if bairro and nome != nome_similar:
                dados_de_associacao = dados_associacoes_bairro.get(nome.strip(), None)
                if dados_de_associacao is None:
                    AssociacaoBairro.get_create_or_update(nome.strip(), Bairro(id=bairro['pk']))
                    logger.debug('Associação cadastrada; {}; {}; {}'.format(nome, bairro['nome'], taxa))
            return bairro

        bairro = None
        if nome:
            bairro = get_bairro_encontrado(nome, dados_bairro, dados_associacoes_bairro)
            if bairro is None:
                logger.debug('Bairro não encontrando, buscado em habitações; {}'.format(nome))
                bairro = get_bairro_encontrado(nome, dados_habitacoes_bairro, dados_associacoes_bairro)
            if bairro is None:
                logger.debug('Bairro não encontrando, buscado em associações; {}'.format(nome))
                bairro = get_bairro_encontrado(nome, dados_associacoes_bairro, dados_associacoes_bairro)
        return bairro

    def tratar_bairro(self, nome_bairro, dados_cep=None):
        bairro = None

        # busca na associação de bairro, o bairro fornecido no endereço
        if nome_bairro:
            if self.cache.associacoes_bairros.get(nome_bairro, None):
                bairro = self.cache.associacoes_bairros[nome_bairro]
            elif nome_bairro:
                bairro = self._get_bairro(nome_bairro, self.cache.bairros, self.cache.habitacoes_bairros,
                                          self.cache.associacoes_bairros)

        # se não encontrar o bairro, busca na associação de bairro, o bairro pelo nome do bairro obtido do CEP
        if dados_cep and bairro is None:
            try:
                if dados_cep['bairro']:
                    nome_bairro = dados_cep['bairro'].upper().strip()
                    if self.cache.associacoes_bairros.get(nome_bairro, None):
                        bairro = self.cache.associacoes_bairros[nome_bairro]
                    elif nome_bairro:
                        bairro = self._get_bairro(nome_bairro, self.cache.bairros, self.cache.habitacoes_bairros,
                                                  self.cache.associacoes_bairros)
            except:
                pass


        # TODO: após processar no servidor, desativar o código baixo. Retornar a associação já existente na notificação
        # try:
        #     if bairro is None \
        #             and dados['bairro'] is not None \
        #             and dados_cep is not None \
        #             and dados['bairro'].upper().strip() != dados_cep['bairro'].upper().strip():
        #         bairro = notificacao_previa.bairro if notificacao_previa else None
        # except:
        #     pass

        if bairro is None and nome_bairro is not None:
            logger.debug('Bairro não encontrado; {};'.format(nome_bairro))

        return bairro

    def _tratar_bairro(self, notificacao_previa, nome_bairro, dados_cep):
        bairro = self.tratar_bairro(nome_bairro, dados_cep)

        # se bairro igual a OUTROS, verifica a cidade.
        bairro_outro_e_localidade_cep_pertence_cidade = False
        if bairro and bairro['nome'] == 'OUTRO':
            if dados_cep and dados_cep['localidade'].upper().strip() == self.cache.municipio_base.nome.upper():
                bairro = None
                bairro_outro_e_localidade_cep_pertence_cidade = True

        # Se o bairro obtido da associacao for OUTRO e o bairro obtido do CEP for pertecente a localidade de Natal,
        # isto é bairro_OUTRO_pertence_cidade = True
        # Registre no histórico essa associação para posterior validação.
        historico_associacao_bairro = None
        if notificacao_previa and bairro and bairro_outro_e_localidade_cep_pertence_cidade:
            historico_associacao_bairro = self.cache.historico_notificacao_ass_bairro_outros.get(
                (notificacao_previa['pk'], bairro['pk']), None)
            if historico_associacao_bairro is None:
                obj, created = HistoricoNotificacaoAssociacaoBairroOutros.objects.get_or_create(
                    notificacao=Notificacao(pk=notificacao_previa['pk']),
                    defaults={'bairro': Bairro(pk=bairro['pk'])})

                historico_associacao_bairro = {
                    'bairro_id': obj.bairro_id,
                    'confirmado': obj.confirmado,
                }
        return bairro, historico_associacao_bairro

    def _tratar_cep(self, cep):
        dados_cep = None
        if cep:
            try:
                cep = digits(cep)
                if self.cache.ceps.get(cep, None) is not None:
                    dados_cep = self.cache.ceps[cep]
                else:
                    logger.debug('CEP não encontrado {}'.format(cep))

            except:
                cep = None
        return dados_cep

    def _get_dados_previo_se_alterado(self, notificacao_previa, dados_novo, hash_dados):
        if notificacao_previa and notificacao_previa['hash_dados'] != hash_dados:
            dados_previo = Notificacao.objects.filter(pk=notificacao_previa['pk']).values('dados')[0]['dados']
            added, removed, modified, same = dict_compare(dados_previo, dados_novo)
            if modified:
                return modified
        return None

    def _obter_dados_de_pessoa(self, dados_notificacao):
        dados_pessoais = {}
        for field_pessoa, field_notificacao in self.get_pessoas_fields().items():
            try:
                dados_pessoais[field_pessoa] = dados_notificacao[field_notificacao]
            except:
                dados_pessoais[field_pessoa] = None
        return dados_pessoais

    def _tratar_dados_de_pessoa(self, dados_notificacao, dados_notificacao_modificados=None):
        dados_pessoais = self._obter_dados_de_pessoa(dados_notificacao)

        pessoa_parse = PessoaParse(dados_pessoais)

        pessoa = None
        if pessoa_parse.cpf:
            pessoa = self.cache.pessoas_fisica.get(pessoa_parse.cpf, None)

            # verifica se houve mudança nos dados do esusve
            houve_alteracoes_nos_dados_pessoais = False
            if dados_notificacao_modificados:
                # Verifica se a mudança está relacionada aos dados pessoais
                for chave in dados_notificacao_modificados.keys():
                    if chave in PessoaFisica.FIELDS:
                        houve_alteracoes_nos_dados_pessoais = True

            if houve_alteracoes_nos_dados_pessoais or pessoa is None:
                pessoa_fisica = pessoa_parse.atualizar_dados()
                pessoa = {'pk': pessoa_fisica.pk}
        return pessoa

    def _tratar_dados_operador(self, dados):
        estabelecimento_cache = None
        estabelecimento = None
        cpf = digits(dados['operador_cpf'])

        associacao_operador = self.cache.associacoes_operadores.get(cpf, None)

        if associacao_operador:
            estabelecimento_cache = associacao_operador['estabelecimento_saude']
            if estabelecimento_cache:
                estabelecimento = EstabelecimentoSaude(pk=estabelecimento_cache['pk'],
                                                       dados_cnes={'NO_RAZAO_SOCIAL': ''})

        codigo_cnes = dados['operador_cnes']
        if codigo_cnes and len(codigo_cnes) == 7:
            estabelecimento_cache = self.cache.cnes.get(codigo_cnes, None)
            if estabelecimento_cache:
                estabelecimento = EstabelecimentoSaude(pk=estabelecimento_cache['pk'],
                                                       dados_cnes={'NO_RAZAO_SOCIAL': ''})

        if cpf and len(cpf) == 11:
            dados = {
                'operador_cpf': dados['operador_cpf'],
                'operador_cnes': dados['operador_cnes'],
                'operador_email': dados['operador_email'],
                'operador_nome_completo': dados['operador_nome_completo'],
            }
            save_data = {
                'estabelecimento_saude': estabelecimento,
                'dados': dados
            }
            associacao_operador, created = AssociacaoOperadorCNES.objects.get_or_create(
                cpf=cpf, defaults=save_data
            )

        return estabelecimento

    def _tratar_alteracoes(self, dados_modificados, notificacao_previa):
        houve_alteracao = False
        try:
            if dados_modificados:
                houve_alteracao = True
                # alerta resultado_do_teste
                logger.debug(
                    'Notificação foi alterada no ESUS-VE; {}; {}'.format(notificacao_previa['numero'], dados_modificados))

                # Reativa as notificações cancelada por similaridade - funcionalidade definir pricinpal
                Notificacao.objects.filter(notificacao_principal_id=notificacao_previa['pk']).update(ativa=True,
                                                                                         notificacao_principal=None,
                                                                                         tipo_motivo_desativacao=None)
                Notificacao.objects.filter(id=notificacao_previa['pk']).update(ativa=True,
                                                                          notificacao_principal=None,
                                                                          tipo_motivo_desativacao=None)
        except:
            self._cache_status_processamento.set_status(StatusProcessamento.INTERROMPIDO)
            raise
        return houve_alteracao

    def _get_hash(self, dados):
        raise NotImplementedError()

    def _obter_dados(self):
        raise NotImplementedError()

    def _desativar_notificacoes_canceladas(self):
        '''
        Marca como excluídas as notificações com evolucao_caso Cancelado
        :return:
        '''
        logger.debug('Desativando notificações canceladas...')
        Notificacao.ativas.filter(dados__evolucao_caso='Cancelado').update(ativa=False,
                                                                          tipo_motivo_desativacao=TipoNotificacaoMotivoCancelamento.EVOLUCAO_CASO_CANCELADA)

        quant = Notificacao.ativas.filter(dados__evolucao_caso='Cancelado').count()
        logger.info('Foram desativadas {} notificacoes com evolução do caso = "Cancelada"'.format(quant))
        return quant

    def _desativar_notificacoes_iguais(self, colunas=None, ativa=True):
        '''
        Desativa as notificações com json dados iguais, permanecendo apenas a primeira de cada grupo.
        O grupo é definido pela colunas


        :param dnotificacoes:
        :return:
        '''

        logger.debug('Destativando notificacações iguais...')
        colunas = colunas or ['dados__data_da_notificacao', 'dados__nome_completo',
                              'dados__data_de_nascimento']

        qs = Notificacao.objects.filter(ativa=ativa).values('hash_dados')
        qs = qs.annotate(Count('pk')).filter(pk__count__gt=1)

        qs = Notificacao.objects.filter(ativa=ativa, hash_dados__in=Subquery(qs.values('hash_dados')))
        qs = qs.values('pk', 'dados')
        nrepetidas_agrupadas = {}
        for notificacao in qs:
            chaves = []
            for col in colunas:
                chaves.append(notificacao['dados'][col.split('__')[-1]])

            chave = tuple(chaves)
            if nrepetidas_agrupadas.get(chave, None) is None:
                nrepetidas_agrupadas[chave] = set()
            nrepetidas_agrupadas[chave].add(notificacao['pk'])

        quant_notificacoes_desativadas = 0
        for chave, cpks in nrepetidas_agrupadas.items():
            pks = list(cpks)
            notificacao_principal = pks[0]
            for pk_outra_notificacao in pks[1:]:
                if ativa:
                    Notificacao.ativas.filter(pk=pk_outra_notificacao).update(ativa=False,
                                                                                   notificacao_principal=notificacao_principal,
                                                                                   tipo_motivo_desativacao=TipoNotificacaoMotivoCancelamento.NOTIFICACACAO_REPETIDA)
                quant_notificacoes_desativadas += 1
        return quant_notificacoes_desativadas

    def _processar_notificacoes_similares(self):
        '''
        Salva no cache ControleCache.notificacoes_similares() as notificações similares.

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
                  'data_de_nascimento': '1998-05-26T03:00:00.000Z'}]
        }

        Retorna: quantidade de notificações similares.

        :param colunas:
        :return:
        '''
        from notificacoes.processar_notificacoes import ObterNotificacaoEsusveAPI

        logger.debug('Processando notificações similares...')

        ControleCache.notificacoes_similares().reset()

        colunas = ['dados__data_da_notificacao', 'dados__nome_completo',
                   'dados__data_de_nascimento']
        self._desativar_notificacoes_iguais()

        qs = Notificacao.similares.values(*colunas, 'pk', 'numero', 'dados', 'fonte_dados')
        todas_notificacoes = {}

        # O dicionário auxiliar armazena os números das notificações similares.
        # Dicionário onde a chave são os valores relativos as colunas da lista colunas
        # e o valor é uma conjunto de número de notificações.
        repetidas_agrupadas_chave = {}

        # Dicionário auxiliar, criado para poder a partir do número da notificação obter a chave do dicionário repetidas_agrupadas_chave
        # todas_repetidas_chave = {}

        # A iteração abaixo agrupa os números das notificações similares, cuja colunas declarada na variável "colunas" possuem os mesmos valores.
        for notificacao in qs:
            chaves = []
            for col in colunas:
                chaves.append(notificacao['dados'][col.split('__')[-1]])

            chave = tuple(chaves)
            if repetidas_agrupadas_chave.get(chave, None) is None:
                repetidas_agrupadas_chave[chave] = set()
            repetidas_agrupadas_chave[chave].add(notificacao['pk'])
            dados = notificacao['dados']
            dados['pk'] = notificacao['pk']
            dados['numero_da_notificacao'] = notificacao['numero']
            dados['fonte_dados'] = TipoFonteDados.display(notificacao['fonte_dados'])
            for c in ObterNotificacaoEsusveAPI.DESCONSIDERAR_COLUNAS:
                dados.pop(c, None)
            todas_notificacoes[notificacao['pk']] = dados

            ## todas_repetidas_chave[notificacao['pk']] = chave

        # lista contendo uma lista das notificações similares.
        # A lista possuiu uma lista de dicionários com o nome das colunas e seus respectivos valores das notificações similares.
        notificacoes_repetidas_com_diferencas = []

        scol_sivep = set(ObterNotificacaoSivepGripeDBF().PARSE_COLUNAS.values())
        scol_esusve = set(ObterNotificacaoEsusveAPI.PARSE_COLUNAS.values())
        cols_diff = scol_sivep.symmetric_difference(scol_esusve)

        contador = 0
        for chave, pks in repetidas_agrupadas_chave.items():
            contador += 1
            notificacoes_repetidas_diferentes = []
            for pk1 in pks:
                dados1 = todas_notificacoes[pk1]
                for pk2 in pks:
                    dados2 = todas_notificacoes[pk2]
                    if dados1 != dados2:
                        if dados1['fonte_dados'] != dados2['fonte_dados']:
                            for col in cols_diff:
                                dados1.pop(col, None)
                                dados2.pop(col, None)

                        dados_diff = set(dados1.items()) - set(dados2.items())
                        dados_diff.add(('fonte_dados', dados1['fonte_dados']))
                        notificacoes_repetidas_diferentes.append(dados_diff)

                        dados_diff = set(dados2.items()) - set(dados1.items())
                        dados_diff.add(('fonte_dados', dados2['fonte_dados']))
                        notificacoes_repetidas_diferentes.append(dados_diff)

            notificacoes_repetidas_com_diferencas_grupo = []
            if notificacoes_repetidas_diferentes:
                nomes_de_chaves = set()
                for cdados in notificacoes_repetidas_diferentes:
                    for c, v in cdados:
                        nomes_de_chaves.add(c)
                for pk in pks:
                    diffs = {}
                    cdados = todas_notificacoes[pk]
                    for c in nomes_de_chaves:
                        try:
                            diffs[c] = cdados[c]
                        except:
                            diffs[c] = None
                    for col in colunas:
                        c = col.split('__')[-1]
                        diffs[c] = cdados[c]
                    notificacoes_repetidas_com_diferencas_grupo.append(diffs)
                notificacoes_repetidas_com_diferencas.append(notificacoes_repetidas_com_diferencas_grupo)
                ControleCache.notificacoes_similares().add(chave, notificacoes_repetidas_com_diferencas_grupo)

        dados_nomes_chaves = Notificacao.MAPEAMENTO_COLUNAS
        dados_nomes_chaves['numero_da_notificacao'] = 'Número da Notificação'
        dados_nomes_chaves['pk'] = 'Chave interna da Notificação'
        dados_nomes_chaves['fonte_dados'] = 'Fonte de Dados'

        ## dados_retornados = (notificacoes_repetidas_com_diferencas, repetidas_agrupadas_chave, todas_repetidas_chave,
        #                     dados_nomes_chaves)

        # ControleCache.notificacoes_similares().set(dados_retornados)
        ControleCache.notificacoes_similares().set_status(StatusProcessamento.CONCLUIDO)

        quant_notificacoes_similares = len(notificacoes_repetidas_com_diferencas)
        if quant_notificacoes_similares > 0:
            Alerta.ha_notificacoes_similares()

        return quant_notificacoes_similares

    def _processar_notificacoes_alteradas(self, data):
        '''
        data deve está no formato date
        :param data:
        :return:
        '''
        logger.debug('Processando notificações alteradas...')
        def processar_alteracoes(chaves_alteradas, dados_alterados):
            for chave, valores in dados_alterados.items():
                if chaves_alteradas.get(chave, None) is None:
                    chaves_alteradas[chave] = {}
                if chave in Notificacao.CAMPOS_CONTADORES:
                    if chaves_alteradas[chave].get(repr(valores), None) is None:
                        chaves_alteradas[chave][repr(valores)] = 0
                    chaves_alteradas[chave][repr(valores)] += 1
                else:
                    if chaves_alteradas[chave] == {}:
                        chaves_alteradas[chave] = {repr(('valor antigo', 'novo valor')): 0}
                    chaves_alteradas[chave][repr(('valor antigo', 'novo valor'))] += 1

        qs = Notificacao.recuperar_notificacoes_alteradas(data, apenas_com_resultado_alterado=False,
                                                  apenas_dados_originais_do_esusve_alerados=False)

        chaves_alteradas = {}
        for dados_alterados in qs.values_list('dados_alterado', flat=True):
            for chave, valores in dados_alterados.items():
                if isinstance(valores, dict):
                    if chaves_alteradas.get(chave, None) is None:
                        chaves_alteradas[chave] = {}
                    processar_alteracoes(chaves_alteradas[chave], valores)
                else:
                    processar_alteracoes(chaves_alteradas, {chave: valores})

        alteradas = {
            'alteracoes': {
                'quant': qs.count(),
                'chaves_alteradas': chaves_alteradas
            }
        }
        self._cache_status_processamento.add(alteradas)

    def _processar_resumo(self, fonte_dados, hoje=None, total_linhas_arquivo=0, upload_importacao=None):
        logger.debug('Processando resumo, gerando indicadores do processamento...')
        qs_obj = Notificacao.objects.filter(fonte_dados=fonte_dados)
        qs_tivas = Notificacao.ativas.filter(fonte_dados=fonte_dados)

        if hoje is None:
            hoje = timezone.now()

        if upload_importacao is None:
            filename = ''
            qs_upload_importacao = UploadImportacao.objects.filter(datahora__date=hoje).order_by('-datahora')
            if qs_upload_importacao.exists():
                upload_importacao = qs_upload_importacao[0]
                self._cache_status_processamento.set_nome_arquivo(upload_importacao.arquivo.nome)

        quant_notificacoes_desativadas = self._desativar_notificacoes_canceladas()

        quant_notificacoes_similares = self._processar_notificacoes_similares()

        quant_desativadas_total = qs_obj.filter(ativa=False).count()
        qs_processadas_hoje = qs_obj.filter(dados_atualizados_em__date=hoje)
        total_processadas_hoje = qs_processadas_hoje.count()

        desativadas_hoje = {}
        from django.db.models import Count
        for valor in qs_processadas_hoje.filter(tipo_motivo_desativacao__isnull=False).values(
                'tipo_motivo_desativacao').annotate(quant=Count('pk')).order_by():
            for t in TipoNotificacaoMotivoCancelamento.TIPO:
                if t[0] == valor['tipo_motivo_desativacao']:
                    desativadas_hoje[t[1]] = valor['quant']
                    break

        desativadas = {}
        for valor in qs_obj.values('tipo_motivo_desativacao').annotate(quant=Count('pk')).order_by():
            for t in TipoNotificacaoMotivoCancelamento.TIPO:
                if t[0] == valor['tipo_motivo_desativacao']:
                    desativadas[t[1]] = valor['quant']
                    break

        status_detalhe = self._cache_status_processamento.get_status_detalhe()

        dresumo = {
            'arquivo': upload_importacao.arquivo.path if upload_importacao else '',
            'timestamp_inicio': status_detalhe['timestamp_inicio'].strftime('%d/%m/%Y, %H:%M:%S'),
            'timestamp_fim': datetime.now().strftime('%d/%m/%Y, %H:%M:%S'),
            'total_linhas_arquivo': total_linhas_arquivo,
            'total_registradas_e_ou_atualizadas_hoje': total_processadas_hoje,
            'total_desativadas': quant_desativadas_total,
            'total_ativas': qs_tivas.count(),
            'total_similares': quant_notificacoes_similares,
            'desativadas_hoje': desativadas_hoje,
            'desativadas': desativadas,
            'pendecias': {
                'sem bairros associados': qs_tivas.filter(bairro__isnull=True).count(),
                'sem estabelecimentos associados': qs_tivas.filter(estabelecimento_saude__isnull=True).count(),
                'sem número de telefone para contato': qs_tivas.filter(dados__telefone_celular=None).count(),
                'sem CPF': qs_tivas.filter(pessoa__isnull=True).count(),
                'sem CEPs associados': qs_tivas.filter(dados_cep__isnull=True).count(),
            },
        }
        self._cache_status_processamento.add({'importacao': dresumo})

        # Resumo das notificações
        dados_chaves = {}
        for dados_alterados in qs_tivas.values_list('dados', flat=True):
            for chave, valor in dados_alterados.items():
                if dados_chaves.get(chave, None) is None:
                    dados_chaves[chave] = {}
                if chave in Notificacao.CAMPOS_CONTADORES:
                    if dados_chaves.get(chave):
                        if dados_chaves[chave].get(valor, None) is None:
                            dados_chaves[chave][valor] = 0
                        dados_chaves[chave][valor] += 1
                else:
                    if dados_chaves[chave] == {}:
                        dados_chaves[chave] = {'valor': 0}
                    dados_chaves[chave]['valor'] += 1
        self._cache_status_processamento.add({'dados_chaves': dados_chaves})

        qs_obj = qs_tivas.values('bairro').annotate(quant=Count('pk')).values_list('bairro__nome', 'quant')
        self._cache_status_processamento.add({'bairros': list(qs_obj)})

        self._processar_notificacoes_alteradas(hoje)

        try:
            mail_admins(subject='Resumo do processamento da bases esusvem em {}'.format(hoje),
                        message=self.self._cache_status_processamento.get(),
                        fail_silently=False)
        except:
            pass

    def _recuperar_resumo(self):
        return self._cache_status_processamento.get()

    def processar_notificacoes(self, dados):
        ha_alguma_notificacao_alterada = False
        dict_obitos = {}
        hoje = timezone.now()
        contador = 0
        total_notificacoes = len(dados)
        parte_valor_anterior = 0
        for num_notificacao, dados_da_notificacao in dados.items():
            save_data = {}
            contador += 1
            hash_dados = self._get_hash(dados_da_notificacao)

            id_notificacao = (num_notificacao, self._tipo_fonte_dados)

            notificacao_previa = self.cache.notificacoes_ja_processadas.get(id_notificacao, None)

            # Ativa todas as notificações ao reprocessar os dados
            if self.reprocessar and notificacao_previa and notificacao_previa['notificacao_principal_id'] is None:
                save_data['ativa'] = True
                save_data['tipo_motivo_desativacao'] = None

            dados_modificados = self._get_dados_previo_se_alterado(notificacao_previa, dados_da_notificacao,
                                                                   hash_dados)
            try:
                dados_cep = self._tratar_cep(dados_da_notificacao['cep'])
            except Exception as err:
                self._cache_status_processamento.set_status(StatusProcessamento.INTERROMPIDO)
                raise

            try:
                nome_bairro = None
                if dados_da_notificacao['bairro']:
                    nome_bairro = dados_da_notificacao['bairro'].upper().strip()

                bairro, historico_associacao_bairro = self._tratar_bairro(notificacao_previa, nome_bairro, dados_cep)

                # desativa as notificações cuja associação está vinculado a OUTROS
                # e a localidade obtida do CEP pertence a Natal (historico_associacao_bairro it not None)
                # Desativa aquelas que não foi confirmada ainda.
                if historico_associacao_bairro and not historico_associacao_bairro['confirmado']:
                    save_data['ativa'] = False
                    save_data[
                        'tipo_motivo_desativacao'] = TipoNotificacaoMotivoCancelamento.BAIRRO_OUTROS_ONDE_CEP_PERTENCE_CIDADE

                # Desativa as notificações de bairros não pertencente a Natal
                if bairro and bairro['municipio']['pk'] != settings.CODIGO_IBGE_MUNICIPIO_BASE:
                    save_data['ativa'] = False
                    save_data['tipo_motivo_desativacao'] = TipoNotificacaoMotivoCancelamento.BAIRRO_OUTROS

                # Se a associação de bairro mudou de Nulo/OUTROS para um pertecente a cidade base, então ative a notificação
                if notificacao_previa and bairro \
                        and notificacao_previa['bairro_id'] != bairro['pk'] \
                        and bairro['municipio']['pk'] == settings.CODIGO_IBGE_MUNICIPIO_BASE:
                    save_data['ativa'] = True
                    save_data['tipo_motivo_desativacao'] = None

            except Exception as err:
                self._cache_status_processamento.set_status(StatusProcessamento.INTERROMPIDO)
                raise

            estabelecimento_saude = None
            try:
                if dados_da_notificacao.get('co_uni_not'):
                    codigo_cnes = dados_da_notificacao['co_uni_not']
                    estabelecimento_cache = self.cache.cnes.get(codigo_cnes)
                    if estabelecimento_cache:
                        estabelecimento_saude = EstabelecimentoSaude(pk=estabelecimento_cache['pk'],
                                                                    dados_cnes={'NO_RAZAO_SOCIAL': ''})
                else:
                    estabelecimento_saude = self._tratar_dados_operador(dados_da_notificacao)
            except Exception as err:
                self._cache_status_processamento.set_status(StatusProcessamento.INTERROMPIDO)
                raise

            try:
                houve_alteracoes = self._tratar_alteracoes(dados_modificados, notificacao_previa)
                if houve_alteracoes:
                    ha_alguma_notificacao_alterada = True
            except Exception as err:
                self._cache_status_processamento.set_status(StatusProcessamento.INTERROMPIDO)
                raise

            try:
                pessoa = self._tratar_dados_de_pessoa(dados_da_notificacao, dados_modificados)
            except Exception as err:
                self._cache_status_processamento.set_status(StatusProcessamento.INTERROMPIDO)
                raise

            data_da_notificacao = None
            if dados_da_notificacao['data_da_notificacao']:
                data_da_notificacao = to_date(dados_da_notificacao['data_da_notificacao']).date()

            data_da_coleta_do_teste = None
            if dados_da_notificacao['data_da_coleta_do_teste']:
                data_da_coleta_do_teste = to_date(dados_da_notificacao['data_da_coleta_do_teste']).date()

            data_do_inicio_dos_sintomas = None
            if dados_da_notificacao['data_do_inicio_dos_sintomas']:
                data_do_inicio_dos_sintomas = to_date(dados_da_notificacao['data_do_inicio_dos_sintomas']).date()

            data_incidencia = data_do_inicio_dos_sintomas or data_da_coleta_do_teste or data_da_notificacao

            data_de_nascimento = None
            if dados_da_notificacao['data_de_nascimento']:
                data_de_nascimento = to_date(dados_da_notificacao['data_de_nascimento']).date()

            municipio_residencia = None
            try:
                municipio_residencia = self.cache.municipios[
                    (dados_da_notificacao['municipio_de_residencia'].upper().strip(),
                     dados_da_notificacao['estado_de_residencia'].upper().strip())]
            except:
                if dados_da_notificacao['estado_de_residencia'] is None and dados_da_notificacao[
                    'municipio_de_residencia'] and \
                        dados_da_notificacao[
                            'municipio_de_residencia'].upper().strip() == self.cache.municipio_base.nome.upper():
                    municipio_residencia = self.cache.municipios[(
                        dados_da_notificacao['municipio_de_residencia'].upper().strip(),
                        self.cache.municipio_base.estado.nome.upper())]

            municipio_da_notificacao = None
            try:
                municipio_da_notificacao = self.cache.municipios[(
                    dados_da_notificacao['municipio_da_notificacao'].upper().strip(),
                    dados_da_notificacao['estado_da_notificacao'].upper().strip())]
            except:
                if dados_da_notificacao['estado_da_notificacao'] is None and dados_da_notificacao[
                    'municipio_da_notificacao'] and \
                        dados_da_notificacao[
                            'municipio_da_notificacao'].upper().strip() == self.cache.municipio_base.nome.upper():
                    municipio_da_notificacao = self.cache.municipios[
                        (dados_da_notificacao['municipio_da_notificacao'], self.cache.municipio_base.estado.nome)]

            # #Se o município de residência for o município base e o município de notificação for diferente do município de residência,
            # #assume então o município de notificacação como sendo o de residência
            # if (municipio_residencia and dados['municipio_de_residencia'].upper().strip() == self.cache.municipio_base.nome.upper()) \
            #     and (municipio_da_notificacao and municipio_da_notificacao['pk'] != municipio_residencia['pk']):
            #         municipio_da_notificacao = municipio_residencia

            # salvando dados
            save_data.update({
                'pessoa': PessoaFisica(pk=pessoa['pk']) if pessoa else None,
                'estabelecimento_saude': estabelecimento_saude,
                'municipio_residencia': Municipio(pk=municipio_residencia['pk']) if municipio_residencia else None,
                'municipio_ocorrencia': Municipio(
                    pk=municipio_da_notificacao['pk']) if municipio_da_notificacao else Municipio(
                    pk=self.cache.municipio_base.pk),
                'bairro': Bairro(pk=bairro['pk']) if bairro else None,
                'hash_dados': hash_dados,
                'dados': dados_da_notificacao,
                'data': data_da_notificacao,
                'data_da_coleta_do_teste': data_da_coleta_do_teste,
                'data_do_inicio_dos_sintomas': data_do_inicio_dos_sintomas,
                'data_incidencia': data_incidencia,
                'data_de_nascimento': data_de_nascimento,
                'dados_cep': dados_cep if dados_cep != {} else None,
                'dados_atualizados_em': hoje,
                'numero_gal': dados_da_notificacao.get('requi_gal', None),
            })

            # Desativa as notificações onde o município de residêncian é diferente da cidade base
            if dados_da_notificacao['municipio_de_residencia'] and dados_da_notificacao[
                'municipio_de_residencia'].upper().strip() != self.cache.municipio_base.nome.upper():
                save_data['ativa'] = False
                save_data['tipo_motivo_desativacao'] = TipoNotificacaoMotivoCancelamento.MUNICIPIO_RESIDENCIA_EXTERNO

            notificacao_pk = None
            try:
                if notificacao_previa is None:
                    obj, created = Notificacao.objects.get_or_create(
                        numero=num_notificacao, fonte_dados=self._tipo_fonte_dados, defaults=save_data
                    )
                    if data_da_notificacao is None:
                        Alerta.notificacao_com_data_vazia(obj)
                    notificacao_pk = obj.pk

                else:
                    notificacao_pk = notificacao_previa['pk']
                    # verifica se há alterações nos dados salvos no processamento anterior
                    dados_originais = {}
                    novos_dados = {
                        'pessoa_id': pessoa['pk'] if pessoa else None,
                        'estabelecimento_saude_id': estabelecimento_saude.pk if estabelecimento_saude else None,
                        'municipio_residencia_id': municipio_residencia['pk'] if municipio_residencia else None,
                        'municipio_ocorrencia_id': municipio_da_notificacao[
                            'pk'] if municipio_da_notificacao else self.cache.municipio_base.pk,
                        'bairro_id': bairro['pk'] if bairro else None,
                        'ativa': save_data.get('ativa', notificacao_previa['ativa']),
                        'tipo_motivo_desativacao': save_data.get('tipo_motivo_desativacao',
                                                                 notificacao_previa['tipo_motivo_desativacao']),
                        'data_incidencia': save_data.get('data_incidencia', notificacao_previa['data_incidencia']),
                    }
                    for chave in novos_dados.keys():
                        dados_originais[chave] = notificacao_previa[chave]

                    added, removed, dados_alterado, same = dict_compare(dados_originais, novos_dados)
                    if dados_modificados:
                        dados_alterado.update({'dados': dados_modificados})

                    if dados_alterado or notificacao_previa['hash_dados'] != hash_dados:
                        Notificacao.objects.filter(pk=notificacao_previa['pk']).update(**save_data)

                        try:
                            dados_alterado.pop('data_incidencia')
                        except:
                            pass
                        if dados_alterado:
                            obj, created = HistoricoNotificacaoAtualizacao.objects.update_or_create(
                                notificacao=Notificacao(pk=notificacao_previa['pk']),
                                data=hoje,
                                defaults={'dados_alterado': dados_alterado}
                            )
            except Exception as err:
                self._cache_status_processamento.set_status(StatusProcessamento.INTERROMPIDO)
                raise

            dict_obitos.update(self._obter_dados_de_obitos(notificacao_pk, dados_da_notificacao, bairro, pessoa))

            # Registra em cache o percentual a cada 1% de evolução
            try:
                percentual = 0
                percentual = int((contador / total_notificacoes) * 100)

                parte_valor = int((contador / total_notificacoes) * 100)
                if percentual > 0 and parte_valor != parte_valor_anterior:
                    parte_valor_anterior = parte_valor
                    self._cache_status_processamento.set_percentual(
                            round((contador / total_notificacoes) * 100, 2))
            except:
                raise

            msg = 'PROCESSADO      ; {}; {}; {}; {}; {};'.format(contador, num_notificacao,
                                                                 dados_cep['cep'] if dados_cep else '',
                                                                 dados_da_notificacao['bairro'],
                                                                 bairro['nome'] if bairro else '')
            logger.debug(msg)

        Obito.criar_se_nao_exisir(dict_obitos)

        # Desativando as notifificações com municípios de residência fora de Natal
        # qs_fora_de_natal = Notificacao.ativas.exclude(dados__municipio_de_residencia__iexact='Natal')
        # qs_fora_de_natal.update(ativa=False,
        #                         tipo_motivo_desativacao=TipoNotificacaoMotivoCancelamento.MUNICIPIO_RESIDENCIA_EXTERNO)

        # qs_fora_de_natal = Notificacao.objects.filter(numero__in=notificacoes_com_bairros_fora_do_municipio)
        # qs_fora_de_natal.update(ativa=False,
        #                         tipo_motivo_desativacao=TipoNotificacaoMotivoCancelamento.BAIRRO_OUTROS)
        #
        #
        # qs_bairro_outros_cep_localidade_pertece_cidade = Notificacao.objects.filter(numero__in=notificacoes_com_bairros_outro_e_localidade_cep_pertecente_a_cidade)
        # qs_bairro_outros_cep_localidade_pertece_cidade.update(ativa=False,
        #                         tipo_motivo_desativacao=TipoNotificacaoMotivoCancelamento.BAIRRO_OUTROS_ONDE_CEP_PERTENCE_CIDADE)

        # Desativando notificações com nome do notificado vazio
        Notificacao.ativas.filter(dados__nome_completo=None).update(ativa=False,
                                                                    tipo_motivo_desativacao=TipoNotificacaoMotivoCancelamento.NOME_COMPLETO_VAZIO)

        if self._tipo_fonte_dados == TipoFonteDados.ESUSVE:
            Alerta.processamento_base_esusve_concluida()
        else:
            Alerta.processamento_base_sivep_gripe_concluida()

        fonte_de_dados_indicadores_alterados.send(sender=Notificacao)

        if ha_alguma_notificacao_alterada:
            Alerta.ha_notificacao_alterada()

        self._processar_resumo(self._tipo_fonte_dados, hoje, contador, self._upload_importacao)
        dresumo = self._recuperar_resumo()

        dresumo.update({'cache_memoria_utilizada': self.cache.total_memoria_utilizada()})

        # Limpando caches
        self.cache.limpar()

        logger.info(dresumo['importacao'])
        return dresumo

    def _obter_dados_de_obitos(self, num_notificacao, dados_da_notificacao, dbairro, dpessoa):
        raise NotImplementedError()

    def _atualizar_cache_de_filtros(self):
        dados = {
            'classificacao_final': list(Notificacao.objects.distinct('dados__classificacao_final').values_list(
                'dados__classificacao_final', flat=True)),
            'evolucao_caso': list(Notificacao.objects.distinct('dados__evolucao_caso').values_list(
                'dados__evolucao_caso', flat=True)),
            'estado_do_teste': list(Notificacao.objects.distinct('dados__estado_do_teste').values_list(
                'dados__estado_do_teste', flat=True)),
            'resultado_do_teste': list(Notificacao.objects.distinct('dados__resultado_do_teste').values_list(
                'dados__resultado_do_teste', flat=True))
        }
        ControleCache.filtros_de_notificacao().set(dados)

    def processar(self):
        try:
            dados = self._obter_dados()
        except Exception as err:
            self._cache_status_processamento.set_status(StatusProcessamento.INTERROMPIDO)
            raise

        if self._upload_importacao is None:
            sresumo = 'Não há arquivos a serem processados.'
            logger.debug(sresumo)
            return sresumo

        if self._cache_status_processamento.status() == StatusProcessamento.INTERROMPIDO:
            raise Exception('Status processamento consta interrompido.')

        self._cache_status_processamento.reset()

        logger.info('Processando {} notificações...'.format(len(dados)))

        dresumo = self.processar_notificacoes(dados)

        self._cache_status_processamento.set_status(StatusProcessamento.CONCLUIDO)

        self._upload_importacao.processado = True
        self._upload_importacao.dados_do_processamento = dresumo
        self._upload_importacao.save()

        self._cache_status_processamento.clear()
        self._atualizar_cache_de_filtros()

        return dresumo['importacao']


class _ObterNotificacaoEsusve(ObterNotificacao):
    def __init__(self, tipo, reprocessar, qs_upload_importacao):
        self._tipo_fonte_dados = TipoFonteDados.ESUSVE
        super(_ObterNotificacaoEsusve, self).__init__(tipo, reprocessar, qs_upload_importacao)

    @property
    def cache(self):
        if self._cache is None:
            self._cache = ProcessarNotificacaoCache()
            self._cache.processar()
        return self._cache

    def _obter_dados_de_obitos(self, num_notificacao, dados_da_notificacao, dbairro, dpessoa):
        return {}

class ObterNotificacaoEsusveCSV(_ObterNotificacaoEsusve):
    PARSE_COLUNAS = {
        'Bairro': 'bairro',
        'CBO': 'cbo',
        'CEP': 'cep',
        'CNS': 'cns',
        'CPF': 'cpf',
        'Classificação Final': 'classificacao_final',
        'Complemento': 'complemento',
        'Condições- Diabetes': 'diabetes',
        'Condições- Doenças cardíacas crônicas': 'doencas_cardiacas_cronicas',
        'Condições- Doenças renais crônicas em estágio avançado (graus 3, 4 ou 5)': 'doencas_renais_cronicas_em_estagio_avancado_graus_3_4_ou_5',
        'Condições- Doenças respiratórias crônicas descompensadas': 'doencas_respiratorias_cronicas_descompensadas',
        'Condições- Gestante': 'gestante_de_alto_risco',
        'Condições- Imunossupressão': 'imunossupressao',
        'Condições- Portador de doenças cromossômicas ou estado de fragilidade imunológica': 'portador_de_doencas_cromossomicas_ou_estado_de_fragilidade_imunologica',
        'Data da Notificação': 'data_da_notificacao',
        'Data de Nascimento': 'data_de_nascimento',
        'Data de coleta do teste': 'data_da_coleta_do_teste',
        'Data de encerramento': 'data_de_encerramento',
        'Data do início dos sintomas': 'data_do_inicio_dos_sintomas',
        'Descrição do Sintoma': 'descricao_do_sintoma',
        'É profissional de saúde?': 'e_profissional_de_saude',
        'Estado da Notificação': 'estado_da_notificacao',  # Novo
        'Estado de Residência': 'estado_de_residencia',
        'Estado do Teste': 'estado_do_teste',
        'Estrangeiro': 'estrangeiro',
        'Evolução Caso': 'evolucao_caso',
        'Logradouro': 'logradouro',
        'Município da Notificação': 'municipio_da_notificacao',  # Novo
        'Município de Residência': 'municipio_de_residencia',
        'Nome Completo': 'nome_completo',
        'Nome Completo da Mãe': 'nome_completo_da_mae',
        'Notificante CNES': 'operador_cnes',
        'Notificante CNPJ': 'notificante_cnpj',  # Novo
        'Notificante CPF': 'operador_cpf',
        'Notificante Email': 'operador_email',
        'Notificante Nome Completo': 'operador_nome_completo',
        'Número': 'numero_res',
        'Pais de origem': 'pais_de_origem',
        'Passaporte': 'passaporte',
        'Profissional de Segurança': 'profissional_de_seguranca',
        'Raça/Cor': 'raca_cor',
        'Resultado do Teste': 'resultado_do_teste',
        'Sexo': 'sexo',
        'Sintoma- Dispneia': 'dispneia',
        'Sintoma- Dor de Garganta': 'dor_de_garganta',
        'Sintoma- Febre': 'febre',
        'Sintoma- Outros': 'outros',
        'Sintoma- Tosse': 'tosse',
        'Telefone Celular': 'telefone_celular',
        'Telefone de Contato': 'telefone_de_contato',
        'Tem CPF?': 'tem_cpf',
        'Tipo de Teste': 'tipo_de_teste',
        # '': 'tipo_de_teste1', - Removido
        # ': 'resultado_do_teste1', -- Removido
        # '': 'Tipo de Teste.1', -- Removido
        # '': 'estado_do_teste1' - Removido
    }

    def __init__(self, reprocessar=False, qs_upload_importacao=None):
        super().__init__(TipoArquivo.ESUSVE_ARQUIVO_CSV, reprocessar, qs_upload_importacao)

    def _get_hash(self, dados):
        return hashlib.sha224(str(dados).encode()).hexdigest()

    def get_pessoas_fields(self):
        dados = Notificacao.get_pessoas_fields()
        dados.update({
            'bairro_nome': 'bairro',
            'municipio_nome': 'municipio_de_residencia',
            'municipio_ibge': None,
            'uf_nome': 'estado_de_residencia',
            'uf_sigla': None,
            'uf_ibge': None,

        })
        return dados

    def _obter_dados(self):
        if self._upload_importacao is None:
            return None, None
        filename = self._upload_importacao.arquivo.path
        df = None
        try:
            with ZipFile(filename) as myzip:
                with myzip.open(myzip.namelist()[0]) as myfile:
                    df = pd.read_csv(myfile, delimiter=';', index_col='Número da Notificação')
        except BadZipFile:
            pass

        if df is None:
            df = pd.read_csv(filename, delimiter=';', index_col='Número da Notificação')

        df.rename(columns=self.PARSE_COLUNAS, inplace=True)
        colunas = df.columns.to_list()
        # import collections
        # od = collections.OrderedDict(sorted(Notificacao.PARSE_COLUNAS.items()))
        # for k, v in od.items(): print("'{}':'{}',".format(k, v))

        if len(colunas) != 52:
            raise ValueError('Há {} colunas no CSV do ESUSVE, deveria constar 52'.format(len(colunas)))

        try:
            dados = json.loads(df.to_json(orient='index'))
        except ValueError as erro:
            # Caso o erro específico for o de ter "index" repetidos
            if "DataFrame index must be unique for orient='index'." in erro.args:
                import collections
                index_repetidos = [item for item, count in collections.Counter(df.index.array).items() if count > 1]
                df_index = df.index.to_list()
                for index_repetido in index_repetidos:
                    index_lista = df_index.index(index_repetido)
                    df_index[index_lista] = '{:020}'.format(df_index[index_lista])

                df.index = df_index
                df.index = df.index.astype(str)
                dados = json.loads(df.to_json(orient='index'))

        for numero, d in dados.items():
            for k, v in d.items():
                if isinstance(v, float):
                    d[k] = str(int(v))
        return dados


class ObterNotificacaoEsusveAPI(_ObterNotificacaoEsusve):
    COLUNAS_DEFAULT_NONE = ['notificante_cnpj', 'operador_cpf', 'operador_email', 'operador_nome_completo', 'pais_de_origem']

    PARSE_COLUNAS = {
        # Mapeamento da coluna obtidas dos dados da API com as existentes no CSV
        # Isso foi feito para manter o padrão dos dados do CSV
        'cbo': 'cbo',
        'cep': 'cep',
        'cns': 'cns',
        'cpf': 'cpf',
        'sexo': 'sexo',
        'bairro': 'bairro',
        'racaCor': 'raca_cor',
        'logradouro': 'logradouro',
        'passaporte': 'passaporte',
        'complemento': 'complemento',
        'estrangeiro': 'estrangeiro',
        'cnes': 'operador_cnes',
        'evolucaoCaso': 'evolucao_caso',
        'nomeCompleto': 'nome_completo',
        'tipoTeste': 'tipo_de_teste',
        'estadoNotificacao': 'estado_da_notificacao',
        'municipioNotificacao': 'municipio_da_notificacao',
        'profissionalSaude': 'e_profissional_de_saude',
        'telefoneContato': 'telefone_de_contato',
        'dataNotificacao': 'data_da_notificacao',
        'outrosSintomas': 'descricao_do_sintoma',
        'estadoTeste': 'estado_do_teste',
        'classificacaoFinal': 'classificacao_final',
        'nomeMae': 'nome_completo_da_mae',
        'telefone': 'telefone_celular',
        'estado': 'estado_de_residencia',
        'numero': 'numero_res',
        'profissionalSeguranca': 'profissional_de_seguranca',
        'resultadoTeste': 'resultado_do_teste',
        'dataTeste': 'data_da_coleta_do_teste',
        'dataEncerramento': 'data_de_encerramento',
        'dataNascimento': 'data_de_nascimento',
        'municipio': 'municipio_de_residencia',
        'dataInicioSintomas': 'data_do_inicio_dos_sintomas',

        # Colunas existentes apenas nos dados obtidos da API Notifica
        '@timestamp': '@timestamp',
        '_created_at': '_created_at',
        '_p_usuarioAlteracao': '_p_usuarioAlteracao',
        '_p_usuario': '_p_usuario',
        '_updated_at': '_updated_at',
        'descricaoRacaCor': 'descricaoRacaCor',
        'desnormalizarNome': 'desnormalizarNome',
        'nomeCompletoDesnormalizado': 'nomeCompletoDesnormalizado',
        'estadoIBGE': 'estadoIBGE',
        'estadoNotificacaoIBGE': 'estadoNotificacaoIBGE',
        'idade': 'idade',
        'municipioCapital': 'municipioCapital',
        'municipioIBGE': 'codigo_municipio_de_residencia',
        'municipioNotificacaoCapital': 'municipioNotificacaoCapital',
        'municipioNotificacaoIBGE': 'codigo_municipio_da_notificacao',
        'source_id': 'source_id',
        'condicoes': 'condicoes',
        'sintomas': 'sintomas',
        'etnia': 'etnia',
        'idOrigem': 'idOrigem',
        'rpa': 'rpa',

        # colunas existentes no CSV que não constam nos dados obtidos da API Notifica
        # Mantida para manter o padrão dos dados do CSV.
        'notificante_cnpj': 'notificante_cnpj',  # default None
        'operador_cpf': 'operador_cpf',  # default None
        'operador_email': 'operador_email',  # default None
        'operador_nome_completo': 'operador_nome_completo',  # default None
        'pais_de_origem': 'pais_de_origem',  # default Nonew
        'tem_cpf': 'tem_cpf',  # True se há CPF

        # colunas existentes no CSV que não constam nos dados obtidos da API Notifica
        # Excluídas,
        # 'disturbios_olfativos': 'disturbios_olfativos',
        # 'coriza': 'coriza',
        # 'dor_de_cabeca': 'dor_de_cabeca',
        # 'assintomatico': 'assintomatico',
        # 'obesidade': 'obesidade',
        # 'disturbios_gustativos': 'disturbios_gustativos',

        # Colunas criadas a partir da coluna 'sintomas'.
        # Isso foi feito para manter o padrão dos dados do CSV
        # 'dispneia': 'dispneia',
        # 'dor_de_garganta': 'dor_de_garganta',
        # 'febre': 'febre',
        # 'outros': 'outros',
        # 'tosse': 'tosse',
        # 'outros_paciente_assintomatico': 'outros_paciente_assintomatico',

        # Colunas criadas a partir da coluna 'condicoes'.
        # Isso foi feito para manter o padrão dos dados do CSV
        # 'diabetes': 'diabetes',
        # 'doencas_cardiacas_cronicas': 'doencas_cardiacas_cronicas',
        # 'doencas_renais_cronicas_em_estagio_avancado_graus_3_4_ou_5': 'doencas_renais_cronicas_em_estagio_avancado_graus_3_4_ou_5',
        # 'doencas_respiratorias_cronicas_descompensadas': 'doencas_respiratorias_cronicas_descompensadas',
        # 'gestante_de_alto_risco': 'gestante_de_alto_risco',
        # 'gestante': 'gestante',
        # 'imunossupressao': 'imunossupressao',
        # 'portador_de_doencas_cromossomicas_ou_estado_de_fragilidade_imunologica': 'portador_de_doencas_cromossomicas_ou_estado_de_fragilidade_imunologica',

    }
    DESCONSIDERAR_COLUNAS = ['@timestamp', '_created_at', '_p_usuarioAlteracao', '_p_usuario',
                             '_updated_at', 'desnormalizarNome', 'nomeCompletoDesnormalizado', 'idade', 'source_id'
                             ]

    def __init__(self, reprocessar=False, qs_upload_importacao=None):
        super().__init__(TipoArquivo.ESUSVE_API_JSON, reprocessar, qs_upload_importacao)

    def _get_hash(self, dados):
        dados_copy = dados.copy()
        for c in self.DESCONSIDERAR_COLUNAS:
            dados_copy.pop(c)
        return hashlib.sha224(str(dados_copy).encode()).hexdigest()

    def _obter_dados_originais(self):
        user = settings.AUTENTICACAO_API_ESUSVE['USUARIO']
        pwd = settings.AUTENTICACAO_API_ESUSVE['SENHA']

        index = user

        url = 'https://' + user + ':' + pwd + '@elasticsearch-saps.saude.gov.br'

        # https://elasticsearch-saps.saude.gov.br/notificacoes-esusve*/_search?pretty
        logger.debug('Obtendo dados de {}'.format(url))

        es = Elasticsearch([url], send_get_body_as='POST')
        body = {"query": {"match_all": {}}}
        # Apenas município de residência de Natal
        # body = {"match": {
        #     # "municipio": "Natal"
        # }}
        data_ultima_importacao = None
        qs = UploadImportacao.objects.filter(tipo=TipoArquivo.ESUSVE_API_JSON).order_by('-datahora')
        if qs.exists():
            upload_importacao = qs[0]
            data_ultima_importacao =upload_importacao.datahora.strftime('%Y-%m-%dT%H:%M')

        if data_ultima_importacao:
            body = {"query" : {
                        "range": {
                            "@timestamp": {
                                "time_zone": "-03:00",
                                "gte": data_ultima_importacao
                                #"gte": "now"
                            }
                        }
                    }
                }
        results = elasticsearch.helpers.scan(es, query=body, index=index)

        dados_originais = [document['_source'] for document in results]

        dir_media = os.path.join(settings.BASE_DIR, 'media')
        filename_esusve = os.path.join(dir_media,
                                       'esusve-uf_{}.json'.format(datetime.now().strftime("%Y_%m_%d_%H_%M_%S")))
        logger.debug('Salvando dados no arquivo {}'.format(filename_esusve))
        with open(filename_esusve, 'w') as fp:
            json.dump(dados_originais, fp)
            self._upload_importacao = UploadImportacao.objects.create(arquivo=os.path.basename(fp.name),
                                                                      datahora=timezone.now(),
                                                                      tipo=TipoArquivo.ESUSVE_API_JSON)
            self._cache_status_processamento.set_nome_arquivo(self._upload_importacao.arquivo.name)
        return dados_originais

    def _obter_dados(self):
        dados_originais = None
        if self._upload_importacao is None:
            dados_originais = self._obter_dados_originais()
        else:
            filename = self._upload_importacao.arquivo.path
            logger.debug('Obtendo dados do arquivo {}'.format(filename))
            with open(filename, 'r') as f:
                dados_originais = json.loads(f.read())

        df = pd.DataFrame.from_dict(dados_originais)
        df.set_index('numeroNotificacao', inplace=True)

        df.rename(columns=self.PARSE_COLUNAS, inplace=True)

        #tratamento para manter padrão da notificação do ESUS-VE
        for col in self.COLUNAS_DEFAULT_NONE:
            df[col] = None
        df['tem_cpf'] = pd.notna(df['cpf'])
        df['tem_cpf'].replace({True: 'Sim', False: 'Não'}, inplace=True)

        df['data_de_nascimento'] = df['data_de_nascimento'].apply(convert_date).dt.strftime('%Y-%m-%d')
        df['data_da_notificacao'] = df['data_da_notificacao'].apply(convert_date).dt.strftime('%Y-%m-%d')
        df['data_da_coleta_do_teste'] = df['data_da_coleta_do_teste'].apply(convert_date).dt.strftime('%Y-%m-%d')
        df['data_de_encerramento'] = df['data_de_encerramento'].apply(convert_date).dt.strftime('%Y-%m-%d')
        df['data_do_inicio_dos_sintomas'] = df['data_do_inicio_dos_sintomas'].apply(convert_date).dt.strftime('%Y-%m-%d')

        df['municipio_de_residencia'] = df['municipio_de_residencia'].str.upper()
        df['municipio_da_notificacao'] = df['municipio_da_notificacao'].str.upper()

        df['codigo_municipio_da_notificacao'] = df['codigo_municipio_da_notificacao'].str[:-1]
        df['codigo_municipio_de_residencia'] = df['codigo_municipio_de_residencia'].str[:-1]

        #df['data_do_inicio_dos_sintomas'].dt.strftime('%Y-%m-%d')

        #
        # # Convertendo string sintomas em colunas específica para cada doença. A coluna é do tipo string Sim/Não
        # sintomasset = set()
        # for doencas in list(df['sintomas'].unique()):
        #     try:
        #         for doenca_nome in doencas.split(','):
        #             if doenca_nome.strip() != '':
        #                 sintomasset.add(doenca_nome.strip())
        #     except:
        #         pass
        #
        # for doenca_nome in sintomasset:
        #     df[normalize_str(doenca_nome)] = df['sintomas'].str.contains(doenca_nome, na=False)
        #     df[normalize_str(doenca_nome)].replace({True: 'Sim', False: 'Não'}, inplace=True)
        #     # df_api[normalize_str(sintoma)] = df_api['sintomas'].str.extract(pat='({})'.format(sintoma)).isin([sintoma])
        #
        # # Convertendo string condições em colunas específica para cada comorbidade. A coluna é do tipo string Sim/Não
        # comorbidadesset = set()
        # for comorbidades in list(df['condicoes'].unique()):
        #     try:
        #         for comorbidade_nome in comorbidades.split(','):
        #             if comorbidade_nome.strip() != '':
        #                 comorbidadesset.add(comorbidade_nome.strip())
        #     except:
        #         pass
        # comorbidadesset.remove('4 ou 5)')
        # comorbidadesset.remove('Doenças renais crônicas em estágio avançado (graus 3')
        #
        # for comorbidade_nome in comorbidadesset:
        #     df[normalize_str(comorbidade_nome)] = df['condicoes'].str.contains(comorbidade_nome, na=False)
        #     df[normalize_str(comorbidade_nome)].replace({True: 'Sim', False: 'Não'}, inplace=True)
        #
        # comorbidade_nome = 'Doenças renais crônicas em estágio avançado (graus 3, 4 ou 5)'
        # df[normalize_str(comorbidade_nome)] = df['condicoes'].str.contains(comorbidade_nome, na=False)
        # df[normalize_str(comorbidade_nome)].replace({True: 'Sim', False: 'Não'}, inplace=True)
        #
        # # filtrar data frame pela substring
        # # dfe = df_api[df_api['condicoes'].str.contains('Doenças renais crônicas em estágio avançado', na=False)]['condicoes']
        # # df_api[df_api['condicoes'].str.contains('Portador de doenças cromossômicas', na=False)]['condicoes']
        # df.drop('condicoes', axis=1, inplace=True)
        # df.drop('sintomas', axis=1, inplace=True)
        diff = set(df.columns.to_list()) - set(self.PARSE_COLUNAS.values())
        if diff:
            raise ValueError('Houve alterações nas colunas dos dados obtidos da API ESUSVE Notifica: {}'.format(diff))

        df.replace({np.nan: None})
        dados = json.loads(df.to_json(orient='index'))
        return dados


class ObterNotificacaoSivepGripeDBF(ObterNotificacao):
    COLUNAS_DEFAULT_NONE = ['cns', 'passaporte', 'operador_cpf', 'notificante_cnpj', 'operador_cnes', 'operador_email',
                            'telefone_celular', 'e_profissional_de_saude', 'profissional_de_seguranca', 'gestante_de_alto_risco']


    COLUNAS = {
        #Colunas criadas para manter o padrão da notificação ESUS-VE

        #ver pac_cocbo / pac_dscbo
        'cns': {'campo': 'cns', 'descricao': ''},  # Default None
        'passaporte': {'campo': 'passaporte', 'descricao': ''},  # Default None
        'operador_cpf': {'campo': 'operador_cpf', 'descricao': ''},  # Default None
        'notificante_cnpj': {'campo': 'notificante_cnpj', 'descricao': ''},  # Default None
        'operador_cnes': {'campo': 'operador_cnes', 'descricao': ''},  # Default None
        'operador_email': {'campo': 'operador_email', 'descricao': ''},  # Default None
        'telefone_celular': {'campo': 'telefone_celular', 'descricao': ''},  # Default None
        'e_profissional_de_saude': {'campo': 'e_profissional_de_saude', 'descricao': ''},  # Default None
        'profissional_de_seguranca': {'campo': 'profissional_de_seguranca', 'descricao': ''},  # Default None
        'gestante_de_alto_risco': {'campo': 'gestante_de_alto_risco', 'descricao': ''}, # Default None

        'telefone_de_contato': {'campo': 'telefone_de_contato', 'descricao': ''},
        #Unificar as colunas nu_ddd_tel e nu_telefon no formato (nu_ddd_tel) nu_telefon
        # 'nu_ddd_tel': {'campo': 'nu_ddd_tel', 'descricao': ''},
        # 'nu_telefon': {'campo': 'nu_telefon', 'descricao': ''},

        'tem_cpf': {'campo': 'tem_cpf', 'descricao': ''},
        #Regra verificar se existe cpf, se sim, definir tem_cpf para True

        #Colunas adaptadas para o padrão de dados notificação ESUS-VE
        'nu_notific': {'campo': 'nu_notific', 'descricao': ''},
        'nome_prof': {'campo': 'operador_nome_completo', 'descricao': 'Nome completo do profissionalde saúde(sem abreviações) responsávelpela notificação.'},
        'nm_logrado': {'campo': 'logradouro', 'descricao': 'Logradouro(rua, avenida,quadra, travessa, etc.) do endereçode residência do paciente.'},
        'nu_numero': {'campo': 'numero_res', 'descricao': 'No do logradouro (noda casaoudo edifício).'},
        'nm_complem': {'campo': 'complemento', 'descricao': 'Complemento do logradouro(bloco, apto,casa,etc.)'},
        'nm_bairro': {'campo': 'bairro', 'descricao': 'Bairro de residência do paciente.'},
        'nu_cep': {'campo': 'cep', 'descricao': ''},
        'id_pais': {'campo': 'pais_de_origem', 'descricao': ''},
        # Padrão SIVEP Gripe: BRASIL
        # Padrão ESUSVE: Brasil
        # Sempre converter para maiúscula
        'evolucao': {'campo': 'evolucao', 'descricao': ''},
        'evolucao_caso': {'campo': 'evolucao_caso', 'descricao': ''},
        # Padrão SIVEP Gripe:  1-Cura; 2-Óbito; 3- Óbito por outras ca usas 9-Ignorado
        # Padrão ESUSVE: None, '', Cancelado, Cura, Em tratamento domiciliar, Ignorado, Internado, Internado em UTI, Óbito

        'nm_pacient': {'campo': 'nome_completo', 'descricao': ''},
        'cs_sexo': {'campo': 'sexo', 'descricao': ''},
        # Padrão do SEVEP Gripe 1-Masculino 2-Feminino 9-Ignorado
        # Padrão ESUSVE: 'Feminino', Indefinido, Masculino
        'nu_cpf': {'campo': 'cpf', 'descricao': ''},
        'cs_raca': {'campo': 'raca_cor', 'descricao': ''},
        # Padrão SIVEP Gripe: 1-Branca 2-Preta 3-Amarela 4-Parda 5-Indígena 9-Ignorado
        # Padrão ESUSVE: None, '', Amarela, Branca, Ignorado, Indigena, Parda, Preta

        #capos datas, formato armazenado:
        'dt_notific': {'campo': 'data_da_notificacao', 'descricao': 'Data de preenchimentoda ficha de notificação.'},
        'dt_nasc': {'campo': 'data_de_nascimento', 'descricao': 'Data denascimento do paciente.'},
        'dt_coleta': {'campo': 'data_da_coleta_do_teste', 'descricao': 'Data da coleta da amostrapara realizaçãodoteste diagnóstico.'},
        'dt_encerra': {'campo': 'data_de_encerramento', 'descricao': 'Data do encerramento do caso.'},
        'dt_sin_pri': {'campo': 'data_do_inicio_dos_sintomas', 'descricao': 'Data de1o sintomas do caso'},

        'sg_uf_not': {'campo': 'estado_da_notificacao',
                      'descricao': 'UnidadeFederativa onde está localizadaa Unidade Sentinela que realizoua notificação.'},
        'sg_uf': {'campo': 'estado_de_residencia', 'descricao': 'Unidade Federativa de residência do paciente'},
        #Padrão SIVEP Gripe: RN
        #Padrão ESUSVE: Rio Grande do Norte

        'nm_mae_pac': {'campo': 'nome_completo_da_mae', 'descricao': 'Nome completo da mãe do paciente'},
        'id_municip': {'campo': 'municipio_da_notificacao',
                       'descricao': 'Nome do Município onde está localizadaa Unidade Sentinela que realizoua notificação.'},
        'co_mun_not': {'campo': 'codigo_municipio_da_notificacao',
                       'descricao': 'Código IBGE do Município onde está localizadaa Unidade Sentinela que realizoua notificação.'},
        'id_mn_resi': {'campo': 'municipio_de_residencia', 'descricao': 'Nome do município de residênciado paciente'},
        'co_mun_res': {'campo': 'codigo_municipio_de_residencia', 'descricao': 'Código ibge do =município de residênciado paciente'},
        'pac_cocbo': {'campo': 'cbo', 'descricao': 'Ocupação profissionaldo paciente'},

        'criterio': {'campo': 'classificacao_final', 'descricao': 'Indicarqualo critério de confirmação'},
        # Padrão ESUSVE: None, '', Confirmado Clínico-Epidemiológico, Confirmado Laboratorial, Confirmação Laboratorial, Descartado, Síndrome Gripal Não Especificada
        # 73–Critério de Encerramento (criterio): 1. Laboratorial, 2. Clínico Epidemiológico, 3. Clínico, 4. Clínico Imagem


        #Foi feito um algorítmo que relaciona as variáveis: 'amostra', 'tp_tes_an', 'pos_an_out', 'an_sars2', 'ds_an_out', 'pcr_resul', 'pos_pcrout', 'pcr_sars2', 'tp_sor', 'out_sor', 'res_igg', 'res_igm', 'res_iga'
        'estado_do_teste': {'campo': 'estado_do_teste', 'descricao': ''},
        'tipo_de_teste': {'campo': 'tipo_de_teste', 'descricao': ''},
        'resultado_do_teste': {'campo': 'resultado_do_teste', 'descricao': ''},

        'sintomas': {'campo': 'sintomas', 'descricao': ''},
        # Colunas abaixo foram convertidas para a coluna sintomas
        # 'febre': {'campo': 'febre', 'descricao': ''},
        # 'tosse': {'campo': 'tosse', 'descricao': ''},
        # 'garganta': {'campo': 'garganta', 'descricao': ''},
        # 'dispneia': {'campo': 'dispneia', 'descricao': ''},
        # 'desc_resp': {'campo': 'desc_resp', 'descricao': ''},
        # 'saturacao': {'campo': 'saturacao', 'descricao': ''},
        # 'diarreia': {'campo': 'diarreia', 'descricao': ''},
        # 'vomito': {'campo': 'vomito', 'descricao': ''},
        # 'dor_abd': {'campo': 'dor_abd', 'descricao': ''},
        # 'fadiga': {'campo': 'fadiga', 'descricao': ''},
        # 'perd_olft': {'campo': 'perd_olft', 'descricao': ''},
        # 'perd_pala': {'campo': 'perd_pala', 'descricao': ''},
        # 'outro_sin': {'campo': 'outro_sin', 'descricao': ''},
        'outro_des': {'campo': 'descricao_do_sintoma', 'descricao': ''},

        'condicoes': {'campo': 'condicoes', 'descricao': ''},
        # Colunas abaixo foram convertidas para a coluna condicoes
        # 'puerpera': {'campo': 'puerpera', 'descricao': ''},
        # 'cardiopati': {'campo': 'cardiopati', 'descricao': ''},
        # 'hematologi': {'campo': 'hematologi', 'descricao': ''},
        # 'sind_down': {'campo': 'sind_down', 'descricao': ''},
        # 'hepatica': {'campo': 'hepatica', 'descricao': ''},
        # 'asma': {'campo': 'asma', 'descricao': ''},
        # 'diabetes': {'campo': 'diabetes', 'descricao': ''},
        # 'neurologic': {'campo': 'neurologic', 'descricao': ''},
        # 'pneumopati': {'campo': 'pneumopati', 'descricao': ''},
        # 'imunodepre': {'campo': 'imunodepre', 'descricao': ''},
        # 'renal': {'campo': 'renal', 'descricao': ''},
        # 'out_morbi': {'campo': 'out_morbi', 'descricao': ''},
        'morb_desc': {'campo': 'descricao_da_morbidades', 'descricao': ''},


        # Colunas do SIVEP Gripe que não foram mapeadas
        'res_an': {'campo': 'res_an', 'descricao': ''},
        'classi_fin': {'campo': 'classi_fin', 'descricao': ''},
        'dt_res': {'campo': 'dt_res', 'descricao': ''},
        'res_igg': {'campo': 'res_igg', 'descricao': ''},
        'res_igm': {'campo': 'res_igm', 'descricao': ''},
        'res_iga': {'campo': 'res_iga', 'descricao': ''},
        'nu_do': {'campo': 'nu_do', 'descricao': ''},
        'sem_not': {'campo': 'sem_not', 'descricao': ''},
        'sem_pri': {'campo': 'sem_pri', 'descricao': ''},
        'id_regiona': {'campo': 'id_regiona', 'descricao': ''},
        'co_regiona': {'campo': 'co_regiona', 'descricao': ''},
        'id_unidade': {'campo': 'id_unidade', 'descricao': 'Unidade Sentinela que realizouo atendimento, coletadeamostrae registro docaso'},
        'co_uni_not': {'campo': 'co_uni_not', 'descricao': 'Unidade Sentinela que realizouo atendimento, coletadeamostrae registro docaso'},
        'nu_idade_n': {'campo': 'nu_idade_n', 'descricao': ''},
        'tp_idade': {'campo': 'tp_idade', 'descricao': ''},
        'cod_idade': {'campo': 'cod_idade', 'descricao': ''},
        'cs_gestant': {'campo': 'cs_gestant', 'descricao': ''},
        'cs_etinia': {'campo': 'cs_etinia', 'descricao': ''},
        'cs_escol_n': {'campo': 'cs_escol_n', 'descricao': ''},
        'co_pais': {'campo': 'co_pais', 'descricao': ''},
        'id_rg_resi': {'campo': 'id_rg_resi', 'descricao': ''},
        'co_rg_resi': {'campo': 'co_rg_resi', 'descricao': ''},
        'cs_zona': {'campo': 'cs_zona', 'descricao': ''},
        'surto_sg': {'campo': 'surto_sg', 'descricao': ''},
        'nosocomial': {'campo': 'nosocomial', 'descricao': ''},
        'ave_suino': {'campo': 'ave_suino', 'descricao': ''},
        'outro_des': {'campo': 'outro_des', 'descricao': ''},
        'fator_risc': {'campo': 'fator_risc', 'descricao': ''},
        'obesidade': {'campo': 'obesidade', 'descricao': ''},
        'obes_imc': {'campo': 'obes_imc', 'descricao': ''},
        'vacina': {'campo': 'vacina', 'descricao': ''},
        'dt_ut_dose': {'campo': 'dt_ut_dose', 'descricao': ''},
        'mae_vac': {'campo': 'mae_vac', 'descricao': ''},
        'dt_vac_mae': {'campo': 'dt_vac_mae', 'descricao': ''},
        'm_amamenta': {'campo': 'm_amamenta', 'descricao': ''},
        'dt_doseuni': {'campo': 'dt_doseuni', 'descricao': ''},
        'dt_1_dose': {'campo': 'dt_1_dose', 'descricao': ''},
        'dt_2_dose': {'campo': 'dt_2_dose', 'descricao': ''},
        'antiviral': {'campo': 'antiviral', 'descricao': ''},
        'tp_antivir': {'campo': 'tp_antivir', 'descricao': ''},
        'out_antiv': {'campo': 'out_antiv', 'descricao': ''},
        'dt_antivir': {'campo': 'dt_antivir', 'descricao': ''},
        'hospital': {'campo': 'hospital', 'descricao': ''},
        'dt_interna': {'campo': 'dt_interna', 'descricao': 'Data em que o paciente foi hospitalizado.'},
        'sg_uf_inte': {'campo': 'sg_uf_inte', 'descricao': ''},
        'id_rg_inte': {'campo': 'id_rg_inte', 'descricao': ''},
        'co_rg_inte': {'campo': 'co_rg_inte', 'descricao': ''},
        'id_mn_inte': {'campo': 'id_mn_inte', 'descricao': ''},
        'co_mu_inte': {'campo': 'co_mu_inte', 'descricao': ''},
        'nm_un_inte': {'campo': 'nm_un_inte', 'descricao': ''},
        'co_un_inte': {'campo': 'co_un_inte', 'descricao': ''},
        'uti': {'campo': 'uti', 'descricao': ''},
        'dt_entuti': {'campo': 'dt_entuti', 'descricao': ''},
        'dt_saiduti': {'campo': 'dt_saiduti', 'descricao': ''},
        'suport_ven': {'campo': 'suport_ven', 'descricao': ''},
        'raiox_res': {'campo': 'raiox_res', 'descricao': ''},
        'raiox_out': {'campo': 'raiox_out', 'descricao': ''},
        'dt_raiox': {'campo': 'dt_raiox', 'descricao': ''},
        'amostra': {'campo': 'amostra', 'descricao': ''},
        'tp_amostra': {'campo': 'tp_amostra', 'descricao': ''},
        'out_amost': {'campo': 'out_amost', 'descricao': ''},
        'requi_gal': {'campo': 'requi_gal', 'descricao': 'Número da requisiçãode exames o pelo sistema GAL'},
        'pcr_resul': {'campo': 'pcr_resul', 'descricao': ''},
        'dt_pcr': {'campo': 'dt_pcr', 'descricao': ''},
        'pos_pcrflu': {'campo': 'pos_pcrflu', 'descricao': ''},
        'tp_flu_pcr': {'campo': 'tp_flu_pcr', 'descricao': ''},
        'pcr_fluasu': {'campo': 'pcr_fluasu', 'descricao': ''},
        'fluasu_out': {'campo': 'fluasu_out', 'descricao': ''},
        'pcr_flubli': {'campo': 'pcr_flubli', 'descricao': ''},
        'flubli_out': {'campo': 'flubli_out', 'descricao': ''},
        'pos_pcrout': {'campo': 'pos_pcrout', 'descricao': ''},
        'pcr_vsr': {'campo': 'pcr_vsr', 'descricao': ''},
        'pcr_para1': {'campo': 'pcr_para1', 'descricao': ''},
        'pcr_para2': {'campo': 'pcr_para2', 'descricao': ''},
        'pcr_para3': {'campo': 'pcr_para3', 'descricao': ''},
        'pcr_para4': {'campo': 'pcr_para4', 'descricao': ''},
        'pcr_adeno': {'campo': 'pcr_adeno', 'descricao': ''},
        'pcr_metap': {'campo': 'pcr_metap', 'descricao': ''},
        'pcr_boca': {'campo': 'pcr_boca', 'descricao': ''},
        'pcr_rino': {'campo': 'pcr_rino', 'descricao': ''},
        'pcr_outro': {'campo': 'pcr_outro', 'descricao': ''},
        'ds_pcr_out': {'campo': 'ds_pcr_out', 'descricao': ''},
        'lab_pcr': {'campo': 'lab_pcr', 'descricao': ''},
        'co_lab_pcr': {'campo': 'co_lab_pcr', 'descricao': ''},
        'classi_out': {'campo': 'classi_out', 'descricao': ''},
        'dt_evoluca': {'campo': 'dt_evoluca', 'descricao': 'Data da alta ou óbito'},
        'observa': {'campo': 'observa', 'descricao': ''},
        'reg_prof': {'campo': 'reg_prof', 'descricao': ''},
        'dt_digita': {'campo': 'dt_digita', 'descricao': ''},
        'histo_vgm': {'campo': 'histo_vgm', 'descricao': ''},
        'pais_vgm': {'campo': 'pais_vgm', 'descricao': ''},
        'co_ps_vgm': {'campo': 'co_ps_vgm', 'descricao': ''},
        'lo_ps_vgm': {'campo': 'lo_ps_vgm', 'descricao': ''},
        'dt_vgm': {'campo': 'dt_vgm', 'descricao': ''},
        'dt_rt_vgm': {'campo': 'dt_rt_vgm', 'descricao': ''},
        'pcr_sars2': {'campo': 'pcr_sars2', 'descricao': ''},
        'pac_dscbo': {'campo': 'pac_dscbo', 'descricao': ''},
        'out_anim': {'campo': 'out_anim', 'descricao': ''},
        'tomo_res': {'campo': 'tomo_res', 'descricao': ''},
        'tomo_out': {'campo': 'tomo_out', 'descricao': ''},
        'dt_tomo': {'campo': 'dt_tomo', 'descricao': ''},
        'tp_tes_an': {'campo': 'tp_tes_an', 'descricao': ''},
        'dt_res_an': {'campo': 'dt_res_an', 'descricao': ''},
        'lab_an': {'campo': 'lab_an', 'descricao': ''},
        'co_lab_an': {'campo': 'co_lab_an', 'descricao': ''},
        'pos_an_flu': {'campo': 'pos_an_flu', 'descricao': ''},
        'tp_flu_an': {'campo': 'tp_flu_an', 'descricao': ''},
        'pos_an_out': {'campo': 'pos_an_out', 'descricao': ''},
        'an_sars2': {'campo': 'an_sars2', 'descricao': ''},
        'an_vsr': {'campo': 'an_vsr', 'descricao': ''},
        'an_para1': {'campo': 'an_para1', 'descricao': ''},
        'an_para2': {'campo': 'an_para2', 'descricao': ''},
        'an_para3': {'campo': 'an_para3', 'descricao': ''},
        'an_adeno': {'campo': 'an_adeno', 'descricao': ''},
        'an_outro': {'campo': 'an_outro', 'descricao': ''},
        'ds_an_out': {'campo': 'ds_an_out', 'descricao': ''},
        'tp_am_sor': {'campo': 'tp_am_sor', 'descricao': ''},
        'sor_out': {'campo': 'sor_out', 'descricao': ''},
        'dt_co_sor': {'campo': 'dt_co_sor', 'descricao': ''},
        'tp_sor': {'campo': 'tp_sor', 'descricao': ''},
        'out_sor': {'campo': 'out_sor', 'descricao': ''},
    }

    @property
    def PARSE_COLUNAS(self):
        colunas = {}
        for chave, valor in self.COLUNAS.items():
            campo = valor.get('campo', None)
            if not campo:
                campo = chave
            colunas[chave] = campo
        return colunas

    def __init__(self, reprocessar=False, qs_upload_importacao=None):
        super().__init__(TipoArquivo.SIVEP_GRIPE_DBF, reprocessar, qs_upload_importacao)
        self._tipo_fonte_dados = TipoFonteDados.SIVEP_GRIPE

    def _get_hash(self, dados_sivepgripe):
        return hashlib.sha224(str(dados_sivepgripe).encode()).hexdigest()

    def _obter_dados_de_pessoa(self, dados_notificacao):
        dados_de_pessoa = super()._obter_dados_de_pessoa(dados_notificacao)
        dados_de_pessoa['celulares'] = dados_notificacao['telefone_de_contato']
        return dados_de_pessoa

    def _obter_dados(self):
        class _RecordSivepGripe(object):
            def __init__(self, items):
                for (name, value) in items:
                    setattr(self, name, value)

        if self._upload_importacao is None:
            return {}

        filename = self._upload_importacao.arquivo.path

        records = DBF(filename, recfactory=_RecordSivepGripe, lowernames=True, encoding='iso-8859-1')

        dados = {}
        for record in records:
            dados[record.nu_notific] = record.__dict__

        df = pd.DataFrame.from_dict(dados, orient='index', columns=records.field_names)

        df.rename(columns=self.PARSE_COLUNAS, inplace=True)

        #tratamento para manter padrão da notificação do ESUS-VE
        for col in self.COLUNAS_DEFAULT_NONE:
            df[col] = None

        df['telefone_de_contato'] = df[['nu_ddd_tel', 'nu_telefon']].apply(lambda x: '({}) {}'.format(x[0], x[1]), axis=1)
        df.drop('nu_ddd_tel', axis=1, inplace=True)
        df.drop('nu_telefon', axis=1, inplace=True)

        df['tem_cpf'] = pd.notna(df['cpf'])
        df['tem_cpf'].replace({True: 'Sim', False: 'Não'}, inplace=True)

        df['data_de_nascimento'] = df['data_de_nascimento'].apply(convert_date).dt.strftime('%Y-%m-%d')
        df['data_da_notificacao'] = df['data_da_notificacao'].apply(convert_date).dt.strftime('%Y-%m-%d')
        df['data_da_coleta_do_teste'] = df['data_da_coleta_do_teste'].apply(convert_date).dt.strftime('%Y-%m-%d')
        df['data_de_encerramento'] = df['data_de_encerramento'].apply(convert_date).dt.strftime('%Y-%m-%d')
        df['data_do_inicio_dos_sintomas'] = df['data_do_inicio_dos_sintomas'].apply(convert_date).dt.strftime('%Y-%m-%d')

        df['pais_de_origem'] = df['pais_de_origem'].str.upper()

        df['evolucao_caso'] = df['evolucao'].replace(SivepTipoEvolucaoCaso.TIPO)
        df['sexo'].replace(SivepTipoSexo.TIPO, inplace=True)
        df['raca_cor'].replace(SivepTipoRacaCor.TIPO, inplace=True)
        df['classificacao_final'].replace(SivepTipoCriterioEncerramento.TIPO, inplace=True)

        df['municipio_de_residencia'] = df['municipio_de_residencia'].str.upper()
        df['municipio_da_notificacao'] = df['municipio_da_notificacao'].str.upper()

        df['estado_da_notificacao'] = df['estado_da_notificacao'].str.upper()
        df['estado_de_residencia'] = df['estado_de_residencia'].str.upper()
        df['estado_da_notificacao'].replace(self.cache.ufs, inplace=True)
        df['estado_de_residencia'].replace(self.cache.ufs, inplace=True)
        df['estado_da_notificacao'] = df['estado_da_notificacao'].str.upper()
        df['estado_de_residencia'] = df['estado_de_residencia'].str.upper()

        df['tp_tes_an'] = df['tp_tes_an'].astype(int).astype(str)
        df['tp_sor'] = df['tp_sor'].astype(int).astype(str)


        dsintomas = {'febre': 'Febre',
                     'tosse': 'Tosse',
                     'garganta': 'Dor de Garganta',
                     'dispneia': 'Dispneia',
                     'desc_resp': 'Desconforto Respiratório',
                     'saturacao': 'Saturação O2< 95%',
                     'diarreia': 'Diarreia',
                     'vomito': 'Vômito',
                     'dor_abd': 'Dor abdominal',
                     'fadiga': 'Fadiga',
                     'perd_olft': 'Perda do Olfato',
                     'perd_pala': 'Perda do Paladar',
                     'outro_sin': 'Outros'}

        dcondicoes = {'puerpera': 'Puérpera',
                      'cardiopati': 'Doença Cardiovascular Crônica',
                      'hematologi': 'Doença Hematológica Crônica',
                      'sind_down': 'Síndrome de Down',
                      'hepatica': 'Doença Hepática Crônica',
                      'asma': 'Asma',
                      'diabetes': 'Diabetes mellitus',
                      'neurologic': 'Doença Neurológica Crônica',
                      'pneumopati': 'Outra Pneumatopatia Crônica',
                      'imunodepre': 'Imunodeficiência ou Imunodepressão',
                      'renal': 'Doença Renal Crônica',
                      'obesidade': 'Obesidade',
                      'out_morbi': 'Outros'}

        df['sintomas'] = None
        df['condicoes'] = None
        df['tipo_de_teste'] = ''
        df['resultado_do_teste'] = ''
        df['estado_do_teste'] = ''
        for index, row in df.iterrows():
            sintomas = []
            for c, v in dsintomas.items():
                if row[c] == SivepSimNao.SIM:
                    sintomas.append(v)
            df.at[index, 'sintomas'] = ', '.join(sintomas)

            condicoes = []
            for c, v in dcondicoes.items():
                if row[c] == SivepSimNao.SIM:
                    condicoes.append(v)
            df.at[index, 'condicoes'] = ', '.join(condicoes)


            tipo_de_teste = ''
            estado_do_teste = 'Exame Não Solicitado'
            res_test_an = ''
            res_test_pcr = ''
            res_test_sor = ''

            #amostra - 55-Coletou amostra?
            if row['amostra'] == SivepSimNao.SIM:
                estado_do_teste = 'Coletado'

            #tp_tes_an  - 59 - Tipo do Teste antigênico
            #pos_an_out - 63 - Agente etiológico – Teste Antigênico. Positivo para outros vírus?
            #ds_an_out  - 63 - Agente etiológico – Teste Antigênico. Outro vírus respiratório (Descrição)
            #res_an     - 61 - Resultado do Teste Antigênico
            #an_sars2   - 63-Agente etiológico – Teste Antigênico. SARS-CoV-2
            if row['tp_tes_an']: #teste antigênico
                if row['pos_an_out'] == SivepSimNao.SIM \
                        and (row['an_sars2'] == SivepSimNao.SIM\
                        or row['ds_an_out']):
                        estado_do_teste = 'Concluído'
                        res_test_an = 'Positivo'

                        if row['tp_tes_an'] == SivepTipoTesteAntigenico.IMUNOFLUORESCENCIA:
                            tipo_de_teste = 'Imunofluorescência (IF)'
                        elif row['tp_tes_an'] == SivepTipoTesteAntigenico.TESTE_RPAIDO_ANTIGENICO:
                            tipo_de_teste = 'TESTE RÁPIDO - ANTÍGENO'


            #pcr_resul  - 64-Resultado da RT-PCR/outr o método por Biologia Molecular ()
            #pos_pcrout - 66- Agente etiológico – RT-PCR/outro método por Biologia Molecular: Positivo para outros vírus?
            #pcr_sars2  - 66- Agente etiológico – RT-PCR/outro método por Biologia Molecular: SARS-CoV-2
            if row['pcr_resul'] and row['pcr_resul'] != SivepTipoResultadoRTPCROutroMetodo.NAO_REALIZADO: #teste rt-pcr
                    if row['pos_pcrout'] == SivepSimNao.SIM and row['pcr_sars2'] == SivepSimNao.SIM:
                        if row['pcr_resul'] == SivepTipoResultadoRTPCROutroMetodo.DETECTAVEL:
                            res_test_pcr = 'Positivo'
                        elif row['pcr_resul'] == SivepTipoResultadoRTPCROutroMetodo.NAO_DETECTAVEL:
                            res_test_pcr = 'Negativo'
                        elif row['pcr_resul'] == SivepTipoResultadoRTPCROutroMetodo.INCONCLUSIVO:
                            res_test_pcr = 'Inconclusivo ou Indeterminado'
                    if row['pcr_resul'] in (SivepTipoResultadoRTPCROutroMetodo.DETECTAVEL,
                                            SivepTipoResultadoRTPCROutroMetodo.NAO_DETECTAVEL,
                                            SivepTipoResultadoRTPCROutroMetodo.INCONCLUSIVO):
                        estado_do_teste = 'Concluído'
                        if res_test_pcr:
                            tipo_de_teste = 'RT-PCR'

            # tp_sor  - 70- Tipo de Sorologia para SARS-Cov-2
            # res_igg - 70- Resultado do Teste Sorológico para SARS-CoV-2
            # res_igm - 70- Resultado do Teste Sorológico para SARS-CoV-2
            # res_iga - 70- Resultado do Teste Sorológico para SARS-CoV-2
            if row['tp_sor']:  # teste rápido sorológicos
                if row['tp_sor'] == SivepTipoSorologiaSARSCov2.TESTE_RAPIDO:
                    tipo_de_teste = 'TESTE RÁPIDO - ANTICORPO'
                elif row['tp_sor'] == SivepTipoSorologiaSARSCov2.ELISA:
                    tipo_de_teste = 'Enzimaimunoensaio – ELISA'
                elif row['tp_sor'] == SivepTipoSorologiaSARSCov2.QUIMILUMINESCENCIA:
                    tipo_de_teste = 'Eletroquimioluminescência – ECLIA'
                elif row['tp_sor'] == SivepTipoSorologiaSARSCov2.OUTRO:
                    tipo_de_teste = row['out_sor']
                else:  # None
                    pass

                if row['res_igg'] in (SivepTipoResultadoTeste.POSITIVO, SivepTipoResultadoTeste.NEGATIVO,
                                      SivepTipoResultadoTeste.INCONCLUSIVO):
                    estado_do_teste = 'Concluído'
                if row['res_igm'] in (SivepTipoResultadoTeste.POSITIVO, SivepTipoResultadoTeste.NEGATIVO,
                                      SivepTipoResultadoTeste.INCONCLUSIVO):
                    estado_do_teste = 'Concluído'

                if tipo_de_teste:
                    if row['res_igg'] == SivepTipoResultadoTeste.NEGATIVO and row[
                        'res_igm'] == SivepTipoResultadoTeste.NEGATIVO:
                        res_test_sor = 'Negativo'
                        estado_do_teste = 'Concluído'
                    if row['res_igg'] == SivepTipoResultadoTeste.POSITIVO or row[
                        'res_igm'] == SivepTipoResultadoTeste.POSITIVO:
                        res_test_sor = 'Positivo'
                        estado_do_teste = 'Concluído'

            df.at[index, 'tipo_de_teste'] = tipo_de_teste
            df.at[index, 'resultado_do_teste'] = res_test_an or res_test_pcr or res_test_sor
            df.at[index, 'estado_do_teste'] = estado_do_teste

            #Os testes rápidos sorológicos, por imunoensaio enzimático (teste Elisa)
            # e por imunoensaio quimioluminescente (teste Clia)
            # têm o objetivo de detectar anticorpos específicos contra a Covid-19
            # que o nosso organismo produz em resposta à infecção viral

            #testes sorológicos para detecção de anticorpos
            # Enzimaimunoensaio (ELISA)  - baseia numa reação enzimática
            # Quimioluminescência (CLIA) - torna a reação antígeno-anticorpo visível por uma reação química;
            # Eletroquimioluminescência,
            # Imunofluorescência (IFI), - a leitura do resultado é feita a partir da fluorescência formada na reação do antígeno com o anticorpo
            # Imunocromatográfico (testes rápidos),

            #Já o teste molecular, como o RT-PCR, detecta o material genético do vírus, que nesse
            # caso é uma molécula de ácido ribonucleico (RNA) convertida a ácido
            # desoxirribonucleico (DNA) no laboratório,

            # '?': {'campo': 'estado_do_teste', 'descricao': ''},
            # # Padrão ESUSVE:
            # None,
            # '',
            # Coletado,
            # Concluído,
            # Exame Não Solicitado,
            # Solicitado
            # # ver campo Coletou amostra?(AMOSTRA) 1-Sim 2-Não 9-Ignorado

            # '?': {'campo': 'tipo_de_teste', 'descricao': ''},
            # # Padrão ESUSVE:
            # None,
            # Enzimaimunoensaio - ELISA IgM -  Enzimaimunoensaio – ELISA,
            # Enzimaimunoensaio – ELISA,
            # Imunoensaio por Eletroquimioluminescência - ECLIA IgG, ->  Eletroquimioluminescência – ECLIA
            # Imunoensaio por Eletroquimioluminescência – ECLIA,
            # Quimioluminescência - CLIA, OK
            # RT-PCR,
            # TESTE RÁPIDO - ANTICORPO,
            # TESTE RÁPIDO - ANTÍGENO

            # '?': {'campo': 'resultado_do_teste', 'descricao': ''},
            # # Padrão ESUSVE:
            # None,
            # Inconclusivo ou Indeterminado,
            # Negativo,
            # Positivo


        # Códigos utilizados para gerar a planilha que foi enviada para o CIEVS
        # df['tp_tes_an'].replace(SivepTipoTesteAntigenico.TIPO, inplace=True)
        # df['res_an'].replace(SivepTipoResultadoTeste.TIPO, inplace=True)
        # df['tp_sor'].replace(SivepTipoSorologiaSARSCov2.TIPO, inplace=True)
        # df['pcr_resul'].replace(SivepTipoResultadoRTPCROutroMetodo.TIPO, inplace=True)
        # df['pos_pcrout'].replace(SivepSimNao.TIPO, inplace=True)
        # df['pos_an_out'].replace(SivepSimNao.TIPO, inplace=True)
        # df['amostra'].replace(SivepSimNao.TIPO, inplace=True)
        # df['res_igg'].replace(SivepTipoResultadoTeste.TIPO, inplace=True)
        # df['res_igm'].replace(SivepTipoResultadoTeste.TIPO, inplace=True)
        # df['res_iga'].replace(SivepTipoResultadoTeste.TIPO, inplace=True)
        #
        # cols = ['tipo_de_teste', 'resultado_do_teste', 'estado_do_teste', 'amostra', 'tp_tes_an', 'pos_an_out', 'an_sars2', 'ds_an_out', 'pcr_resul', 'pos_pcrout', 'pcr_sars2', 'tp_sor', 'out_sor', 'res_igg', 'res_igm', 'res_iga']
        # df1 = df[cols].agg('; '.join, axis=1)
        # print(';'.join(cols))
        # for c in df1.unique():
        #     print(c)
        # breakpoint()

        for c in dsintomas.keys():
            df.drop(c, axis=1, inplace=True)

        for c in dcondicoes.keys():
            df.drop(c, axis=1, inplace=True)

        df['tipo_de_teste'].replace({'RT/PCR': 'RT-PCR',
                                     'RT -PCR':'RT-PCR',
                                     'IMUNOENSAIO FLUORESCENTE':'Imunofluorescência (IF)',
                                     'FIA':'Imunofluorescência (IF)'}, inplace=True)

        diff = set(df.columns.to_list()) - set(self.PARSE_COLUNAS.values())
        if diff:
            raise ValueError('Houve alterações nas colunas dos dados obtidos do CSV do SIVEP Gripe: {}'.format(diff))

        df.replace({np.nan: None})

        try:
            dados = json.loads(df.to_json(orient='index'))
        except ValueError as erro:
            # Caso o erro específico for o de ter "index" repetidos
            if "DataFrame index must be unique for orient='index'." in erro.args:
                import collections
                index_repetidos = [item for item, count in collections.Counter(df.index.array).items() if count > 1]
                df_index = df.index.to_list()
                for index_repetido in index_repetidos:
                    index_lista = df_index.index(index_repetido)
                    df_index[index_lista] = '{:020}'.format(df_index[index_lista])

                df.index = df_index
                df.index = df.index.astype(str)
                dados = json.loads(df.to_json(orient='index'))

        for numero, d in dados.items():
            for k, v in d.items():
                if isinstance(v, float):
                    d[k] = str(int(v))
        return dados

    def _obter_dados_de_obitos(self, notificacao_pk, dados_da_notificacao, dbairro, dpessoa):
        classificacao_final = 'Confirmado' if dados_da_notificacao['classi_fin'] == SivepTipoClassificacaoFinalCaso.SRAG_POR_COVID19 else 'Descartado'
        data_do_obito = to_date(dados_da_notificacao['dt_evoluca']) #datetime.strptime(dados_da_notificacao['dt_evoluca'], '%d/%m/%Y').date() if len(dados_da_notificacao['dt_evoluca']) > 5 else None

        if dados_da_notificacao['evolucao'] == SivepTipoEvolucaoCaso.OBITO \
                and dados_da_notificacao['codigo_municipio_de_residencia'] == settings.CODIGO_IBGE_MUNICIPIO_BASE \
                and dados_da_notificacao['classi_fin'] == SivepTipoClassificacaoFinalCaso.SRAG_POR_COVID19:
            return {
                notificacao_pk: {
                            'numero_declaracao_obito': dados_da_notificacao['nu_do'],
                            'local_do_obito': dados_da_notificacao['co_uni_not'],
                            'data_do_obito': data_do_obito,
                            'resultado_do_teste_covid_19': classificacao_final,
                            'bairro': Bairro(pk=dbairro['pk']) if dbairro else None,
                            'pessoa': PessoaFisica(pk=dpessoa['pk']) if dpessoa else None
                            }
                }
        return {}
