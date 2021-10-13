import importlib
import json
import os

from django.db.models import Max
from django.dispatch import receiver
from django.utils import timezone
from highcharts import Highchart, Highmap
from highcharts.highcharts.highchart_types import PLOT_OPTION_ALLOWED_ARGS
from highcharts.highcharts.highcharts import HighchartsEncoder
from highcharts.highmaps import highmaps
from past.types import basestring

from base.caches import ControleCache
from base.signals import fonte_de_dados_indicadores_alterados
from base.utils import dict_compare, normalize_str
from indicadores.catalogo import get_catalogo_indicadores
from indicadores.enums import TipoVisualizacao, ValorFormaExbicao, TipoMapa
from indicadores.htmltable import HTMLTable
from indicadores.indicadores import *
from indicadores.utils import levenshtein_closest

logger = logging.getLogger(__name__)


TIPO_VISUALIZACAO_MAP = {
    TipoVisualizacao.BARRA: 'bar',
    TipoVisualizacao.BARRA_STAKING: 'bar',
    TipoVisualizacao.COLUNA: 'column',
    TipoVisualizacao.COLUNA_STAKING: 'column',
    TipoVisualizacao.LINHA: 'line',
    TipoVisualizacao.PIZZA: 'pi',
}

@receiver(fonte_de_dados_indicadores_alterados)
def reset_cache_indicadores_boletim(sender, **kwargs):
    PainelBoletim._reset_cache()
    PainelCatalogo._reset_cache()
    PainelPublico._reset_cache()


class HighchartBase(Highchart):
    def __init__(self, **kwargs):
        super(HighchartBase, self).__init__(**kwargs)
        self.setOptions = {
            'lang': {
                'months': ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro',
                           'Outubro', 'Novembro', 'Dezembro'],
                'weekdays': ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'],
                'decimalPoint': ',',
                'thousandsSep': ' ',
                'loading': 'Carregando...',
                'numericSymbols': None,
            },
        }
        self.add_JSsource('js/Highcharts-Stock-8.1.2/code/highstock.js')
        self.add_JSsource('js/Highcharts-Stock-8.1.2/indicators/indicators.js')
        self.data_extra = []
        self.FONTSIZE = '8px'

    def add_data_extra(self, data):
        self.data_extra.append(data)


class CustomHighchart(HighchartBase):
    def __init__(self, **kwargs):
        super(CustomHighchart, self).__init__()
        self.container_title = kwargs.get('container_title', '')
        self.exibir_titulo = kwargs.get('exibir_titulo', True)
        self.exibir_identificador = kwargs.get('exibir_titulo', False)

    def buildcontainer(self):
        super(CustomHighchart, self).buildcontainer()
        container = self.container
        self.container = ''
        return container

    def buildcontent(self):
        self.options['credits'] = {'text': 'Fonte: Salus'}
        self.option = json.dumps(self.options, cls=HighchartsEncoder)
        self.setoption = json.dumps(self.setOptions, cls=HighchartsEncoder)

        for i in range(0, len(self.data_extra)):
            self.data_temp[i].__dict__.update({
                                               "data_extra": self.data_extra[i],
                                           })

        self.data = json.dumps(self.data_temp, cls=HighchartsEncoder)
        self.data_list = [json.dumps(x, cls=HighchartsEncoder) for x in self.data_temp]
        if self.drilldown_flag:
            self.drilldown_data = json.dumps(self.drilldown_data_temp, cls=HighchartsEncoder)

        return self.template_content_highcharts.render(chart=self)


