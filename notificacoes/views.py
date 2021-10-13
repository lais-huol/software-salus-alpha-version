from datetime import date, timedelta
from urllib.parse import urlencode

from braces.views import SetHeadlineMixin
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, FormView, UpdateView, ListView

from base.alertas import Alerta
from base.caches import ControleCache
from base.filters import NotificacaoFilter
from base.models import AssociacaoNomeEstabelecimentoSaude, AssociacaoOperadorCNES, PessoaFisica
from base.models import EstabelecimentoSaude
from base.utils import qs_to_csv_response, qs_to_xlsx_response
from notificacoes.processar_notificacoes import ObterNotificacaoSivepGripeDBF
from .forms import AssociacaoBairroGeralForm, AssociacaoOperadorCNESForm, \
    AssociacaoPacienteForm, AssociacaoNomeEstabelecimentoForm, UploadImportacaoESUSVEForm, \
    GALForm, get_novo_monitoramento_form_instance, NotificacaoFiltroForm, MonitoramentoFiltroForm, \
    ConfirmarObitoPacienteInternacaoForm, AssociacaoBairroNotificacaoForm, AlterarAssociacaoNomeEstabelecimentoForm, \
    UploadImportacaoSivepForm, AtualizarAssociacaoBairroNotificacaoForm, InativarNotificacoesFormClass, \
    EncerramentoCasoForm, get_registrar_obito_form, ObitoCnsCpfForm, ObitoFiltroForm, VincularPessoaObitoForm, \
    get_validar_obito_form, ConfirmarVincularPessoaObitoForm
from .models import Notificacao, Bairro, Monitoramento, PacienteInternacao, Obito

QTD_REGISTROS_POR_PAGINA = 50


class NotificacaoPessoaView(DetailView):
    model = PessoaFisica
    context_object_name = 'pessoa'
    template_name = 'notificacoes/notificacao_pessoa.html'

    def get_context_data(self, **kwargs):
        context = super(NotificacaoPessoaView, self).get_context_data(**kwargs)
        context['notificacoes'] = self.object.notificacao_set.all()
        return context


class NotificacaoListView(LoginRequiredMixin, ListView):
    template_name = 'notificacoes/notificacao_list.html'
    queryset = Notificacao.ativas
    paginate_by = 10
    titulo = 'Notificações ativas'
    form = None

    def get_queryset(self):
        self.form = NotificacaoFiltroForm(self.request.user, data=self.request.GET)
        if self.form.is_valid():
            self.paginate_by = self.form.obter_resultados_por_pagina() or 10
            qs = self.form.obter_queryset(Notificacao.qs_visiveis(self.request.user, self.queryset))
        else:
            qs = Notificacao.qs_visiveis(self.request.user, self.queryset)
            qs = qs.filter(encerrada_em__isnull=True)
        return qs.order_by('-numero')

    def get_context_data(self, **kwargs):
        context = super(NotificacaoListView, self).get_context_data(**kwargs)
        context['titulo'] = self.titulo
        context['form'] = self.form
        return context


class NotificacaoExportacaoView(View):
    queryset = Notificacao.ativas

    def get(self, request):
        campos = {
            'numero': 'Número',
            'ativa': 'Extra Ativa',
            'numero_gal': 'Extra Requisição GAL',
            'bairro__nome': 'Extra Bairro',
            'estabelecimento_saude__codigo_cnes': 'Extra Código CNES do Estabelecimento de Cadastro',
            'estabelecimento_saude__dados_cnes__NO_FANTASIA': 'Extra Nome do Estabelecimento de Cadastro',
            'latitude': 'Extra Latitude',
            'longitude': 'Extra Longitude',
            'estabelecimento_saude_referencia__codigo_cnes': 'Extra Código CNES do Estabelecimento de Referência',
            'estabelecimento_saude_referencia__dados_cnes__NO_FANTASIA': 'Extra Nome do Estabelecimento de Referência',
        }

        qs = self.get_queryset().values(*campos.keys(),
                                        *[f'dados__{x}' for x in Notificacao.MAPEAMENTO_COLUNAS.keys()],
                                        *[f'paciente_internado__dados_censo_leitos__{x}' for x in
                                          PacienteInternacao.MAPEAMENTO_COLUNAS.keys()])

        return self.exportar(qs, 'arquivo', {
            **campos,
            **{f'dados__{k}': f'{v}' for k, v in Notificacao.MAPEAMENTO_COLUNAS.items()},
            **{f'paciente_internado__dados_censo_leitos__{k}': f'Extra {v}' for k, v in
               PacienteInternacao.MAPEAMENTO_COLUNAS.items()},
        })

    def exportar(self, qs, arquivo, dados):
        raise NotImplementedError

    def get_queryset(self):
        self.form = NotificacaoFiltroForm(self.request.user, data=self.request.GET)
        if self.form.is_valid():
            self.paginate_by = self.form.obter_resultados_por_pagina() or 10
            return self.form.obter_queryset(Notificacao.qs_visiveis(self.request.user, self.queryset))
        return self.queryset.none()


