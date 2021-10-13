from django.urls import path, include
from rest_framework import routers

from . import views

app_name = 'api'


router = routers.DefaultRouter()
# router.register(r'notificacao', views.NotificacaoViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('<int:pk>/gal', views.NotificacaoGALAPIView.as_view(), name='notificacao_gal'),
    path('<str:pk>/associacaocnes', views.AssociacaoNomeEstabelecimentoSaudeAPIView.as_view(), name='associacao_nome_estabelecimento'),

    path('publica/extrato_geral', views.PainelGeralAPIView.as_view(), name='publica_extrato_geral'),
    path('publica/microdados', views.MicrodadosAPIView.as_view(), name='publica_microdados'),

    path('cns/<str:cpf_ou_cns>', views.CNSView.as_view(), name='api_cns'),

    path('busca_paciente', views.BuscaPacienteView.as_view(), name='busca_paciente'),
]
