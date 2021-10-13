from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'base'

urlpatterns = [
    path('pessoa/', views.BuscaPessoaView.as_view(), name='busca_pessoa'),
    path('pessoa/<str:pk>/', views.PessoaView.as_view(), name='pessoa'),
    path('carregando', views.TemplateView.as_view(template_name='preload.html'), name='carregando'),
    path('meu_perfil', views.PerfilUsuarioView.as_view(), name='meu_perfil'),
    path('alterar_senha', views.AlterarSenhaUsuarioView.as_view(), name='alterar_senha'),
    path('cadastrar', views.CadastroUsuarioView.as_view(), name='cadastrar'),
    path('cadastrar/usuario_distrito', views.CadastroUsuarioDistritoView.as_view(), name='cadastrar_usuario_distrito'),
    path('cadastrar/usuario_ab', views.CadastroUsuarioABView.as_view(), name='cadastrar_usuario_ab'),
    path('cadastrar/usuario_vigilancia', views.CadastroUsuarioVigilanciaView.as_view(), name='cadastrar_usuario_vigilancia'),
    path('cadastrar/usuario_estabelecimento_saude', views.CadastroEstabelecimentoSaudeView.as_view(), name='cadastrar_usuario_estabelecimento_saude'),
    path('cadastrar/usuario/importar/', views.ImportarUsuariosFormView.as_view(), name='cadastrar_usuario_importar'),
    path('entrar/', auth_views.LoginView.as_view(), {'template_name': '/login.html'}, name='login'),
    path('sair/', auth_views.LogoutView.as_view(), name='logout'),
    path('alertas/', views.AlertaListView.as_view(), name='alertas'),
    path('localizasus/', views.LocalizaSUSView.as_view(), name='localizasus'),
]