class CustomHighmap(Highmap):
    def __init__(self, **kwargs):
        super(CustomHighmap, self).__init__(**kwargs)
        self.set_dict_options({
            'lang': {
                'months': ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro',
                           'Outubro', 'Novembro', 'Dezembro'],
                'weekdays': ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'],
                'decimalPoint': ',',
                'thousandsSep': '.',
                'loading': 'Carregando...',
                'numericSymbols': None,
            },
        })
        self.container_title = kwargs.get('container_title', '')
        self.exibir_titulo = kwargs.get('exibir_titulo', True)
        self.exibir_identificador = kwargs.get('exibir_titulo', False)

        self.options['chart'].ALLOWED_OPTIONS['map'] = (dict)
        # self.data_extra = []
        # self.FONTSIZE = '9px'

    # def add_data_extra(self, data):
    #     self.data_extra.append(data)

    def buildcontainer(self):
        super(CustomHighmap, self).buildcontainer()
        container = self.container
        self.container = ''
        return container

    def buildcontent(self):
        self.buildhtmlheader()
        self.options['credits'] = {'text': 'Fonte: Salus'}
        self.option = json.dumps(self.options, cls=highmaps.HighchartsEncoder)
        self.setoption = json.dumps(self.setOptions, cls=highmaps.HighchartsEncoder)
        self.data = json.dumps(self.data_temp, cls=highmaps.HighchartsEncoder)

        if self.drilldown_flag:
            self.drilldown_data = json.dumps(self.drilldown_data_temp, cls=highmaps.HighchartsEncoder)
        self._htmlcontent = self.template_content_highcharts.render(chart=self).encode('utf-8')

        return self._htmlcontent.decode('utf-8') # need to ensure unicode
        # self.option = json.dumps(self.options, cls=HighchartsEncoder)
        # self.setoption = json.dumps(self.setOptions, cls=HighchartsEncoder)
        # self.data = json.dumps(self.data_temp, cls=HighchartsEncoder)

        # if self.drilldown_flag:
        #     self.drilldown_data = json.dumps(self.drilldown_data_temp, cls=HighchartsEncoder)
        # self._htmlcontent = self.template_content_highcharts.render(chart=self)
        # return self._htmlcontent
    #     # self.options['credits'] = {'text': 'Fonte: Salus'}
    #     self.option = json.dumps(self.options, cls=HighchartsEncoder)
    #     self.setoption = json.dumps(self.setOptions, cls=HighchartsEncoder)
    #     self.data = json.dumps(self.data_temp, cls=HighchartsEncoder)
    #
    #     if self.drilldown_flag:
    #         self.drilldown_data = json.dumps(self.drilldown_data_temp, cls=HighchartsEncoder)
    #     return self.template_content_highcharts.render(chart=self)



class IndicadorParametro(object):
    def __init__(self, request):
        self.request = request
        self._set_parametros_from_request(request)

    @property
    def kwargs(self):
        raise NotImplementedError()

    @property
    def filtro_apresentacao(self):
        raise NotImplementedError()

    def _set_parametros_from_request(self, request):
        raise NotImplementedError()


class ParametroPublico(IndicadorParametro):
    def __init__(self, request):
        super(ParametroPublico, self).__init__(request)

    @property
    def kwargs(self):
        akwargs = {}
        akwargs['data_inicial'] = self.data_inicial
        akwargs['data_final'] = self.data_final
        akwargs['ano_boletim'] = self.ano_boletim
        akwargs['semana_boletim'] = self.semana_boletim
        akwargs['async'] = self._async

        return akwargs

    @property
    def filtro_apresentacao(self):
        return ''

    def _set_parametros_from_request(self, request):
        self.data_inicial = Notificacao.objects.aggregate(Min('data'))['data__min']
        self.data_final = timezone.now().date()
        self._async = True

        obj_semana = DataSemana.get_semana(self.data_final)
        self.semana_boletim = obj_semana.semana
        self.ano_boletim = obj_semana.ano


class ParametroBoletim(IndicadorParametro):
    def __init__(self, request=None, dados_parametro=None):
        super(ParametroBoletim, self).__init__(request)
        self.semana_ano_boletim = None
        if dados_parametro is not None:
            self.__dict__ = dados_parametro

    def _set_parametros_from_request(self, request):
        if request:
            self.data_do_boletim = request.GET.get('data_do_boletim', None)
            self.semana_ano_boletim = request.GET.get('semana_boletim', None)  # padrão semana/ano
            self.data_do_boletim = datetime.date.fromisoformat(self.data_do_boletim)
            self.numero_do_boletim = request.GET.get('numero_do_boletim', None)

        semana_e_ano = self.semana_ano_boletim.split('/')
        self.semana_boletim = int(semana_e_ano[0])
        self.ano_boletim = int(semana_e_ano[1])

        data_semana = DataSemana(self.ano_boletim, self.semana_boletim)
        self.semana_data_inicial, self.semana_data_final = data_semana.get_periodo((0, 0))
        self.quinzena_data_inicial, self.quinzena_data_final = data_semana.get_periodo((-1,0))

        self.semana_data_inicial, self.semana_data_final = DataSemana(self.ano_boletim,
                                                                      self.semana_boletim).get_periodo()

        self.data_inicial = Notificacao.objects.aggregate(min_data=Min('data'))['min_data']


    @property
    def kwargs(self):
        akwargs = {}
        akwargs['data_final'] = self.data_do_boletim
        akwargs['data_inicial'] = self.data_inicial
        akwargs['semana_boletim'] = self.semana_boletim
        akwargs['ano_boletim'] = self.ano_boletim
        return akwargs

    @property
    def filtro_apresentacao(self):
        data_inicio_apresentacao = DataExtenso(self.data_inicial).data_extenso('%d/{m:3}/%Y')
        data_final_apresentacao = DataExtenso(self.data_do_boletim).data_extenso('%d/{m:3}/%Y')
        return '({}-{})'.format(
            data_inicio_apresentacao,
            data_final_apresentacao
        )