class NotificacaoXLSXView(LoginRequiredMixin, NotificacaoExportacaoView):
    def exportar(self, qs, arquivo, dados):
        return qs_to_xlsx_response(qs, arquivo, dados)


class NotificacaoCSVView(LoginRequiredMixin, NotificacaoExportacaoView):
    def exportar(self, qs, arquivo, dados):
        return qs_to_csv_response(qs, arquivo, dados)


class NotificacaoPendenteListView(NotificacaoListView):
    queryset = Notificacao.pendentes
    titulo = 'Notificações pendentes'


class NotificacaoGALListView(PermissionRequiredMixin, ListView):
    permission_required = 'notificacoes.pode_alterar_o_gal'
    template_name = 'notificacoes/gal_list.html'
    queryset = Notificacao.ativas.filter(dados__resultado_do_teste=None, numero_gal__isnull=True)
    paginate_by = 20

    def get_queryset(self):
        self.form = NotificacaoFiltroForm(self.request.user, data=self.request.GET)

        if self.request.user.is_usuario_distrito:
            qs = self.queryset.filter(bairro__distrito=self.request.user.perfil_distrito.distrito)
        else:
            qs = Notificacao.qs_visiveis(self.request.user, self.queryset)
        return qs.order_by('-numero')

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super(NotificacaoGALListView, self).get_context_data()
        context['titulo'] = 'Associar número de requisição do GAL'
        context['form'] = self.form
        return context


@permission_required('notificacoes.pode_definir_notificacoes_principais')
def definir_principais(request):
    if not Notificacao.get_similaridades_processamento_foi_concluido():
        messages.warning(request, 'Há um processamento em andamento. '
                                  'Aguarde sua finalização para poder tratar as similaridades de notificações.')

    form = InativarNotificacoesFormClass(page=request.GET.get('page'), data=request.POST or None)
    page_obj = form.page_obj
    paginator = form.paginator

    if form.is_valid():
        qtd_agrupamentos_ainda_pendentes = form.save()
        messages.success(request, 'As notificações selecionadas foram devidamente definidas como principais.')
        if qtd_agrupamentos_ainda_pendentes:
            return HttpResponseRedirect(reverse('notificacoes:definir_principais'))
        messages.info(request, 'Não há mais notificações para analisar.')
        return HttpResponseRedirect(reverse('notificacoes:listar'))
    return render(request, 'notificacoes/definir_principais.html', locals())


@login_required
def listar_alteradas(request):
    dia = date.today()
    historico_alteracoes = Notificacao.recuperar_notificacoes_alteradas(dia)
    return render(request, 'notificacoes/listar_alteradas.html', locals())


