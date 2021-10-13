import logging
from collections import OrderedDict

from django import forms
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import AbstractUser, PermissionsMixin
from django.contrib.postgres.fields import JSONField
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from localflavor.br.forms import BRCPFField as BRCPFFormField
from localflavor.br.models import BRCPFField
from localflavor.br.validators import BRCPFValidator

from base import rest_cns
from base.caches import ControleCache
from base.managers import BairrosAtivosManager, DistritosAtivosManager, MunicipiosAtivosManager
from base.utils import digits
from newadmin.utils import CepModelField

logger = logging.getLogger(__name__)


class UserManager(BaseUserManager):
    use_in_migrations = False

    def _create_user(self, cpf, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        cpf_validator = BRCPFValidator()
        if not cpf:
            raise ValueError('O CPF precisa ser definido')
        if not email:
            raise ValueError('O E-mail precisa ser definido')
        cpf_validator(cpf)
        email = self.normalize_email(email)
        user = self.model(cpf=cpf, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, cpf=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(cpf, email, password, **extra_fields)

    def create_superuser(self, cpf=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(cpf, email, password, **extra_fields)

    def with_perm(self, perm, is_active=True, include_superusers=True, backend=None, obj=None):
        if backend is None:
            backends = auth._get_backends(return_tuples=True)
            if len(backends) == 1:
                backend, _ = backends[0]
            else:
                raise ValueError(
                    'You have multiple authentication backends configured and '
                    'therefore must provide the `backend` argument.'
                )
        elif not isinstance(backend, str):
            raise TypeError(
                'backend must be a dotted import path string (got %r).'
                % backend
            )
        else:
            backend = auth.load_backend(backend)
        if hasattr(backend, 'with_perm'):
            return backend.with_perm(
                perm,
                is_active=is_active,
                include_superusers=include_superusers,
                obj=obj,
            )
        return self.none()


class Usuario(AbstractBaseUser, PermissionsMixin):
    USERNAME_FIELD = 'cpf'

    cpf = BRCPFField(verbose_name='CPF', primary_key=True)
    nome = models.CharField(verbose_name='nome completo', max_length=255)
    email = models.EmailField(verbose_name='e-mail')
    telefone = models.CharField(max_length=20)

    REQUIRED_FIELDS = ['nome', 'email', 'telefone']

    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    def __str__(self):
        return self.nome

    @property
    def is_usuario_distrito(self):
        return hasattr(self, 'perfil_distrito') and self.perfil_distrito.ativo

    @property
    def is_usuario_ab(self):
        return hasattr(self, 'perfil_ab') and self.perfil_ab.ativo

    @property
    def is_usuario_ae(self):
        return hasattr(self, 'perfil_ae') and self.perfil_ae.ativo

    def is_gestor(self):
        return self.has_perm('base.e_gestor')

    @property
    def is_usuario_vigilancia(self):
        return hasattr(self, 'perfil_vigilancia') and self.perfil_vigilancia.ativo

    @property
    def is_usuario_estabelecimento(self):
        return hasattr(self, 'perfil_estabelecimento') and self.perfil_estabelecimento.ativo

    objects = UserManager()

    class Meta:
        verbose_name = 'usuário'
        permissions = [
            ('e_gestor', 'É gestor'),
        ]


class PerfilDistrito(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil_distrito')
    distrito = models.ForeignKey('Distrito', on_delete=models.CASCADE)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.usuario.nome

    class Meta:
        verbose_name = 'perfil de distrito'
        verbose_name_plural = 'perfis de distrito'


class PerfilVigilancia(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil_vigilancia')
    municipio = models.ForeignKey('Municipio', on_delete=models.CASCADE)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.usuario.nome

    class Meta:
        verbose_name = 'perfil de vigilância'
        verbose_name_plural = 'perfis de vigilância'


class PerfilAtencaoBasica(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil_ab')
    municipio = models.ForeignKey('Municipio', on_delete=models.CASCADE)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.usuario.nome

    class Meta:
        verbose_name = 'Perfil Departamento de Atenção Básica'
        verbose_name_plural = 'Perfis Departamento de Atenção Básica'


class PerfilAtencaoEspecializada(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil_ae')
    municipio = models.ForeignKey('Municipio', on_delete=models.CASCADE)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.usuario.nome

    class Meta:
        verbose_name = 'perfil de atenção especializada'
        verbose_name_plural = 'perfis de atenção especializada'


class PerfilEstabelecimentoSaude(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil_estabelecimento')
    estabelecimento_saude = models.ForeignKey('EstabelecimentoSaude', on_delete=models.CASCADE, null=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.usuario.nome

    class Meta:
        verbose_name = 'perfil de estabelecimento de saúde'
        verbose_name_plural = 'perfis de estabelecimento de saúde'



class UnidadeFederativa(models.Model):
    codigo_ibge = models.CharField(verbose_name='código IBGE', max_length=2, primary_key=True)
    sigla = models.CharField(max_length=2)
    nome = models.CharField(max_length=255)


class Municipio(models.Model):
    codigo_ibge = models.CharField(verbose_name='código IBGE', max_length=6, primary_key=True)
    codigo_ibge_estado = models.CharField(verbose_name='código IBGE do estado', max_length=2)
    nome = models.CharField(max_length=255)
    quant_populacao = models.PositiveIntegerField(verbose_name='População estimada')
    estado = models.ForeignKey('UnidadeFederativa', on_delete=models.CASCADE)

    objects = models.Manager()
    ativos = MunicipiosAtivosManager()

    def __str__(self):
        return self.nome

    @classmethod
    def get_nome_by_ibge(cls, codigo_ibge):
        qs =cls.objects.filter(codigo_ibge=codigo_ibge)
        return qs.first().nome if qs.exists() else None


class Distrito(models.Model):
    municipio = models.ForeignKey('Municipio', on_delete=models.CASCADE)
    nome = models.CharField(max_length=255)
    quant_populacao = models.PositiveIntegerField(verbose_name='População estimada')

    objects = models.Manager()
    ativos = DistritosAtivosManager()

    def __str__(self):
        return self.nome

    @classmethod
    def qs_visiveis(cls, user):
        """
        Retorna os bairros visíveis para o usuário.

        Se tiver a perm notificacao.pode_ver_todas, retornará todos as ativos;
        caso contrário, retornará os ativas de sua área.
        """
        qs = cls.ativos
        if user.has_perm('notificacoes.pode_ver_todas_as_notificacoes'):
            return qs
        if user.is_usuario_distrito:
            return qs.filter(id=user.perfil_distrito.distrito.id)
        return cls.objects.none()


class Bairro(models.Model):
    nome = models.CharField(max_length=255)
    municipio = models.ForeignKey('Municipio', on_delete=models.CASCADE)
    distrito = models.ForeignKey('Distrito', on_delete=models.CASCADE, null=True)
    quant_populacao = models.PositiveIntegerField(verbose_name='População estimada')

    objects = models.Manager()
    ativos = BairrosAtivosManager()

    def __str__(self):
        return self.nome

    @classmethod
    def qs_visiveis(cls, user):
        """
        Retorna os bairros visíveis para o usuário.

        Se tiver a perm notificacao.pode_ver_todas, retornará todos as ativos;
        caso contrário, retornará os ativas de sua área.
        """
        qs = cls.ativos
        if user.has_perm('notificacoes.pode_ver_todas_as_notificacoes'):
            return qs
        if user.is_usuario_distrito:
            return qs.filter(distrito=user.perfil_distrito.distrito)
        return cls.objects.none()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        ControleCache.bairros().reset()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        ControleCache.bairros().reset()


class AssociacaoBairro(models.Model):
    nome = models.CharField(max_length=255, unique=True)
    bairro = models.ForeignKey('Bairro', on_delete=models.PROTECT)

    def __str__(self):
        return '{} -> {} '.format(self.nome, self.bairro.nome)

    class Meta:
        verbose_name = 'associação de bairro'
        verbose_name_plural = 'associações de bairros'

    @classmethod
    def get_create_or_update(cls, nome, bairro):
        associacao = AssociacaoBairro()
        try:
            associacao = AssociacaoBairro.objects.get(nome=nome)
        except AssociacaoBairro.DoesNotExist:
            pass
        associacao.nome = nome
        associacao.bairro = bairro
        return associacao.save()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        ControleCache.associacoes_bairros().reset()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        ControleCache.associacoes_bairros().reset()


class HabitacoesBairro(models.Model):
    CONJUNTO_HABITACIONAIS = 'C'
    LOTEAMENTO = 'L'
    TIPO = [[CONJUNTO_HABITACIONAIS, u'Conjunto Habitacionais'],
            [LOTEAMENTO, u'Loteamento'],
            ]
    nome = models.CharField(max_length=255)
    bairro = models.ForeignKey('Bairro', on_delete=models.PROTECT)
    tipo = models.CharField(max_length=1, choices=TIPO, null=True)

    def __str__(self):
        return '{} - {} - {} '.format(self.bairro.nome, self.nome, self.tipo)

    class Meta:
        verbose_name = 'habitação de bairro'
        verbose_name_plural = 'habitações de bairros'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        ControleCache.habitacoes_bairros().reset()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        ControleCache.habitacoes_bairros().reset()


class EstabelecimentoSaude(models.Model):
    codigo_cnes = models.CharField(verbose_name='código CNES', max_length=7, primary_key=True)
    dados_cnes = JSONField()
    data_extracao = models.DateTimeField(null=True)
    distrito = models.ForeignKey(Distrito, null=True, on_delete=models.PROTECT)

    @property
    def nome(self):
        return self.dados_cnes.get('NO_FANTASIA')

    @property
    def nome_empresarial(self):
        return self.dados_cnes['NO_RAZAO_SOCIAL']

    @property
    def municipio(self):
        return self.dados_cnes['CO_MUNICIPIO_GESTOR']

    @property
    def bairro(self):
        return self.dados_cnes['NO_BAIRRO']

    @property
    def telefone(self):
        return self.dados_cnes['NU_TELEFONE']


    objects = models.Manager()

    def __str__(self):
        return '{} - {}'.format(self.codigo_cnes, self.nome)

    @classmethod
    def qs_visiveis(cls, user):
        """
        Retorna os estabelecimentos visíveis para o usuário.

        Se tiver a perm notificacao.pode_ver_todas, retornará todas as ativas;
        caso contrário, retornará as ativas de seu estabelecimento de saúde.
        """
        qs = cls.objects
        if user.is_usuario_estabelecimento:
            estabelecimento_saude_do_user = user.perfil_estabelecimento.estabelecimento_saude
            return qs.filter(codigo_cnes=estabelecimento_saude_do_user.codigo_cnes)
        return qs

    class Meta:
        verbose_name = 'estabelecimento de saúde'
        verbose_name_plural = 'estabelecimentos de saúde'


class AssociacaoNomeEstabelecimentoSaude(models.Model):
    codigo_cnes = models.CharField(verbose_name='código CNES', max_length=7, primary_key=True)
    nome = models.CharField(max_length=255)
    estabelecimento_saude = models.ForeignKey('EstabelecimentoSaude', on_delete=models.CASCADE, null=True)

    def __str__(self):
        if self.estabelecimento_saude:
            return '{} - {} ({})'.format(self.codigo_cnes, self.nome, self.estabelecimento_saude.nome)
        else:
            return '{} - {} ({})'.format(self.codigo_cnes, self.nome, None)

    def _remove_nome_do_cache(self, nome):
        nomes_pendentes = ControleCache.nomes_estabelecimento_a_associar()
        nomes_pendentes.remove([nome,])

    def save(self, *args, **kwargs):
        self.codigo_cnes = self.estabelecimento_saude.codigo_cnes
        super(AssociacaoNomeEstabelecimentoSaude, self).save(*args, **kwargs)

        self._remove_nome_do_cache(self.nome)

    class Meta:
        verbose_name = 'associação de nome e estabelecimento de sáude'
        verbose_name_plural = 'associações de nomes de estabelecimentos de sáude'


class Sexo():
    MASCULINO = 'M'
    FEMININO = 'F'
    NAO_INFORMADO = 'N'
    INDEFINIDO = 'I'

    CHOICES = (
        (MASCULINO, u'Masculino'),
        (FEMININO, u'Feminino'),
        (NAO_INFORMADO, u'Não Informado'),
        (INDEFINIDO, u'Indefinido')
    )

class PessoaFisica(models.Model):

    FIELDS = OrderedDict([
        ['cpf', BRCPFFormField(label='CPF', max_length=11, help_text='Informe apenas os números')],
        ['nome', forms.CharField(label='Nome completo')],
        ['cns', forms.CharField(label='CNS', required=False)],
        ['sexo', forms.ChoiceField(label='Sexo', choices=[['', '---'], ['F', 'F'], ['M', 'M']], required=False)],
        ['data_de_nascimento', forms.DateField(label='Data de nascimento', required=False)],
        ['telefones', forms.CharField(label='Telefone de contato', max_length=60, required=False)],  # phonenumber
        ['celulares', forms.CharField(label='Telefone celular', max_length=60, required=False)],  # phonenumber
        ['email', forms.EmailField(label='Email', max_length=80, required=False)],
        ['cep', forms.CharField(label='CEP', max_length=9, required=False)],
        ['logradouro', forms.CharField(label='Logradouro', max_length=80, required=False)],
        ['numero', forms.CharField(label='Número (SN para sem número)', max_length=10, required=False)],
        ['complemento', forms.CharField(label='Complemento', max_length=80, required=False)],
        ['bairro', forms.CharField(label='Bairro', max_length=80, required=False)],  # fk para bairro?
        ['municipio', forms.ModelChoiceField(label='Município', queryset=Municipio.objects.all(), required=False)],  # fk para municipio
    ])
    cpf = models.CharField(
        verbose_name='CPF', max_length=11, primary_key=True, validators=[MinLengthValidator(11)], unique=True)

    nome = models.CharField(max_length=80)
    cns = models.CharField(u'Cartão Sus', max_length=15, null=True, blank=True)
    sexo = models.CharField(u'Sexo', max_length=1, choices=Sexo.CHOICES, default=Sexo.NAO_INFORMADO)
    data_de_nascimento = models.DateField(u'Data de Nascimento', null=True)
    telefones = models.CharField(u'Telefones', max_length=60, null=True, blank=True)
    celulares = models.CharField(u'Celulares', max_length=60, null=True, blank=True)
    email = models.CharField(u'Email', max_length=80, null=True, blank=True)
    nome_da_mae = models.CharField(max_length=255, blank=True)

    RACAS = ['Branca', 'Preta', 'Parda', 'Amarela', 'Indígena']
    RACA_CHOICES = zip(RACAS, RACAS)
    raca = models.CharField(
        max_length=255,
        choices=RACA_CHOICES,
        blank=True,
        verbose_name='Raça',
    )
    nome_social = models.CharField(max_length=255, blank=True)
    logradouro = models.CharField(u'Logradouro', max_length=80, null=True, blank=True)
    numero = models.CharField(u'Número', max_length=10, null=True, blank=True)
    complemento = models.CharField(u'Complemento', max_length=80, null=True, blank=True)
    bairro = models.CharField(u'Bairro', max_length=80, null=True, blank=True)
    municipio = models.ForeignKey('base.Municipio', null=True, blank=True, on_delete=models.CASCADE)
    cep = CepModelField(u'CEP', null=True, blank=True)

    def __str__(self):
        return '{} - {}'.format(self.cpf, self.nome)

    def get_dados_pessoa(self):
        dados = self.__dict__.copy()
        dados.pop('_state')
        return dados

    @staticmethod
    def get_by_cpf_ou_cnes(cpf_ou_cns):
        cpf_ou_cns = digits(cpf_ou_cns)
        return PessoaFisica.objects.filter(
            models.Q(cpf=cpf_ou_cns) |
            models.Q(cns=cpf_ou_cns)
        ).first()

    @staticmethod
    def get_or_create_by_cpf_ou_cnes(cpf_ou_cns, api_sleep_time=0):
        cpf_ou_cns = digits(cpf_ou_cns)
        if not cpf_ou_cns:
            return None
        pf = PessoaFisica.get_by_cpf_ou_cnes(cpf_ou_cns)
        if not pf:
            dados_cns = rest_cns.get_dados(cpf_ou_cns=cpf_ou_cns, sleep_time=api_sleep_time)
            if not dados_cns:
                return None
            cpf_do_cns = digits(dados_cns['cpf'])
            pf_by_cpf = PessoaFisica.get_by_cpf_ou_cnes(cpf_do_cns)
            if not pf_by_cpf:  # pode ser que o CPF já exista na base, pois uma pessoa pode ter diferentes CNS.
                pf = PessoaFisica.objects.create(
                    cpf=cpf_do_cns,
                    cns=dados_cns['cns'],
                    sexo=dados_cns['sexo'],
                    data_de_nascimento=dados_cns['data_de_nascimento'],
                    nome=dados_cns['nome'],
                    cep=dados_cns['cep'],
                    logradouro=dados_cns['logradouro'],
                    numero=dados_cns['numero'],
                    complemento=dados_cns['complemento'],
                    bairro=dados_cns['bairro'],
                    municipio_id=dados_cns.get('municipio'),
                    nome_da_mae=dados_cns['nome_da_mae'],
                )
            else:
                pf_by_cpf.cns = pf_by_cpf.cns or dados_cns['cns']
                pf_by_cpf.sexo = pf_by_cpf.sexo or dados_cns['sexo']
                pf_by_cpf.data_de_nascimento = pf_by_cpf.data_de_nascimento or dados_cns['data_de_nascimento']
                pf_by_cpf.save()
                return pf_by_cpf
        return pf


    @classmethod
    def atualizar_dados_monitoramento(cls, cpf, dados_monitoramento):
        pessoa, created = cls.objects.update_or_create(
            cpf=cpf, defaults={**dados_monitoramento}
        )
        return pessoa


class AssociacaoOperadorCNES(models.Model):
    cpf = models.CharField(verbose_name='CPF', max_length=11, primary_key=True)
    estabelecimento_saude = models.ForeignKey('EstabelecimentoSaude', on_delete=models.CASCADE, null=True)
    dados = JSONField()

    def __str__(self):
        return '{} - {}'.format(self.cpf, self.estabelecimento_saude)

    @classmethod
    def recuperar_nomes_a_serem_associados(cls):
        '''
        retorna uma lista de tuplas com os dados (nome, cpf, codigo_cnes, email)
        Ex:
        (
            ('fulano', '111.111.111-11', '1111111', 'fulano@gmail.com'),
        )
        :return:
        '''
        operadores_a_serem_associados = []
        qs = AssociacaoOperadorCNES.objects.filter(estabelecimento_saude__isnull=True)
        qs = qs.values_list('dados__operador_nome_completo', 'dados__operador_cpf', 'dados__operador_cnes', 'dados__operador_email')
        for dados in qs:
            nome, cpf, cnes, email = dados
            if nome is None:
                continue
            dados_operadores = (nome,
                                cpf,
                                cnes or '',
                                email or ''
            )
            operadores_a_serem_associados.append(dados_operadores)
        return operadores_a_serem_associados

    @classmethod
    def definir_principais(cls, cpfs_associados):
        '''
        recebe uma lista de tuplas com cpfs e código cnes do estabelecimento.
        Ex.:
        (
        ('098.767.444-70', '24084457')
        )
        :param cpfs_associados:lista de tuplas com cpfs e código cnes do estabelecimento.
        :return:
        '''
        total_updated = 0
        for cpf, estabelecimento in cpfs_associados:
            cpf = cpf.replace('.','').replace('-','')
            update = AssociacaoOperadorCNES.objects.filter(cpf=cpf).update(estabelecimento_saude=estabelecimento)
            total_updated += update
        return total_updated