class ParametroCatalogo(ParametroBoletim):
    def __init__(self):
        super(ParametroCatalogo, self).__init__(request=None, dados_parametro=None)

    def _set_parametros_from_request(self, request):
        self.data_do_boletim =  Notificacao.objects.aggregate(Max('data'))['data__max']
        semana = DataSemana.get_semana(self.data_do_boletim)
        self.semana_ano_boletim = '{}/{}'.format(semana.semana, semana.ano)# padrão semana/ano

        super(ParametroCatalogo, self)._set_parametros_from_request(request)

        self.numero_do_boletim = 0


class PainelIndicadorComum(object):
    def __init__(self, indicador_parametro, exibir_titulo=True, exibir_identificador=False):
        '''
        :param parametros: do tipo IndicadorParametro
        '''
        self.args = indicador_parametro
        self._exibir_titulo = exibir_titulo
        self._exibir_identificador = exibir_identificador
        class_nome = self._get_nome_cache()

        self._cache = ControleCache.indicadores(class_nome)
        args = self.args.__dict__.copy()
        args.pop('request', None)

        if self._cache.exists():
            cache_args = self._cache.get().get('parametros', None)
            if cache_args:
                a, r, diff, s = dict_compare(cache_args, args)

                if diff:
                    self._cache.reset()

        self._cache.add('parametros', args)

    def _get_nome_cache(self):
        return self.__class__._get_class_nome()

    def _get_dados_in_cache(self, pk):
        if self._cache.exists():
            _cache = self._cache.get()
            if _cache.get(pk):
                logger.debug('Obtendo dados do indicador [{}]  do cache [{}].'.format(pk, self._get_nome_cache()))
                return _cache[pk]
            else:
                logger.debug('Gerando dados para o indicador {}'.format(pk))
        else:
            logger.debug('Gerando dados para o indicador {}'.format(pk))

        return None

    @classmethod
    def _get_class_nome(cls):
        return '{}.{}'.format(__name__, cls.__name__.lower()).replace('.', '__')

    @classmethod
    def _reset_cache(cls):
        class_nome = cls._get_class_nome()
        ControleCache.indicadores(class_nome).reset()

    def get_ids_catalogo(self):
        raise NotImplementedError()

    @property
    def cache(self):
        return self._cache

    def exibir_titulo(self):
        return self._exibir_titulo

    def exibir_identificador(self):
        return self._exibir_identificador

    def _get_catalogo_indicadores(self, chave=None):
        return get_catalogo_indicadores(chave)

    def get_titulo(self, chave):
        catalogo = self._get_catalogo_indicadores()
        return catalogo[chave]['titulo']

    def get_tags(self):
        tags = []
        catalogo = self._get_catalogo_indicadores()
        for chave in self.get_ids_catalogo():
            tag = {
                'chave': chave,
                'titulo': catalogo[chave]['titulo']
            }
            tags.append(tag)
        return tags

    def _get_dados(self, catalogo, pk):
        logger.debug('')
        kwargs = {}
        mod_name, func_name = catalogo['fonte']['funcao'].split('.')
        if mod_name != 'self':
            module = importlib.import_module('indicadores.{}'.format(mod_name))
            func = getattr(module, func_name)
        else:
            func = getattr(self, func_name)
        if catalogo['fonte'].get('parametros', None):
            kwargs = catalogo['fonte']['parametros']
        kwargs.update(self.args.kwargs)
        try:
            dados_in_cache = self._get_dados_in_cache(pk)
            if dados_in_cache:
                return dados_in_cache
            dados = func(**kwargs) if kwargs else func()
            self._cache.add(pk, dados)
            return dados
        except:
            raise
        return None


    def get_dados(self, pk):
        try:
            catalogo = self._get_catalogo_indicadores(pk)
        except KeyError:
            return None
        return self._get_dados(catalogo, pk)

    def get_visualizacao(self, pk):
        try:
            catalogo = self._get_catalogo_indicadores(pk)
        except KeyError:
            return None

        if self.args.kwargs.get('async') and any([catalogo.get(x) for x in ['grafico', 'mapa']]):
            return {
                'titulo': catalogo['titulo'],
                'conteudo': (f'<div id="{pk}" data-async="true" style="height: 250px;"><div class="status"><div class="bouncingLoader"><div></div><div></div><div></div></div></div></div>', ''),
                'tipo': TipoConteudoVisualizacao.GRAFICO
            }
        dados = self._get_dados(catalogo, pk)
        if catalogo.get('grafico', None):
            dgrafico = catalogo['grafico']
            dgrafico['titulo'] = catalogo['titulo']
            grafico_func = dgrafico.get('funcao', self._get_grafico)
            return grafico_func(pk, dgrafico, dados)
        elif catalogo.get('tabela', None):
            dtabela = catalogo['tabela']
            dtabela['titulo'] = catalogo['titulo']
            tabela_func = dtabela.get('funcao', self._get_tabela)
            return tabela_func(pk, dtabela, dados)
        elif catalogo.get('mapa', None):
            dmapa = catalogo['mapa']
            dmapa['titulo'] = catalogo['titulo']
            dmapa_func = dmapa.get('funcao', self._get_mapa)
            return dmapa_func(pk, dmapa, dados)
        # dados = self._get_dados(catalogo, pk)
        return self._get_valor(catalogo, dados)

    def _get_mapa(self, pk, dmapa, dados):
        if dmapa['tipo'] == TipoMapa.CALOR:
            l = leaflet.Leaflet(pk, legend_heatmap=True, exibir_titulo=self.exibir_titulo())
            l.set_heatmap_data(dados)
            if self.exibir_titulo():
                l.titulo = '{} - {}.'.format(dmapa['titulo'], self.args.filtro_apresentacao)
            return {
                'tipo': TipoConteudoVisualizacao.MAPA,
                    'conteudo': (l.buildcontainer(), l.buildcontent()),
                    'titulo': dmapa['titulo']
                    }
        elif dmapa['tipo'] == TipoMapa.PADRAO:
            H = CustomHighmap(container_title='',
                                exibir_titulo=self.exibir_titulo(),
                                exibir_identificador=self.exibir_identificador)
            H.loading = ''
            with open(os.path.join(settings.BASE_DIR, dmapa.get('geojson'))) as f:
                geojson = json.load(f)
            bairros_geojson = [x['properties']['Name'] for x in geojson['features']]

            dados_colunas = dados['series']
            empty = False
            for nome in dados_colunas:
                if dados_colunas[nome] == []:
                    empty = True

            if empty:
                return {'tipo': TipoConteudoVisualizacao.MAPA,
                        'conteudo': (H.buildcontainer(), H.buildcontent()),
                        'titulo': dmapa['titulo']
                        }

            if dmapa.get('dados_extra'):
                for chave, nova_chave in dmapa['dados_extra'].items():
                    dados_colunas[nova_chave] = dados[chave]

            colunas = [dados_colunas[x] for x in dmapa['colunas']]

            linhas = list(zip(*colunas))
            mapeamento_colunas = dmapa.get('mapeamento_colunas')
            data = []
            for linha in linhas:
                data_l = {}
                for icol, col in enumerate(linha):
                    if icol == 0:
                        col = levenshtein_closest(col, bairros_geojson, True)[0][0]
                    data_l[mapeamento_colunas[icol]] = col
                data.append(data_l)

            titulo = '{} - {}.'.format(dmapa['titulo'], self.args.filtro_apresentacao)

            H.add_map_data(geojson)
            # H.add_data_set(bairros, 'mapline', 'Rivers', color='Highcharts.getOptions().colors[0]')
            H.add_data_set(data, 'map', dmapa['valor'], mapData=geojson, joinBy=['Name', 'code'], dataLabels={
                    'enabled': True,
                    'format': '{point.properties.Name}'
                })

            options = {  # construct option dict
                'chart': {'renderTo': pk, 'map': geojson},
                'title': {
                    'text': ''
                },
                'mapNavigation': {
                    'enabled': True,
                    'buttonOptions': {
                        'verticalAlign': 'bottom'
                    }
                },
                'colorAxis': {
                },
            }
            if self.exibir_titulo():
                options['title'] = {'text': '<p>{}</p>'.format(titulo)}

            H.set_dict_options(options)

            return {'tipo': TipoConteudoVisualizacao.MAPA,
                    'conteudo': (H.buildcontainer(), H.buildcontent()),
                    'titulo': dmapa['titulo']
                    }


    def _get_valor(self, catalogo, dados):
        return {'tipo': TipoConteudoVisualizacao.VALOR,
                'conteudo': dados,
                'titulo': catalogo['titulo'],
                }


    def _add_data_set(self, custom_high_chart, dgrafico, *args, **kwargs):
        kwargs['marker'] = {'enabled': False}
        high_chart_option = dgrafico.get('high_chart_option', None)
        # highchart_types.DATA_SERIES_ALLOWED_OPTIONS
        if high_chart_option:
            for k, v in high_chart_option.items():
                try:
                    custom_high_chart.set_options(k, v)
                except TypeError:
                    pass
            if high_chart_option.get('series', None) and high_chart_option['series'].get('marker', None):
                kwargs['marker'] = high_chart_option['series']['marker']

        kwargs['id'] = normalize_str(kwargs['name'])

        custom_high_chart.add_data_set(*args, **kwargs)
        high_chars_series = dgrafico.get('high_chars_series', None)
        if high_chars_series:
            plot_options = {
                'series': {'showInLegend': True}
            }
            plot_options.update(high_chart_option.get('plotOptions', {}))
            custom_high_chart.set_options('plotOptions', plot_options)
            for series in high_chars_series:
                tipo = series['type']
                PLOT_OPTION_ALLOWED_ARGS.update({
                    tipo: {
                        'linkedTo': basestring,
                        'dashStyle' : basestring,
                        'color': basestring,
                        'params': dict,
                        'marker': dict}
                })
                series['linkedTo'] = normalize_str(series['linkedTo'])
                custom_high_chart.add_data_set([], series_type=tipo, **series)

    def _get_tabela(self, pk, dtabela, dados):
        T = HTMLTable(pk, cols=dtabela['colunas'], classes=dtabela['classes'])
        dados_colunas = dados['series']
        if dtabela.get('dados_extra'):
            for chave, nova_chave in dtabela['dados_extra'].items():
                dados_colunas[nova_chave] = dados[chave]
        colunas = [dados_colunas[x] for x in T.cols]
        linhas = list(zip(*colunas))
        T.set_rows(linhas)

        return {
            'tipo': TipoConteudoVisualizacao.TABELA,
            'conteudo': T.buildcontent(),
            'titulo': dtabela['titulo'],
        }

    def _get_grafico(self, pk, dgrafico, dados):
        def get_valor(valor):
            if isinstance(valor, tuple) or isinstance(valor, list):
                if dgrafico['valor_forma_exibicao'] == ValorFormaExbicao.AMBOS:
                    return valor[1]
                elif dgrafico['valor_forma_exibicao'] == ValorFormaExbicao.VALOR:
                    return valor[0]
                elif dgrafico['valor_forma_exibicao'] == ValorFormaExbicao.PERCENTUAL:
                    return valor[1]
            return valor

        def data_labels_default(data_labels):
            high_chart_option = dgrafico.get('high_chart_option', data_labels)
            hseries = high_chart_option.get('series', data_labels)
            new_data_labels = hseries.get('dataLabels', data_labels)
            data_labels['style'] = data_labels.get('style',  {'fontSize': H.FONTSIZE})
            data_labels['formatter'] = data_labels.get('formatter', ''' 
            function() {
                if (Number.isInteger(this.y)) {
                    return this.y
                } else {
                    return Highcharts.numberFormat(this.y, 2);
                }
            }''' )
            data_labels['color'] = data_labels.get('color', 'black')
            # data_labels['align'] = data_labels.get('align','left')
            # data_labels['x'] = data_labels.get('x', 2)
            # data_labels['y'] = data_labels.get('y',  -5)
            data_labels['rotation'] = data_labels.get('rotation', 0)
            data_labels.update(new_data_labels)
            return data_labels

        titulo = '{} - {}.'.format(dgrafico['titulo'], self.args.filtro_apresentacao)

        high_chart_option = dgrafico['high_chart_option']

        H = CustomHighchart(container_title='',
                            exibir_titulo=self.exibir_titulo(),
                            exibir_identificador = self.exibir_identificador)
        H.loading = ''

        tooltip_default = {'crosshairs': True,
                           'shared': True,
                           # 'formatter': """function() {
                           #      return this.points.reduce(function (s, point) {
                           #          return s + '<br/>' + point.series.name + ': ' +
                           #              point.y + 'm';
                           #      }, '<b>' + this.x + '</b>');
                           #  },"""
                        }
        H.set_options('tooltip', tooltip_default)

        H.set_options('chart', {'renderTo': pk,
                                'zoomType': 'x',
                                'type':TIPO_VISUALIZACAO_MAP[dgrafico['tipo']]})
        if self.exibir_titulo():
            H.set_options('title', {'text': '<p>{}</p>'.format(titulo)})
        else:
            H.set_options('title', {'text': '<p></p>'})

        x_axis = {'labels':{'style': {'fontSize': H.FONTSIZE}}}
        x_axis.update(high_chart_option.get('xAxis', {}))
        y_axis = {'labels':{'style': {'fontSize': H.FONTSIZE}}}
        y_axis.update(high_chart_option.get('yAxis', {}))
        H.set_options('xAxis', x_axis)
        H.set_options('yAxis', y_axis)

        if dgrafico['tipo'] == TipoVisualizacao.LINHA:
            H.set_options('xAxis', {'categories': tuple(dados['categories'])})
            H.set_options('plotOptions', {'line': {
                'dataLabels': data_labels_default({
                    'enabled': True,
                    'style': {'fontSize': H.FONTSIZE},
                })
            }})
            for nome, valores in dados['series'].items():
                serie_data = [get_valor(v) for v in valores]
                self._add_data_set(H, dgrafico, serie_data, TIPO_VISUALIZACAO_MAP[dgrafico['tipo']], name=nome)

        elif dgrafico['tipo'] == TipoVisualizacao.PIZZA:
            H.set_options('plotOptions', {'pie': {
                                                'allowPointSelect': True,
                                                'cursor': 'pointer',
                                                'dataLabels': data_labels_default({
                                                    'enabled': True,
                                                    'style': {'fontSize': H.FONTSIZE},
                                                    'format': '<b>{point.name}</b>: {point.percentage:.2f} %'
                                                }),
                                                # 'innerSize': 50,
                                                'depth': 45
                                            }
                                        }
                          )

            for nome, valores in dados['series'].items():
                serie_data = []
                for i in range(0, len(valores)):
                    categoria = list(dados['categories'])[i]
                    valor = get_valor(valores[i])
                    serie_data.append((categoria, valor))
                self._add_data_set(H, dgrafico, serie_data, TIPO_VISUALIZACAO_MAP[dgrafico['tipo']], name=nome)

        elif dgrafico['tipo'] in(TipoVisualizacao.BARRA, TipoVisualizacao.BARRA_STAKING, TipoVisualizacao.COLUNA, TipoVisualizacao.COLUNA_STAKING):
            if dgrafico['tipo'] in (TipoVisualizacao.COLUNA_STAKING, TipoVisualizacao.BARRA_STAKING):
                H.set_options('plotOptions', {'column': {'stacking': 'normal'}, })
            H.set_options('xAxis', {'categories':  tuple(dados['categories']) })
            H.set_options('colors', {})
            H.set_options('plotOptions', {'column': {'dataLabels': data_labels_default({'enabled': True,
                                                                    'style': {'fontSize': H.FONTSIZE}})
                                                     },
                                          })

            data_labels = {'color': 'black',}
            if dgrafico['valor_forma_exibicao'] ==  ValorFormaExbicao.AMBOS:
                tooltip = {
                    'shared': False,
                    'formatter': """function() {
                                            var serie = this.series;
                                            var index = this.series.data.indexOf(this.point);
                                            var s = '<b>' + this.x + '</b><br>';
                                            s += '<span style=\"color:' + serie.color + '\">' + serie.options.name + '</span>: <b>' + this.y +\"%\" + '</b><br/>Total: ';
                                            s  += serie.options.data_extra[index]         
                                            return s;  
                                        },"""
                    }
                tooltip_default.update(tooltip)
                H.set_options('tooltip', tooltip)

                data_labels = data_labels_default({'color': 'black','distance': 0,})
            for nome, valores in dados['series'].items():
                serie_data = [get_valor(v) for v in valores]
                self._add_data_set(H, dgrafico, serie_data, TIPO_VISUALIZACAO_MAP[dgrafico['tipo']],
                               name=nome,
                               dataLabels=data_labels,
                )
                if dgrafico['valor_forma_exibicao'] == ValorFormaExbicao.AMBOS:
                    valores_tooltip = [v[0] for v in valores]
                    H.add_data_extra(valores_tooltip)

        return {
            'tipo': TipoConteudoVisualizacao.GRAFICO,
            'conteudo': [H.buildcontainer(), H.buildcontent()],
            'titulo': dgrafico['titulo'],
        }

    def get_visualizacoes(self):
        visualizacoes = []
        for chave in self.get_ids_catalogo():
            visualizacao = self.get_visualizacao(chave)
            visualizacoes.append(visualizacao)
        return visualizacoes

    def get_dict_visualizacoes(self, ids):
        visualizacoes = {}
        for chave in ids:
            visualizacoes[chave] = self.get_visualizacao(chave)
        return visualizacoes

    def data_ultima_atualizacao_esusve(self, **kwargs):
        data_ultima_atualizacao_esusve = Notificacao.objects.aggregate(Max('dados_atualizados_em'))['dados_atualizados_em__max'].date()
        return {'valor': data_ultima_atualizacao_esusve}


