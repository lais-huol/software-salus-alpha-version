import json

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView

from base.caches import ControleCache
from base.utils import DateTimeEncoder
from indicadores import catalogo
from indicadores.boletim_template import preparar_contexto_painel
from indicadores.forms import ModeloPainelForm, BoletimForm
from indicadores.models import ModeloPainel, ModeloAplicacao
from indicadores.paineis import ParametroBoletim, PainelBoletim, ParametroCatalogo, ParametroPublico, \
    PainelPublico, PainelCatalogo


class InicioView(LoginRequiredMixin, View):
    def get(self, request):
        indicador_parametro = ParametroCatalogo()
        indicador = PainelCatalogo(indicador_parametro, True, True)

        notificacoes_ativas = indicador.get_dados('casos_notificados')['valor']

        dados = indicador.get_dados('resultado_dos_testes_por_tipo_grafico_pizza')
        valores = list(dados['series'].values())[0]
        categorias = list(dados['categories'])
        notificacoes_resultado_do_teste = {}

        for i in range(0, len(dados['categories'])):
            notificacoes_resultado_do_teste[categorias[i]] = valores[i]

        dados = indicador.get_dados('evolucao_caso_testes_por_tipo_grafico_pizza')
        valores = list(dados['series'].values())[0]
        categorias = list(dados['categories'])
        notificacoes_evolucao_do_caso = {}
        for i in range(0, len(dados['categories'])):
            notificacoes_evolucao_do_caso[categorias[i]] = valores[i]

        dados = indicador.get_dados('estado_do_teste_por_tipo_grafico_pizza')
        valores = list(dados['series'].values())[0]
        categorias = list(dados['categories'])
        notificacoes_estado_do_teste = {}

        for i in range(0, len(dados['categories'])):
            notificacoes_estado_do_teste[categorias[i]] = valores[i]

        return render(request, 'indicadores/inicio.html', locals())


class PainelPublicoViewMixin():
    def setup(self, request, *args, **kwargs):

        """Initialize attributes shared by all view methods."""
        super(PainelPublicoViewMixin, self).setup(request, *args, **kwargs)
        indicador_parametro = ParametroPublico(request)
        self.indicador = PainelPublico(indicador_parametro, True, False)


class PainelPublicoView(PainelPublicoViewMixin, TemplateView):
    template_name = 'indicadores/painel_publico.html'

    def get_context_data(self, **kwargs):
        context = super(PainelPublicoView, self).get_context_data()
        super_template = "base_public.html"
        modo_publico = True
        modelo = ModeloPainel.objects.filter(tipo='publico').last()
        if modelo:
            contexto_modelo, scripts = preparar_contexto_painel(self.indicador.get_dict_visualizacoes(modelo.vars()))
            boletim = modelo.render(contexto_modelo)
            context.update(locals())
        return context


class BoletimViewMixin():
    def setup(self, request, *args, **kwargs):

        """Initialize attributes shared by all view methods."""
        super(BoletimViewMixin, self).setup(request, *args, **kwargs)
        indicador_parametro = ParametroBoletim(request)
        self.indicador = PainelBoletim(indicador_parametro, False, False)


class PreviaBoletimView(LoginRequiredMixin, BoletimViewMixin, TemplateView):
    template_name = 'indicadores/boletim_modal.html'

    def get_context_data(self, **kwargs):
        context = super(PreviaBoletimView, self).get_context_data()

        modelo = get_object_or_404(ModeloPainel, id=self.request.GET['modelo'])

        if modelo:
            contexto_modelo, scripts = preparar_contexto_painel(self.indicador.get_dict_visualizacoes(modelo.vars()))
            boletim = modelo.render(contexto_modelo)
            context.update(locals())
        return context


class IndicadoresCatalogoViewMixin():
    def setup(self, request, *args, **kwargs):

        """Initialize attributes shared by all view methods."""
        super(IndicadoresCatalogoViewMixin, self).setup(request, *args, **kwargs)

        indicador_parametro = ParametroCatalogo()
        self.indicador = PainelCatalogo(indicador_parametro, True, True)


class PreviaIndicadorView(LoginRequiredMixin, IndicadoresCatalogoViewMixin, TemplateView):
    template_name = 'indicadores/boletim_modal.html'

    def get_context_data(self, **kwargs):
        context = super(PreviaIndicadorView, self).get_context_data()

        indicador = self.request.GET['indicador']
        modelo = ModeloPainel(conteudo=f'%%#{indicador}#%%')
        print(modelo.conteudo)

        if modelo:
            contexto_modelo, scripts = preparar_contexto_painel({indicador: self.indicador.get_visualizacao(indicador)})
            boletim = modelo.render(contexto_modelo)
            context.update(locals())
        return context


class IndicadorAjaxPainelPublicoView(PainelPublicoViewMixin, TemplateView):
    template_name = 'indicadores/indicador_ajax.html'

    def get_context_data(self, **kwargs):
        self.indicador.args._async = False
        context = super(IndicadorAjaxPainelPublicoView, self).get_context_data()

        indicador = self.request.GET['indicador']
        modelo = ModeloPainel(conteudo=f'%%#{indicador}#%%')

        if modelo:
            contexto_modelo, scripts = preparar_contexto_painel({indicador: self.indicador.get_visualizacao(indicador)})
            boletim = modelo.render(contexto_modelo)
            context.update(locals())
        return context


