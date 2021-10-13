from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = 'administracao'

urlpatterns = [
    path('bairro/novo/', views.BairroCreateView.as_view(), name='cadastrar_bairro'),
    path('bairros', views.BairroListView.as_view(), name='listar_bairros'),
    path('bairro/remover/<int:pk>', views.BairroDeleteView.as_view(), name='remover_bairro'),
    path('bairro/editar/<int:pk>', views.BairroEditView.as_view(), name='alterar_bairro'),

    path('habitacao/novo/', views.HabitacaoCreateView.as_view(), name='cadastrar_habitacao'),
    path('habitacao', views.HabitacaoListView.as_view(), name='listar_habitacoes'),
    path('habitacao/remover/<int:pk>', views.HabitacaoDeleteView.as_view(), name='remover_habitacao'),
    path('habitacao/editar/<int:pk>', views.HabitacaoEditView.as_view(), name='alterar_habitacao'),

    path('distrito/novo/', views.DistritoCreateView.as_view(), name='cadastrar_distrito'),
    path('distrito', views.DistritoListView.as_view(), name='listar_distritos'),
    path('distrito/remover/<int:pk>', views.DistritoDeleteView.as_view(), name='remover_distrito'),
    path('distrito/editar/<int:pk>', views.DistritoEditView.as_view(), name='alterar_distrito'),

    # path('associacaobairro/novo/', views.AssociacaoBairroCreateView.as_view(), name='cadastrar_associacaobairro'),
    path('associacaobairro', views.AssociacaoBairroListView.as_view(), name='listar_associacoesbairro'),
    # path('associacaobairro/remover/<int:pk>', views.AssociacaoBairroDeleteView.as_view(), name='remover_associacaobairro'),
    path('associacaobairro/editar/<int:pk>', views.AssociacaoBairroEditView.as_view(), name='alterar_associacaobairro'),

    path('pacientesinternados', views.PacienteInternacaoListView.as_view(), name='listar_pacientesinternados'),
    path('pacienteinternado/editar/<int:pk>', views.PacienteInternacaoEditView.as_view(), name='alterar_pacienteinternado'),

    path('uploadimportacao', views.UploadImportacaoListView.as_view(), name='listar_uploadimportacao'),
    path('uploadimportacao/visualizar/<int:pk>', views.UploadImportacaoDetailView.as_view(), name='visualizar_uploadimportacao'),
]
