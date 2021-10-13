import re

from django.db.models import Func, F, Value, CharField
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import cache_page
from rest_framework import viewsets, mixins, generics, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.serializers import NotificacaoSerializer, NotificacaoGALSerializer, \
    AssociacaoNomeEstabelecimentoSaudeSerializer
from base import rest_cns
from base.models import PessoaFisica
from base.utils import qs_to_csv_response, AgeYear
from indicadores.paineis import ParametroCatalogo, PainelCatalogo
from notificacoes.models import Notificacao, AssociacaoNomeEstabelecimentoSaude

from django.contrib.postgres.search import SearchVector


class NotificacaoViewSet(mixins.RetrieveModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = Notificacao.ativas.all()
    serializer_class = NotificacaoSerializer


class NotificacaoGALAPIView(generics.UpdateAPIView):
    queryset = Notificacao.objects.all()
    serializer_class = NotificacaoGALSerializer
    permission_classes = (IsAuthenticated,)


class AssociacaoNomeEstabelecimentoSaudeAPIView(generics.CreateAPIView):
    queryset = AssociacaoNomeEstabelecimentoSaude.objects.all()
    serializer_class = AssociacaoNomeEstabelecimentoSaudeSerializer
    permission_classes = (IsAuthenticated,)

    def perform_create(self, serializer):
        obj = AssociacaoNomeEstabelecimentoSaude.objects.filter(
            nome=serializer.validated_data.get('nome', None)
        ).first()
        if obj:
            obj.delete()
            obj.codigo_cnes = serializer.validated_data.get('codigo_cnes', None)
            obj.save()
        else:
            serializer.save()


class CNSView(views.APIView):

    permission_classes = (IsAuthenticated,)

    def get(self, request, cpf_ou_cns):
        cpf_ou_cns = re.sub('\D', '', cpf_ou_cns)
        if not cpf_ou_cns:
            return Response(data={})
        return Response(data=rest_cns.get_dados(cpf_ou_cns))



class BuscaPacienteView(views.APIView):

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        busca = request.GET['busca']
        if not busca.lower().islower():
            busca = re.sub('\D', '', busca)
        resultado = PessoaFisica.objects.annotate(search=SearchVector('nome', 'cpf', 'cns'),
            data_nascimento=Func(
                F('data_de_nascimento'),
                Value('dd/MM/yyyy'),
                function='to_char',
                output_field=CharField()
            )).filter(search=busca)\
            .only('nome', 'cpf', 'cns', 'data_nascimento').values('nome', 'cpf', 'cns', 'data_nascimento')[:20]

        if not busca:
            return Response(data={})
        return Response(data=resultado)


# API SEMPLA


class PainelGeralAPIView(views.APIView):
    def get(self, request, format=None):
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


        dados = indicador.get_dados('casos_confirmados_por_tipo_teste_grafico_pizza')
        valores = list(dados['series'].values())[0]
        categorias = list(dados['categories'])

        notificacoes_tipo_do_teste = {}
        for i in range(0, len(dados['categories'])):
            inteiro, porcentagem = valores[i]
            inteiro = int(inteiro)
            notificacoes_tipo_do_teste[categorias[i]] = (inteiro, porcentagem)

        dados = indicador.get_dados('casos_confirmados_raca_grafico_coluna')
        valores = list(dados['series'].values())[0]
        categorias = list(dados['categories'])

        notificacoes_confirmadas_raca_cor = {}
        for i in range(0, len(dados['categories'])):
            inteiro, porcentagem = valores[i]
            inteiro = int(inteiro)
            notificacoes_confirmadas_raca_cor[categorias[i]] = (inteiro, porcentagem)

        dados = indicador.get_dados('notificacoes_raca_grafico_coluna')
        valores = list(dados['series'].values())[0]
        categorias = list(dados['categories'])

        notificacoes_gerais_raca_cor = {}
        for i in range(0, len(dados['categories'])):
            inteiro, porcentagem = valores[i]
            inteiro = int(inteiro)
            notificacoes_gerais_raca_cor[categorias[i]] = (inteiro, porcentagem)

        dict_dados = {'resultado_do_teste': notificacoes_resultado_do_teste,
                      'estado_do_teste': notificacoes_estado_do_teste,
                      'tipo_do_teste': notificacoes_tipo_do_teste,
                      'todas_raca_cor': notificacoes_gerais_raca_cor,
                      'confirmados_raca_cor': notificacoes_confirmadas_raca_cor,
                      'total_recuperados': indicador.get_dados('total_recuperados'),
                      'total_isolamento': indicador.get_dados('total_isolamento')
                      }

        return Response(dict_dados)


@method_decorator(cache_page(60 * 60 * 22), name='dispatch')
class MicrodadosAPIView(View):
    queryset = Notificacao.ativas

    def get(self, request):
        colunas = Notificacao.MAPEAMENTO_COLUNAS.copy()
        colunas_exclude = ['cpf', 'cns', 'nome_completo', 'passaporte', 'complemento', 'operador_cpf', 'bairro',
                           'notificante_cnpj', 'operador_email', 'telefone_celular', 'data_de_nascimento',
                           'telefone_de_contato', 'nome_completo_da_mae', 'operador_nome_completo', 'outros',
                           'logradouro', 'numero_res', 'cep']
        for key in colunas_exclude:
            colunas.pop(key)
        qs = self.get_queryset().annotate(idade=AgeYear('data_de_nascimento')).values(
            *[f'dados__{x}' for x in colunas], 'idade'
        )

        return self.exportar(qs, 'download', {
            **{f'dados__{k}': f'{v}' for k, v in colunas.items()}, 'idade': 'Idade'
        })

    def exportar(self, qs, arquivo, dados):
        return qs_to_csv_response(qs, arquivo, dados)

    def get_queryset(self):
        return self.queryset.all()
