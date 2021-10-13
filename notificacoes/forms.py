import hashlib
import re
from datetime import datetime

from django import forms
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.transaction import atomic
from localflavor.br.forms import BRCPFField

from base.alertas import Alerta
from base.caches import ControleCache
from base.models import Bairro, PessoaFisica, Usuario, EstabelecimentoSaude, Distrito, Municipio
from base.signals import fonte_de_dados_indicadores_alterados
from base.utils import calculateAge, serialize_dict
from .models import Notificacao, UploadImportacao, Monitoramento, PacienteInternacao, Obito, TipoArquivo, \
    TipoMotivoEncerramento, TipoFonteDados
from .processar_notificacoes import ObterNotificacao


class DateInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kwargs):
        kwargs["format"] = "%Y-%m-%d"
        super().__init__(**kwargs)


class UploadImportacaoSivepForm(forms.ModelForm):
    arquivo = forms.FileField(help_text='Arquivo exportado do Sivep-Gripe VE')

    def save(self, commit=True):
        self.instance.tipo = TipoArquivo.SIVEP_GRIPE_DBF
        return super(UploadImportacaoSivepForm, self).save()

    class Meta:
        model = UploadImportacao
        fields = ('arquivo',)


class UploadImportacaoESUSVEForm(forms.ModelForm):
    arquivo = forms.FileField(help_text='Arquivo exportado do e-SUS VE')

    class Meta:
        model = UploadImportacao
        fields = ('arquivo',)


class GALForm(forms.ModelForm):
    numero_gal = forms.CharField(label='Requisição do GAL', min_length=12, max_length=12,
                                 help_text='Digite o número correspondente ao exame no sistema GAL')

    class Meta:
        model = Notificacao
        fields = ('numero_gal',)


class InativarNotificacoesFormClass(forms.Form):
    def __init__(self, page=None, *args, **kwargs):
        super(InativarNotificacoesFormClass, self).__init__(*args, **kwargs)
        self.informacoes_repetidas = Notificacao.recuperar_notificacoes_similares()

        self.nomes_chaves = Notificacao.MAPEAMENTO_COLUNAS
        self.nomes_chaves['numero_da_notificacao'] = 'Número da Notificação'
        self.nomes_chaves['fonte_dados'] = 'Fonte de dados'

        # A variável self.informacoes_repetidas antes armazenava uma lista contendo uma lista de dicionários com
        # as colunas das notificações similares.
        # Agopa a variável é um dicionário onde a chave é uma tupla no formato
        #  "esusve_notificacoes_similares_('2020-05-26T12:41:28.091Z', 'MARCELO GLAUBER DA SILVA PEREIRA', '1985-03-24T03:00:00.000Z')
        # e o valor continua igual como era antes, ou seja, se vc fizer
        # list(self.informacoes_repetidas.values()) # irá ter justamente o conteúdo da variável antes da alteração.

        # Demais detalhes do conteúdo do cache, veja descrição em _CacheNotificacoesSimilares(_cacheBase)


        self.paginator = Paginator(list(self.informacoes_repetidas.values()), 20)
        self.page_obj = self.paginator.get_page(page)

        agrupamentos = []
        if list(self.informacoes_repetidas.values()):
            for idx, agrupamento in enumerate(self.page_obj, 1):
                numeros = [i['pk'] for i in agrupamento]
                field = forms.MultipleChoiceField(
                    widget=forms.CheckboxSelectMultiple,
                    choices=zip(numeros, numeros),
                    required=False
                )
                chave = f'{agrupamento[0]["nome_completo"]}{agrupamento[0]["data_de_nascimento"]}{agrupamento[0]["data_da_notificacao"]}'
                chave = hashlib.sha224(chave.encode()).hexdigest()[:10]
                field_name = 'group_{}'.format(chave)
                self.base_fields[field_name] = field
                cols = []
                for col in sorted(agrupamento[0].keys()):
                    if col in ('nome_completo', 'data_da_notificacao', 'data_de_nascimento', 'pk', 'fonte_dados'):
                        # não exibindo essas colunas porque tais informações já estão no título de cada agrupamento
                        continue
                    cols.append(dict(name=col, label=self.nomes_chaves.get(col, col)))
                agrupamentos.append(
                    dict(
                        field_name=field_name,
                        cols=cols,
                        object_list=agrupamento,
                    )
                )
        self.agrupamentos = agrupamentos

    def save(self):  # salva e retorna a qtd de agrupamentos pendentes
        numeros_requisicoes_principais = [v for v in self.cleaned_data.values() if v]
        if numeros_requisicoes_principais:
            Notificacao.definir_principais(numeros_requisicoes_principais=numeros_requisicoes_principais)
        return len(self.informacoes_repetidas) - len(numeros_requisicoes_principais)


