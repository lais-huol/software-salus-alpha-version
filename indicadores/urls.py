from django.urls import path
from django.views.decorators.cache import cache_page

from . import views

app_name = 'indicadores'

urlpatterns = [
    path('', views.InicioView.as_view(), name='inicio'),
    path('boletins', views.BoletimListView.as_view(), name='listar_boletins'),
    path('boletins/novo', views.BoletimCreateView.as_view(extra_context={'titulo': 'Novo boletim'}), name='novo_boletim'),
    path('boletins/<int:pk>', views.BoletimDetailView.as_view(), name='visualizar_boletim'),
    path('boletins/editar/<int:pk>', views.BoletimEditView.as_view(extra_context={'titulo': 'Alterar boletim'}), name='editar_boletim'),
    path('boletins/remover/<int:pk>', views.BoletimDeleteView.as_view(), name='remover_boletim'),
    path('modelos_painel', views.ModeloPainelListView.as_view(), name='listar_modelos_painel'),
    path('modelos_painel/novo', views.ModeloPainelCreateView.as_view(extra_context={'titulo': 'Novo modelo de painel'}), name='novo_modelo_painel'),
    path('modelos_painel/<int:pk>', views.ModeloPainelEditView.as_view(extra_context={'titulo': 'Alterar modelo de painel'}), name='editar_modelo_painel'),
    path('modelos_painel/remover/<int:pk>', views.ModeloPainelDeleteView.as_view(), name='remover_modelo_painel'),
    path('modelos_painel/clonar/<int:pk>', views.ModeloPainelCloneView.as_view(extra_context={'titulo': 'Novo modelo de painel'}), name='clonar_modelo_painel'),
    path('painel_publico', (views.PainelPublicoView.as_view()), name='painel_publico'),
    path('previa_boletim', views.PreviaBoletimView.as_view(), name='previa_boletim'),
    path('previa_indicador', views.PreviaIndicadorView.as_view(), name='previa_indicador'),
    path('painel_publico/indicador_ajax', views.IndicadorAjaxPainelPublicoView.as_view(), name='painel_publico_indicador_ajax'),
    path('gerais', views.IndicadoresGeraisView.as_view(), name='gerais'),
]
