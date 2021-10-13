import csv
from io import StringIO

from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.db.transaction import atomic
from django.utils.crypto import get_random_string
from localflavor.br.forms import BRCPFField

from base.models import Usuario, PerfilDistrito, Distrito, PerfilVigilancia, Municipio, PessoaFisica, \
    PerfilEstabelecimentoSaude, EstabelecimentoSaude, PerfilAtencaoBasica
from base.utils import JSONModelFormMixin, digits, send_password_reset_link

SIM_NAO_CHOICES = (
    (False, 'Não'),
    (True, 'Sim'),
)


class UsuarioForm(UserCreationForm):

    cpf = BRCPFField(max_length=11)

    class Meta:
        model = Usuario
        fields = ("nome", "cpf", "email", "telefone", "password1", "password2")


class UsuarioDistritoForm(UsuarioForm):
    distrito = forms.ModelChoiceField(queryset=Distrito.ativos.all(), required=True, widget=forms.Select)
    gestor = forms.BooleanField(label='É gestor?', required=False)

    def __init__(self, usuario, *args, **kw):
        super(UsuarioDistritoForm, self).__init__(*args, **kw)
        self.usuario = usuario
        if not usuario.is_superuser:
            if usuario.is_usuario_vigilancia:
                self.fields['distrito'].queryset = Distrito.ativos.filter(municipio=usuario.perfil_vigilancia.municipio)
            if usuario.is_usuario_distrito:
                self.fields['distrito'].queryset = Distrito.ativos.filter(
                    municipio=usuario.perfil_distrito.distrito.municipio)

    def save(self, *args, **kw):
        try:
            with transaction.atomic():
                grupo_gestor, created = Group.objects.get_or_create(name='Gestor')
                grupo_gestor.permissions.add(Permission.objects.get(codename='e_gestor'))

                instance = super().save(*args, **kw)
                PerfilDistrito(distrito=self.cleaned_data.get('distrito'), usuario=instance).save()
                grupo, __ = Group.objects.get_or_create(name='Distrito')
                grupo.user_set.add(instance)
                if self.cleaned_data.get('gestor'):
                    grupo_gestor.user_set.add(instance)
                send_password_reset_link(instance)
        finally:
            return instance

    class Meta:
        model = Usuario
        fields = ("nome", "cpf", "email", "telefone", "distrito", "gestor", "password1", "password2")


class UsuarioVigilanciaForm(UsuarioForm):
    gestor = forms.BooleanField(label='É gestor?', required=False)

    def __init__(self, usuario, *args, **kw):
        super().__init__(*args, **kw)
        self.usuario = usuario

    def save(self, *args, **kw):
        try:
            with transaction.atomic():
                grupo_gestor, created = Group.objects.get_or_create(name='Gestor')
                grupo_gestor.permissions.add(Permission.objects.get(codename='e_gestor'))

                instance = super().save(*args, **kw)
                if self.usuario.is_usuario_vigilancia:
                    municipio = self.usuario.perfil_vigilancia.municipio
                else:
                    municipio = Municipio.ativos.first()
                PerfilVigilancia(municipio=municipio, usuario=instance).save()
                grupo, __ = Group.objects.get_or_create(name='CIEVS - Centro de Informações Estratégicas em Vigilância em Saúde')
                grupo.user_set.add(instance)
                if self.cleaned_data.get('gestor'):
                    grupo_gestor.user_set.add(instance)
                send_password_reset_link(instance)
        finally:
            return instance

    class Meta:
        model = Usuario
        fields = ("nome", "cpf", "email", "telefone", "gestor", "password1", "password2")


class UsuarioABForm(UsuarioForm):
    gestor = forms.BooleanField(label='É gestor?', required=False)

    def __init__(self, usuario, *args, **kw):
        super().__init__(*args, **kw)
        self.usuario = usuario

    def save(self, *args, **kw):
        try:
            with transaction.atomic():
                grupo_gestor, created = Group.objects.get_or_create(name='Gestor')
                grupo_gestor.permissions.add(Permission.objects.get(codename='e_gestor'))

                instance = super().save(*args, **kw)
                if self.usuario.is_usuario_vigilancia:
                    municipio = self.usuario.perfil_vigilancia.municipio
                else:
                    municipio = Municipio.ativos.first()
                PerfilAtencaoBasica(municipio=municipio, usuario=instance).save()
                grupo, __ = Group.objects.get_or_create(name='Atenção Básica')
                grupo.user_set.add(instance)
                if self.cleaned_data.get('gestor'):
                    grupo_gestor.user_set.add(instance)
                send_password_reset_link(instance)
        finally:
            return instance

    class Meta:
        model = Usuario
        fields = ("nome", "cpf", "email", "telefone", "gestor", "password1", "password2")


