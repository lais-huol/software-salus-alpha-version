from braces.views import SuccessURLRedirectListMixin, SetHeadlineMixin, GroupRequiredMixin, LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db import transaction
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView

from administracao.forms import PacienteInternacaoForm, DistritoForm, BairroForm, HabitacaoForm, AssociacaoBairroForm
from base.mixins import DeleteMessagesMixin
from base.models import Bairro, HabitacoesBairro, Distrito, AssociacaoBairro
from indicadores.models import ModeloPainel


# BAIRRO
from notificacoes.models import Notificacao, PacienteInternacao, UploadImportacao


class BairroListView(LoginRequiredMixin, ListView):
    permission_required = 'base.e_gestor'
    template_name = 'administracao/bairro_list.html'
    queryset = Bairro.ativos.all().order_by('nome')


class BairroCreateView(LoginRequiredMixin, PermissionRequiredMixin, SetHeadlineMixin, CreateView):
    permission_required = 'base.e_gestor'
    headline = 'Novo bairro'
    model = Bairro
    form_class = BairroForm
    template_name = 'formulario.html'
    success_url = reverse_lazy('administracao:listar_bairros')


class BairroEditView(LoginRequiredMixin, PermissionRequiredMixin, SetHeadlineMixin, UpdateView):
    permission_required = 'base.e_gestor'
    headline = 'Alterar bairro'
    model = Bairro
    form_class = BairroForm
    template_name = 'formulario.html'
    queryset = Bairro.ativos.all()
    success_url = reverse_lazy('administracao:listar_bairros')


class BairroDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteMessagesMixin, DeleteView):
    permission_required = 'base.e_gestor'
    model = Bairro
    queryset = Bairro.ativos.all()
    template_name = 'confirmar_remocao.html'
    message_protected = 'O bairro {0} está vinculado a outras partes do sistema e não pode ser removido.'
    message_deleted = 'O bairro {0} foi removido com sucesso!'
    success_url = reverse_lazy('administracao:listar_bairros')



# HABITAÇÕES

class HabitacaoListView(LoginRequiredMixin, GroupRequiredMixin, ListView):
    permission_required = 'base.e_gestor'
    group_required = 'CIEVS - Centro de Informações Estratégicas em Vigilância em Saúde'
    template_name = 'administracao/habitacao_list.html'
    queryset = HabitacoesBairro.objects.all().order_by('nome')


class HabitacaoCreateView(LoginRequiredMixin, PermissionRequiredMixin, GroupRequiredMixin, SetHeadlineMixin, CreateView):
    permission_required = 'base.e_gestor'
    group_required = 'CIEVS - Centro de Informações Estratégicas em Vigilância em Saúde'
    headline = 'Nova habitação de bairro'
    model = HabitacoesBairro
    form_class = HabitacaoForm
    template_name = 'formulario.html'
    success_url = reverse_lazy('administracao:listar_habitacoes')


class HabitacaoEditView(LoginRequiredMixin, PermissionRequiredMixin, GroupRequiredMixin, SetHeadlineMixin, UpdateView):
    permission_required = 'base.e_gestor'
    group_required = 'CIEVS - Centro de Informações Estratégicas em Vigilância em Saúde'
    headline = 'Alterar habitação de bairro'
    form_class = HabitacaoForm
    template_name = 'formulario.html'
    queryset = HabitacoesBairro.objects.all()
    success_url = reverse_lazy('administracao:listar_habitacoes')


class HabitacaoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, GroupRequiredMixin, DeleteMessagesMixin, DeleteView):
    permission_required = 'base.e_gestor'
    group_required = 'CIEVS - Centro de Informações Estratégicas em Vigilância em Saúde'
    queryset = HabitacoesBairro.objects.all()
    template_name = 'confirmar_remocao.html'
    message_protected = 'A habitação de bairro {0} está vinculada a outras partes do sistema e não pode ser removida.'
    message_deleted = 'A habitação de bairro {0} foi removida com sucesso!'
    success_url = reverse_lazy('administracao:listar_habitacoes')


# DISTRITOS


class DistritoListView(LoginRequiredMixin, GroupRequiredMixin, ListView):
    permission_required = 'base.e_gestor'
    group_required = 'CIEVS - Centro de Informações Estratégicas em Vigilância em Saúde'
    template_name = 'administracao/distrito_list.html'
    queryset = Distrito.ativos.all().order_by('nome')


class DistritoCreateView(LoginRequiredMixin, PermissionRequiredMixin, GroupRequiredMixin, SetHeadlineMixin, CreateView):
    permission_required = 'base.e_gestor'
    group_required = 'CIEVS - Centro de Informações Estratégicas em Vigilância em Saúde'
    headline = 'Novo distrito'
    form_class = DistritoForm
    model = Distrito
    template_name = 'formulario.html'
    success_url = reverse_lazy('administracao:listar_distritos')


