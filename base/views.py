from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, FormView, UpdateView, TemplateView, DetailView

from .forms import UsuarioForm, UsuarioDistritoForm, UsuarioVigilanciaForm, UsuarioPerfilForm, \
    UsuarioEstabelecimentoSaudeForm, UsuarioABForm, ImportarUsuariosForm
from .models import PessoaFisica


class BuscaPessoaView(TemplateView):
    template_name = 'busca_pessoa.html'


class PessoaView(DetailView):
    model = PessoaFisica
    context_object_name = 'pessoa'
    template_name = 'pessoa.html'


class CadastroView(CreateView):
    template_name = 'formulario.html'
    success_url = '/'
    titulo = None


    def get_context_data(self, **kwargs):
        kwargs = super(CadastroView, self).get_context_data(**kwargs)
        kwargs.update({'titulo': self.titulo })
        return kwargs

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'usuario': self.request.user})
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Cadastro de usuário realizado com sucesso.')
        return super(CadastroView, self).form_valid(form)


class CadastroUsuarioView(CadastroView):
    form_class = UsuarioForm


class CadastroUsuarioDistritoView(PermissionRequiredMixin, CadastroView):
    titulo = 'Cadastro de usuários (Distrito)'
    form_class = UsuarioDistritoForm
    permission_required = ('base.e_gestor', )


class CadastroUsuarioVigilanciaView(PermissionRequiredMixin, CadastroView):
    titulo = 'Cadastro de usuários (Vigilância)'
    form_class = UsuarioVigilanciaForm
    permission_required = ('base.e_gestor', )


class CadastroUsuarioABView(PermissionRequiredMixin, CadastroView):
    titulo = 'Cadastro de usuários (Departamento de Atenção Básica)'
    form_class = UsuarioABForm
    permission_required = ('base.e_gestor', )


class CadastroEstabelecimentoSaudeView(PermissionRequiredMixin, CadastroView):
    titulo = 'Cadastro de usuários (Estabelecimento de Saúde)'
    form_class = UsuarioEstabelecimentoSaudeForm
    permission_required = ('base.e_gestor', )


class PerfilUsuarioView(LoginRequiredMixin, UpdateView):
    form_class = UsuarioPerfilForm
    template_name = 'registration/perfil.html'
    success_url = reverse_lazy('base:meu_perfil')

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs.update({'titulo': 'Meu perfil'})
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, 'Dados alterados com sucesso.')
        return super(PerfilUsuarioView, self).form_valid(form)


class AlterarSenhaUsuarioView(LoginRequiredMixin, FormView):
    form_class = PasswordChangeForm
    template_name = 'formulario.html'
    success_url = '/'

    def get_success_url(self):
        return reverse_lazy('base:meu_perfil')

    def get_object(self, queryset=None):
        return self.request.user

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user': self.request.user})
        return kwargs

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs.update({'titulo': 'Alterar senha'})
        return kwargs

    def form_valid(self, form):
        user = form.save()
        update_session_auth_hash(self.request, user)
        messages.success(self.request, 'Senha alterada com sucesso.')

        return super().form_valid(form)


class AlertaListView(ListView, LoginRequiredMixin):
    template_name = 'alert_list.html'

    def get_queryset(self):
        return self.request.user.notifications.unread()


class ImportarUsuariosFormView(FormView, UserPassesTestMixin):
    form_class = ImportarUsuariosForm
    template_name = 'formulario.html'
    success_url = '/'

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        kwargs.update(
            {
                'titulo': 'Importar usuários',
                'texto': 'Cole aqui o conteúdo do google planilhas. Colunas esperadas: cpf, nome, email, telefone e '
                         '(cnes_unidade ou id_distrito).'
            }
        )
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Usuários importados')
        return super().form_valid(form)


class LocalizaSUSView(TemplateView):
    template_name = 'iframe.html'

    def get_context_data(self, **kwargs):
        context = super(LocalizaSUSView, self).get_context_data()
        context['url'] = 'https://localizasus.lais.ufrn.br'
        return context
