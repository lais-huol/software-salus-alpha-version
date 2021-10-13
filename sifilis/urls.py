from django.urls import path

from . import views

app_name = 'sifilis'

urlpatterns = [
    path('pessoa/<str:pk>', views.DadosPessoaView.as_view(), name='listar_por_pessoa'),
    path('pessoa/<str:pessoa_pk>/planos-terapeuticos/adicionar/',
         views.adicionar_plano_terapeutico_passo_1,
         name='adicionar_plano_terapeutico'),
    path('pessoa/<str:pessoa_pk>/planos-terapeuticos/adicionar/cid:<str:cid_pk>/',
         views.adicionar_plano_terapeutico_passo_2,
         name='adicionar_plano_terapeutico_passo_2'),
    path('pessoa/<str:pessoa_pk>/planos-terapeuticos/adicionar/cid:<str:cid_pk>/adicionar-novo-plano-terapeutico/',
         views.adicionar_novo_plano_terapeutico_e_vincular_ao_paciente,
         name='adicionar_novo_plano_terapeutico_e_vincular_ao_paciente'),
    path('planos-terapeuticos-de-pacientes/<int:pk>/',
         views.plano_terapeutico_paciente_view,
         name='plano_terapeutico_paciente'),
    path('planos-terapeuticos-de-pacientes/<int:pk>/suspender/',
         views.plano_terapeutico_paciente_suspender,
         name='plano_terapeutico_paciente_suspender'),
    path('planos-terapeuticos-de-pacientes/<int:pk>/finalizar/',
         views.plano_terapeutico_paciente_finalizar,
         name='plano_terapeutico_paciente_finalizar'),
    path('pessoa/<str:pessoa_pk>/exames/adicionar/',
         views.adicionar_exame_passo_1,
         name='adicionar_exame'),
    path('pessoa/<str:pessoa_pk>/exames/adicionar/tipoexame:<str:tipoexame_pk>/',
         views.adicionar_exame_passo_2,
         name='adicionar_exame_passo_2'),
    path('pessoa/<str:pessoa_pk>/relacionamentos/adicionar/',
         views.adicionar_relacionamento,
         name='adicionar_relacionamento'),
    path('pessoa/<str:pessoa_pk>/antecedentes/adicionar/',
         views.adicionar_antecedente,
         name='adicionar_antecedente'),
]