class AtualizarAssociacaoBairroNotificacaoForm(forms.Form):
    def __init__(self, *args, bairros_associados=None, **kwargs):
        super().__init__(*args, **kwargs)
        bairros = Bairro.ativos.order_by('nome').all()
        self.bairros_associados = bairros_associados
        if self.bairros_associados:
            for bairro_associado, num_notificacao in self.bairros_associados:
                if bairro_associado:
                    field_name = num_notificacao
                    self.fields[field_name] = forms.ModelChoiceField(required=False,
                                                                     label=f'{bairro_associado}',
                                                                     queryset=bairros)

    def obter_notificacao_bairro(self):
        return [(bairro, self.cleaned_data[bairro]) for bairro in self.changed_data]


class AtualizarAssociacaoBairroNotificacaoForm(forms.Form):
    def __init__(self, *args, bairros_associados=None, **kwargs):
        super().__init__(*args, **kwargs)
        bairros = Bairro.ativos.order_by('nome').all()
        self.bairros_associados = bairros_associados
        if self.bairros_associados:
            for bairro_associado, num_notificacao in self.bairros_associados:
                if bairro_associado:
                    field_name = num_notificacao
                    self.fields[field_name] = forms.ModelChoiceField(required=False,
                                                                     label=f'{bairro_associado}',
                                                                     queryset=bairros)

    def obter_notificacao_bairro(self):
        return [(bairro, self.cleaned_data[bairro]) for bairro in self.changed_data]


class AssociacaoBairroNotificacaoForm(forms.Form):
    def __init__(self, *args, notificacoes=None, **kwargs):
        super().__init__(*args, **kwargs)
        bairros = Bairro.ativos.order_by('nome').all()
        self.notificacoes = notificacoes
        if self.notificacoes:
            for notificacao in self.notificacoes:
                num_notificacao = notificacao.numero
                field_name = num_notificacao
                self.fields[field_name] = forms.ModelChoiceField(required=False,
                                                                 label=f'Definir bairro',
                                                                 queryset=bairros)
                self.fields[field_name + '_check'] = forms.BooleanField(required=False)

    def obter_notificacao_bairro(self):
        return [(bairro, self.cleaned_data[bairro]) for bairro in self.changed_data if
                not bairro.endswith('_check')]

    def obter_bairros_a_remover(self):
        return [Notificacao.objects.get(numero=notificacao[0:-6]) for notificacao in self.changed_data if
                notificacao.endswith('_check')]


class AssociacaoBairroGeralForm(forms.Form):
    def __init__(self, *args, bairros_faltantes=None, **kwargs):
        super().__init__(*args, **kwargs)
        bairros = Bairro.ativos.order_by('nome').all()
        self.bairros_faltantes = bairros_faltantes
        if self.bairros_faltantes:
            for bairro_faltante, num_notificacao in self.bairros_faltantes:
                if bairro_faltante:
                    field_name = num_notificacao
                    self.fields[field_name] = forms.ModelChoiceField(required=False,
                                                                     label=f'{bairro_faltante}',
                                                                     queryset=bairros)
                    self.fields[field_name + '_check'] = forms.BooleanField(required=False)

    def obter_notificacao_bairro(self):
        return [(bairro, self.cleaned_data[bairro]) for bairro in self.changed_data if
                not bairro.endswith('_check')]

    def obter_bairros_a_remover(self):
        return [Notificacao.objects.get(numero=notificacao[0:-6]) for notificacao in self.changed_data if
                notificacao.endswith('_check')]


class AssociacaoPacienteModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        nome = obj.dados["nome_completo"]
        data_de_nascimento = datetime.strptime(obj.dados["data_de_nascimento"], '%d/%m/%Y')
        idade = calculateAge(data_de_nascimento)
        cpf = obj.dados["cpf"] or ''
        resultado_do_teste = obj.dados["resultado_do_teste"] or ''
        return f'{nome} / {obj.dados["data_de_nascimento"]} ({idade} anos) / {cpf} / {resultado_do_teste}'


