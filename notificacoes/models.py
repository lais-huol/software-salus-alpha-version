import difflib
import hashlib
import json
import logging
import os
import re
from datetime import datetime, date
from zipfile import BadZipFile, ZipFile

import elasticsearch
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import mail_admins
from django.core.validators import FileExtensionValidator
from django.db import models
from django.db.models import Count, Subquery, FloatField, Q, DateField
from django.db.transaction import atomic
from django.urls import reverse
from django.utils import timezone
import pandas as pd
from elasticsearch import Elasticsearch

from base import rest_localizasus
from base.alertas import Alerta
from base.caches import ControleCache, StatusProcessamento
from base.extracao.rest_laiscep import recuperar_ceps
from base.extracao.rest_leitos_imd import get_leitos_lista_geral
from base.extracao.rest_regularn import get_solicitacoes
from base.models import AssociacaoBairro, HabitacoesBairro, Bairro, Usuario, PerfilEstabelecimentoSaude, \
    AssociacaoNomeEstabelecimentoSaude, PessoaFisica, EstabelecimentoSaude, AssociacaoOperadorCNES, Municipio
from base.models import AssociacaoBairro, HabitacoesBairro, Bairro, Usuario, PerfilEstabelecimentoSaude, \
    AssociacaoNomeEstabelecimentoSaude, PessoaFisica, EstabelecimentoSaude, AssociacaoOperadorCNES, PerfilDistrito
from base.signals import fonte_de_dados_indicadores_alterados
from base.utils import normalize_keys, dict_compare, calculateAge, elapsed_time, run_async, \
    users_with_perm, to_date, ToDate, normalize_str, digits, levenshtein_distance, get_size
from .managers import NotificacoesAtivasManager, NotificacoesPendentesManager, NotificacoesAlteradasManager, \
    NotificacoesSimilaresManager, MonitoramentosAtivosManager

logger = logging.getLogger(__name__)


@run_async
def enviar_email_progresso(percentual, nome_function):
    try:
        assunto = 'Função {} - progresso {}%'.format(nome_function, percentual)
        mail_admins(subject=assunto,
                    message='',
                    fail_silently=False)
    except:
        raise

class TipoDisplay():
    @classmethod
    def display(cls, valor):
        tipo = {x: y for x, y in cls.__dict__['TIPO']}
        return tipo[valor]


class TipoArquivo(TipoDisplay):
    ESUSVE_ARQUIVO_CSV = 0
    ESUSVE_API_JSON = 1
    SIVEP_GRIPE_DBF = 2
    SIVEP_GRIPE_API_JSON = 3
    TIPO = [[ESUSVE_ARQUIVO_CSV, 'ESUS-VE NOTIFICA CSV'],
            [ESUSVE_API_JSON, 'ESUS-VE NOTIFICA API'],
            [SIVEP_GRIPE_DBF, 'SIVEP GRIPE DBF'],
            [SIVEP_GRIPE_API_JSON, 'SIVEP GRIPE API'],
            ]


class TipoNotificacaoMotivoCancelamento(TipoDisplay):
    MUNICIPIO_RESIDENCIA_EXTERNO = 1
    EVOLUCAO_CASO_CANCELADA = 2
    OUTROS = 3
    NOTIFICACACAO_REPETIDA = 4
    NOTIFICACAO_SIMILAR = 5
    BAIRRO_OUTROS = 6
    BAIRRO_OUTROS_ONDE_CEP_PERTENCE_CIDADE = 7
    NOME_COMPLETO_VAZIO = 8

    TIPO = [
        [MUNICIPIO_RESIDENCIA_EXTERNO, 'Município de residência externo'],
        [EVOLUCAO_CASO_CANCELADA, 'Evolução do caso igual a cancelado'],
        [OUTROS, 'motivo desconhecido'],
        [NOME_COMPLETO_VAZIO, 'Nome completo vazio'],
        [NOTIFICACACAO_REPETIDA, 'Notificação repetida'],
        [NOTIFICACAO_SIMILAR, 'Notificação similar'],
        [BAIRRO_OUTROS, 'Bairro outros'],
        [BAIRRO_OUTROS_ONDE_CEP_PERTENCE_CIDADE,
         'Associações de bairro pertecente a outros, mas localidade obtida do CEP pertence a cidade']
    ]

class TipoMotivoEncerramento(TipoDisplay):
    CURA = 1
    OBITO = 2

    TIPO = [
        [CURA, 'Cura'],
        [OBITO, 'Óbito']
    ]

class TipoFonteDados(TipoDisplay):
    ESUSVE = 0
    SIVEP_GRIPE = 1
    TIPO = [[ESUSVE, 'ESUS-VE NOTIFICA'],
            [SIVEP_GRIPE, 'SIVEP GRIPE'],
            ]


class UploadImportacao(models.Model):
    STATUS_PROCESSAMENTO_CONCLUIDO = 1
    STATUS_PROCESSAMENTO_EM_EXECUCAO = 2
    STATUS_PROCESSAMENTO_NAO_INICIALIZADO = 3
    STATUS_PROCESSAMENTO_FALHA = 4

    arquivo = models.FileField()
    usuario = models.ForeignKey('base.Usuario', on_delete=models.CASCADE, null=True)
    datahora = models.DateTimeField(auto_now_add=True)
    processado = models.BooleanField(default=False)
    dados_do_processamento = JSONField(null=True, blank=True)
    tipo = models.PositiveIntegerField(choices=TipoArquivo.TIPO, default=TipoArquivo.ESUSVE_ARQUIVO_CSV)

    @property
    def status_processamento(self):
        cache_processar_notificacoes = ControleCache.processamento_notificacoes(self)
        if self.processado:
            return self.STATUS_PROCESSAMENTO_CONCLUIDO
        else:
            if cache_processar_notificacoes.status() == StatusProcessamento.INICIALIZADO:
                return self.STATUS_PROCESSAMENTO_EM_EXECUCAO
            elif cache_processar_notificacoes.status() == StatusProcessamento.INTERROMPIDO:
                return self.STATUS_PROCESSAMENTO_FALHA
        return self.STATUS_PROCESSAMENTO_NAO_INICIALIZADO

    @property
    def status_processamento_display(self):
        cache_processar_notificacoes = ControleCache.processamento_notificacoes(self)
        if self.status_processamento == self.STATUS_PROCESSAMENTO_CONCLUIDO:
            return 'Concluído'
        else:
            if self.status_processamento == self.STATUS_PROCESSAMENTO_EM_EXECUCAO:
                status_detalhe = cache_processar_notificacoes.get_status_detalhe()
                str = ''' Em Processamento...
                Iniciado em {}
                Percentual de Execução: {}%                
                '''.format(status_detalhe['timestamp_inicio'].strftime('%d/%m/%Y, %H:%M:%S'),
                           status_detalhe['percentual_execucao'])
                return str
            elif self.status_processamento == self.STATUS_PROCESSAMENTO_FALHA:
                return 'Falha no processamento'
        return 'Não Inicializado'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        ControleCache.processamento_notificacoes(self).reset()


    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        ControleCache.processamento_notificacoes(self).reset()



