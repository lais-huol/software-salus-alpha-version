import datetime
import json
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone

from base.caches import ControleCache
from base.models import Bairro, HabitacoesBairro, AssociacaoBairro
from base.signals import fonte_de_dados_indicadores_alterados
from base.utils import calculateAge
from indicadores.paineis import ParametroBoletim, PainelBoletim, ParametroCatalogo, PainelCatalogo, ParametroPublico, \
    PainelPublico
from indicadores.catalogo import get_catalogo_indicadores
from indicadores.indicadores import *
from indicadores.catalogo import get_catalogo_indicadores
from indicadores.models import ModeloAplicacao
from notificacoes.models import Notificacao, UploadImportacao, PacienteInternacao

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Carrega dados iniciais'

    def validar_indicadores_boletim(self):
        class Get():
            def __init__(self, data_do_boletim, semana_para, numero_do_boletim):
                self.dict = {}
                self.dict['semana_boletim'] = semana_para
                self.dict['data_do_boletim'] = data_do_boletim
                self.dict['numero_do_boletim'] = numero_do_boletim

            def get(self, chave, valor_padrao):
                return self.dict.get(chave, valor_padrao)

        class Request():
            GET = Get('2020-07-07', '27/2020', 13)
        request = Request()

        indicador_parametro = ParametroBoletim(request)
        indicador = PainelBoletim(indicador_parametro)
        indicador.cache.reset()
        print(indicador_parametro.data_inicial, indicador_parametro.data_final)
        for chave in indicador.get_ids_catalogo():
            try:
                print('gerando indicador', chave)
                indicador.get_dados(chave)
            except Exception as err:
                print('>>>>>>>>>>>>>>>>>>>>>>>> Falha ao gerar o indicador ', chave)
                raise err


    def validar_indicadores_painel_publico(self):
        indicador_parametro = ParametroPublico(request=None)
        indicador = PainelPublico(indicador_parametro, True, True)
        indicador.cache.reset()
        print(indicador_parametro.data_inicial, indicador_parametro.data_final)
        for chave in indicador.get_ids_catalogo():
            try:
                print('gerando indicador', chave)
                indicador.get_dados(chave)
            except Exception as err:
                print('>>>>>>>>>>>>>>>>>>>>>>>> Falha ao gerar o indicador ', chave)
                raise err

    def validar_indicadores_catalogo(self):
        indicador_parametro = ParametroCatalogo()
        indicador = PainelCatalogo(indicador_parametro, True, True)
        indicador.cache.reset()
        for chave in get_catalogo_indicadores().keys():
            try:
                print('gerando indicador', chave)
                indicador.get_dados(chave)
            except AttributeError:
                print('>>>>>>>>>>>>>>>>>>>>>>>> atributo não encontrado ', chave)
            except Exception as err:
                print('>>>>>>>>>>>>>>>>>>>>>>>> Falha ao gerar o indicador ', chave)
                # raise err

    def teste_indicador_catalogo(self, pk):
        indicador_parametro = ParametroCatalogo()
        indicador = PainelCatalogo(indicador_parametro, True, True)
        indicador.cache.reset()
        print(indicador.get_visualizacao(pk))
        print(indicador.get_dados(pk))


    def handle(self, *args, **kwargs):
        # self.validar_indicadores_catalogo()
        # self.validar_indicadores_painel_publico()
        # self.teste_indicador_catalogo('taxa_mortalidade')
        # ,
        # evolucao_caso_por_data_tipo_grafico_linha
        self.validar_indicadores_painel_publico()
        # self.validar_indicadores_catalogo()
        #taxa_incidencia_acumulada_distrito_por_data_notificacao_grafico_linha
        #taxa_incidencia_acumulada_por_data_notificacao_grafico_linha
        #casos_acumulados_confirmados_distrito_por_semana_notificacao_grafico_linha

        import sys;
        sys.exit()


        # print(indicador.get_dados('obitos'))
        # print(indicador.get_dados('grafico_obitos_confirmados_dia'))
        # print(indicador.get_dados('grafico_obitos_confirmados_dia_acumulado'))
        # print(indicador.get_dados('grafico_obitos_confirmados_semana'))
        # print(indicador.get_dados('grafico_obitos_confirmados_semana_acumulado'))
        # print(indicador.get_dados('grafico_obitos_confirmados_sexo_idade'))
        # print(indicador.get_dados('grafico_casos_confirmados_sexo_idade'))
        # # print(indicador.get_dados('grafico_letalidade_por_data'))
        # print(indicador.get_dados('grafico_obitos_confirmados_por_data'))



        import sys; sys.exit()
        valores = list(dados['series'].values())[0]
        categorias = list(dados['categories'])

        notificacoes_estado_do_teste = {}
        for i in range(0, len(dados['categories'])):
            notificacoes_estado_do_teste[categorias[i]] = valores[i]


        # dados = indicador.get_dados('grafico_resultado_dos_testes_por_tipo_de_resultado')

        print(notificacoes_estado_do_teste)
        #


        notificacoes_estado_do_teste = {
            'Solicitado': qs.filter(dados__estado_do_teste='Solicitado').count(),
            'Coletado': qs.filter(dados__estado_do_teste='Coletado').count(),
            'Concluído': qs.filter(dados__estado_do_teste='Concluído').count(),
            'Desconhecido': qs.filter(dados__estado_do_teste=None).count(),
        }
        print(notificacoes_estado_do_teste)

        import sys; sys.exit()

        # gestante_de_alto_risco
        # municipio_de_notificacao
        # estado_de_notificacao
        # notificante_cnpj
        # estado_do_teste1
        # tipo_de_teste1
        # resultado_do_teste1
        # gestante
        # data_de_coleta_do_teste

        # Notificacao.processar_notificacoes_similares()
        # qs = Notificacao.objects.filter(dados__municipio_de_residencia__iexact='Natal')
        # for n in qs.values('dados__municipio_de_notificacao',
        #                                     'dados__estado_de_notificacao',).annotate(Count('numero')).order_by('dados__municipio_de_notificacao'):
        #     print('{}/{}: {}'.format(n['dados__municipio_de_notificacao'],
        #                                      n['dados__estado_de_notificacao'],
        #                                      n['numero__count']))

        # fonte_de_dados_indicadores_alterados.send(sender=None)

        # #para visualizar somente os dados
        # dados = indicador.get_dados('grafico_resultado_dos_testes_por_tipo_de_resultado')
        # print(dados)

        # print(indicador.get_visualizacao('grafico_obitos_confirmados')) #titulo

        # import ipdb; ipdb.set_trace()

        # #Obtem json dos dados do csv com óbitos ('indicadores/fixtures/lais_obitos.csv')
        # # e adiciona no cache com a chave 'obitos_planilha'
        # from base.utils import csv_to_json
        # from django.core.cache import cache
        # obitos_json_data = csv_to_json('indicadores/fixtures/lais_obitos.csv')
        # cache.set('obitos_planilha', obitos_json_data)
        # print("Imprimindo dados do cache - key: 'obitos_planilha'")
        # print(cache.get('obitos_planilha'))

