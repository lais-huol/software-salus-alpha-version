from django.urls import path

from . import views

app_name = 'notificacoes'

urlpatterns = [
    path('', views.NotificacaoListView.as_view(), name='listar'),
    path('pessoa/<str:pk>', views.NotificacaoPessoaView.as_view(), name='listar_por_pessoa'),
    path('xlsx/', views.NotificacaoXLSXView.as_view(), name='baixar_excel'),
    path('csv/', views.NotificacaoCSVView.as_view(), name='baixar_csv'),
    path('recentes', views.NotificacaoRecentesView.as_view(), name='listar_recentes'),
    path('gal/', views.NotificacaoGALListView.as_view(), name='listar_gal'),
    path('pendentes/', views.NotificacaoPendenteListView.as_view(), name='listar_pendentes'),
    path('atualizacoes/', views.listar_alteradas, name='listar_alteradas'),
    path('<int:pk>/', views.NotificacaoDetailView.as_view(), name='visualizar'),
    path('_<int:pk>/', views.NotificacaoAllDetailView.as_view(), name='visualizar_todos'),
    path('<int:pk>/alterar_gal/', views.GALFormView.as_view(), name='alterar_gal'),
    path('<int:pk>/monitoramentos/novo/', views.novo_monitoramento, name='novo_monitoramento'),
    path('<int:pk>/monitoramentos/novo-sem-contato/', views.novo_monitoramento_sem_contato, name='novo_monitoramento_sem_contato'),
    path('monitoramentos/', views.MonitoramentoListView.as_view(), name='listar_monitoramentos'),
    path('monitoramentos/<int:pk>/', views.MonitoramentoDetailView.as_view(), name='visualizar_monitoramento'),
    path('importar/esusve/', views.ImportarNotificacaoEsusveFormView.as_view(), name='importar_esusve'),
    path('importar/sivep/', views.ImportarNotificacaoSivepFormView.as_view(), name='importar_sivep'),
    path('associar_bairros/', views.AssociacaoBairroView.as_view(), name='associar_bairros'),
    path('associar_bairros_individuais/', views.AssociacaoBairroNotificacaoView.as_view(), name='associar_bairros_individuais'),
    path('associar_estabelecimentos/', views.AssociacaoEstabelecimentoView.as_view(), name='associar_estabelecimentos'),
    path('estabelecimentos_associados/', views.EstabelecimentosAssociadosView.as_view(), name='estabelecimentos_associados'),
    path('associar/bairros_associados/', views.BairrosAssociadosView.as_view(), name='bairros_associados'),
    path('associar_pacientes/', views.AssociacaoPacienteView.as_view(), name='associar_pacientes'),
    path('associar/pacientes_associados/', views.PacientesAssociadosView.as_view(), name='pacientes_associados'),
    path('associar/associar_operadorcnes/', views.AssociacaoOperadorCNESView.as_view(), name='associar_operador_cnes'),
    path('definir_principais/', views.definir_principais, name='definir_principais'),
    path('resetar_cache_processamento/', views.ResetarCacheProcessamentoView.as_view(), name='resetar_cache_processamento'),
    path('listar_pacientes/<str:tipo>', views.PacienteInternacaoListView.as_view(), name='listar_pacientes'),
    path('paciente/<int:pk>/verificar_obito/', views.paciente_verificar_obito, name='paciente_verificar_obito'),
    path('teste/', views.teste, name='teste'),
    path('obitos/registrar', views.iniciar_registrar_obito, name='iniciar_registrar_obito'),
    path('obitos/registrar/<str:cpf>', views.registrar_obito, name='registrar_obito'),
    path('obitos/<int:pk>/vincular-pessoa', views.vincular_pessoa_a_obito, name='vincular_pessoa_a_obito'),
    path('obitos/<int:pk>/vincular-pessoa/<str:cpf>', views.vincular_pessoa_a_obito_confirmar, name='vincular_pessoa_a_obito_confirmar'),
    path('obitos/validar/<int:pk>', views.validar_obito, name='validar_obito'),
    path('obitos/', views.ObitoListView.as_view(), name='listar_obitos'),
    path('obitos/<int:pk>/', views.ObitoDetailView.as_view(), name='visualizar_obito'),
]