class PainelBoletim(PainelIndicadorComum):
    def __init__(self, indicador_parametro, exibir_titulo=True, exibir_identificador=False):
        self._dados = None
        super(PainelBoletim, self).__init__(indicador_parametro, exibir_titulo, exibir_identificador)

    def _get_dados_in_cache(self, pk):
        if self._dados:
            if self._dados.get(pk, None):
                    logger.debug('Obtendo indicador [{}] de dados do [Boletim].'.format(pk))
                    return self._dados[pk]
        return super(PainelBoletim, self)._get_dados_in_cache(pk)

    def set_dados(self, dados):
        self._dados = dados

    def data_do_boletim(self, **kwargs):
        return {'valor': self.args.data_do_boletim}

    def numero_do_boletim(self, **kwargs):
        try:
            semana_a_considerar = kwargs['semana_a_considerar']
            semana = Week(self.args.ano_boletim, self.args.semana_boletim)
            semana_de = semana + min(semana_a_considerar)

            data_semana = DataSemana(self.args.ano_boletim, self.args.semana_boletim)
            periodo = data_semana.get_periodo(semana_a_considerar)
            data_inicio = DataExtenso(periodo[0]).data_extenso('%d-{m:3}')
            data_fim = DataExtenso(periodo[1]).data_extenso('%d/{m:3}')
            valor = '{} ({} - {})'.format(semana_de.week, data_inicio, data_fim)
        except KeyError:
            valor =  self.args.numero_do_boletim

        return {'valor': valor}

    def data_inicio_semana_epi(self, **kwargs):
        return {'valor': self.args.semana_data_inicial}

    def data_fim_semana_epi(self, **kwargs):
        return {'valor': self.args.semana_data_final}

    def data_inicio_quinzena_epi(self, **kwargs):
        return {'valor': self.args._quinzena_data_inicial}

    def data_fim_quinzena_epi(self, **kwargs):
        return {'valor': self.args._quinzena_data_final}

    def get_ids_catalogo(self):
        return [
            'grafico-casos-suspeitos',
            'grafico-casos-confirmados',
            'grafico-casos-confirmados-distrito',
            'grafico-casos-confirmados-sexo-idade',
            'grafico-obitos-confirmados-distrito',
            'grafico-obitos-confirmados-sexo-idade'
            'grafico_ocupacao_leitos_fixo'
        ]


