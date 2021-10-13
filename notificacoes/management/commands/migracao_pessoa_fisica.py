import logging
from datetime import datetime
from django.apps.registry import apps
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.core.management.base import BaseCommand

from base.models import Sexo
from base.utils import digits, normalize_str
from notificacoes.models import TipoArquivo
from notificacoes.processar_notificacoes import ObterNotificacao, PessoaParse

logger = logging.getLogger(__name__)


Bairro = apps.get_model('base', 'Bairro')
Municipio = apps.get_model('base', 'Municipio')
PessoaFisica = apps.get_model('base', 'PessoaFisica')


class Pessoa():
    SEXO_PARSE = {
        'Feminino': Sexo.FEMININO,
        'Masculino': Sexo.MASCULINO,
        'F': Sexo.FEMININO,
        'M': Sexo.MASCULINO,
        'Indefinido': Sexo.INDEFINIDO
    }
    def __init__(self, _pessoa):
        self._pessoa = _pessoa
        self._obter_notificacao = ObterNotificacao(TipoArquivo.ESUSVE_ARQUIVO_CSV)

    @property
    def pk(self):
        return self._pessoa['pk']

    @property
    def cns(self):
        dado = self._pessoa['dados_monitoramento'].get('cns') or self._pessoa['dados'].get('cns')
        _cns = None
        if dado:
            _cns = digits(dado)
            if len(_cns) > 15:
                return None
        return _cns

    @property
    def nome_completo(self):
        dado = self._pessoa['dados_monitoramento'].get('nome_completo') or self._pessoa['dados'].get('nome_completo')
        if dado:
            return dado[:80]
        return None

    @property
    def sexo(self):
        dado = self._pessoa['dados_monitoramento'].get('sexo') or self._pessoa['dados'].get('sexo')
        if dado:
            return PessoaParse.SEXO_PARSE[dado]
        return Sexo.NAO_INFORMADO

    @property
    def data_de_nascimento(self):
        try:
            dado = self._pessoa['dados_monitoramento'].get('data_de_nascimento') or self._pessoa['dados'].get('data_de_nascimento')
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
    def telefone_de_contato(self):
        dado = self._pessoa['dados_monitoramento'].get('telefone_de_contato') or self._pessoa['dados'].get('telefone_de_contato')
        if dado:
            return dado
        return None

    @property
    def celular(self):
        dado = self._pessoa['dados_monitoramento'].get('telefone_celular') or self._pessoa['dados'].get('telefone_celular')
        if dado:
            return dado
        return None

    @property
    def email(self):
        dado = self._pessoa['dados_monitoramento'].get('email') or self._pessoa['dados'].get('email')
        if dado:
            return dado
        return None


    @property
    def cep(self):
        dado = self._pessoa['dados_monitoramento'].get('cep') or self._pessoa['dados'].get('cep')
        if dado:
            cep = digits(dado)
            return f'{cep[:5]}-{cep[5:8]}'
        return None

    @property
    def logradouro(self):
        dado = self._pessoa['dados_monitoramento'].get('logradouro') or self._pessoa['dados'].get('logradouro')
        if dado:
            return dado[:80]
        return None

    @property
    def numero(self):
        dado = self._pessoa['dados_monitoramento'].get('numero_res') or self._pessoa['dados'].get('numero_res')
        if dado:
            return dado[:10]
        return None

    @property
    def complemento(self):
        dado = self._pessoa['dados_monitoramento'].get('complemento') or self._pessoa['dados'].get('complemento')
        return dado

    @property
    def bairro_nome(self):
        return self._pessoa['dados_monitoramento'].get('bairro') or self._pessoa['dados'].get('bairro')

    @property
    def bairro (self):
        nome = self._pessoa['dados_monitoramento'].get('bairro') or self._pessoa['dados'].get('bairro')
        if self._pessoa['dados_monitoramento']:
            if nome and (not self._pessoa['notificacao__bairro__nome'] \
                    or normalize_str(nome) != normalize_str(self._pessoa['notificacao__bairro__nome'])):
                cache_bairro = self._obter_notificacao.tratar_bairro(nome)
                if cache_bairro and cache_bairro['nome'] != settings.BAIRRO_OUTROS:
                    return Bairro(pk=cache_bairro['pk'])

        if self._pessoa['notificacao__bairro__pk'] and self._pessoa['notificacao__bairro__nome'] != settings.BAIRRO_OUTROS:
            return Bairro(pk=self._pessoa['notificacao__bairro__pk'])

        cache_bairro = self._obter_notificacao.tratar_bairro(nome)
        if cache_bairro and cache_bairro['nome'] != settings.BAIRRO_OUTROS:
            return Bairro(pk=cache_bairro['pk'])
        return None

    @property
    def municipio_de_residencia (self):
        nome = self._pessoa['dados_monitoramento'].get('municipio_de_residencia') or self._pessoa['dados'].get(
            'municipio_de_residencia')
        if self._pessoa['dados_monitoramento']:
            if nome and (not self._pessoa['notificacao__municipio_residencia__nome'] \
                    or normalize_str(nome) != normalize_str(self._pessoa['notificacao__municipio_residencia__nome'])):
                    try:
                        return Municipio.objects.get(nome__iexact=nome.split('/')[0])
                    except MultipleObjectsReturned:
                        qs = Municipio.objects.filter(nome__iexact=nome.split('/')[0], estado__codigo_ibge=settings.CODIGO_IBGE_UF_BASE)
                        if qs.exists():
                            return qs[0]
                    except Municipio.DoesNotExist:
                        return None
        if self._pessoa['notificacao__municipio_residencia__pk']:
            return Municipio(pk=self._pessoa['notificacao__municipio_residencia__pk'])
        return None


    @classmethod
    def get_qs(cls):
        return PessoaFisica.objects.filter(data_de_nascimento__isnull=True).values('pk', 'notificacao__bairro__pk', 'notificacao__bairro__nome', 'notificacao__municipio_residencia__pk', 'notificacao__municipio_residencia__nome', 'dados_monitoramento', 'dados')

def atualizar_endereco():
    for pessoa_dados in Pessoa.get_qs():
        pessoa = Pessoa(pessoa_dados)

        save_data = {
            'nome': pessoa.nome_completo,
            'cns': pessoa.cns,
            'sexo': pessoa.sexo,
            'data_de_nascimento': pessoa.data_de_nascimento,
            'telefones': pessoa.telefone_de_contato,
            'celulares': pessoa.celular,
            'email': pessoa.email,
            'cep': pessoa.cep,
            'logradouro': pessoa.logradouro,
            'numero': pessoa.numero,
            'complemento': pessoa.complemento,
            # 'bairro': pessoa.bairro,
            'bairro': pessoa.bairro_nome,
            'municipio': pessoa.municipio_de_residencia,
        }
        # logger.debug(save_data)
        # logger.debug(pessoa.__dict__)
        PessoaFisica.objects.filter(pk=pessoa.pk).update(**save_data)

    print("atualizar_endereco concúida")


class Command(BaseCommand):
   def handle(self, *args, **kwargs):
       atualizar_endereco()