class DistritoEditView(LoginRequiredMixin, PermissionRequiredMixin, GroupRequiredMixin, SetHeadlineMixin, UpdateView):
    permission_required = 'base.e_gestor'
    group_required = 'CIEVS - Centro de Informações Estratégicas em Vigilância em Saúde'
    headline = 'Alterar distrito'
    form_class = DistritoForm
    template_name = 'formulario.html'
    queryset = Distrito.ativos
    success_url = reverse_lazy('administracao:listar_distritos')


class DistritoDeleteView(LoginRequiredMixin, PermissionRequiredMixin, GroupRequiredMixin, DeleteMessagesMixin, DeleteView):
    permission_required = 'base.e_gestor'
    group_required = 'CIEVS - Centro de Informações Estratégicas em Vigilância em Saúde'
    queryset = Distrito.ativos
    template_name = 'confirmar_remocao.html'
    message_protected = 'O distrito de bairro {0} está vinculado a outras partes do sistema e não pode ser removido.'
    message_deleted = 'O distrito {0} foi removido com sucesso!'
    success_url = reverse_lazy('administracao:listar_distritos')


# ASSOCIAÇÕES DE BAIRRO

class AssociacaoBairroListView(LoginRequiredMixin, GroupRequiredMixin, ListView):
    permission_required = 'base.e_gestor'
    group_required = 'CIEVS - Centro de Informações Estratégicas em Vigilância em Saúde'
    template_name = 'administracao/associacaobairro_list.html'
    queryset = AssociacaoBairro.objects.all().order_by('nome')


class AssociacaoBairroCreateView(LoginRequiredMixin, PermissionRequiredMixin, GroupRequiredMixin, SetHeadlineMixin, CreateView):
    permission_required = 'base.e_gestor'
    group_required = 'CIEVS - Centro de Informações Estratégicas em Vigilância em Saúde'
    headline = 'Nova associação de bairro'
    form_class = AssociacaoBairroForm
    model = AssociacaoBairro
    template_name = 'formulario.html'
    success_url = reverse_lazy('administracao:listar_associacoesbairro')


class AssociacaoBairroEditView(LoginRequiredMixin, PermissionRequiredMixin, GroupRequiredMixin, SetHeadlineMixin, UpdateView):
    permission_required = 'base.e_gestor'
    group_required = 'CIEVS - Centro de Informações Estratégicas em Vigilância em Saúde'
    headline = 'Alterar associação de bairro'
    form_class = AssociacaoBairroForm
    template_name = 'formulario.html'
    queryset = AssociacaoBairro.objects.all()
    success_url = reverse_lazy('administracao:listar_associacoesbairro')

    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            ret = super().post(request, *args, **kwargs)
            Notificacao.objects.filter(dados__bairro__iexact=self.object.nome).update(bairro=self.object.bairro)
            return ret



# PACIENTES INTERNADOS



class PacienteInternacaoListView(LoginRequiredMixin, GroupRequiredMixin, ListView):
    permission_required = 'base.e_gestor'
    group_required = 'CIEVS - Centro de Informações Estratégicas em Vigilância em Saúde'
    template_name = 'administracao/pacienteinternado_list.html'
    queryset = PacienteInternacao.objects.filter(notificacao__isnull=False).all()


class PacienteInternacaoEditView(LoginRequiredMixin, SetHeadlineMixin, PermissionRequiredMixin, GroupRequiredMixin, UpdateView):
    permission_required = 'base.e_gestor'
    group_required = 'CIEVS - Centro de Informações Estratégicas em Vigilância em Saúde'
    headline = 'Alterar paciente internado'
    form_class = PacienteInternacaoForm
    template_name = 'formulario.html'
    queryset = PacienteInternacao.objects.filter(notificacao__isnull=False).all()
    success_url = reverse_lazy('administracao:listar_pacientesinternados')

# UPLOAD IMPORTACAO


class UploadImportacaoListView(LoginRequiredMixin, GroupRequiredMixin, ListView):
    permission_required = 'base.e_gestor'
    group_required = 'CIEVS - Centro de Informações Estratégicas em Vigilância em Saúde'
    template_name = 'administracao/uploadimportacao_list.html'
    queryset = UploadImportacao.objects.all().order_by('-datahora')


class UploadImportacaoDetailView(LoginRequiredMixin, GroupRequiredMixin, DetailView):
    permission_required = 'base.e_gestor'
    group_required = 'CIEVS - Centro de Informações Estratégicas em Vigilância em Saúde'
    template_name = 'administracao/uploadimportacao_detail.html'
    queryset = UploadImportacao.objects.all()