class PainelPublico(PainelIndicadorComum):
    def __init__(self, indicador_parametro, exibir_titulo=True, exibir_identificador=False):
        super(PainelPublico, self).__init__(indicador_parametro, exibir_titulo, exibir_identificador)

    def get_ids_catalogo(self):
        return [
            'total_recuperados', #Casos recuperados
            'total_isolamento', #Em Acompanhamento
            'casos_confirmados', #Casos confirmados acumulado
            'casos_novos_casos_ultimos_7_dias', #card 2660 - casos novos últimos 7 dias
            'taxa_incidencia', #cards 2670
            'total_obitos_confirmados', #Óbitos acumulados
            'obitos_novos_confirmados_ultimo_7_dias', # card 2661 - óbitos confirmados  - casos novos últimos 7 dias
            'taxa_letalidade',
            'taxa_mortalidade', #card 2691
            #'tabela_sintese_casos_obitos_incidencia_mortalidade_por_bairo',
            #'tabela_sintese_casos_obitos_incidencia_mortalidade_por_distrito',
            'casos_confirmados_por_data_notificacao_grafico_coluna', #card 2701
            'casos_confirmados_por_semana_grafico_coluna', #card 2700
            'casos_confirmados_acumulados_por_data_notificacao_grafico_linha', #cards 2699
            'casos_confirmados_acumulados_por_semana_grafico_linha', #cards 2698
            'casos_acumulados_confirmados_distrito_por_data_notificacao_grafico_linha', #cards 2672
            'casos_acumulados_confirmados_distrito_por_semana_notificacao_grafico_linha', # cards 2689
            # 'casos_novos_bairro_por_semana_anterior_3_grafico_linha',
            # 'casos_acumulados_confirmados_bairro_por_data_notificacao_grafico_linha', #Cancelado, card 2671
            # 'casos_acumulados_confirmados_bairro_por_semana_notificacao_grafico_linha', #Cancelado, card 2690
            'casos_confirmados_distrito_grafico_coluna', # cards 2664
            'casos_confirmados_bairro_grafico_coluna', #cards 2694
            'mapa_de_casos_confirmados_acumulados_por_bairro_endereco_moradia', #Cards 2695
            'casos_novos_confirmado_bairro_por_semana_anterior_5_grafico_linha', #cards 2696
            'mapa_de_calor_casos_confirmados_semana_atual', #cards 2697
            'mapa_de_calor_casos_confirmados_semana_anterior_1', #cards 2697
            'mapa_de_calor_casos_confirmados_semana_anterior_2',#cards 2697
            'mapa_de_calor_casos_confirmados_semana_anterior_3',#cards 2697
            'mapa_de_calor_casos_confirmados_semana_anterior_4',#cards 2697
            'mapa_de_calor_casos_confirmados_semana_anterior_5',#cards 2697
            '',
            '',
            '',
            'taxa_letalidade_por_data_grafico_linha', #cards/2733
            'taxa_letalidade_distrito_data_grafico_linha', #ards/2734
            'taxa_letalidade_distrito_grafico_coluna', #cards/2735
            'taxa_letalidade_bairro_grafico_coluna', #ards/2736
            '',
            '',
            'obitos_confirmados_dia_grafico_coluna',  # card 2706
            'obitos_confirmados_semana_grafico_coluna',  # card 2707
            'obitos_confirmados_dia_acumulado_grafico_linha',  # card 2708
            'obitos_confirmados_semana_acumulado_grafico_linha',  # card 2709
            'obitos_acumulados_confirmados_distrito_por_data_obito_grafico_linha',  # cardss 2711
            'obitos_acumulados_confirmados_distrito_por_semana_grafico_linha',  # card 2712
            'obitos_confirmados_distrito_grafico_coluna',  # card 2713
            'obitos_confirmados_bairro_grafico_coluna',  # card 2714
            'mapa_de_obitos_por_bairro_endereco_moradia',  # card 2715
            'obitos_novos_confirmado_bairro_por_semana_anterior_5_grafico_linha',  # card 2716
            '',
            '',
            '',
            'taxa_mortalidade_distrito_grafico_coluna', #cards/2669
            'taxa_mortalidade_bairro_grafico_coluna', #cards/2667
            'taxa_mortalidade_por_data_obito_grafico_linha', #cards/2732
            'taxa_mortalidade_por_distrito_data_obito_grafico_linha', #cards/2731
            'mapa_mortalidade_por_bairro_endereco_moradia' #card 2676


            'taxa_incidencia_distrito_grafico_coluna', #card 2729
            'taxa_incidencia_bairro_grafico_coluna', #card 2626
            'mapa_incidencia_por_bairro_endereco_moradia', #card 2673
            'taxa_incidencia_acumulada_por_data_notificacao_grafico_linha', #card 2730
            'taxa_incidencia_acumulada_distrito_por_data_notificacao_grafico_linha', # card 2728
        ]


class PainelCatalogo(PainelBoletim):
    def __init__(self, indicador_parametro, exibir_titulo=True, exibir_identificador=False):
        super(PainelCatalogo, self).__init__(indicador_parametro, exibir_titulo, exibir_identificador)