class IndicadoresGeraisView(LoginRequiredMixin, TemplateView):
    template_name = 'indicadores/indicadores_gerais.html'

    def get_context_data(self, **kwargs):
        context = super(IndicadoresGeraisView, self).get_context_data()

        lista_catalogo = catalogo.get_catalogo_indicadores()

        context.update(locals())
        return context


# MODELO DE PAINEL

class ModeloPainelListView(LoginRequiredMixin, ListView):
    permission_required = ('base.e_gestor', )
    template_name = 'indicadores/modelopainel_list.html'
    queryset = ModeloPainel.objects.all()
    paginate_by = 10


class ModeloPainelCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = ('base.e_gestor', )
    form_class = ModeloPainelForm
    template_name = 'indicadores/formulario_modelo_boletim.html'
    success_url = reverse_lazy('indicadores:listar_modelos_painel')


class ModeloPainelEditView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = ('base.e_gestor', )
    form_class = ModeloPainelForm
    template_name = 'indicadores/formulario_modelo_boletim.html'
    queryset = ModeloPainel.objects.filter(modeloaplicacao__isnull=True).all()
    success_url = reverse_lazy('indicadores:listar_modelos_painel')

    def post(self, request, *args, **kwargs):
        PainelBoletim._reset_cache()
        return super().post(request, *args, **kwargs)


class ModeloPainelDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = ('base.e_gestor', )
    form_class = ModeloPainelForm
    queryset = ModeloPainel.objects.filter(modeloaplicacao__isnull=True).all()
    template_name = 'confirmar_remocao.html'
    success_url = reverse_lazy('indicadores:listar_modelos_painel')


class ModeloPainelCloneView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = ('base.e_gestor', )
    form_class = ModeloPainelForm
    queryset = ModeloPainel.objects.all()
    template_name = 'indicadores/formulario_modelo_boletim.html'
    success_url = reverse_lazy('indicadores:listar_modelos_painel')

    def get_form_kwargs(self):
        if self.request.method == 'GET':
            objeto = get_object_or_404(ModeloPainel, id=self.kwargs['pk'])
            return {'data': {'conteudo': objeto.conteudo}}
        return super(ModeloPainelCloneView, self).get_form_kwargs()

# BOLETINS EPIDEMIOLÓGICOS

class BoletimListView(ListView):
    template_name = 'indicadores/boletim_list.html'
    queryset = ModeloAplicacao.objects.all()
    paginate_by = 10


class BoletimCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = ('base.e_gestor', )
    form_class = BoletimForm
    template_name = 'indicadores/form_aplicacaopainel.html'
    success_url = reverse_lazy('indicadores:listar_boletins')

    def form_valid(self, form):
        dados = {'parametros': {'data_do_boletim': form.cleaned_data['data_do_boletim'],
                                'semana_ano_boletim': form.cleaned_data['semana_boletim'],
                                'numero_do_boletim': form.cleaned_data['numero_do_boletim']}}
        obj = form.save(commit=False)
        obj.dados = json.dumps(dados, cls=DateTimeEncoder)
        self.object = obj.save()
        return super(BoletimCreateView, self).form_valid(form)


class BoletimEditView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = ('base.e_gestor', )
    form_class = BoletimForm
    template_name = 'indicadores/form_aplicacaopainel.html'
    queryset = ModeloAplicacao.objects.all()
    success_url = reverse_lazy('indicadores:listar_boletins')


class BoletimDetailView(DetailView):
    template_name = 'indicadores/boletim.html'
    queryset = ModeloAplicacao.objects.all()

    def get_context_data(self, **kwargs):
        context = super(BoletimDetailView, self).get_context_data()
        # semana_atual = self.indicador.args.semana_atual

        modelo = self.object.modelo
        dados = ControleCache.decode(self.object.dados)

        indicador_parametro = ParametroBoletim(None, dados['parametros'])
        self.indicador = PainelBoletim(indicador_parametro, False, False)

        tem_dados = False
        if len(dados.keys()) != 1: #dicionários dados possui chaves além da chave parametros
            tem_dados = True

        if tem_dados:
            self.indicador.set_dados(dados)
        else:
            if len(self.indicador.cache.get().keys()) == 1:
                #gerando o cache
                self.indicador.get_dict_visualizacoes(modelo.vars())
            self.object.dados = self.indicador.cache.get(DateTimeEncoder)
            self.object.save()

        contexto_modelo, scripts = preparar_contexto_painel(self.indicador.get_dict_visualizacoes(modelo.vars()))


        boletim = modelo.render(contexto_modelo)
        filtro = False

        context.update(locals())
        return context


class BoletimDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    permission_required = ('base.e_gestor', )
    form_class = BoletimForm
    queryset = ModeloAplicacao.objects.all()
    template_name = 'confirmar_remocao.html'
    success_url = reverse_lazy('indicadores:listar_boletins')