class UsuarioEstabelecimentoSaudeForm(UsuarioForm):

    estabelecimento_saude = forms.ModelChoiceField(queryset=EstabelecimentoSaude.objects.all(), label='Estabelecimento de saúde')

    class Meta:
        model = Usuario
        fields = ("nome", "cpf", "estabelecimento_saude", "email", "telefone", "password1", "password2")

    def __init__(self, usuario, *args, **kw):
        super().__init__(*args, **kw)
        self.usuario = usuario

    @atomic
    def save(self, *args, **kw):
        instance = super().save(*args, **kw)
        PerfilEstabelecimentoSaude.objects.get_or_create(
            estabelecimento_saude=self.cleaned_data['estabelecimento_saude'],
            usuario=instance,
        )
        send_password_reset_link(instance)
        return instance


class AlterarSenhaUsuarioForm(PasswordChangeForm):
    class Meta:
        model = Usuario
        fields = ('old_password', 'new_password1', 'new_password2')


class UsuarioPerfilForm(forms.ModelForm):
    # senha = forms.CharField(widget=forms.PasswordInput, help_text='Para alterar sua senha, clique aqui.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['cpf'].widget.attrs['readonly'] = True
            # self.fields['senha'].widget.attrs['readonly'] = True
            # self.fields['senha'].widget.attrs['value'] = "*****"

    class Meta:
        model = Usuario
        readonly = ("cpf",)
        fields = ("nome", "cpf", "email", "telefone",)


class PessoaFisicaForm(JSONModelFormMixin, forms.ModelForm):

    cpf = BRCPFField(max_length=11)

    def __init__(self, *args, **kwargs):

        for fname, ffield in PessoaFisica.FIELDS.items():
            self.base_fields[fname] = ffield
        super(PessoaFisicaForm, self).__init__(*args, **kwargs)

    class Meta:
        model = PessoaFisica
        fields = ['cpf']
        json_form_fields = PessoaFisica.FIELDS.keys()

    #TODO: Sedir excluir o método atualizar_dados_esusve, pois apaguei o campo PessoaFisica.dados_esusve.
    #TODO: Sedir, validar o cadastor de pessoa física a partir do monitoramento.
    # def save(self, *args, **kwargs):
    #     PessoaFisica.atualizar_dados(self.cleaned_data['cpf'], **self.cleaned_data)


class ImportarUsuariosForm(forms.Form):
    conteudo = forms.CharField(widget=forms.Textarea(attrs={'rows': 20, 'cols': 80}))

    def clean_conteudo(self):

        def ajusta_dic(dic):
            for k, v in dic.items():
                dic[k] = v.strip() if isinstance(v, str) else ''

        usuarios = []
        io_file = StringIO(self.cleaned_data['conteudo'])
        for i in csv.DictReader(io_file, delimiter='\t'):
            ajusta_dic(i)
            cpf = digits(i['cpf'])
            if Usuario.objects.filter(cpf=cpf).exists():
                raise forms.ValidationError(f'Usuário {cpf} já existe')
            if not i['nome'] or not i['email']:
                raise forms.ValidationError(f'Defina nome e email para {cpf}')
            if not i['cnes_unidade'] and not i['id_distrito']:
                raise forms.ValidationError(f'Defina cnes_unidade ou id_distrito para {cpf}')
            estabelecimento, distrito = None, None
            if i['cnes_unidade']:
                estabelecimento = EstabelecimentoSaude.objects.filter(codigo_cnes=i['cnes_unidade']).first()
                if not estabelecimento:
                    raise forms.ValidationError('Estabelecimento {} não encontrado'.format(i['cnes_unidade']))
            if i['id_distrito']:
                distrito = Distrito.objects.filter(id=i['id_distrito']).first()
                if not distrito:
                    raise forms.ValidationError('Distrito {} não encontrado'.format(i['id_distrito']))
            usuarios.append(
                dict(
                    cpf=cpf,
                    nome=i['nome'],
                    email=i['email'],
                    telefone=i['telefone'],
                    estabelecimento=estabelecimento,
                    distrito=distrito,
                )
            )
        return usuarios

    @atomic
    def save(self):
        for u_dict in self.cleaned_data['conteudo']:
            distrito = u_dict.pop('distrito')
            estabelecimento = u_dict.pop('estabelecimento')
            u = Usuario(**u_dict)
            u.set_password(get_random_string())
            u.save()
            if distrito and not estabelecimento:  # Informou distrito mas não informou estabelecimento, então é usuário de distrito
                PerfilDistrito.objects.create(usuario=u, distrito=distrito, ativo=True)
                grupo_gestor, created = Group.objects.get_or_create(name='Gestor')
                grupo_gestor.user_set.add(u)
            if estabelecimento:  # Informou estabelecimento, então é usuário de estabelecimento
                PerfilEstabelecimentoSaude.objects.create(usuario=u, estabelecimento_saude=estabelecimento)
            if distrito and estabelecimento:  # Aproveitando para atualizar distrito do estabelecimento
                EstabelecimentoSaude.objects.filter(pk=estabelecimento.pk).update(distrito=distrito)
            send_password_reset_link(u)