@login_required
def novo_monitoramento(request, pk):
    notificacao = get_object_or_404(Notificacao.qs_visiveis(request.user), pk=pk)
    dados_pessoa = notificacao.get_dados_pessoa()
    ultimo_monitoramento = notificacao.monitoramento_set.order_by('-id').first()

    form = get_novo_monitoramento_form_instance(request, notificacao, request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Monitoramento cadastrado com sucesso.')
        return HttpResponseRedirect(reverse_lazy('notificacoes:visualizar', args=[pk]))


    possui_monitoramentos = notificacao.monitoramento_set.exclude(dados={}).count() >= 1
    if possui_monitoramentos and request.user.has_perm('notificacoes.pode_encerrar_monitoramento'):
        form_encerramento = EncerramentoCasoForm(request.POST or None, instance=notificacao, request=request)
        if form_encerramento.is_valid():
            form_encerramento.save()
            messages.success(request, 'Encerramento cadastrado com sucesso.')
            return HttpResponseRedirect(reverse_lazy('notificacoes:visualizar', args=[pk]))


    return render(request, 'notificacoes/novo_monitoramento.html', locals())


@login_required
def novo_monitoramento_sem_contato(request, pk):
    notificacao = get_object_or_404(Notificacao.qs_visiveis(request.user), pk=pk)
    Monitoramento.objects.create(notificacao=notificacao,
                                 pessoa=notificacao.pessoa,
                                 criado_por=request.user,
                                 data_de_investigacao=timezone.now().date())
    messages.success(request, 'Monitoramento cadastrado com sucesso.')
    return HttpResponseRedirect(reverse_lazy('notificacoes:visualizar', args=[pk]))


class NotificacaoDetailView(LoginRequiredMixin, DetailView):
    model = Notificacao

    def get_queryset(self):
        return Notificacao.qs_visiveis(self.request.user)

    def get_context_data(self, **kwargs):
        context = super(NotificacaoDetailView, self).get_context_data(**kwargs)
        context['categorias'] = Notificacao.CATEGORIAS_CAMPOS
        context['datas_dias'] = [
            'data_da_notificacao',
            'data_do_inicio_dos_sintomas',
        ]
        context['datas'] = [
            'data_de_nascimento',
        ]
        context['sintomas'] = context['object'].get_sintomas_as_list()
        context['morbidades'] = context['object'].get_morbidades_as_list()
        return context


class NotificacaoAllDetailView(NotificacaoDetailView):
    model = Notificacao

    def get_queryset(self):
        return Notificacao.objects.all()


class AssociacaoBairroView(PermissionRequiredMixin, View):
    permission_required = 'notificacoes.pode_associar_bairros'

    def get(self, request):
        bairros_pendentes = Notificacao.recuperar_nomes_de_bairro_pendentes()
        if not bairros_pendentes:
            messages.info(request, 'Não há bairros pendentes de associação. '
                                   'Você foi redirecionado para a definição de notificações principais.')
            return redirect(reverse_lazy('notificacoes:definir_principais'))

        paginator = Paginator(bairros_pendentes, QTD_REGISTROS_POR_PAGINA)

        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        form = AssociacaoBairroGeralForm(bairros_faltantes=page_obj.object_list)
        bairros = Bairro.ativos.all()
        return render(request, template_name='notificacoes/associacao_bairro_list.html', context=locals())

    def post(self, request):
        bairros_pendentes = Notificacao.recuperar_nomes_de_bairro_pendentes()
        form = AssociacaoBairroGeralForm(data=request.POST, bairros_faltantes=bairros_pendentes)
        if form.is_valid():
            bairros_a_remover = form.obter_bairros_a_remover()
            bairros_associados = form.obter_notificacao_bairro()
            if bairros_associados:
                Notificacao.atualiza_bairros_de_notificacoes(bairros_associados)
            if bairros_a_remover:
                Notificacao.remover_notificacoes_fora_de_area(bairros_a_remover)
            messages.success(request, 'Associação de bairros realizada com sucesso.')

        return self.get(request)


class BairrosAssociadosView(PermissionRequiredMixin, View):
    permission_required = 'notificacoes.pode_associar_bairros'

    def get(self, request):
        qs = Notificacao.ativas.filter(bairro__isnull=False).exclude(dados__bairro=None)
        bairros_associados = Notificacao.recuperar_nomes_de_bairro_associados(qs=qs)
        if not bairros_associados:
            messages.info(request, 'Não há bairros associados para atualizar. '
                                   'Você foi redirecionado para a definição de notificações principais.')
            return redirect(reverse_lazy('notificacoes:definir_principais'))

        #Adiciona Filtro por bairro
        filter = NotificacaoFilter(request.GET, queryset=qs)
        label_bairro = None
        if filter.qs:
            bairros_associados = Notificacao.recuperar_nomes_de_bairro_associados(filter.qs)
            bairro_filter = request.GET.get('bairro', None)
            if bairro_filter:
                label_bairro = Bairro.objects.get(pk=bairro_filter)

        #Adiciona paginação
        paginator = Paginator(bairros_associados, QTD_REGISTROS_POR_PAGINA)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        form = AtualizarAssociacaoBairroNotificacaoForm(bairros_associados=page_obj.object_list)

        bairros = Bairro.ativos.all()
        return render(request, template_name='notificacoes/bairros_associados_list.html', context=locals())

    def post(self, request):
        bairros_associados = Notificacao.recuperar_nomes_de_bairro_associados()
        form = AtualizarAssociacaoBairroNotificacaoForm(data=request.POST, bairros_associados=bairros_associados)
        if form.is_valid():
            bairros_associados = form.obter_notificacao_bairro()
            if bairros_associados:
                Notificacao.atualiza_bairros_de_notificacoes(bairros_associados)
            messages.success(request, 'Associação de bairros realizada com sucesso.')


class AssociacaoBairroNotificacaoView(PermissionRequiredMixin, View):
    permission_required = 'notificacoes.pode_associar_bairros'

    def get(self, request):
        notificacoes_bairros_pendentes = Notificacao.recuperar_nomes_de_bairro_pendentes(obter_de_historico=True)
        notificacoes = {n.numero: n for n in notificacoes_bairros_pendentes}
        if not notificacoes_bairros_pendentes:
            messages.info(request, 'Não há notificações com bairros pendentes de associação. '
                                   'Você foi redirecionado para a definição de notificações principais.')
            return redirect(reverse_lazy('notificacoes:definir_principais'))
        paginator = Paginator(notificacoes_bairros_pendentes, QTD_REGISTROS_POR_PAGINA)

        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        form = AssociacaoBairroNotificacaoForm(notificacoes=page_obj.object_list)
        bairros = Bairro.ativos.all()
        return render(request, template_name='notificacoes/associacao_bairro_individual_list.html', context=locals())

    def post(self, request):
        notificacoes_bairros_pendentes = Notificacao.recuperar_nomes_de_bairro_pendentes(obter_de_historico=True)
        form = AssociacaoBairroNotificacaoForm(data=request.POST, notificacoes=notificacoes_bairros_pendentes)
        if form.is_valid():
            bairros_associados = form.obter_notificacao_bairro()
            bairros_a_remover = form.obter_bairros_a_remover()
            if bairros_associados:
                Notificacao.atualiza_bairros_de_notificacoes(bairros_associados, considerar_notificacao=True)
            if bairros_a_remover:
                Notificacao.remover_notificacoes_fora_de_area(bairros_a_remover, considerar_notificacao=True)
            messages.success(request, 'Associação de bairros realizada com sucesso.')

        return self.get(request)


class GALFormView(PermissionRequiredMixin, UpdateView):
    permission_required = 'notificacoes.pode_alterar_o_gal'
    form_class = GALForm
    template_name = 'formulario_modal.html'

    def get_context_data(self, **kwargs):
        context = super(GALFormView, self).get_context_data()
        context['titulo'] = 'Alterar requisição do GAL'
        return context

    def get_success_url(self):
        messages.success(self.request, 'Associação de requisição GAL realizada com sucesso.')
        return reverse_lazy('notificacoes:visualizar', args=[self.kwargs.get(self.pk_url_kwarg)])

    def get_queryset(self):
        queryset = Notificacao.ativas
        if self.request.user.is_usuario_distrito:
            queryset = queryset.filter(bairro__distrito=self.request.user.perfil_distrito.distrito)
        return queryset.all()




class ImportarNotificacaoSivepFormView(PermissionRequiredMixin, SetHeadlineMixin, FormView):
    form_class = UploadImportacaoSivepForm
    permission_required = 'notificacoes.pode_importar_notificacoes'
    template_name = 'formulario.html'
    headline = 'Importar notificações do SIVEP Gripe'
    success_url = reverse_lazy('notificacoes:listar')

    def test_func(self):
        return settings.IMPORTAR_NOTIFICACOES_VIA_CSV

    def get(self, request, *args, **kwargs):
        # if Notificacao.get_processamento_foi_concluido():
        return super(ImportarNotificacaoSivepFormView, self).get(request, *args, **kwargs)
        # else:
        #     msg = '''O sistema está processando os dados da planilha e, por isso, não está aceitando novos envios. Assim que concluir,
        #     você receberá um alerta.'''
        #     messages.warning(self.request, msg)
        #     return HttpResponseRedirect(reverse_lazy('notificacoes:listar'))

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        instance = form.save()
        dados_sivep = ObterNotificacaoSivepGripeDBF().processar()
        msg = '''O sistema está processando os dados da planilha e, assim que concluir, 
        você receberá um alerta.'''
        messages.warning(self.request, msg)
        return super().form_valid(form)



class ImportarNotificacaoEsusveFormView(UserPassesTestMixin, PermissionRequiredMixin, FormView):
    form_class = UploadImportacaoESUSVEForm
    permission_required = 'notificacoes.pode_importar_notificacoes'
    template_name = 'formulario.html'
    headline = 'Importar notificações do e-SUS VE'
    success_url = reverse_lazy('notificacoes:listar')

    def test_func(self):
        return settings.IMPORTAR_NOTIFICACOES_VIA_CSV

    def get(self, request, *args, **kwargs):
        if Notificacao.get_processamento_foi_concluido():
            return super(ImportarNotificacaoEsusveFormView, self).get(request, *args, **kwargs)
        else:
            msg = '''O sistema está processando os dados da planilha e, por isso, não está aceitando novos envios. Assim que concluir, 
            você receberá um alerta.'''
            messages.warning(self.request, msg)
            return HttpResponseRedirect(reverse_lazy('notificacoes:listar'))

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        instance = form.save()
        msg = '''O sistema está processando os dados da planilha e, assim que concluir, 
        você receberá um alerta.'''
        messages.warning(self.request, msg)
        return super().form_valid(form)


class AssociacaoPacienteView(PermissionRequiredMixin, View):
    permission_required = 'notificacoes.pode_associar_pacientes'

    def get(self, request):
        pacientes = PacienteInternacao.recuperar_nomeas_a_associar()
        if not pacientes:
            messages.info(request, 'Não há pacientes para associar no momento.')
            # return redirect(reverse_lazy('notificacoes:listar'))
        pacientes = [(k, v) for k, v in pacientes.items()]
        paginator = Paginator(pacientes, QTD_REGISTROS_POR_PAGINA)

        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        form = AssociacaoPacienteForm(pacientes=page_obj.object_list)
        return render(request, template_name='notificacoes/associacao_leitos_list.html', context=locals())

    def post(self, request):
        pacientes = PacienteInternacao.recuperar_nomeas_a_associar()
        pacientes = [(k, v) for k, v in pacientes.items()]
        form = AssociacaoPacienteForm(data=request.POST, pacientes=pacientes)
        nomes_a_associar = []
        if form.is_valid():
            for field in form.changed_data:
                notificacao = form.cleaned_data[field]
                paciente_internado_id = field
                nomes_a_associar.append((notificacao, paciente_internado_id))
        PacienteInternacao.definir_principais(nomes_a_associar)
        return self.get(request)


class PacientesAssociadosView(PermissionRequiredMixin, View):
    permission_required = 'notificacoes.pode_associar_pacientes'

    def get(self, request):
        #Todo Verificar com a equipe como obter os registros de pacientes já associados, qual a regra?
        pacientes = PacienteInternacao.objects.filter(notificacao__isnull=False)
        if not pacientes:
            messages.info(request, 'Não há pacientes para associar no momento.')
            # return redirect(reverse_lazy('notificacoes:listar'))

        paginator = Paginator(pacientes, QTD_REGISTROS_POR_PAGINA)

        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        form = AssociacaoPacienteForm(pacientes=page_obj.object_list)
        return render(request, template_name='notificacoes/leitos_associados_list.html', context=locals())

    def post(self, request):
        pacientes = PacienteInternacao.recuperar_nomeas_a_associar()
        form = AssociacaoPacienteForm(data=request.POST, pacientes=pacientes)
        nomes_a_associar = []
        if form.is_valid():
            for field in form.changed_data:
                notificacao = form.cleaned_data[field]
                paciente_internado_id = field
                nomes_a_associar.append((notificacao, paciente_internado_id))
        PacienteInternacao.definir_principais(nomes_a_associar)
        return self.get(request)


class PacientesAssociadosView(PermissionRequiredMixin, View):
    permission_required = 'notificacoes.pode_associar_pacientes'

    def get(self, request):
        #Todo Verificar com a equipe como obter os registros de pacientes já associados, qual a regra?
        pacientes = PacienteInternacao.objects.filter(notificacao__isnull=False)
        if not pacientes:
            messages.info(request, 'Não há pacientes para associar no momento.')
            # return redirect(reverse_lazy('notificacoes:listar'))

        paginator = Paginator(pacientes, QTD_REGISTROS_POR_PAGINA)

        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        form = AssociacaoPacienteForm(pacientes=page_obj.object_list)
        return render(request, template_name='notificacoes/leitos_associados_list.html', context=locals())

    def post(self, request):
        pacientes = PacienteInternacao.recuperar_nomeas_a_associar()
        form = AssociacaoPacienteForm(data=request.POST, pacientes=pacientes)
        nomes_a_associar = []
        if form.is_valid():
            for field in form.changed_data:
                notificacao = form.cleaned_data[field]
                paciente_internado_id = field
                nomes_a_associar.append((notificacao, paciente_internado_id))
        PacienteInternacao.definir_principais(nomes_a_associar)
        return self.get(request)


class AssociacaoOperadorCNESView(PermissionRequiredMixin, View):
    permission_required = 'notificacoes.pode_associar_operadores'

    def get(self, request):
        operadores = AssociacaoOperadorCNES.recuperar_nomes_a_serem_associados()
        estabelecimentos = EstabelecimentoSaude.objects.all()
        if not operadores:
            messages.info(request, 'Não há operador para vincular no momento.')
            # return redirect(reverse_lazy('notificacoes:listar'))
        from django.core.paginator import Paginator
        paginator = Paginator(operadores, QTD_REGISTROS_POR_PAGINA)  # Show 25 contacts per page.

        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        form = AssociacaoOperadorCNESForm(operadores=page_obj.object_list)
        return render(request, template_name='notificacoes/associacao_operador_cnes.html', context=locals())

    def post(self, request):
        operadores = AssociacaoOperadorCNES.recuperar_nomes_a_serem_associados()
        form = AssociacaoOperadorCNESForm(data=request.POST, operadores=operadores)
        cpfs_associados = []
        if form.is_valid():
            for field in form.changed_data:
                cpf = field[3:]
                cnes = form.cleaned_data[field]
                cpfs_associados.append((cpf, cnes))
        update = AssociacaoOperadorCNES.definir_principais(cpfs_associados)
        if not update:
            messages.error(request, 'Ocorreu um erro ao realizar associações.')
        elif update >= 1:
            messages.info(request, 'Operadores associados com sucesso.'.format(update))

        return self.get(request)


class MonitoramentoListView(LoginRequiredMixin, ListView):
    template_name = 'notificacoes/monitoramento_list.html'
    paginate_by = 10
    titulo = 'Monitoramento'
    form = None

    def get(self, request, *args, **kwargs):
        return super(MonitoramentoListView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        self.form = MonitoramentoFiltroForm(self.request.user, data=self.request.GET)
        if self.form.is_valid():
            self.paginate_by = self.form.obter_resultados_por_pagina() or 10
            return self.form.obter_queryset(Monitoramento.qs_visiveis(self.request.user)).all()
        return Monitoramento.qs_visiveis(self.request.user).all()

    def get_context_data(self, **kwargs):
        context = super(MonitoramentoListView, self).get_context_data(**kwargs)
        context['titulo'] = self.titulo
        context['form'] = self.form
        return context


class MonitoramentoDetailView(LoginRequiredMixin, DetailView):
    model = Monitoramento

    def get_queryset(self):
        return Monitoramento.objects.all()  # TODO: filtrar pelos monitoramentos da unidade de saude


# class AssociacaoEstabelecimentoView(LoginRequiredMixin, View): # TODO: Construir metodo
#     def get(self, request):
#         titulo = 'Associar estabelecimentos'
#         estabelecimentos = PacienteInternacao.recuperar_nomes_de_estabelecimento_pendentes()
#
#         dataset_rows = [
#             [
#                 nome_estabelecimento,
#                 None,
#             ] for nome_estabelecimento in estabelecimentos]
#
#         return render(self.request, 'notificacoes/associacao_estabelecimento.html', locals())
#
#     @staticmethod
#     def _tag_a(numero):
#         return '<span class="modal-trigger notificacao-detalhe-modal-trigger" data-notificacao="{0}" ' \
#                'data-animation="blur" data-plugin="custommodal" data-overlaycolor="#38414a">{0}</span>'.format(
#             numero
#         )
#
#     def get_context_data(self, *, object_list=None, **kwargs):
#         values = self.get_queryset().values('numero', 'dados', 'bairro__nome', 'estabelecimento_saude__dados_cnes__noFantasia',
#                                             'bairro__distrito__nome', 'numero_gal')
#
#
#         return context


class AssociacaoEstabelecimentoView(LoginRequiredMixin, View):
    permission_required = 'notificacoes.pode_associar_estabelecimentos'

    def get(self, request):
        estabelecimentos_pendentes = PacienteInternacao.recuperar_nomes_de_estabelecimento_pendentes()
        estabelecimentos = EstabelecimentoSaude.objects.all()
        if not estabelecimentos_pendentes:
            messages.info(request, 'Não há estabelecimentos para associar no momento.')

        paginator = Paginator(estabelecimentos_pendentes, QTD_REGISTROS_POR_PAGINA)

        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        form = AssociacaoNomeEstabelecimentoForm(estabelecimentos=page_obj.object_list)
        return render(request, template_name='notificacoes/associacao_estabelecimento.html', context=locals())

    def post(self, request):
        estabelecimentos = PacienteInternacao.recuperar_nomes_de_estabelecimento_pendentes()
        form = AssociacaoNomeEstabelecimentoForm(data=request.POST, estabelecimentos=estabelecimentos)
        if form.is_valid():
            for i, nome_estabelecimento in enumerate(estabelecimentos):
                estabelecimento = form.cleaned_data[str(i)]
                if estabelecimento:
                    AssociacaoNomeEstabelecimentoSaude(nome=nome_estabelecimento, estabelecimento_saude=estabelecimento).save()
        # TODO: Erro
        #PacienteInternacao.processar_pdf_censo_leitos_imd(None, None, None, request.user)
        return self.get(request)


class EstabelecimentosAssociadosView(LoginRequiredMixin, View):
    permission_required = 'notificacoes.pode_associar_estabelecimentos'

    def get(self, request):
        #Todo Verificar com a equipe se o queryset esta correto
        estabelecimentos_associados = AssociacaoNomeEstabelecimentoSaude.objects.filter(estabelecimento_saude__isnull=False)
        estabelecimentos = EstabelecimentoSaude.objects.all()
        if not estabelecimentos_associados:
            messages.info(request, 'Não há estabelecimentos para associar no momento.')

        paginator = Paginator(estabelecimentos_associados, QTD_REGISTROS_POR_PAGINA)

        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        form = AlterarAssociacaoNomeEstabelecimentoForm(estabelecimentos=page_obj.object_list)
        return render(request, template_name='notificacoes/estabelecimentos_associados.html', context=locals())

    def post(self, request):
        estabelecimentos_associados = AssociacaoNomeEstabelecimentoSaude.objects.filter(estabelecimento_saude__isnull=False)
        form = AlterarAssociacaoNomeEstabelecimentoForm(data=request.POST, estabelecimentos=estabelecimentos_associados)
        if form.is_valid():
            count_update = 0
            for field in form.changed_data:
                estabelecimento = form.cleaned_data[field]
                estabelecimento_nome = field
                update = AssociacaoNomeEstabelecimentoSaude.objects.filter(nome=estabelecimento_nome).update(estabelecimento_saude=estabelecimento)
                count_update += update
            if count_update:
                messages.success(request, "Alterações realizadas com sucesso.")
        # TODO: Erro
        #PacienteInternacao.processar_pdf_censo_leitos_imd(None, None, None, request.user)
        return self.get(request)


class PacienteInternacaoListView(View):
    def get(self, request, tipo):
        if tipo not in [PacienteInternacao.INTERNADO, PacienteInternacao.OBITO, PacienteInternacao.LIBERADO]:
            raise Http404()
        tipos = {PacienteInternacao.OBITO: 'Lista de pacientes - Óbitos',
                 PacienteInternacao.LIBERADO: 'Lista de pacientes - Liberados',
                 PacienteInternacao.INTERNADO: 'Lista de pacientes - Internados'}
        titulo = tipos[tipo]
        tipo_obito = tipo == PacienteInternacao.OBITO
        pacientes = PacienteInternacao.objects.filter(tipo=tipo).all()
        return render(request, 'notificacoes/pacientes_list.html', locals())


@permission_required('notificacoes.pode_associar_pacientes')
def paciente_verificar_obito(request, pk):
    # NOTA: pega apenas objetos cujo óbito não foi verificado
    obj = get_object_or_404(
        PacienteInternacao,
        data_do_obito__isnull=True,
        tipo=PacienteInternacao.OBITO,
        pk=pk
    )
    titulo = f'Confirmar Óbito'
    form = ConfirmarObitoPacienteInternacaoForm(instance=obj, data=request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Óbito verificado com sucesso')

        return HttpResponseRedirect(reverse_lazy('notificacoes:listar_pacientes', args=[PacienteInternacao.OBITO]))
    return render(request, 'notificacoes/paciente_verificar_obito.html', locals())


class NotificacaoRecentesView(View):
    def get(self, request):
        base_url = reverse_lazy('notificacoes:listar')
        date = timezone.now() - timedelta(days=14)
        query_string = urlencode({'data_notificacao_de': date.strftime('%Y-%m-%d')})
        url = '{}?{}'.format(base_url, query_string)
        return redirect(url)


class ResetarCacheProcessamentoView(PermissionRequiredMixin, View):
    permission_required = 'add_uploadimportacao'

    def get(self, request):
        ControleCache.processamento_notificacoes().reset()
        base_url = reverse_lazy('admin:notificacoes_uploadimportacao_changelist')
        messages.add_message(request, messages.INFO, 'Cache de processamento resetado com sucesso.')
        return redirect(base_url)


@login_required
def teste(request):
    proc_sivep = ObterNotificacaoSivepGripeDBF()
    ret = proc_sivep.processar()
    from django.http import HttpResponse
    return HttpResponse(ret)


@permission_required('notificacoes.pode_registrar_obito')
def iniciar_registrar_obito(request):
    headline = 'Informe CPF ou CNS para iniciar o registro de óbito'
    form = ObitoCnsCpfForm(request.POST or None)
    if form.is_valid():
        return HttpResponseRedirect(
            reverse_lazy('notificacoes:registrar_obito', args=[form.cleaned_data['cpf']]))
    return render(request, 'formulario.html', locals())


@permission_required('notificacoes.pode_registrar_obito')
def registrar_obito(request, cpf):
    headline = 'Registrar óbito'
    form = get_registrar_obito_form(request=request,
                                    pessoa=PessoaFisica.objects.get(cpf=cpf))
    if form.is_valid():
        form.save()
        Alerta.novo_obito_pendente_validacao()
        messages.success(request, 'Óbito registrado com sucesso')
        return HttpResponseRedirect(reverse_lazy('notificacoes:listar_obitos'))
    return render(request, 'notificacoes/obito_form.html', locals())


@permission_required('notificacoes.pode_validar_obito')
def vincular_pessoa_a_obito(request, pk):
    headline = 'Vincular óbito a CNS/CPF'
    obito = get_object_or_404(Obito, pk=pk)
    form = VincularPessoaObitoForm(request.POST or None)
    if form.is_valid():
        return HttpResponseRedirect(
            reverse_lazy('notificacoes:vincular_pessoa_a_obito_confirmar',
                         args=[obito.pk, form.get_pessoa().cpf]))
    return render(request, 'notificacoes/vincular_pessoa_a_obito.html', locals())


@permission_required('notificacoes.pode_validar_obito')
def vincular_pessoa_a_obito_confirmar(request, pk, cpf):
    headline = 'Confirmar vinculação de óbito a CNS/CPF'
    obito = get_object_or_404(Obito, pk=pk)
    pessoa = PessoaFisica.objects.get(cpf=cpf)
    form = ConfirmarVincularPessoaObitoForm(data=request.POST or None, obito=obito, pessoa=pessoa)
    if form.is_valid():
        form.save()
        return HttpResponseRedirect(
            reverse_lazy('notificacoes:validar_obito', args=[obito.pk]))
    return render(request, 'notificacoes/vincular_pessoa_a_obito.html', locals())


@permission_required('notificacoes.pode_validar_obito')
def validar_obito(request, pk):
    headline = 'Validar óbito'
    obito = get_object_or_404(Obito, pk=pk)
    if not obito.pessoa:
        return HttpResponseRedirect(reverse_lazy('notificacoes:vincular_pessoa_a_obito', args=[pk]))
    form = get_validar_obito_form(request=request, obito=obito)
    if form.is_valid():
        form.save()
        messages.success(request, 'Óbito validado com sucesso')
        return HttpResponseRedirect(reverse_lazy('notificacoes:listar_obitos'))
    return render(request, 'notificacoes/obito_form.html', locals())


class ObitoListView(PermissionRequiredMixin, ListView):
    template_name = 'notificacoes/obito_list.html'
    permission_required = 'notificacoes.pode_registrar_obito'
    queryset = Obito.objects.all()
    paginate_by = 10
    titulo = 'Óbitos'
    form = None

    def get_queryset(self):
        self.form = ObitoFiltroForm(self.request.user, data=self.request.GET)
        if self.form.is_valid():
            self.paginate_by = 30
            qs = self.form.obter_queryset(self.queryset)
        else:
            qs = self.form.obter_queryset(self.queryset)
        return qs.order_by('-data_do_obito')

    def get_context_data(self, **kwargs):
        context = super(ObitoListView, self).get_context_data(**kwargs)
        context['titulo'] = self.titulo
        context['form'] = self.form
        return context


class ObitoDetailView(LoginRequiredMixin, DetailView):
    model = Obito

    def get_queryset(self):
        return Obito.objects.all()