class AssociacaoPacienteForm(forms.Form):
    def __init__(self, *args, pacientes=None, **kwargs):
        super().__init__(*args, **kwargs)
        if len(pacientes) > 0:
            for paciente_internacao, nomes_similares in pacientes:
                id, nome, data_nascimento = paciente_internacao
                field_name = str(id)
                dados_internacao = nomes_similares['dados_internacao']
                dados_notificacao = nomes_similares['dados_notificacao']
                pk_similares = [tupla[3] for tupla in dados_notificacao]
                self.fields[field_name] = AssociacaoPacienteModelChoiceField(required=False,
                                                                             label=f"{nome}|{data_nascimento.strftime('%d/%m/%Y')}",
                                                                             queryset=Notificacao.objects.filter(
                                                                                 numero__in=pk_similares))
            self.pacientes = {f'id_{k[0]}': v for k, v in pacientes}


class AssociacaoOperadorCNESForm(forms.Form):
    def __init__(self, *args, operadores=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.operadores = operadores
        if self.operadores:
            for dados in self.operadores:
                field_name = f'cpf{dados[1]}'
                self.fields[field_name] = forms.ModelChoiceField(queryset=EstabelecimentoSaude.objects.all(),
                                                                 required=False, label='|'.join(dados))


class AssociacaoNomeEstabelecimentoForm(forms.Form):
    def __init__(self, *args, estabelecimentos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.estabelecimentos = estabelecimentos
        if self.estabelecimentos:
            for i, estabelecimento in enumerate(estabelecimentos):
                field_name = str(i)
                self.fields[field_name] = forms.ModelChoiceField(queryset=EstabelecimentoSaude.objects.all(),
                                                                 required=False, label=estabelecimento)


class AlterarAssociacaoNomeEstabelecimentoForm(forms.Form):
    def __init__(self, *args, estabelecimentos=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.estabelecimentos = estabelecimentos
        if self.estabelecimentos:
            for i, estabelecimento in enumerate(estabelecimentos):
                field_name = estabelecimento.nome
                estabelecimento_descricao = estabelecimento.estabelecimento_saude.codigo_cnes + " - " + estabelecimento.estabelecimento_saude.nome
                self.fields[field_name] = forms.ModelChoiceField(queryset=EstabelecimentoSaude.objects.all(),
                                                                 required=False,
                                                                 label="{}|{}".format(estabelecimento.nome,
                                                                                      estabelecimento_descricao))


def get_novo_monitoramento_form_instance(request, notificacao, data):
    sim_nao_kw = dict(coerce=int, widget=forms.RadioSelect(), choices=((1, 'Sim'), (0, 'Não')))
    como_se_sente_choices = ['', 'Estável', 'Melhor', 'Pior', 'Assintomático']
    contato_choices = ['', 'Sim, na residência', 'Sim, no trabalho', 'Não', 'Não sabe']
    atuacao_sistema_prisional_choices = ['', 'Interno', 'Policial Penal']

    pf = notificacao.pessoa

    class MonitoramentoForm(forms.Form):

        data_da_investigacao = forms.DateField(label='Data da investigação', widget=DateInput)
        outras_comorbidades = forms.CharField(required=False)
        contato_com_positivo = forms.ChoiceField(
            label='Contato com positivo?',
            choices=zip(contato_choices, contato_choices)
        )
        nome_do_contato = forms.CharField(label='Nome do contato', max_length=100, required=False)
        telefone_do_contato = forms.CharField(label='Telefone do contato', max_length=50, required=False),
        informacoes_adicionais_do_contato = forms.CharField(label='Informações adicionais do contato', max_length=500,
                                                            required=False)

        ocupacao = forms.CharField(label='Ocupação', required=False)
        local_de_trabalho = forms.CharField(label='Local de trabalho', required=False)
        como_se_sente = forms.ChoiceField(
            label='Como está se sentindo hoje?',
            choices=zip(como_se_sente_choices, como_se_sente_choices)
        )


        febre = forms.TypedChoiceField(**sim_nao_kw)
        dor_de_garganta = forms.TypedChoiceField(**sim_nao_kw)
        dispnea = forms.TypedChoiceField(**sim_nao_kw, help_text='falta de ar/dificuldade para respirar',
                                         label='Dispneia')
        diarreia = forms.TypedChoiceField(**sim_nao_kw)
        anosmia = forms.TypedChoiceField(**sim_nao_kw, help_text='diminuição do olfato')
        tosse = forms.TypedChoiceField(**sim_nao_kw)
        outros = forms.CharField(label='Outros sinais/sintomas', required=False)

        pertence_sistema_prisional = forms.TypedChoiceField(label='Pertence ao sistema prisional?', coerce=int, choices=(('', ''), (1, 'Sim'), (0, 'Não')), widget=forms.Select)
        atuacao_sistema_prisional = forms.ChoiceField(
            choices=zip(atuacao_sistema_prisional_choices, atuacao_sistema_prisional_choices),
            label='Atuação no sistema prisional', required=False)
        nome_da_unidade_prisional = forms.CharField(label='Nome da unidade prisional', max_length=100, required=False)


        informacoes_adicionais = forms.CharField(widget=forms.Textarea, label='Informações adicionais',
                                                 required=False)



        def clean_data_da_investigacao(self):
            if self.cleaned_data['data_da_investigacao'] > datetime.today().date():
                raise forms.ValidationError('A data de investigação deve ser anterior ou igual a data atual!')
            return self.cleaned_data['data_da_investigacao']

        def clean_pf_cpf(self):
            if notificacao.pessoa and notificacao.pessoa.cpf != self.cleaned_data['pf_cpf']:
                raise forms.ValidationError('O CPF não pode ser alterado')
            return self.cleaned_data['pf_cpf']

        def fieldnames_pessoa(self):
            return [k for k in self.fields if k.startswith('pf_')]

        def cleaned_data_pessoa(self):
            return {k.lstrip('pf_'): v for k, v in self.cleaned_data.items() if k.startswith('pf_')}

        def fieldnames_monitoramento(self):
            return [k for k in self.fields if not k.startswith('pf_')]

        def cleaned_data_monitoramento(self):
            return {k: v for k, v in self.cleaned_data.items() if not k.startswith('pf_')}

        def has_errors_in_pessoa(self):
            return set(self.fieldnames_pessoa()).intersection(self.errors.keys())

        def save(self):
            dados_pessoais = self.cleaned_data_pessoa()
            cpf = dados_pessoais.pop('cpf')
            pessoa = PessoaFisica.atualizar_dados_monitoramento(cpf, dados_pessoais)
            Notificacao.objects.filter(pk=notificacao.pk).update(pessoa=pessoa)
            dados = self.cleaned_data_monitoramento()
            Monitoramento.objects.create(
                notificacao=notificacao,
                data_de_investigacao=dados['data_da_investigacao'],
                pessoa=pessoa,
                criado_por=request.user,
                dados=serialize_dict(dados),
            )

    initial = {}
    for fname, formfield in PessoaFisica.FIELDS.items():
        formfieldname = f'pf_{fname}'
        MonitoramentoForm.base_fields[formfieldname] = formfield
        initial[formfieldname] = getattr(pf, fname, None)

    form = MonitoramentoForm(data=data, initial=initial)
    return form


class NotificacaoFiltroForm(forms.Form):
    pesquisa_texto = forms.CharField(required=False, label='Pesquisa por texto')
    data_notificacao_de = forms.DateField(required=False, widget=DateInput, label='Data de notificação (de)')
    data_notificacao_ate = forms.DateField(required=False, widget=DateInput, label='Data de notificação (até)')
    bairro = forms.ModelChoiceField(required=False, queryset=None)
    distrito = forms.ModelChoiceField(required=False, queryset=None)
    estabelecimento = forms.ModelChoiceField(required=False, queryset=None, label='Estabelecimento de saúde')
    encerrada = forms.ChoiceField(required=False, choices=([(None, '---------'), ('nao', 'Não'), ('sim', 'Sim'), ]),
                                  label='Encerrada')
    resultado_do_teste = forms.ChoiceField(required=False, label='Resultado do teste')
    estado_do_teste = forms.ChoiceField(required=False, label='Estado do teste')
    evolucao_caso = forms.ChoiceField(required=False, label='Evolução do caso')
    classificacao_final = forms.ChoiceField(required=False, label='Classificação final')
    resultados_por_pagina = forms.IntegerField(required=False, label='Nº de resultados por página', min_value=1)
    fonte_de_dados = forms.ChoiceField(required=False, choices=[[None, '---------']]+TipoFonteDados.TIPO)

    def __init__(self, usuario: Usuario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

        em_branco = (None, '---------')
        self.filtros_extra = ControleCache.filtros_de_notificacao().get()

        for campo, lista in self.filtros_extra.items():
            lista = list(lista)
            prepend = [em_branco]
            if None in lista:
                lista.remove(None)
                if campo == 'classificacao_final':
                    prepend.append(('None', 'Suspeito'))
                else:
                    prepend.append(('None', 'Não informado'))
            self.fields[campo].choices = prepend + list(zip(lista, lista))

        self.fields['bairro'].queryset = Bairro.qs_visiveis(usuario)

        codigos_cnes = Notificacao.qs_visiveis(usuario).values_list('estabelecimento_saude__codigo_cnes')
        qs_estabelecimeto = EstabelecimentoSaude.objects.filter(codigo_cnes__in=codigos_cnes)
        self.fields['estabelecimento'].queryset = qs_estabelecimeto

        self.fields['distrito'].queryset = Distrito.qs_visiveis(usuario)
        self.fields['resultados_por_pagina'].initial = 20
        self.fields['encerrada'].initial = 'nao'

    def obter_queryset(self, qs):
        pesquisa_texto = self.cleaned_data['pesquisa_texto']
        fonte_de_dados = self.cleaned_data['fonte_de_dados']

        if fonte_de_dados:
            qs = qs.filter(fonte_dados=fonte_de_dados)
        if pesquisa_texto:
            qs = qs.filter(
                Q(dados__nome_completo__icontains=pesquisa_texto) | Q(numero__icontains=pesquisa_texto) |
                Q(dados__data_do_inicio_dos_sintomas__icontains=pesquisa_texto))

        for campo in self.filtros_extra.keys():
            valor = self.cleaned_data[campo]
            if valor == 'None':
                params = {f'dados__{campo}': None}
            elif valor:
                params = {f'dados__{campo}': valor}
            else:
                continue
            qs = qs.filter(**params)

        bairro = self.cleaned_data['bairro']
        estabelecimento = self.cleaned_data['estabelecimento']
        distrito = self.cleaned_data['distrito']
        encerrada = self.cleaned_data['encerrada']
        if bairro:
            qs = qs.filter(bairro=bairro)
        if estabelecimento:
            qs = qs.filter(estabelecimento_saude=estabelecimento)
        if distrito:
            qs = qs.filter(bairro__distrito=distrito)
        if encerrada:
            qs = qs.filter(encerrada_em__isnull=True) if encerrada == 'nao' or encerrada == '' else qs.exclude(
                encerrada_em__isnull=True)
        data_de = self.cleaned_data['data_notificacao_de']
        data_ate = self.cleaned_data['data_notificacao_ate']
        if data_de:
            qs = qs.filter(data__gte=data_de)
        if data_ate:
            qs = qs.filter(data__lte=data_ate)

        return qs.all()

    def obter_resultados_por_pagina(self):
        return self.cleaned_data['resultados_por_pagina']


class MonitoramentoFiltroForm(forms.Form):
    MONITORAMENTO_PENDENTE_CHOICES = [
        (None, '---------'),
        (24, '24 horas'),
        (48, '48 horas'),
    ]

    pesquisa_texto = forms.CharField(required=False, label='Pesquisa por nome')
    data_de = forms.DateField(required=False, widget=DateInput, label='Data de investigação (de)')
    data_ate = forms.DateField(required=False, widget=DateInput, label='Data de investigação (até)')
    estabelecimento = forms.ModelChoiceField(required=False, queryset=None, label='Estabelecimento de saúde')
    operador = forms.ModelChoiceField(required=False, queryset=None, label='Operador')
    distrito = forms.ModelChoiceField(required=False, queryset=None, label='Distrito')
    monitoramento_pendente = forms.TypedChoiceField(required=False, label='Monitoramento pendente', coerce=int,
                                                    choices=MONITORAMENTO_PENDENTE_CHOICES)
    resultados_por_pagina = forms.IntegerField(required=False, label='Nº de resultados por página', min_value=1)

    def __init__(self, usuario: Usuario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

        self.fields['estabelecimento'].queryset = EstabelecimentoSaude.qs_visiveis(usuario)
        self.fields['operador'].queryset = Usuario.objects.filter(monitoramento__isnull=False).distinct()
        self.fields['distrito'].queryset = Distrito.qs_visiveis(usuario)
        self.fields['resultados_por_pagina'].initial = 20

    def obter_queryset(self, qs):
        monitoramento_pendente = self.cleaned_data['monitoramento_pendente']
        if monitoramento_pendente:
            qs = Monitoramento.get_pendentes(monitoramento_pendente, qs=qs)
        pesquisa_texto = self.cleaned_data['pesquisa_texto']
        if pesquisa_texto:
            qs = qs.filter(
                Q(notificacao__dados__nome_completo__icontains=pesquisa_texto) | Q(
                    notificacao__numero__icontains=pesquisa_texto))

        estabelecimento = self.cleaned_data['estabelecimento']
        if estabelecimento:
            qs = qs.filter(notificacao__estabelecimento_saude=estabelecimento)

        operador = self.cleaned_data['operador']
        if operador:
            qs = qs.filter(criado_por=operador)

        distrito = self.cleaned_data['distrito']
        if distrito:
            qs = qs.filter(notificacao__estabelecimento_saude__distrito=distrito)

        data_de = self.cleaned_data['data_de']
        data_ate = self.cleaned_data['data_ate']
        if data_de:
            qs = qs.filter(data_de_investigacao__gte=data_de)
        if data_ate:
            qs = qs.filter(data_de_investigacao__lte=data_ate)
        return qs.all().order_by('-data_de_investigacao')

    def obter_resultados_por_pagina(self):
        return self.cleaned_data['resultados_por_pagina']


class ConfirmarObitoPacienteInternacaoForm(forms.ModelForm):
    class Meta:
        model = PacienteInternacao
        fields = ['cns', 'data_do_obito', 'resultado_do_teste_covid_19',
                  'estabelecimento_saude', 'sexo',
                  'idade', 'endereco_logradouro', 'endereco_numero', 'endereco_bairro']

    def __init__(self, *args, **kwargs):
        self.field_order = ['data_do_obito', 'resultado_do_teste_covid_19',
                            'estabelecimento_saude', 'sexo', 'idade',
                            'endereco_logradouro', 'endereco_numero', 'endereco_bairro']
        super(ConfirmarObitoPacienteInternacaoForm, self).__init__(*args, **kwargs)
        self.initial.update(
            resultado_do_teste_covid_19=self.instance._get_resultado_do_teste_covid_19(),
        )
        notificacao_vinculada = self.instance.get_notificacao_vinculada()
        if notificacao_vinculada:
            qs_notificacoes = Notificacao.objects.none()  # evitar field
            sexo = notificacao_vinculada.dados.get('sexo')
            self.initial.update(dict(
                endereco_logradouro=notificacao_vinculada.dados.get('logradouro'),
                endereco_numero=notificacao_vinculada.dados.get('numero_res'),
                sexo=sexo and sexo[0] or '',
            ))
        else:
            qs_notificacoes = PacienteInternacao.get_notificacoes_com_nomes_similares(
                self.instance.dados_censo_leitos['paciente_nome'],
                self.instance.data_de_nascimento)
        if qs_notificacoes.exists():
            self.field_order.insert(0, 'notificacao')
            self.fields['notificacao'] = forms.ModelChoiceField(
                label='Associar à Notificação',
                queryset=qs_notificacoes,
                required=False,
            )

    def clean_cns(self):
        return re.sub('\D', '', self.cleaned_data.get('cns', ''))

    def clean_estabelecimento_saude(self):
        if self.instance.estabelecimento_saude and self.cleaned_data[
            'estabelecimento_saude'] != self.instance.estabelecimento_saude:
            raise forms.ValidationError('O estabelecimento de saúde não pode ser alterado')
        return self.cleaned_data['estabelecimento_saude']

    @atomic
    def save(self, commit=True):
        instance = super(ConfirmarObitoPacienteInternacaoForm, self).save(commit=commit)
        if self.cleaned_data.get('notificacao'):
            Notificacao.objects.filter(pk=self.cleaned_data['notificacao'].pk).update(paciente_internado=instance)
        fonte_de_dados_indicadores_alterados.send(sender=PacienteInternacao)
        return instance


class EncerramentoCasoForm(forms.ModelForm):
    data_do_encerramento = forms.DateField(label='Data da Cura/Óbito', widget=DateInput)

    class Meta:
        model = Notificacao
        fields = ['encerrada_motivo', 'data_do_encerramento', 'encerrada_observacoes']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super(EncerramentoCasoForm, self).__init__(*args, **kwargs)

    def clean_data_do_encerramento(self):
        if self.cleaned_data['data_do_encerramento'] > datetime.today().date():
            raise forms.ValidationError('A data do encerramento deve ser anterior ou igual a data atual!')
        return self.cleaned_data['data_do_encerramento']

    @atomic
    def save(self, commit=True, **kwargs):

        # Encerrando a notificação
        instance = super(EncerramentoCasoForm, self).save(commit=commit)
        notificacao = self.instance
        notificacao.encerrada_por = self.request.user
        notificacao.encerrada_em = datetime.now()
        notificacao.save()

        # Encerrado por óbito?
        if notificacao.encerrada_motivo == TipoMotivoEncerramento.OBITO:
            Obito.objects.create(
                pessoa=notificacao.pessoa,
                bairro=notificacao.bairro,
                data_do_obito=notificacao.data_do_encerramento,
            )
            Alerta.novo_obito_pendente_validacao()

        return instance


class ObitoCnsCpfForm(forms.Form):
    cpf = BRCPFField(min_length=11, max_length=11, label='CPF somente números', required=False)
    cns = forms.CharField(min_length=15, max_length=15, label='CNS somente números', required=False)

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        if not self.cleaned_data['cpf'] and not self.cleaned_data['cns']:
            raise forms.ValidationError('Informe CPF ou CNS')
        pessoa = PessoaFisica.get_or_create_by_cpf_ou_cnes(
            cpf_ou_cns=self.cleaned_data['cpf'] or self.cleaned_data['cns'])
        if not pessoa:
            raise forms.ValidationError('Pessoa não encontrada com os dados fornecidos')
        Notificacao.validar_se_pode_criar_obito_para_pessoa(pessoa)
        return self.cleaned_data


class VincularPessoaObitoForm(ObitoCnsCpfForm):

    def get_pessoa(self):
        return PessoaFisica.get_by_cpf_ou_cnes(self.cleaned_data['cpf'] or self.cleaned_data['cns'])


class ConfirmarVincularPessoaObitoForm(forms.Form):

    confirmar = forms.BooleanField(label='Confirmar vinculação de óbito à pessoa')

    def __init__(self, obito, pessoa, *args, **kwargs):
        self.obito = obito
        self.pessoa = pessoa
        super().__init__(*args, **kwargs)

    def save(self):
        self.obito.pessoa = self.pessoa
        self.obito.save()
        return self.obito


class RegistrarObitoForm(forms.ModelForm):

    class Meta:
        model = Obito
        fields = ['pessoa', 'numero_declaracao_obito', 'arquivo_declaracao_obito', 'local_do_obito',
                  'data_do_obito', 'resultado_do_teste_covid_19', 'arquivo_resultado_exame_covid19', 'bairro']

    # Fields pessoa
    pessoa_municipio = forms.ModelChoiceField(
        queryset=Municipio.objects, label='Município')
    pessoa_logradouro = forms.CharField(label='Logradouro')
    pessoa_numero = forms.CharField(label='Número')
    pessoa_complemento = forms.CharField(label='Complemento', required=False)
    pessoa_bairro = forms.CharField(required=False, label='Bairro')
    pessoa_cep = forms.CharField(label='CEP')

    field_order = [
        'pessoa',
        'pessoa_municipio',
        'bairro', 'pessoa_bairro', 'pessoa_logradouro', 'pessoa_numero', 'pessoa_complemento', 'pessoa_cep',
        'numero_declaracao_obito', 'arquivo_declaracao_obito', 'local_do_obito', 'data_do_obito',
        'resultado_do_teste_covid_19', 'arquivo_resultado_exame_covid19',
    ]

    @staticmethod
    def get_codigo_ibge_municipio_base():  # usado no template para javascript
        return settings.CODIGO_IBGE_MUNICIPIO_BASE

    def set_form_initial(self, pessoa=None, obito=None):
        default_initial = self.initial
        if obito:
            pessoa = obito.pessoa
            notificacao_dados_pessoa = obito.notificacao and obito.notificacao.get_dados_pessoa() or {}
        else:
            notificacao_dados_pessoa = {}
        extra_initial = {
            'pessoa': pessoa.pk,
            'pessoa_municipio': notificacao_dados_pessoa.get('municipio_id') or pessoa.municipio,
            'pessoa_logradouro': notificacao_dados_pessoa.get('logradouro') or pessoa.logradouro,
            'pessoa_numero': notificacao_dados_pessoa.get('numero') or pessoa.numero,
            'pessoa_bairro': notificacao_dados_pessoa.get('bairro') or pessoa.bairro,
            'bairro': ObterNotificacao.get_bairro(notificacao_dados_pessoa.get('bairro') or pessoa.bairro),
            'pessoa_cep': notificacao_dados_pessoa.get('cep') or pessoa.cep,
        }
        self.initial = extra_initial
        self.initial.update(default_initial)
        self.fields['pessoa'].queryset = PessoaFisica.objects.filter(pk=pessoa.pk)
        self.fields['data_do_obito'].widget = DateInput()

    def clean(self):
        municipio = self.cleaned_data['pessoa_municipio']
        if municipio.pk == self.get_codigo_ibge_municipio_base():
            if not self.cleaned_data['bairro']:
                raise forms.ValidationError('Por favor, selecione o bairro.')
            self.cleaned_data['pessoa_bairro'] = self.cleaned_data['bairro'].nome
        else:
            if not self.cleaned_data['pessoa_bairro']:
                raise forms.ValidationError('Por favor, informe o bairro.')
            self.cleaned_data['bairro'] = Bairro.objects.get(nome=settings.BAIRRO_OUTROS)
        return self.cleaned_data

    @atomic
    def save(self, commit=True):
        obj = super().save(self)
        for k in [k for k in self.cleaned_data if k.startswith('pessoa_')]:
            field_pessoa = k.lstrip('pessoa_')
            setattr(obj.pessoa, field_pessoa, self.cleaned_data[k])
        obj.pessoa.save()
        return obj


class ValidarObitoForm(RegistrarObitoForm):

    class Meta:
        model = Obito
        fields = ['pessoa', 'numero_declaracao_obito', 'arquivo_declaracao_obito', 'local_do_obito',
                  'data_do_obito', 'resultado_do_teste_covid_19', 'arquivo_resultado_exame_covid19', 'bairro',
                  'confirmado_covid19']
    confirmado_covid19 = forms.ChoiceField(required=True,
                                           label='Óbito confirmado por COVID-19? ',
                                           choices=([(None, '---------'), (False, 'Não'), (True, 'Sim'), ]))

    def clean_confirmado_covid19(self):
        if not self.cleaned_data['resultado_do_teste_covid_19'] == "Confirmado" and self.cleaned_data['confirmado_covid19'] == "True":
            raise forms.ValidationError('O Óbito só pode ser validado por COVID-19 se o resultado do teste for Confirmado')
        return self.cleaned_data['confirmado_covid19']


def get_registrar_obito_form(request, pessoa):
    Notificacao.validar_se_pode_criar_obito_para_pessoa(pessoa)
    form = RegistrarObitoForm(data=request.POST or None, files=request.FILES or None)
    form.set_form_initial(pessoa=pessoa)
    return form


def get_validar_obito_form(request, obito):
    form = ValidarObitoForm(instance=obito, data=request.POST or None, files=request.FILES or None)
    form.set_form_initial(obito=obito)
    return form


class ObitoFiltroForm(forms.Form):
    RESULTADO_DO_TESTE_COVID_19_CHOICES = [
        (None, '---------'),
        ("Confirmado", 'Confirmado'),
        ("Descartado", 'Descartado'),
        ("Suspeito", 'Suspeito'),
    ]

    pesquisa_texto = forms.CharField(required=False, label='Pesquisa por nome ou CPF')
    data_de = forms.DateField(required=False, widget=DateInput, label='Data do óbito (de)')
    data_ate = forms.DateField(required=False, widget=DateInput, label='Data do óbito (até)')
    estabelecimento = forms.ModelChoiceField(required=False, queryset=None, label='Local do Óbito')
    resultado_do_teste_covid_19 = forms.TypedChoiceField(required=False, label='Resultado do Teste',
                                                         choices=RESULTADO_DO_TESTE_COVID_19_CHOICES)
    confirmado = forms.ChoiceField(required=False, choices=([(None, '---------'), ('nao', 'Não'), ('sim', 'Sim'), ]),
                                   label='Óbito por COVID-19?')

    def __init__(self, usuario: Usuario, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

        self.fields['estabelecimento'].queryset = EstabelecimentoSaude.qs_visiveis(usuario)

    def obter_queryset(self, qs):
        resultado_do_teste_covid_19 = self.cleaned_data['resultado_do_teste_covid_19']
        if resultado_do_teste_covid_19:
            qs = Obito.objects.filter(resultado_do_teste_covid_19=resultado_do_teste_covid_19)
        pesquisa_texto = self.cleaned_data['pesquisa_texto']
        if pesquisa_texto:
            qs = qs.filter(Q(pessoa__nome__icontains=pesquisa_texto) | Q(pessoa__cpf__icontains=pesquisa_texto))

        estabelecimento = self.cleaned_data['estabelecimento']
        if estabelecimento:
            qs = qs.filter(local_do_obito=estabelecimento)

        confirmado = self.cleaned_data['confirmado']
        if confirmado:
            qs = qs.filter(confirmado_covid19__isnull=False) if confirmado == 'sim' else qs.filter(confirmado_covid19__isnull=True)

        data_de = self.cleaned_data['data_de']
        data_ate = self.cleaned_data['data_ate']
        if data_de:
            qs = qs.filter(data_do_obito__gte=data_de)
        if data_ate:
            qs = qs.filter(data_do_obito__lte=data_ate)
        return qs.all().order_by('-data_do_obito')