# https://datasus.saude.gov.br/wp-content/uploads/2020/04/Ficha-COVID-19-09_04.pdf
class Notificacao(models.Model):
    numero = models.CharField(verbose_name='número da notificação', max_length=20)
    dados = JSONField()
    fonte_dados = models.PositiveIntegerField(choices=TipoFonteDados.TIPO, default=TipoFonteDados.ESUSVE)
    dados_alterado = JSONField(null=True, default=None)
    hash_dados = models.CharField(verbose_name='Hash dados esusve', max_length=56, db_index=True)
    dados_atualizados_em = models.DateTimeField(null=True)

    data = models.DateField('Data da Notificação', null=True)  # data_da_notificacao
    data_incidencia = models.DateField(verbose_name="Data de incidência",
                                       null=True)  # data_da_coleta_do_teste ou data_do_inicio_dos_sintomas ou data_da_notificacao
    data_da_coleta_do_teste = models.DateField(verbose_name="Data da coleta do teste", null=True)
    data_do_inicio_dos_sintomas = models.DateField(verbose_name="Data do início dos sintomas", null=True)
    data_de_nascimento = models.DateField(verbose_name="Data de nascimento", null=True)

    numero_gal = models.CharField(verbose_name='requisição do GAL', max_length=12, null=True)
    bairro = models.ForeignKey('base.Bairro', on_delete=models.SET_NULL, null=True)
    estabelecimento_saude = models.ForeignKey(
        to='base.EstabelecimentoSaude',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Estabelecimento de Saúde do cadastro')
    estabelecimento_saude_referencia = models.ForeignKey(
        to='base.EstabelecimentoSaude',
        on_delete=models.SET_NULL,
        null=True,
        related_name='notificacaoreferencia_set',
        verbose_name='Estabelecimento de Saúde de referência')
    paciente_internado = models.ForeignKey('PacienteInternacao', on_delete=models.SET_NULL, null=True)
    pessoa = models.ForeignKey(PessoaFisica, on_delete=models.SET_NULL, null=True)

    notificacao_principal = models.ForeignKey('Notificacao', on_delete=models.SET_NULL, null=True)
    ativa = models.BooleanField(default=True)

    dados_cep = JSONField(null=True)
    dados_cep_atualizados_em = models.DateTimeField(null=True)

    longitude = FloatField(null=True)
    latitude = FloatField(null=True)
    coordenadas_atualizadas_em = models.DateTimeField(null=True)

    tipo_motivo_desativacao = models.PositiveIntegerField(
        choices=TipoNotificacaoMotivoCancelamento.TIPO, null=True)
    municipio_residencia = models.ForeignKey(
        to='base.Municipio',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Município de residência',
        related_name='municipio_residencia')
    municipio_ocorrencia = models.ForeignKey(
        to='base.Municipio',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Município de ocorrência da Notificação',
        related_name='municipio_ocorrencia'
    )

    # Encerramento de caso
    encerrada_motivo = models.PositiveIntegerField("Motivo do Encerramento",
                                                   choices=TipoMotivoEncerramento.TIPO, null=True)
    encerrada_observacoes = models.TextField("Observações do Encerramento", null=True)
    data_do_encerramento = models.DateField('Data do Encerramento', null=True)
    encerrada_por = models.ForeignKey(Usuario, verbose_name='Encerrado por', null=True, on_delete=models.PROTECT)
    encerrada_em = models.DateTimeField("Encerrada em", null=True)

    objects = models.Manager()
    ativas = NotificacoesAtivasManager()
    similares = NotificacoesSimilaresManager()
    pendentes = NotificacoesPendentesManager()
    alteradas = NotificacoesAlteradasManager()

    class Meta:
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
        permissions = [
            ('pode_definir_notificacoes_principais', 'Pode definir notificações principais'),
            ('pode_associar_bairros', 'Pode associar bairros'),
            ('pode_importar_notificacoes', 'Pode importar notificações'),
            ('pode_importar_pacientes', 'Pode importar pacientes'),
            ('pode_associar_pacientes', 'Pode associar pacientes'),
            ('pode_associar_operadores', 'Pode associar operadores'),
            ('pode_associar_estabelecimentos', 'Pode associar estabelecimentos'),
            ('pode_ver_todas_as_notificacoes', 'Pode ver todas as notificações'),
            ('pode_alterar_o_gal', 'Pode alterar o GAL')
        ]

    CATEGORIAS_CAMPOS = {
        'Identificação': [
            'nome_completo', 'data_de_nascimento', 'sexo', 'tem_cpf', 'cpf', 'nome_completo_da_mae', 'telefone_celular',
            'telefone_de_contato', 'raca_cor', 'passaporte', 'logradouro', 'numero_res',
            'complemento', 'bairro', 'municipio_de_residencia', 'estado_de_residencia', 'cep', 'estrangeiro',
            'pais_de_origem', 'e_profissional_de_saude', 'profissional_de_seguranca', 'cbo', 'cns'
        ],
        'Notificação': [
            'data_da_notificacao', 'estado_do_teste', 'data_da_coleta_do_teste', 'tipo_de_teste', 'resultado_do_teste',
            'evolucao_caso', 'classificacao_final'  # 'tipo_de_teste1','resultado_do_teste1', 'estado_do_teste1',
        ],
        # NOTA: comentamos "Sintomas" e "Morbidades" porque agora são abas com comportamento específico no template
        # 'Sintomas': [
        #     'data_do_inicio_dos_sintomas', 'descricao_do_sintoma', 'dispneia',
        #     'dor_de_garganta', 'febre',
        #     'imunossupressao', 'tosse', 'outros'
        # ],
        # 'Morbidades': [
        #     'diabetes', 'doencas_cardiacas_cronicas', 'doencas_renais_cronicas_em_estagio_avancado_graus_3_4_ou_5',
        #     'portador_de_doencas_cromossomicas_ou_estado_de_fragilidade_imunologica', 'gestante_de_alto_risco',
        #     'doencas_respiratorias_cronicas_descompensadas',
        # ],
        'Operador': [
            'operador_cpf', 'operador_cnes', 'operador_email', 'operador_nome_completo', 'notificante_cnpj'
        ]
    }

    MAPEAMENTO_COLUNAS = {
        'cbo': 'CBO',
        'cep': 'CEP',
        'cns': 'CNS',
        'cpf': 'CPF',
        'sexo': 'Sexo',
        'febre': 'Febre',
        'tosse': 'Tosse',
        'bairro': 'Bairro',
        'outros': 'Outros',
        'tem_cpf': 'Tem CPF?',
        'diabetes': 'Diabetes',
        'dispneia': 'Dispneia',
        'raca_cor': 'Raça/Cor',
        'logradouro': 'Logradouro',
        'passaporte': 'Passaporte',
        'complemento': 'Complemento',
        'estrangeiro': 'Estrangeiro',
        'operador_cpf': 'CPF do Operador',
        'notificante_cnpj': 'Notificante CNPJ',
        'evolucao_caso': 'Evolução do Caso',
        'nome_completo': 'Nome Completo',
        'operador_cnes': 'CNES do Operador',
        'tipo_de_teste': 'Tipo de Teste',
        'operador_email': 'E-mail do Operador',
        'pais_de_origem': 'Pais de origem',
        # 'tipo_de_teste1': 'Tipo de Teste.1',
        'dor_de_garganta': 'Dor de Garganta',
        'estado_do_teste': 'Estado do Teste',
        'imunossupressao': 'Imunossupressão',
        # 'estado_do_teste1': 'Estado do Teste.1',
        'telefone_celular': 'Telefone Celular',
        'data_de_nascimento': 'Data de Nascimento',
        'resultado_do_teste': 'Resultado do Teste',
        'classificacao_final': 'Classificação Final',
        'data_da_notificacao': 'Data da Notificação',
        # 'resultado_do_teste1': 'Resultado do Teste.1',
        'telefone_de_contato': 'Telefone de Contato',
        'data_de_encerramento': 'Data de encerramento',
        'descricao_do_sintoma': 'Descrição do Sintoma',
        'estado_de_residencia': 'Estado de Residência',
        'estado_da_notificacao': 'Estado da Notificação',
        'nome_completo_da_mae': 'Nome Completo da Mãe',
        'gestante_de_alto_risco': 'Gestante de alto risco',
        'operador_nome_completo': 'Nome Completo do Operador',
        'data_da_coleta_do_teste': 'Data da Coleta do Teste',
        'e_profissional_de_saude': 'É profissional de saúde?',
        'municipio_de_residencia': 'Município de Residência',
        'municipio_da_notificacao': 'Município da Notificacao',
        'profissional_de_seguranca': 'Profissional de Segurança',
        'doencas_cardiacas_cronicas': 'Doenças cardíacas crônicas',
        'data_do_inicio_dos_sintomas': 'Data do início dos sintomas',
        'numero_res': 'Número',
        'doencas_respiratorias_cronicas_descompensadas': 'Doenças respiratórias crônicas descompensadas',
        'doencas_renais_cronicas_em_estagio_avancado_graus_3_4_ou_5': 'Doenças renais crônicas em estágio avançado (graus 3, 4 ou 5)',
        'portador_de_doencas_cromossomicas_ou_estado_de_fragilidade_imunologica': 'Portador de doenças cromossômicas ou estado de fragilidade imunológica',
    }

    CAMPOS_CONTADORES = ['ativa', 'tipo_motivo_desativacao', 'evolucao_caso', 'tipo_de_teste', 'estado_do_teste',
                         'resultado_do_teste', 'classificacao_final', 'tem_cpf', 'diabetes',
                         'dispneia', 'raca_cor', 'febre', 'tosse', 'outros', 'dor_de_garganta', 'sexo', 'estrangeiro',
                         'doencas_respiratorias_cronicas_descompensadas',
                         'doencas_renais_cronicas_em_estagio_avancado_graus_3_4_ou_5',
                         'portador_de_doencas_cromossomicas_ou_estado_de_fragilidade_imunologica', 'imunossupressao',
                         'doencas_cardiacas_cronicas', 'gestante_de_alto_risco', 'e_profissional_de_saude', 'cbo',
                         'etinia']

    def get_absolute_url(self):
        return reverse('notificacoes:visualizar', args=[self.pk])

    def __str__(self):
        return f'Notificação {self.numero} - ' \
               f'{self.dados["nome_completo"]} ' \
               f'{self.dados["data_de_nascimento"]} ' \
               f'{self.dados["cpf"]} ' \
               f'{self.dados["resultado_do_teste"]}'

    @classmethod
    def get_pessoas_fields(cls):
        return {
            'cpf': 'cpf',
            'nome': 'nome_completo',
            'cns': 'cns',
            'sexo': 'sexo',
            'data_de_nascimento': 'data_de_nascimento',
            'telefones': 'telefone_de_contato',
            'celulares': 'telefone_celular',
            'email': 'email',
            'cep': 'cep',
            'logradouro': 'logradouro',
            'numero': 'numero_res',
            'complemento': 'complemento',
            'bairro': 'bairro',
            'municipio_id': 'municipioIBGE',
            'nome_da_mae': 'nome_completo_da_mae',
        }

    def get_dados_pessoa(self):
        dados_notificacao = self.dados
        dados_pessoais = {}
        for field_pessoa, field_notificacao in Notificacao.get_pessoas_fields().items():
            try:
                dados_pessoais[field_pessoa] = dados_notificacao[field_notificacao]
            except:
                dados_pessoais[field_pessoa] = None
        return dados_pessoais

    def get_associacao_bairro(self):
        # TODO: Jailton, em algum momento a notificação deixou de ser associada ao bairro?
        return '{} -> {}'.format(self.dados['bairro'], self.bairro) #.nome)

    def get_endereco_completo(self, usar_bairro_original=True):
        if self.dados.get('logradouro'):
            if not usar_bairro_original and self.bairro and self.bairro.nome != settings.BAIRRO_OUTROS:
                bairro_str = self.bairro.nome
            elif self.dados.get('bairro'):
                bairro_str = self.dados['bairro']
            else:
                return ''
            values = [
                self.dados['logradouro'],
                self.dados.get('numero_res') or '',
                bairro_str,
                self.dados['municipio_de_residencia'],
                self.dados['estado_de_residencia'],
            ]
            return ', '.join([value for value in values if value])
        else:
            return ''

    def get_sintomas_as_list(self):
        val = (self.dados.get('sintomas', '') or '').strip()
        values = [v.strip() for v in val.split(',')]
        return [v for v in values if v]

    def get_morbidades_as_list(self):
        val = (self.dados.get('condicoes', '') or '').strip()
        values = [v.strip() for v in val.split(',')]
        return [v for v in values if v]

    @staticmethod
    def validar_se_pode_criar_obito_para_pessoa(pessoa):
        notificacoes_deste_cpf = Notificacao.objects.filter(pessoa=pessoa, ativa=True)
        if notificacoes_deste_cpf.exists() and \
                not notificacoes_deste_cpf.filter(encerrada_motivo=TipoMotivoEncerramento.OBITO).exists():
            raise ValidationError(
                f'Existe notificação em aberto para o CPF {pessoa.cpf}. Por favor, encerre-a para registrar o óbito.')
        if Obito.objects.filter(pessoa=pessoa).exists():
            raise ValidationError(f'Existe óbito registrado para o CPF {pessoa.cpf}.')
        return True

    def pode_registrar_obito(self):
        return self.encerrada_motivo == TipoMotivoEncerramento.OBITO and \
               not Obito.objects.filter(pessoa=self.pessoa).exists()

    @classmethod
    def definir_cnes_referencia(cls):
        total_atualizacoes = 0

        cache_cnes = {}
        for codigo in EstabelecimentoSaude.objects.values_list('codigo_cnes', flat=True):
            cache_cnes[codigo] = codigo
            cache_cnes[codigo.zfill(7)] = codigo  # NOTA TODO: armazenado no banco local registros sem zeros à esquerda

        for obj in cls.ativas.filter(estabelecimento_saude_referencia__isnull=True,
                                     coordenadas_atualizadas_em__isnull=True).select_related('bairro'):
            ref = rest_localizasus.get_estabelecimento_referencia(
                lat=obj.latitude, lng=obj.longitude,
                endereco_completo=obj.get_endereco_completo(usar_bairro_original=False)
            )
            if not ref:
                continue
            cls.objects.filter(pk=obj.pk).update(coordenadas_atualizadas_em=timezone.now())
            codigo_cnes_localizasus = ref['estabelecimento']['codigo_cnes']
            if codigo_cnes_localizasus in cache_cnes:
                update_kw = dict(estabelecimento_saude_referencia_id=cache_cnes[codigo_cnes_localizasus])
                if not obj.latitude:
                    update_kw['latitude'] = ref['origem']['lat']
                    update_kw['longitude'] = ref['origem']['lng']
                cls.objects.filter(pk=obj.pk).update(**update_kw)
                total_atualizacoes += 1

        return total_atualizacoes

    @staticmethod
    def definir_pessoa(api_sleep_time=0):
        total_atualizacoes = 0
        for notificacao in Notificacao.objects.filter(pessoa__isnull=True):
            cpf_ou_cns = notificacao.dados['cpf'] or notificacao.dados['cns']
            if not cpf_ou_cns:
                continue
            pessoa = PessoaFisica.get_or_create_by_cpf_ou_cnes(cpf_ou_cns=cpf_ou_cns,
                                                               api_sleep_time=api_sleep_time)
            if not pessoa:
                continue
            Notificacao.objects.filter(pk=notificacao.pk).update(pessoa=pessoa)
            total_atualizacoes += 1
        return total_atualizacoes

    def get_morbidades_display(self):
        return ', '.join(self.get_morbidades_as_list())

    def get_dados_pessoais_modificados_no_monitoramento(self):
        '''
        Retorna uma lista de tuplas, one o 1o item da tupla é a o nome do campo que teve alteração e o 2o o valor correspondente.
        Ex: [('telefone_celular', '8499999999'), ('nome_completo', 'José da Silva')]
        :return:
        '''
        if not self.pessoa:
            return None
        ch = PessoaFisica.FIELDS
        chave_dados_pessoais = [*ch.keys()]
        esusve_dados_pessoais = {}
        for k, v in self.dados.items():
            if k in chave_dados_pessoais:
                esusve_dados_pessoais[k] = v
        valores_modificados = dict_compare(esusve_dados_pessoais, self.pessoa.__dict__)[2]
        if valores_modificados == {}:
            return None

        dados_modificados = []
        for k, v in valores_modificados.items():
            dados_modificados.append((k, v[1]))
        return dados_modificados

    @property
    def dados_norm(self):
        keys = tuple(self.dados.keys())
        exchange = dict(zip(keys, normalize_keys(keys)))
        return {exchange[key]: value for (key, value) in self.dados.items()}

    @property
    def dados_display(self):
        dados = self.dados
        nomes_da_coluna = Notificacao.MAPEAMENTO_COLUNAS
        dados = {}
        for key, value in dados.items():
            dados[nomes_da_coluna[key]] = value
        return dados

    @property
    def resultado_teste(self):
        return self.dados.resultado_do_teste

    @property
    def operador_cpf(self):
        acpf = self.dados.operador_cpf
        cpf = '{}.{}.{}-{}'.format(acpf[:3], acpf[3:6], acpf[6:9], acpf[9:])
        return cpf

    def get_usuario(self):
        try:
            Usuario.objects.get(cpf=self.operador_cpf)
        except Usuario.DoesNotExist:
            return None

    @property
    def data_da_notificacao(self):
        try:
            return datetime.strptime(self.dados['data_da_notificacao'], '%d/%m/%Y')
        except KeyError:
            return None

    @property
    def estah_encerrada(self):
        return bool(self.encerrada_em)

    @property
    def get_motivo_encerramento_display(self):
        if self.encerrada_motivo:
            return TipoMotivoEncerramento.TIPO[self.encerrada_motivo - 1][1]

    @classmethod
    def qs_visiveis(cls, user, manager=None):
        """
        Retorna as notificações visíveis para o usuário.

        Se tiver a perm notificacao.pode_ver_todas, retornará todas as ativas;
        caso contrário, retornará as ativas de seu estabelecimento de saúde.
        """
        if not manager:
            qs = cls.ativas
        else:
            qs = manager

        if user.has_perm('notificacoes.pode_ver_todas_as_notificacoes'):
            return qs
        if user.is_usuario_distrito:
            return qs.filter(bairro__distrito=user.perfil_distrito.distrito)
        if user.is_usuario_estabelecimento:
            cnes_user = user.perfil_estabelecimento.estabelecimento_saude
            if cnes_user:
                return qs.filter(
                    Q(estabelecimento_saude=cnes_user) | Q(estabelecimento_saude_referencia=cnes_user)
                )
        return cls.objects.none()

    def visivel_para(self):
        """Retorna QuerySet contendo os usuários que podem ver a notificação `self`. Usa a mesma lógica do
        `Notificacao.qs_visiveis`."""
        cpfs = list(users_with_perm('notificacoes.pode_ver_todas_as_notificacoes').values_list('cpf', flat=True))
        if self.bairro:
            cpfs += list(
                PerfilDistrito.objects.filter(distrito=self.bairro.distrito_id).values_list('usuario__cpf', flat=True))
        if self.estabelecimento_saude:
            cpfs += list(
                PerfilEstabelecimentoSaude.objects.filter(estabelecimento_saude=self.estabelecimento_saude).values_list(
                    'usuario__cpf', flat=True))
        return Usuario.objects.filter(cpf__in=cpfs)

    @classmethod
    def recuperar_notificacoes_alteradas(cls, data=None, apenas_com_resultado_alterado=False,
                                         apenas_dados_originais_do_esusve_alerados=True):
        qs = cls.ativas
        qs = HistoricoNotificacaoAtualizacao.objects.filter(data__date=data)
        if apenas_dados_originais_do_esusve_alerados:
            qs = qs.filter(dados_alterado__has_key='dados')
        if apenas_com_resultado_alterado:
            qs = qs.exclude(dados_alterado__dados__resultado_do_teste=None)
        return qs


    @classmethod
    def recuperar_notificacoes_similares(cls):
        '''
        Retorna o conetúdo do cache ControleCache.notificacoes_similares().
        O cache é um dicionário onde a chave é uma tupla e o valor é um dicionário com as colunas diferente das notificações similares
        :return:
        '''
        return ControleCache.notificacoes_similares().get()

    @classmethod
    def get_processamento_foi_concluido(cls):
        return ControleCache.processamento_notificacoes().processamento_foi_concluido()

    @classmethod
    def get_similaridades_processamento_foi_concluido(cls):
        return cls.get_processamento_foi_concluido() and ControleCache.notificacoes_similares().processamento_foi_concluido()

    @classmethod
    def recuperar_nomes_de_bairro_pendentes(cls, obter_de_historico=False):
        '''
        Retorna uma lista com os nomes dos bairros das notificações que não possuem bairro

        Se obter_de_historico = True, retorna o queryset de Notificacao pendentes de confirmação de associação de bairros
        :return:
        '''
        if obter_de_historico:
            return Notificacao.objects.filter(historiconotificacaoassociacaobairrooutros__confirmado=False)

        qs = cls.ativas.filter(bairro__isnull=True).exclude(dados__bairro=None)
        values_list = set(qs.values_list('numero',
                                         'dados__logradouro',
                                         'dados__bairro',
                                         'dados__municipio_de_residencia',
                                         'dados__estado_de_residencia',
                                         'dados_cep__cep',
                                         'dados_cep__bairro',
                                         'dados_cep__localidade',
                                         'dados_cep__uf'))

        # qs.filter(dados__bairro__icontains='alecrim').values('dados__bairro', 'numero')

        dados = {}
        for num_notificacao, logradouro, nome_bairro_residencia, municipio_de_residencia, estado_de_residencia, cep, cep_bairro, cep_localidade, cep_uf in values_list:
            nome_bairro_residencia = nome_bairro_residencia

            # if cep:
            #     nome_bairro_residencia = '{}, {}/{}. DADOS DO CEP: {} -> {} - {}/{}'.format(
            #                                                         logradouro,
            #                                                         nome_bairro_residencia,
            #                                                         municipio_de_residencia,
            #                                                         estado_de_residencia,
            #                                                         cep,
            #                                                         cep_bairro if cep_bairro else 'Centro',
            #                                                         cep_localidade,
            #                                                         cep_uf)

            dados[nome_bairro_residencia] = num_notificacao

        adados = list(set(dados.items()))
        dados = sorted(adados, key=lambda tup: tup[1])
        return dados

    @classmethod
    def atualiza_bairros_de_notificacoes(cls, nomes_bairros, considerar_notificacao=False):
        '''
        Atualiza as notificações com os nomes_bairros
        ex:
        nomes_bairros = (
            ('242000167599', Modelo Bairro),
            ('242000167526', Modelo Bairro),
        )

        :param nomes_bairros:
        :return:
        '''
        for num_notificacao, bairro in nomes_bairros:
            data_update = {
                'bairro': bairro,
                'ativa': True,
                'tipo_motivo_desativacao': None
            }
            if not isinstance(bairro, Bairro):
                raise ValueError('nomes_bairros deve conter instancia da classe models.Bairro')

            if bairro.municipio.codigo_ibge != settings.CODIGO_IBGE_MUNICIPIO_BASE:
                data_update.update({'ativa': False,
                                    'tipo_motivo_desativacao': TipoNotificacaoMotivoCancelamento.BAIRRO_OUTROS}
                                   )
            if considerar_notificacao:
                cls.objects.filter(numero=num_notificacao).update(**data_update)
                HistoricoNotificacaoAssociacaoBairroOutros.objects.filter(notificacao=num_notificacao).update(
                    confirmado=True)
            else:
                nome_bairro = cls.objects.filter(numero=num_notificacao).values_list('dados__bairro', flat=True)[
                    0]
                logger.debug('Desativando notificações onde dados__bairro =  {}'.format(nome_bairro))
                cls.ativas.filter(dados__bairro=nome_bairro).update(**data_update)
                AssociacaoBairro.get_create_or_update(nome_bairro.strip(), bairro)
        fonte_de_dados_indicadores_alterados.send(sender=cls)

    @classmethod
    def remover_notificacoes_fora_de_area(cls, notificacoes, considerar_notificacao=False):
        '''
        Coloca as notificações de fora da cidade do Natal
        ex:
        nomes_bairros = (
            ('242000167599', Modelo Bairro),
            ('242000167526', Modelo Bairro),
        )
        :param nomes_bairros:
        :return:
        '''

        bairro_limbo = Bairro.objects.get(nome=settings.BAIRRO_OUTROS,
                                          municipio__codigo_ibge=settings.CODIGO_IBGE_OUTRO)
        for notificacao in notificacoes:
            if considerar_notificacao:
                cls.objects.filter(numero=notificacao.numero).update(bairro=bairro_limbo,
                                                                     ativa=False,
                                                                     tipo_motivo_desativacao=TipoNotificacaoMotivoCancelamento.BAIRRO_OUTROS
                                                                     )
                HistoricoNotificacaoAssociacaoBairroOutros.objects.filter(notificacao=notificacao.numero).update(
                    confirmado=True)

            else:
                nome_bairro = \
                cls.objects.filter(numero=notificacao.numero).values_list('dados__bairro', flat=True)[0]
                logger.debug('Desativando notificações onde dados__bairro =  {}'.format(nome_bairro))
                cls.ativas.filter(dados__bairro=nome_bairro).update(ativa=False,
                                                                           tipo_motivo_desativacao=TipoNotificacaoMotivoCancelamento.BAIRRO_OUTROS)

                AssociacaoBairro.get_create_or_update(nome_bairro.strip(), bairro_limbo)
            fonte_de_dados_indicadores_alterados.send(sender=cls)

    @classmethod
    def definir_principais(cls, numeros_requisicoes_principais):
        '''
        Recebe uma lista de lista com os pks das notificações definidas como principais.
        a sublista contem os pks dos grupos de notificações

        :param numeros_requisicoes_principais:
        :return:
        '''
        notificacoes_similares = ControleCache.notificacoes_similares().get().items()
        notificacoes_a_serem_desativadas = []
        chaves_a_remover = []

        #Atualiz o campo  notificacao_principal de todos os pks da sublista para o primeiro pk desta.
        #Lembrando que uma sublista corresponde as notificações selecionadas dentro de um grupos de notificações.
        for pks in numeros_requisicoes_principais:
            pk_notificacao_principal = pks[0]
            cls.ativas.filter(pk__in=pks).update(notificacao_principal=pk_notificacao_principal)

        for chave, notificacoes in notificacoes_similares:
            grupo_pks = {}
            ha_chaves_a_remover = False
            pk_notificacao_principal = None
            for n in notificacoes:
                grupo_pks[n['pk']] = True
                for pks in numeros_requisicoes_principais:
                    if str(n['pk']) in pks:
                        pk_notificacao_principal = pks[0]
                        grupo_pks[n['pk']] = False
                        ha_chaves_a_remover = True

            if ha_chaves_a_remover:
                chaves_a_remover.append(chave)
                for pk, desativar in grupo_pks.items():
                    if desativar:
                        cls.ativas.filter(pk=pk).update(ativa=False,
                                                        notificacao_principal=pk_notificacao_principal,
                                                        tipo_motivo_desativacao=TipoNotificacaoMotivoCancelamento.NOTIFICACAO_SIMILAR)

        ControleCache.notificacoes_similares().remove(chaves_a_remover)
        fonte_de_dados_indicadores_alterados.send(sender=cls)

    @classmethod
    def obter_notificacoes_por_data_nascimento(cls, data_nascimento):
        qs = Notificacao.ativas.filter(paciente_internado__isnull=True)
        if isinstance(data_nascimento, (date, datetime)):
            data_nascimento = data_nascimento.strftime('%d/%m/%Y')
        qs = qs.filter(dados__data_de_nascimento=data_nascimento)

        return qs


class HistoricoNotificacaoAtualizacao(models.Model):
    notificacao = models.ForeignKey(Notificacao, on_delete=models.CASCADE)
    data = models.DateTimeField()
    dados_alterado = JSONField()

    class Meta:
        verbose_name = 'Histórico de atualização de notificação'
        verbose_name_plural = 'Históricos de atualizações de notificações'
        unique_together = [['notificacao', 'data']]


class HistoricoNotificacaoAssociacaoBairroOutros(models.Model):
    '''
    Armazena as associação realizadas que diferem daquelas especificada pelo usuário.

    Exemplo.
    O nome do bairro do endereço de residência é "Cidade Verde".
    A associação para esse bairro consta como "OUTRO".
    A cidade obtida através do CEP fornecido no endereço aponta para "Natal"
    Nesse caso, o sistema irá utilizar o nome do bairro obtido do CEP, em um caso específico, obteve "Cancelária"

    Será regitrado neste modelo, o número da notificacao e o bairro obtido.

    '''
    notificacao = models.ForeignKey(Notificacao, on_delete=models.CASCADE)
    confirmado = models.BooleanField(default=False)
    bairro = models.ForeignKey('base.Bairro', on_delete=models.CASCADE)

    def __str__(self):
        return '[{}] {} -> {}'.format(
            self.notificacao.numero,
            self.notificacao.dados['bairro'],
            self.notificacao.bairro.nome
        )


class Monitoramento(models.Model):
    notificacao = models.ForeignKey(Notificacao, on_delete=models.PROTECT, verbose_name='Notificação')
    pessoa = models.ForeignKey('base.pessoafisica', on_delete=models.PROTECT, null=True)
    criado_por = models.ForeignKey(Usuario, on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)
    data_de_investigacao = models.DateField()
    dados = JSONField(default=dict)

    objects = models.Manager()
    ativos = MonitoramentosAtivosManager()

    MAPEAMENTO_COLUNAS = {
        'febre': ('Febre', lambda x: 'Sim' if x else 'Não'),
        'tosse': ('Tosse', lambda x: 'Sim' if x else 'Não'),
        'anosmia': ('Anosmia', lambda x: 'Sim' if x else 'Não'),
        'outros': ('Outros', str),
        'data_da_investigacao': ('Data da investigação', lambda x: date.fromisoformat(x).strftime('%d/%m/%Y')),
        'informacoes_adicionais': ('Informações adicionais', str),
        'dispnea': ('Dispneia', lambda x: 'Sim' if x else 'Não'),
        'diarreia': ('Diarréia', lambda x: 'Sim' if x else 'Não'),
        'comorbidades': ('Comorbidades', lambda x: ', '.join(x)),
        'como_se_sente': ('Como se sente?', str),
        'dor_de_garganta': ('Dor de garganta', lambda x: 'Sim' if x else 'Não'),
        'outras_comorbidades': ('Outras comorbidades', str),
        'contato_com_positivo': ('Contato com positivo', str),
        'ocupacao': ('Ocupação', str),
        'local_de_trabalho': ('Local de trabalho', str),

        'nome_do_contato' : ('Nome do contato', str),
        'telefone_do_contato': ('Telefone do contato', str),
        'informacoes_adicionais_do_contato': ('Informações adicionais do contato', str),

        'pertence_sistema_prisional': ('Pertence ao sistema prisional?', lambda x: 'Sim' if x else 'Não'),
        'atuacao_sistema_prisional': ('Atuação no sistema prisional', str),
        'nome_da_unidade_prisional': ('Nome da unidade prisional', str),
    }

    @property
    def dados_display(self):
        return {Monitoramento.MAPEAMENTO_COLUNAS[campo][0]: Monitoramento.MAPEAMENTO_COLUNAS[campo][1](valor) for
                campo, valor in self.dados.items()}

    class Meta:
        verbose_name = 'Monitoramento'
        verbose_name_plural = 'Monitoramentos'
        permissions = [
            ('pode_encerrar_monitoramento', 'Pode encerrar monitoramento')
        ]
        ordering = ['-data_de_investigacao']

    @classmethod
    def get_pendentes(cls, horas, qs=None):
        if not qs:
            qs = cls.objects
        tempo_decorrido = timezone.now() - timezone.timedelta(hours=horas)
        return qs.filter(data_de_investigacao__lt=tempo_decorrido)

    @classmethod
    def qs_visiveis(cls, user, manager=None):
        """
        Retorna as notificações visíveis para o usuário.

        Se tiver a perm notificacao.pode_ver_todas, retornará todas as ativas;
        caso contrário, retornará as ativas de seu estabelecimento de saúde.
        """
        if not manager:
            qs = cls.ativos
        else:
            qs = manager

        if user.has_perm('notificacoes.pode_ver_todas_as_notificacoes'):
            return qs
        if user.is_usuario_distrito:
            return qs.filter(notificacao__bairro__distrito=user.perfil_distrito.distrito)
        if user.is_usuario_estabelecimento:
            estabelecimento_saude_do_user = user.perfil_estabelecimento.estabelecimento_saude
            return qs.exclude(notificacao__estabelecimento_saude__isnull=True). \
                filter(notificacao__estabelecimento_saude=estabelecimento_saude_do_user)
        return cls.objects.none()


class PacienteInternacao(models.Model):
    '''
    dados_censo_leitos armazena o json no seguinte formato:
        {'  "diagnostico": "COVID-19 CONFIRMADO",
  "id": 0,
  "internacao_admiss\u00e3o": str YYYY-MM-DD
  "internacao_liberacao": str YYYY-MM-DD
  "internacao_motivo_liberacao": str - ALTA, OBITO
  "leito_ativo": false
  "leito_cod_referencia": str
  "leito_motivo_bloqueio": str
  "leito_situacao_leito": str OCUPADO, LIVRE
  "leito_tipo_leito": str ENFERMARIA, SEMI_INTENSIVA, EXTRA, INTENSIVA
  "paciente_data_nascimento": str YYYY-MM-DD
  "paciente_municipio_codigo": str
  "paciente_municipio_nome": str
  "paciente_nome": str
  "requisicao_gal": str
  "unidade_ativo": str
  "unidade_nome": str
  "unidade_tipo": str ESTADUAL, FEDERAL, FILANTROPICA, MUNICIPAL, PRIVADA, UPA
    '''
    INTERNADO = 'I'
    OBITO = 'O'
    LIBERADO = 'A'
    TIPO = [[INTERNADO, 'Internado'],
            [OBITO, 'Óbito'],
            [LIBERADO, 'Liberado'],
            ]
    hash_identificacao = models.CharField(max_length=56, unique=True)
    estabelecimento_saude = models.ForeignKey('base.EstabelecimentoSaude', on_delete=models.SET_NULL, null=True)
    dados_censo_leitos = JSONField()
    data_ultimo_processamento = models.DateTimeField(null=True)
    tipo = models.CharField(max_length=1, choices=TIPO, null=True)

    dados_regularn = JSONField(null=True)
    dados_regularn_atualizados_em = models.DateTimeField(null=True)

    # Campos preenchidos ao verificar óbito
    cns = models.CharField(max_length=255, verbose_name='CNS ou CPF')
    data_do_obito = models.DateField(null=True, verbose_name='Data do óbito')
    RESULTADO_DO_TESTE_COVID_19_CHOICES = ['Confirmado', 'Descartado', 'Suspeito']
    resultado_do_teste_covid_19 = models.CharField(
        blank=True,
        choices=zip(RESULTADO_DO_TESTE_COVID_19_CHOICES, RESULTADO_DO_TESTE_COVID_19_CHOICES),
        max_length=255,
    )
    sexo = models.CharField(max_length=1, choices=[['M', 'Masculino'], ['F', 'Feminino']])
    idade = models.PositiveIntegerField(null=True)
    endereco_logradouro = models.CharField(max_length=255, verbose_name='Endereço / Logradouro')
    endereco_numero = models.CharField(max_length=255, verbose_name='Endereço / Número')
    endereco_bairro = models.ForeignKey(Bairro, null=True, on_delete=models.PROTECT, verbose_name='Endereço / Bairro')

    MAPEAMENTO_COLUNAS = {
        # 'ti': 'Tempo de Internação (dias)',
        # 'idade': 'Idade',
        "diagnostico": 'Diagnóstico',
        # "id": 0,
        "internacao_admissao": 'Data de admissão',
        "internacao_liberacao": 'Data de liberação',
        # "internacao_motivo_liberacao": "ALTA",
        # "leito_ativo": false,
        # "leito_cod_referencia": 'Leito',
        # "leito_motivo_bloqueio": null,
        # "leito_situacao_leito": "LIVRE",
        "leito_tipo_leito": 'Tipo de leito',
        # "paciente_data_nascimento": "1973-07-03",
        # "paciente_municipio_codigo": "8102",
        "paciente_municipio_nome": 'Município',
        "paciente_nome": 'Nome do paciente',
        # "requisicao_gal": null,
        # "unidade_ativo": "true",
        "unidade_nome": 'Unidade',
        # "unidade_tipo": "PRIVADA"
    }

    def _get_resultado_do_teste_covid_19(self):
        val = self.dados_censo_leitos.get('diagnostico', '')
        for op in self.RESULTADO_DO_TESTE_COVID_19_CHOICES:
            if op.upper() in val.upper():
                return op
        return ''

    def get_notificacao_vinculada(self):
        return self.notificacao_set.all().first()

    @property
    def data_de_nascimento(self):
        return to_date(self.dados_censo_leitos['paciente_data_nascimento'])

    @property
    def data_de_nascimento_str(self):
        return to_date(self.dados_censo_leitos['paciente_data_nascimento']).strftime('%d/%m/%Y')

    @classmethod
    def processar_dados_censo_leitos_imd(cls):
        # Desativando processamento de pdf
        # path_pdfs = baixar_pdf_censo_leitos_(settings.AUTENTICACAO_CENSO['USUARIO'],
        #                     settings.AUTENTICACAO_CENSO['SENHA'])
        # PacienteInternacao._processar_pdf_censo_leitos_imd(*path_pdfs)

        dados_da_internacao = get_leitos_lista_geral()
        dados_da_internacao.pop('timestamp')
        tipo_parse = {
            'altas': PacienteInternacao.LIBERADO,
            'obitos': PacienteInternacao.OBITO,
            'internados': PacienteInternacao.INTERNADO
        }
        dados_internados = []
        for tipo, dados_gerais in dados_da_internacao.items():
            for dados in dados_gerais:
                dados['tipo'] = tipo_parse[tipo]
                dados_internados.append(dados)

        mensagem_de_retorno = []
        mensagem_de_retorno2 = PacienteInternacao._processar_dados_censo_leitos_imd(dados_internados)
        mensagem_de_retorno.extend(mensagem_de_retorno2)
        return mensagem_de_retorno

    @classmethod
    @elapsed_time
    def _processar_dados_censo_leitos_imd(cls, dados_da_internacao_todos, pdf=False):
        mensagem_de_retorno = []
        ControleCache.nomes_estabelecimento_a_associar().reset()

        estabelecimentos_cnes = {}
        for associacao_unidade in AssociacaoNomeEstabelecimentoSaude.objects.all():
            estabelecimentos_cnes[associacao_unidade.nome] = associacao_unidade.estabelecimento_saude

        municipio_map = dict(PacienteInternacao.objects.values_list('dados_censo_leitos__paciente_municipio_codigo',
                                                                    'dados_censo_leitos__paciente_municipio_nome').distinct())

        def associar_com_notificacoes(mensagem_de_retorno):

            pacientes = PacienteInternacao.objects.exclude(dados_regularn__cartao_sus=None).values_list('id',
                                                                                                        'dados_regularn__cartao_sus',
                                                                                                        'dados_regularn__numero_gal')
            for id_paciente, numero_cns, numero_gal in pacientes:
                Notificacao.objects.filter(dados__cns=numero_cns).update(paciente_internado=id_paciente,
                                                                                numero_gal=numero_gal)
            quant = Notificacao.objects.filter(paciente_internado__isnull=False).count()

            mensagem_de_retorno.append('Notificações associadas com paciente internação: {}'.format(quant))

        def atualizar_internacoes_nao_existentes(internacoes, mensagem_de_retorno):
            pacientes_nao_encontrados = PacienteInternacao.objects.exclude(hash_identificacao__in=internacoes.keys())
            pacientes_nao_encontrados.update(tipo=cls.LIBERADO)
            mensagem_de_retorno.append(
                'Pacientes definidos como liberados: {}'.format(pacientes_nao_encontrados.count()))

        def recuperar_soliciacoes_do_regularn():
            solicitacoes = get_solicitacoes()
            dsolicitacores = {}
            for solicitacao in solicitacoes:
                identificacao = {
                    'codigo_cnes': solicitacao['estabelecimento_prestador_cnes'] or solicitacao[
                        'estabelecimento_solicitante_cnes'],
                    'paciente_nome': solicitacao['nome'],
                }
                idade = solicitacao['idade']
                for i in (-1, 0, 1):
                    identificacao['idade'] = str(idade + i)
                    hash_identificacao = hashlib.sha224(str(identificacao).encode()).hexdigest()
                    dsolicitacores[hash_identificacao] = solicitacao
            return dsolicitacores

        # dsolicitacores = recuperar_soliciacoes_do_regularn()

        hoje = timezone.now()
        internacoes = {}
        quant = 0
        nomes_pendentes = set()
        for dados_da_intenacao in dados_da_internacao_todos:
            estabelecimento_saude = estabelecimentos_cnes.get(dados_da_intenacao['unidade_nome'], None)

            if estabelecimento_saude is None:
                nomes_pendentes.add(dados_da_intenacao['unidade_nome'])
                continue

            paciente_data_nascimento = to_date(dados_da_intenacao['paciente_data_nascimento'])
            if paciente_data_nascimento is None:
                raise Exception('Paciente sem data')

            identificacao = {
                'codigo_cnes': estabelecimento_saude.codigo_cnes,
                'paciente_nome': dados_da_intenacao['paciente_nome'],
                'paciente_data_nascimento': paciente_data_nascimento,
            }
            hash_identificacao = hashlib.sha224(str(identificacao).encode()).hexdigest()
            internacoes[hash_identificacao] = dados_da_intenacao

            # verifica se o paciente consta no regularn
            dados_regularn = None
            dados_regularn_atualizados_em = None
            paciente_id = hashlib.sha224(str(identificacao).encode()).hexdigest()
            # if dsolicitacores.get(paciente_id):
            #     dados_regularn = dsolicitacores[paciente_id]
            #     dados_regularn_atualizados_em = hoje

            municipio_codigo = dados_da_intenacao['paciente_municipio_codigo']
            dados_da_intenacao['paciente_municipio_nome'] = dados_da_intenacao.get('paciente_municipio_nome',
                                                                                   municipio_map.get(municipio_codigo))

            save_data = {
                'idade': calculateAge(paciente_data_nascimento),
                'dados_censo_leitos': dados_da_intenacao,
                'data_ultimo_processamento': hoje,
                'estabelecimento_saude': estabelecimento_saude,
                'dados_regularn': dados_regularn,
                'dados_regularn_atualizados_em': dados_regularn_atualizados_em,
                'tipo': dados_da_intenacao['tipo']
            }

            paciente_internado, created = cls.objects.update_or_create(
                hash_identificacao=hash_identificacao, defaults=save_data
            )

        ControleCache.nomes_estabelecimento_a_associar().set(nomes_pendentes)
        ControleCache.nomes_estabelecimento_a_associar().set_status(StatusProcessamento.CONCLUIDO)

        if len(nomes_pendentes) > 1 and ControleCache.nomes_paciente_a_associar().pode_enviar_alerta_hoje():
            Alerta.ha_nomes_estabelecimento_a_associar()
            mensagem_de_retorno.append('Há {} nomes de estabelecimentos sem associações'.format(len(nomes_pendentes)))

        atualizar_internacoes_nao_existentes(internacoes, mensagem_de_retorno)

        associar_com_notificacoes(mensagem_de_retorno)

        msn1 = cls.processar_nomes_a_associar()
        mensagem_de_retorno.extend(msn1)

        cache.delete('censo_imd_arq1')
        cache.delete('censo_imd_arq2')
        cache.delete('censo_imd_arq3')

        return mensagem_de_retorno

    @classmethod
    def recuperar_nomeas_a_associar(cls, tipo_internacao=None):
        cache = ControleCache.nomes_paciente_a_associar().get()
        if tipo_internacao is None:
            return cache

        new_cache = {}
        for k, v in cache.items():
            tipo = cache[k]['dados_internacao'][1]
            if tipo_internacao == tipo:
                new_cache[k] = v
        return new_cache

    @classmethod
    def definir_principais(cls, nomes_a_associar):
        ''''
        Recebe uma lista de tuplas com os números de notificação e os respectivos chaves de PacienteInternacao
        A chave é composta
        Ex.:
        (
        ('2024358355', 1),
        ('2024362744', 2)
        )
        '''
        nomes_a_associar_a_serem_removidos = []
        for notificacao, id_paciente_internacao in nomes_a_associar:
            qs = PacienteInternacao.objects.filter(id=int(id_paciente_internacao))
            id, nome, _data_nascimento = \
            qs.values_list('id', 'dados_censo_leitos__paciente_nome', 'dados_censo_leitos__paciente_data_nascimento')[0]
            data_nascimento = to_date(_data_nascimento)
            Notificacao.objects.filter(numero=notificacao.numero).update(paciente_internado=id_paciente_internacao)
            nomes_a_associar_a_serem_removidos.append((id, nome.upper().strip(), data_nascimento))

        ControleCache.nomes_paciente_a_associar().remove(nomes_a_associar_a_serem_removidos)
        fonte_de_dados_indicadores_alterados.send(sender=cls)

    @classmethod
    def get_notificacoes_com_nomes_similares(cls, nome, data_nascimento):
        data_nascimento_expression = ToDate(KeyTextTransform('data_de_nascimento', 'dados'),
                                            output_field=DateField(),
                                            format="'DD/MM/YYYY'")
        qs = Notificacao.ativas.values('ativa').annotate(data_nascimento=data_nascimento_expression)
        notificacoes = qs.filter(data_nascimento=data_nascimento).values_list('numero',
                                                                              'dados__nome_completo',
                                                                              'dados__data_de_nascimento')
        nomes_dos_notificados = {}
        for numero, nnome, data_nascimento in notificacoes:
            nomes_dos_notificados[nnome] = numero

        nomes_similares = difflib.get_close_matches(nome, nomes_dos_notificados.keys(), n=3, cutoff=0.7)

        numeros_notificacao = []
        for nnumero, nnome, ndata_nascimento in notificacoes:
            for nome_similar in nomes_similares:
                if nnome == nome_similar:
                    numeros_notificacao.append(nnumero)
        if numeros_notificacao:
            return Notificacao.objects.filter(numero__in=numeros_notificacao)
        return Notificacao.objects.none()

    @classmethod
    @elapsed_time
    def processar_nomes_a_associar(cls):
        '''
        Armazena no cache o dicinários com os dados de nomes de pacientes que precisam ser associados com notificações
        chave:  tupla com os dados do paciente interancao, formato: (id_paciente_interanacao, nome, idade)
        valor: dicionário com as tuplas de possíveis nomes, formato:
        {
            'dados_internacao': ['id','paciente_nome','leitos__idade','municipio','leito_tipo_leito','internacao_admissao','internacao_liberacao','ti'],
            'dados_notificacao': (nome do notificado, data de nascimento, idade, número da notificacao)
        }
        Exemplo
        {
            (982, 'JOSE MARIA DE AQUINO', '82'): {
                    'dados_internacao': [982, 'JOSE MARIA DE AQUINO', '82', 'Natal', 'Enfermaria', '', '', '6'],
                    'dados_notificacao': [('JOSE MARIA DE AQUINO', '02/12/1937', 82, '242002490929')]
                    }
        }
        :return:
        '''
        mensagem_de_retorno = []
        cache_nomes_paciente_a_associar = ControleCache.nomes_paciente_a_associar()
        cache_nomes_paciente_a_associar.reset()

        mensagem_de_retorno.append('Contador controle alerta ={}, pode enviar alerta hoje = {}'.format(
            cache_nomes_paciente_a_associar.get_contador_controle_envio_alerta(),
            cache_nomes_paciente_a_associar.pode_enviar_alerta_hoje()
        ))

        qs = Notificacao.ativas.filter(paciente_internado__isnull=True)
        notificacoes = qs.values_list('numero',
                                      'dados__nome_completo',
                                      'dados__data_de_nascimento',
                                      'dados__cpf',
                                      'dados__resultado_do_teste')
        notificados_datas_nascimentos = {}
        notificados_numeros = {}
        for numero, anome, data_nascimento, cpf, resultado_do_teste in notificacoes:
            nome = anome.upper().strip()
            data_de_nascimento = to_date(data_nascimento)
            if notificados_datas_nascimentos.get(data_de_nascimento, None) is None:
                notificados_datas_nascimentos[data_de_nascimento] = []
            notificados_datas_nascimentos[data_de_nascimento].append((nome, numero))

            notificados_numeros[numero] = (
            nome, data_nascimento, calculateAge(data_de_nascimento), cpf, resultado_do_teste)

        municipio_nome = Municipio.objects.filter(codigo_ibge=settings.CODIGO_IBGE_MUNICIPIO_BASE).values('nome')[0]['nome']
        qs = PacienteInternacao.objects.filter(notificacao__isnull=True,
                                               dados_censo_leitos__paciente_municipio_nome__iexact=municipio_nome)
        pacientes = qs.values('id',
                              'tipo',
                              'dados_censo_leitos__paciente_nome',
                              'dados_censo_leitos__paciente_data_nascimento',
                              'dados_censo_leitos__paciente_municipio_nome',
                              'dados_censo_leitos__leito_tipo_leito',
                              'dados_censo_leitos__internacao_admissao',
                              'dados_censo_leitos__internacao_liberacao',
                              'dados_censo_leitos__unidade_nome',
                              )

        # nomes_dos_notificados = [*notificados_nomes.keys()]
        dados_retorno = {}
        for dados_paciente in pacientes:
            nome = dados_paciente['dados_censo_leitos__paciente_nome'].upper().strip()
            id = dados_paciente['id']
            data_de_nascimento = to_date(dados_paciente['dados_censo_leitos__paciente_data_nascimento'])
            data_internacao_admissao = to_date(dados_paciente['dados_censo_leitos__internacao_admissao'])
            data_internacao_liberacao = to_date(dados_paciente['dados_censo_leitos__internacao_liberacao'])

            # cálculo do tepo de internação
            ti = None
            try:
                if data_internacao_liberacao:
                    ti = data_internacao_liberacao - data_internacao_admissao
                else:
                    hoje = timezone.now()
                    ti = hoje - data_internacao_admissao
            except:
                pass

            dados_paciente['dados_censo_leitos__ti'] = ti
            dados_paciente['dados_censo_leitos__idade'] = calculateAge(data_de_nascimento)
            chave = (id, nome, data_de_nascimento)
            # datetime.strptime(paciente_data_nascimento, '%d/%m/%Y')

            nomes_similares = None
            if notificados_datas_nascimentos.get(data_de_nascimento, None) is not None:
                nomes_dos_notificados = [nome for nome, numero in notificados_datas_nascimentos[data_de_nascimento]]
                nomes_similares = difflib.get_close_matches(nome, nomes_dos_notificados, n=3)  # n=3, cutoff=0.6

            if nomes_similares:
                dados_retorno[chave] = {
                    'dados_internacao': [*dados_paciente.values()],
                    'dados_notificacao': []
                }
                for nome_similar in nomes_similares:
                    numeros_de_notificacoes = []
                    for anome, numero in notificados_datas_nascimentos[data_de_nascimento]:
                        if anome == nome_similar:
                            numeros_de_notificacoes.append(numero)

                    for numero in numeros_de_notificacoes:
                        notificado_nome, data_nascimento, idade, cpf, resultado_do_teste = notificados_numeros[numero]
                        dados_notificacao = (notificado_nome, data_nascimento, idade, numero, cpf, resultado_do_teste)
                        dados_retorno[chave]['dados_notificacao'].append(dados_notificacao)
        cache_nomes_paciente_a_associar.set(dados_retorno)
        cache_nomes_paciente_a_associar.set_status(StatusProcessamento.CONCLUIDO)
        return mensagem_de_retorno

    @classmethod
    def recuperar_nomes_de_estabelecimento_pendentes(cls):
        return ControleCache.nomes_estabelecimento_a_associar().get()

    @classmethod
    def get_processamento_foi_concluido(cls):
        return ControleCache.nomes_paciente_a_associar().processamento_foi_concluido()


class Obito(models.Model):
    """
    Classe que representa um obito relacionado a uma notificacao
    """
    pessoa = models.ForeignKey(PessoaFisica, on_delete=models.PROTECT, null=True, blank=False)
    bairro = models.ForeignKey('base.Bairro', on_delete=models.SET_NULL, null=True, blank=False)
    notificacao = models.ForeignKey(Notificacao, on_delete=models.SET_NULL, null=True)
    numero_declaracao_obito = models.CharField(
        "Número da Declaração de Óbito", null=False, blank=True, max_length=30)
    local_do_obito = models.ForeignKey(
        to='base.EstabelecimentoSaude',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Local do Óbito',
        help_text="Caso o óbito tenha ocorrido no domicílio, deixe vazio.")
    data_do_obito = models.DateField(null=False, verbose_name='Data do óbito')
    RESULTADO_DO_TESTE_COVID_19_CHOICES = ['Confirmado', 'Descartado', 'Suspeito']
    resultado_do_teste_covid_19 = models.CharField(
        choices=zip(RESULTADO_DO_TESTE_COVID_19_CHOICES, RESULTADO_DO_TESTE_COVID_19_CHOICES),
        max_length=255,
        verbose_name="Resultado do Teste - COVID-19"
    )
    confirmado_covid19 = models.NullBooleanField(default=None)
    arquivo_declaracao_obito = models.FileField(verbose_name='Declaração de Óbito', max_length=255, null=True, blank=True,
                                      upload_to='obito/declaracoes_obito',  validators=[FileExtensionValidator(['pdf'])])
    arquivo_resultado_exame_covid19 = models.FileField(verbose_name='Resultado do Exame - COVID19', max_length=255, null=True, blank=True,
                                      upload_to='obito/resultados_exame_covid19',  validators=[FileExtensionValidator(['pdf'])])

    class Meta:
        verbose_name = 'Óbito'
        verbose_name_plural = 'Óbitos'
        permissions = [
            ('pode_registrar_obito', 'Pode Registrar Óbito'),
            ('pode_validar_obito', 'Pode Validar Óbito')
        ]

    def get_dados_pessoa(self):
        '''
        :return:
        '''
        if self.pessoa:
            return self.pessoa.get_dados_pessoa()
        elif self.notificacao:
            return self.notificacao.get_dados_pessoa()

    @staticmethod
    @atomic
    def criar_se_nao_exisir(dados):
        """
        {
            'notificacao_pk': {
                'numero_declaracao_obito': '',
                'local_do_obito': 'codigo_cnes',
                'data_do_obito': 'YYYY-MM-DD',
                'resultado_do_teste_covid_19': deve estar presente em RESULTADO_DO_TESTE_COVID_19_CHOICES,
                'bairro':  Object Bairro,
                'pessoa': Object PessoaFisica
            }
        }
        """
        logger.debug('Processando dados de óbitos')
        notificacoes_sivep_gripe_existentes = set(Obito.objects.values_list('notificacao', flat=True))
        cpfs_existentes = set(Obito.objects.values_list('pessoa', flat=True))
        for notificacao_pk, kw in dados.items():
            kw = dados[notificacao_pk]
            if notificacao_pk in notificacoes_sivep_gripe_existentes:  # notificaçao sivep gripe existe nos óbitos
                continue
            if kw['pessoa'] and kw['pessoa'].cpf in cpfs_existentes:  # pessoa.cpf existe nos óbitos
                continue
            if not kw['data_do_obito']:
                continue
            assert kw.get('resultado_do_teste_covid_19') in Obito.RESULTADO_DO_TESTE_COVID_19_CHOICES
            kw['local_do_obito'] = EstabelecimentoSaude.objects.filter(codigo_cnes=kw['local_do_obito']).first()
            kw['notificacao_id'] = notificacao_pk
            Obito.objects.create(**kw)
            if kw['pessoa']:
                # NOTA: caso haja notificação não encerrada como óbito para para a pessoa, iremos encerrar as notificações
                #       por motivo de óbito.
                Notificacao.objects.\
                    filter(pessoa=kw['pessoa'], ativa=True).exclude(encerrada_motivo=TipoMotivoEncerramento.OBITO).\
                    update(
                        encerrada_motivo=TipoMotivoEncerramento.OBITO,
                        data_do_encerramento=kw['data_do_obito'],
                        encerrada_observacoes='Encerrada automaticamente devido a óbito registrado no SIVEP GRIPE',
                        encerrada_em=datetime.now()
                    )
