import datetime
import logging
import numpy as np
import pandas as pd
from django.conf import settings
from django.contrib.postgres.fields.jsonb import KeyTextTransform, KeyTransform
from django.core.exceptions import FieldError
from django.db.models import Count, Min, DateField, Q, ExpressionWrapper, PositiveIntegerField, Value, QuerySet, F, \
    CharField, FloatField, RowRange, Sum, Window, Func
from django.db.models.expressions import OrderBy
from django.db.models.functions import ExtractYear, ExtractWeek, ExtractDay, Coalesce, TruncDate, Concat, Cast
from epiweeks import Week

from base.models import Municipio
from base.utils import DataExtenso, AgeYear, ToDate, DataSemana, Round, SumCount
from indicadores import leaflet
from indicadores.enums import TipoConteudoVisualizacao
# from indicadores.indicadores_obitos_planilha import get_obitos_por_distrito, get_num_obitos
from notificacoes.models import Notificacao, TipoNotificacaoMotivoCancelamento, PacienteInternacao, Obito


logger = logging.getLogger(__name__)

# pd.set_option('display.max_rows', None)
# pd.set_option('display.max_columns', None)
# pd.set_option('display.width', None)
# pd.set_option('display.max_colwidth', -1)


DEFAULT_QS_OBITOS = Obito.objects.filter(confirmado_covid19=True)
DEFAULT_QS_CASOS = Notificacao.ativas

def _series_names_parse(nome):
    SERIES_NAMES_MAP = {
        'bairro__distrito': 'base_distrito'
    }
    nome_parse = nome
    if '__' in nome:
        nomes = nome.split('__')
        coluna = nomes[-1]
        tabela = SERIES_NAMES_MAP['__'.join(nomes[:-1])]
        return '{}.{}'.format(tabela, coluna)
    return nome_parse

def covert_data_apresentacao_mes(data):
    return DataExtenso(data).data_extenso('%d/{m:3}')

def covert_data_apresentacao_dia(data):
    return DataExtenso(data).data_extenso('%d/{m:3}/%y')

def covert_data_apresentacao_semana(data):
    data = data - datetime.timedelta(days=1)
    semana = DataSemana.get_semana(data).semana
    return '{}-({})'.format(semana, DataExtenso(data).data_extenso('%d/{m:3}'))

def convert_to_tuple_percent(series):
    try:
        series.fillna(0, inplace=True)
        series_percent = round(series / series.sum() * 100, 2).fillna(0)
        series_percent.rename('{}_percent'.format(series.name), inplace=True)
        nova_series = pd.concat([series, series_percent], axis=1).apply(tuple, axis=1)
        nova_series.rename(series.name)
        return nova_series
    except:
        return series

def _get_series_values_names(series_name):
    series_values_names = []
    if series_name:
        if not isinstance(series_name[0], tuple):
            raise ValueError('series_name precisa ser uma lista de tuplas')
        for snome in series_name:
            series_values_names.append(snome[1])
    return series_values_names

def _get_func_annotate_padrao(**kwargs):
    series_name = kwargs.get('series_name', None)
    acumulado = kwargs.get('acumulado', False)
    expressao_sql = kwargs.get('expressao_sql', None)

    if expressao_sql is None:
        if acumulado:
            expressao_sql = SumCount('pk', output_field=PositiveIntegerField())
        else:
            expressao_sql = Count('pk', output_field=PositiveIntegerField())

    if acumulado:
        if series_name:
            _order_by = _series_names_parse(series_name[0][-1])

            if len(series_name) == 1:
                expressao_sql = Func(
                        expressao_sql,
                        template='%(expressions)s OVER (ORDER BY %(order_by)s %(frame)s)',
                        order_by=_order_by,
                        frame=RowRange(start=None, end=0),
                    )

            elif len(series_name) > 1:
                partition_by = []
                for serie_name in series_name[1:]:
                    coluna_nome = _series_names_parse(serie_name[-1])
                    partition_by.append(coluna_nome)
                partition_by = ','.join(partition_by)

                expressao_sql = Func(
                        expressao_sql,
                        template='%(expressions)s OVER (partition by %(partition_by)s ORDER BY %(order_by)s %(frame)s)',
                        partition_by=partition_by,
                        order_by=_order_by,
                        frame=RowRange(start=None, end=0),
                    )

        return expressao_sql

def _get_field_annotate_padrao(**kwargs):
    def parse_field_transform(field_nome, order=None):
        '''
        Django não suporte campo json em order by
        Essa função é para contorna essa carência

        :param key:
        :return:
        '''
        JSON_FIELDS = ('dados',)

        nomes = field_nome.split('__')

        if len(nomes) == 1 or not nomes[-2] in JSON_FIELDS:
            if order:
                if order == 'asc':
                    return F(field_nome).asc()
                else:
                    return F(field_nome).desc()
            else:
                return F(field_nome)

        if nomes[-2] in JSON_FIELDS:
            return KeyTransform(nomes[-1], '__'.join(nomes[:-1]))

    series_name = kwargs.get('series_name', None)
    acumulado = kwargs.get('acumulado', False)
    expressao_sql = kwargs.get('expressao_sql', None)

    if expressao_sql is None:
        if acumulado:
            expressao_sql = SumCount('pk', output_field=PositiveIntegerField())
        else:
            expressao_sql = Count('pk', output_field=PositiveIntegerField())

    new_fields_annotate = {
        'valor': expressao_sql
    }
    if acumulado:
        if series_name:

            #OrderBy(RawSQL("LOWER(data->>%s)", ("manufacturer_name",)), descending=True)
            #annotate(some_field=RawSQL("metadata #> '{some}' #> '{field}'", [])).values("some_field")
            _order_by = []
            for serie_name in series_name:
                _order_by.append(parse_field_transform(serie_name[-1], 'asc'))

            if len(series_name) == 1:
                window = {
                    'order_by': _order_by,
                }
            elif len(series_name) > 1:
                partition_by = []
                for serie_name in series_name[1:]:
                    partition_by.append(parse_field_transform(serie_name[-1]))
                window = {
                    'partition_by': partition_by,
                    'order_by': _order_by,
                }
        new_fields_annotate = {
            'valor': Window(
                expression=expressao_sql,
                frame=RowRange(start=None, end=0),
                **window
            ),
            'extra_quant': Count('pk')
        }

    return new_fields_annotate

############################ INDICADORES BASE ############################

def _get_df(**kwargs):
    #https://jakevdp.github.io/PythonDataScienceHandbook/03.05-hierarchical-indexing.html
    acumulado = kwargs.get('acumulado', False)
    percentual_e_valor = kwargs.get('com_percentual_e_valor', False)
    dados_mapeamento = kwargs.get('dados_mapeamento', {})
    series_values_names = _get_series_values_names(kwargs.get('series_name'))
    order_by = kwargs.get('order_by', None)
    qs = kwargs.get('qs', None)

    if qs is None and kwargs.get('df', None) is None:
        raise ValueError('qs não pode ser None')

    if not isinstance(qs, dict) and qs.count() == 0 and kwargs.get('df', None) is None:
        return pd.DataFrame([])

    if series_values_names:
        df = kwargs.get('df', pd.DataFrame([]))
        if df.empty:
            df = pd.DataFrame(qs)

        if 'extra_quant' in series_values_names:
            series_values_names.remove('extra_quant')
            df.drop('extra_quant', axis=1, inplace=True)

        # if 'semana' in series_values_names:
        #     df['data_apresentacao'] = df['semana'].astype(str) + ' - (' + df['data_semana'].apply(
        #         covert_data_apresentacao_mes) + ')'
            # ix = series_values_names.index('data_semana')
            # series_values_names.insert(ix, 'data_apresentacao')
            # series_values_names.remove('data_semana')
            # series_values_names.remove('semana')
            # df.drop('semana', axis=1, inplace=True)
            # order_by = order_by or ['data_semana',]

        df.replace(dados_mapeamento, inplace=True)

        for k, v in dados_mapeamento.items():
            df[k].replace(v, inplace=True)

        for coluna in series_values_names:
            df[coluna].fillna('Não Informado', inplace=True)

        order_by = order_by or series_values_names[::-1]
        dfg = df.groupby(series_values_names[::-1]).agg(sum_valor=pd.NamedAgg(column='valor', aggfunc=sum),)
        dfg.sort_values(by=order_by, inplace=True)

        # if acumulado:
        #     if len(series_values_names) > 1:
        #         dfg = dfg.groupby(level=0).cumsum()
        #     else:
        #         dfg = dfg.cumsum()

        dfg.reset_index(inplace=True)

        if 'data_semana' in series_values_names:
            dfg['data_apresentacao'] = dfg['data_semana'].apply(covert_data_apresentacao_semana) + ')'
            ix = series_values_names.index('data_semana')
            series_values_names.insert(ix, 'data_apresentacao')
            series_values_names.remove('data_semana')
            dfg.drop('data_semana', axis=1, inplace=True)
            # order_by = order_by or ['data_semana',]

            # dfg.assign(data_apresentacao=func)



        # df2 = dfg.loc[(dfg['bairro__distrito__nome'] == 'DISTRITO SANITÁRIO LESTE')]

        if len(series_values_names) > 1:
            dfg = dfg.pivot(*series_values_names).reset_index()

        if 'month' in series_values_names:
            dfg['data_apresentacao'] = dfg['month'].apply(covert_data_apresentacao_mes)
        elif 'data' in series_values_names:
            dfg['data_apresentacao'] = dfg['data'].apply(covert_data_apresentacao_dia)
        elif 'data_do_obito' in series_values_names:
            dfg['data_apresentacao'] = dfg['data_do_obito'].apply(covert_data_apresentacao_dia)

        if acumulado:
            dfg.fillna(method='ffill', inplace=True)

        dfg.fillna(0, inplace=True)

        if percentual_e_valor:
            if len(series_values_names) > 1:
                df_total = dfg.sum(axis=1)
                for c in dfg['sum_valor'].columns:
                    dfg['sum_valor', c] = pd.concat([dfg['sum_valor'][c].fillna(0),
                                                     (dfg['sum_valor'][c] / df_total * 100).fillna(0).round(2)],
                                                    axis=1).apply(tuple, axis=1)
            else:
                dfg = dfg.apply(convert_to_tuple_percent)
        return dfg
    elif isinstance(qs, dict):
        df = kwargs.get('df', pd.DataFrame([]))
        if not df.empty:
            return df
        else:
            return pd.DataFrame.from_dict(qs, orient='index', columns=qs.keys())

    df = kwargs.get('df', pd.DataFrame([]))
    if not df.empty:
        return df
    else:
        return pd.DataFrame(qs)

def _tratar_retorno_dados(**kwargs):
    series_name = kwargs.get('series_name', None)
    percentual_e_valor = kwargs.get('com_percentual_e_valor', False)
    series_values_names = _get_series_values_names(kwargs.get('series_name', None))
    processar_df = kwargs.get('processar_df', True)

    df = kwargs.get('df', None)

    if df is None and not processar_df:
        raise ValueError('processar_df não pode ser False quando df é None')

    if processar_df:
        df = _get_df(**kwargs)

    if series_values_names:
        if df.empty:
            series = {}
            if len(series_values_names) > 1:
                for coluna in series_values_names:
                    series[coluna] = []
            else:
                series = {series_name[0][0]: []}

            return {
                'categories': [],
                'series': series
            }

        if 'extra_quant' in series_values_names:
            series_values_names.remove('extra_quant')

        if 'data_semana' in series_values_names:
            ix = series_values_names.index('data_semana')
            series_values_names.insert(ix, 'data_apresentacao')
            series_values_names.remove('data_semana')
        elif 'data' in series_values_names:
            ix = series_values_names.index('data')
            series_values_names.insert(ix, 'data_apresentacao')
            series_values_names.remove('data')
        elif 'data_do_obito' in series_values_names:
            ix = series_values_names.index('data_do_obito')
            series_values_names.insert(ix, 'data_apresentacao')
            series_values_names.remove('data_do_obito')

        # if 'month' in series_values_names \
        #     or 'data' in series_values_names \
        #     or 'data_do_obito' in series_values_names \
        #     or 'semana' in series_values_names:
        #     categories =  df['data_apresentacao'].to_list()
        # else:

        categories = df[series_values_names[0]].to_list()

        series = {}
        if len(series_values_names) > 1:
            for coluna in df['sum_valor'].columns:
                series[coluna] = df['sum_valor'][coluna].to_list()#.fillna(0).astype(int).to_list()
        else:
            if percentual_e_valor:
                dados = df['sum_valor'].to_list()
            else:
                dados = df['sum_valor'].fillna(0).to_list()
            series = {series_name[0][0]: dados}
        return {
                'categories': categories,
                'series': series
            }
    if df.empty:
        return {'valor': 0}
    return {'valor': df['valor'][0]}

def _get_qs(**kwargs):
    '''
    :return:

    '''
    semana_a_considerar = kwargs.get('semana_a_considerar', None)
    filter = kwargs.get('filter', None)
    exclude = kwargs.get('exclude', None)
    data_inicial = kwargs.get('data_inicial', None)
    data_final = kwargs.get('data_final', None)
    fields_annotate = kwargs.get('fields_annotate', {})
    order_by = kwargs.get('order_by', None)
    field_date = kwargs.get('field_date', None)
    dias_a_considerar = kwargs.get('dias_a_considerar', None)
    series_name = kwargs.get('series_name', None)
    values_names = kwargs.get('values_names', [])
    qs = kwargs.get('qs', None)


    if field_date is None:
        raise ValueError('field_date não pode ser None')

    if qs is None:
        raise ValueError('qs não pode ser None')

    if data_inicial is None:
        raise ValueError('data_inicial não pode ser None')

    if data_final is None:
        raise ValueError('data_final não pode ser None')

    if dias_a_considerar:
        data_inicial = data_final - datetime.timedelta(days=dias_a_considerar)

    if semana_a_considerar:
        semana = DataSemana.get_semana(data_final)
        data_inicial, data_final = semana.get_periodo(semana_a_considerar)


    qs = qs.filter(**{'{}__range'.format(field_date): (data_inicial, data_final)})

    if filter:
        qs = qs.filter(**filter)

    if exclude:
        qs = qs.exclude(**exclude)

    total_registros = qs.count()

    series_values_names = _get_series_values_names(series_name)
    # series_values_names = _get_series_values_names(series_name, fields_annotate)
    # if series_values_names:
    #     for vn in series_values_names:
    #         try:
    #             qs = qs.values(vn)
    #         except FieldError:
    #             pass


    if fields_annotate and not series_name and not values_names:
        qs = qs.aggregate(**fields_annotate)
    elif fields_annotate:
        qs = qs.values(
            *series_values_names
        ).annotate(
            **fields_annotate
        ).values(
            *(series_values_names + values_names + list(fields_annotate.keys()))
        ).order_by()


    # if isinstance(qs, QuerySet):
    #     if series_values_names:
    #         qs = qs.values(*series_values_names)
    #
    #     if order_by:
    #         qs = qs.order_by(*order_by)
    return qs, total_registros

def _get_casos(**kwargs):
    kwargs['qs'] = kwargs.get('qs', DEFAULT_QS_CASOS)
    kwargs['field_date'] = kwargs.get('field_date', 'data')
    return _get_qs(**kwargs)

def _get_obitos(**kwargs):
    kwargs['qs'] = kwargs.get('qs', DEFAULT_QS_OBITOS)
    kwargs['field_date'] = kwargs.get('field_date', 'data_do_obito')
    return _get_qs(**kwargs)

def get_obitos_fixo(**kwargs):
    # Retorna dados fixos da planilha obtidos em 07/07/2020
    data_final = kwargs.get('data_final', None)
    return {'valor': 497}

def get_obitos(**kwargs):
    # kwargs['fields_annotate'] = kwargs.get('fields_annotate', {'valor':_get_func_annotate_padrao(**kwargs)})
    kwargs['fields_annotate'] = kwargs.get('fields_annotate', _get_field_annotate_padrao(**kwargs))
    qs, total_casos = _get_obitos(**kwargs)

    kwargs['qs'] = qs
    kwargs['total_casos'] = total_casos

    return _tratar_retorno_dados(**kwargs)

def _get_dados_semana(**kwargs):
    field_date = kwargs.get('field_date', None)
    qs = kwargs.get('qs', None)

    expressao_sql = ToDate(
        Concat(ExtractYear(field_date),
               Value('-'),
               ExtractWeek(field_date),
               Value('-1'),  # 1 início segunda-feria
               output_field=CharField()
               ),
        output_field = DateField(),
        format = "'IYYY-IW-ID'")

    kwargs['qs'] = qs.annotate(data_semana= expressao_sql)
    kwargs['fields_annotate'] = kwargs.get('fields_annotate', _get_field_annotate_padrao(**kwargs))
    return get_casos(**kwargs)

def get_obitos_semana(**kwargs):
    kwargs['field_date'] = 'data_do_obito'
    kwargs['qs'] = DEFAULT_QS_OBITOS
    return _get_dados_semana(**kwargs)

def get_casos_semana(**kwargs):
    kwargs['field_date'] = 'data'
    kwargs['qs'] = DEFAULT_QS_CASOS
    return _get_dados_semana(**kwargs)

def get_casos(**kwargs):
    # kwargs['fields_annotate'] = kwargs.get('fields_annotate', {'valor':_get_func_annotate_padrao(**kwargs)})
    kwargs['fields_annotate'] = kwargs.get('fields_annotate', _get_field_annotate_padrao(**kwargs))

    qs, total_casos = _get_casos(**kwargs)

    kwargs['qs'] = qs
    kwargs['total_casos'] = total_casos

    return _tratar_retorno_dados(**kwargs)

############################ INDICADORES DO BOLETIM ############################
def get_mapa_calor(**kwargs):
    l = leaflet.Leaflet('algumacoisa')
    return {'tipo': TipoConteudoVisualizacao.MAPA, 'conteudo': (l.buildcontainer(), l.buildcontent())}

def get_dados_mapa_calor(**kwargs):
    '''
    Exemplo de uso:
        dados = get_dados_mapa_calor([(2020, 21), (2020, 22)],
                                     chave='resultado_do_teste',
                                     valor='Positivo')

    :param semanas:
            lista com tuplas de número do ano e número da semana.
            Exemplo: [(2020, 21), (2020, 22)]

            chave               valor
            tipo_de_testes:     'TESTE RÁPIDO - ANTÍGENO'
                                'TESTE RÁPIDO - ANTICORPO'
                                'RT-PCR'
                                None

            estado_do_teste:    'Coletado'
                                'Solicitado'
                                'Concluído'
                                None

            resultado_do_teste:     'Positivo' -- confirmado
                                    'Negativo' -- descartado
                                    None       -- suspeito

            classificacao_final:    'Confirmado Laboratorial'
                                    'Descartado'
                                    'Confirmado Clínico-Epidemiológico'
                                    None

            evolucao_caso:          'Ignorado'
                                    'Óbito'
                                    'Cura'
                                    'Em tratamento domiciliar'
                                    'Internado'
                                    None

            raca_cor:               'Branca'
                                    'Parda'
                                    'Amarela'
                                    'Preta'
                                    'Indigena'
                                    None

            sexo:                   'Feminino'
                                    'Masculino'
                                    None


    :return:
    Formato
    {
      max: max(quantidade_de_notificacoes_por_cep),
      data: [{ x: latitude, y: longitude, value: quantidade_de_notificacoes_por_cep}, ...]
    }
    Exemplo:
    {
      max: 5,
      data: [{ x: -23.5503099, y: -46.6342009, value: 5}, ...]
    }
    '''
    #retorna o número da semana datetime.date(2010, 6, 2).isocalendar()[1]

    semana_a_considerar = kwargs['semana_a_considerar']
    semana_boletim = kwargs['semana_boletim']
    ano_boletim = kwargs['ano_boletim']
    filter = kwargs.get('filter', None)
    field_date = kwargs.get('field_date', 'data')

    semana = Week(ano_boletim, semana_boletim)
    semana_de  = semana + min(semana_a_considerar)
    semana_ate = semana + max(semana_a_considerar)

    data_semana = DataSemana(ano_boletim, semana_boletim)
    periodo = data_semana.get_periodo(semana_a_considerar)


    logger.debug('Processando dados de geolocalização das notificações -- semanas {}-{} ({})'.format(semana_de, semana_ate, periodo))

    qs =  DEFAULT_QS_CASOS.filter(**{'{}__range'.format(field_date): periodo})


    if filter:
        qs = qs.filter(**filter)

    casos_totais = qs.count()
    if casos_totais == 0:
        casos_totais = 1

    qs = qs.filter(latitude__isnull=False, longitude__isnull=False).values('latitude', 'longitude')
    casos_ceps_validos = qs.count()
    logger.debug('Percentual de coordenadas válidas: {}/{} - {}'.format(casos_ceps_validos,
                                                         casos_totais,
                                                         round(casos_ceps_validos/casos_totais,2)*100
                                                         )
                 )

    qs = qs.annotate(quant=Count('numero')).values('latitude', 'longitude', 'quant')

    df = pd.DataFrame(qs)
    if not df.empty:
        #remove outliers
        df = df[np.abs(df.quant - df.quant.mean()) <= (10 * df.quant.std())]
        if df.quant.count() == 0:
            return {'max': 0, 'data': []}

        #gera dados para retorno
        valores = []
        for index, row in df.iterrows():
            valor = {
                'x': row['longitude'],
                'y': row['latitude'],
                'value': row['quant']
            }
            valores.append(valor)
        dados = {
            'max': int(df.quant.max()),
            'data': valores
        }
        return dados
    return {'max':0, 'data': []}

def get_num_casos_ocorrencia(**kwargs):
    qs = DEFAULT_QS_CASOS.all()
    qs = qs | Notificacao.objects.filter(tipo_motivo_desativacao__in = (TipoNotificacaoMotivoCancelamento.MUNICIPIO_RESIDENCIA_EXTERNO,
                                                                        TipoNotificacaoMotivoCancelamento.BAIRRO_OUTROS))
    qs = qs.order_by('data')
    kwargs['qs'] = qs
    kwargs['series_name'] = (('Semana de notificação', 'data_semana'), )
    return get_casos_semana(**kwargs)

def get_num_casos_ocorrencia_evolucao_valores(**kwargs):
    qs = DEFAULT_QS_CASOS.all()
    qs = qs | Notificacao.objects.filter(tipo_motivo_desativacao__in = (TipoNotificacaoMotivoCancelamento.MUNICIPIO_RESIDENCIA_EXTERNO,
                                                                        TipoNotificacaoMotivoCancelamento.BAIRRO_OUTROS))
    kwargs['qs'] = qs
    kwargs['series_name'] = (('Semana de notificação', 'data_semana'),)
    dados  = get_casos_semana(**kwargs)
    chave_series = list(dados['series'].keys())[0]
    valores = dados['series'][chave_series]
    s = pd.Series(valores)
    svalores = s.diff().fillna(0).astype(int)
    dados['series'][chave_series] = svalores.to_list()
    return dados

def get_num_casos_ocorrencia_evolucao_percentuais(**kwargs):
    qs = DEFAULT_QS_CASOS.all()

    qs = qs | Notificacao.objects.filter(tipo_motivo_desativacao__in = (TipoNotificacaoMotivoCancelamento.MUNICIPIO_RESIDENCIA_EXTERNO,
                                                                        TipoNotificacaoMotivoCancelamento.BAIRRO_OUTROS))
    kwargs['qs'] = qs
    kwargs['series_name'] = (('Semana de notificação',  'data_semana'),)
    dados  = get_casos_semana(**kwargs)
    chave_series = list(dados['series'].keys())[0]
    valores = dados['series'][chave_series]
    s = pd.Series(valores)
    spercentuais = (s.pct_change().fillna(0) * 100).round(2)
    dados['series'][chave_series] = spercentuais.to_list()
    return dados

def get_faixa_etaria():
    return {
        '< 1': {'Feminino': (0, 0), 'Masculino': (0, 0), 'faixa': (0, 1)},
        '1 a 4': {'Feminino': (0, 0), 'Masculino': (0, 0), 'faixa': (1, 4)},
        '5 a 9': {'Masculino': (0, 0), 'Feminino': (0, 0), 'faixa': (5, 9)},
        '10 a 19': {'Feminino': (0, 0), 'Masculino': (0, 0), 'faixa': (10, 19)},
        '20 a 39': {'Feminino': (0, 0), 'Masculino': (0, 0), 'faixa': (20, 39)},
        '40 a 59': {'Feminino': (0, 0), 'Masculino': (0, 0), 'faixa': (40, 59)},
        '60 a 69': {'Feminino': (0, 0), 'Masculino': (0, 0), 'faixa': (60, 69)},
        '70 a 79': {'Feminino': (0, 0), 'Masculino': (0, 0), 'faixa': (70, 79)},
        '> 80': {'Feminino': (0, 0), 'Masculino': (0, 0), 'faixa': (80, 200)},
    }

def _get_faixa_idade():
    return {
        pd.Interval(left=0, right=1, closed='left'): '< 1',
        pd.Interval(left=1, right=5, closed='left'): '1 a 4',
        pd.Interval(left=5, right=10, closed='left'): '5 a 9',
        pd.Interval(left=10, right=20, closed='left'): '10 a 19',
        pd.Interval(left=20, right=40, closed='left'): '20 a 39',
        pd.Interval(left=40, right=60, closed='left'): '40 a 59',
        pd.Interval(left=60, right=70, closed='left'): '60 a 69',
        pd.Interval(left=70, right=80, closed='left'): '70 a 79',
        pd.Interval(left=80, right=200, closed='left'): '> 80',
    }

def _tratar_dados_proporcao_sexo_idade(qs, df, sexo_parse, nome_field_sexo='sexo'):
    bins = pd.cut(df['idade'], [0, 1, 5, 10, 20, 40, 60, 70, 80, 200], right=False)
    dfg = df.groupby([bins, nome_field_sexo]).agg(sum_valor=pd.NamedAgg(column='quant', aggfunc=sum), ).reset_index()
    dfg = dfg.pivot('idade', nome_field_sexo).reset_index()

    dfg.columns = dfg.columns.droplevel()
    dfg.rename(columns=sexo_parse, inplace=True)

    dfgp = dfg[['HOMENS', 'MULHERES']].apply(lambda c: c / c.sum() * 100).round(2).fillna(0)
    dfgp.rename(columns={'HOMENS': 'percentual_homens', 'MULHERES': 'percentual_mulheres'}, inplace=True)
    dfquant = pd.concat([dfg, dfgp], axis=1)
    for col in sexo_parse.values():
        dfquant[col] = dfquant[col].fillna(0)

    #dfquant.iloc[:, [0]] # dfquant[dfquant.columns[0]]

    #preparando dados para retorno

    categorias = dfquant[dfquant.columns[0]].replace(_get_faixa_idade()).to_list()
    subset = dfquant[['HOMENS', 'percentual_homens']]
    lhomens = [tuple(x) for x in subset.to_numpy()]
    subset = dfquant[['MULHERES', 'percentual_mulheres']]
    lmulheres = [tuple(x) for x in subset.to_numpy()]

    return {'categories': categorias,
           'series': {
               'HOMENS': lhomens,
               'MULHERES': lmulheres
            }
           }

def get_casos_confirmado_proporcao_sexo_idade(**kwargs):
    '''
    Proporção dos casos confirmados de Covid-19 por sexo e faixa etária
    Retorna os dados desde a primeira notificação até a data data_boletim

    exemplo de uso: get_casos_confirmado_proporcao_sexo_idade(timezone.now())

    :param data_boletim: indica a data maxíma para filtro dos dados.

    :return:
    Formato:
        (
        categories = [],
        data = {
        'HOMENS': [(quant, percentual),,,,,,,,,, ],
        'MULHERES': [(quant, percentual),,,,,,,,, ]
        }
    '''
    # data_boletim = kwargs.get('data_boletim', None)
    # data_1a_notificacao = Notificacao.objects.aggregate(min_data=Min('data'))['min_data']

    kwargs['filter'] = {'dados__resultado_do_teste': 'Positivo'}
    kwargs['data_inicial'] = Notificacao.objects.aggregate(min_data = Min('data'))['min_data']
    kwargs['data_final'] = kwargs.get('data_final', None)

    qs, total_casos = _get_casos(**kwargs)

    idade_expression = AgeYear('data_de_nascimento')
    qs = qs.values('ativa').annotate(idade=idade_expression, quant=Count('numero')).values('dados__sexo', 'idade', 'quant')

    df = pd.DataFrame(qs)
    df.rename(columns={'dados__sexo': 'sexo'}, inplace=True)

    return _tratar_dados_proporcao_sexo_idade(qs, df, {'Feminino': 'MULHERES', 'Masculino': 'HOMENS'})


    dados = get_faixa_etaria()

    quant_total = 0
    for dado in qs:
        sexo = dado['dados__sexo']
        idade = dado['idade']
        quant = dado['quant']
        faixa_display = 'None'
        for chave, valor in dados.items():
            if valor['faixa'][0] <= idade <= valor['faixa'][1]:
                faixa_display = chave
                break
        try:
            quant_total = dados[faixa_display][sexo][0] + quant
            dados[faixa_display][sexo] = (quant_total, 0)
        except:
            pass

    for faixa_display, conteudo in dados.items():
        conteudo.pop('faixa')
        for sexo, valores in conteudo.items():
            quant = valores[0]
            percentual = round((quant / total_casos) * 100, 2)
            dados[faixa_display][sexo] = (quant, percentual)

    categories = list(dados.keys())
    dados_retorno = {
        'HOMENS': [v['Feminino'] for v in dados.values()],
        'MULHERES': [v['Masculino'] for v in dados.values()]
    }
    return {
        'categories': categories,
        'series': dados_retorno
        }

def get_obitos_confirmado_proporcao_sexo_idade(**kwargs):
    '''
    Proporção dos casos confirmados de Covid-19 por sexo e faixa etária
    Retorna os dados desde a primeira notificação até a data data_boletim

    exemplo de uso: get_casos_confirmado_proporcao_sexo_idade(timezone.now())

    :param data_boletim: indica a data maxíma para filtro dos dados.

    :return:
    Formato:
        (
        categories = [],
        data = {
        'HOMENS': [(quant, percentual),,,,,,,,,, ],
        'MULHERES': [(quant, percentual),,,,,,,,, ]
        }
    '''
  #   #Dados fixos obtidos da planilha em 07/07/2020
  #   return {'categories': ['< 1', '1 a 4', '5 a 9', '10 a 19', '20 a 39', '40 a 59', '60 a 69', '70 a 79', '> 80'],
  # 'series': {'HOMENS':   [(0, 0.0), (1, 0.20), (0, 0.0), (0, 0.0), (16, 3.22), (54, 10.87), (56, 11.27), (53, 10.66), (68, 13.68)],
	#          'MULHERES': [(0, 0.0), (0, 0.0), (0, 0.0), (0, 0.0), (9, 1.81), (48, 9.66), (33, 6.64), (67, 13.48), (78, 15.69)]
  #            }
  #           }

    qs, total_casos = _get_obitos(**kwargs)
    # qs = qs.exclude(pessoa__sexo='')

    if qs.count() == 0:
        return {'categories': [],
                'series': {
                    'HOMENS': [],
                    'MULHERES': []
                    }
                }

    idade_expression = AgeYear('pessoa__data_de_nascimento')
    qs = qs.values('pessoa__sexo').annotate(
        idade=idade_expression
    ).values(
        'pessoa__sexo', 'idade'
    ).annotate(quant=Count('id')).order_by()

    df = pd.DataFrame(qs)
    return _tratar_dados_proporcao_sexo_idade(qs, df, {'F': 'MULHERES', 'M': 'HOMENS'}, 'pessoa__sexo')

def get_casos_confirmado_proporcao_distrito(**kwargs):
    '''
    Proporção de casos confirmados e óbitos de Covid-19, por distrito sanitário no Município de Natal
    Retorna os dados desde a primeira notificação até a data data_boletim

    exemplo de uso: get_casos_confirmado_proporcao_distrito(timezone.now())

    :param data_boletim: indica a data maxíma para filtro dos dados.

    :return:
    Formato:
        (
        categories = [],
        data = {
        'Casos confirmados': [(quant, percentual),,,,,,,,, ]
        }
    '''

    kwargs['filter'] = {'dados__resultado_do_teste': 'Positivo'}
    kwargs['data_inicial'] = DEFAULT_QS_CASOS.aggregate(min_data = Min('data'))['min_data']
    kwargs['data_final'] = kwargs.get('data_final', None)

    kwargs['series_name'] = (('casos', 'bairro__distrito__nome'),)
    dados_casos = get_casos(**kwargs)

    kwargs['filter'] = None
    kwargs['series_name'] =(('obitos', 'bairro__distrito__nome'),)

    dados_obitos = get_obitos(**kwargs)

    # dados_obitos = get_obitos_por_distrito(**kwargs) #extraído da planilha de óbitos

    df_obitos = pd.DataFrame({'obitos':pd.Series(dados_obitos['series']['obitos'], index=dados_obitos['categories'])})
    df_casos = pd.DataFrame({'casos': pd.Series(dados_casos['series']['casos'], index=dados_casos['categories'])})
    df = pd.concat([df_obitos, df_casos], axis=1)
    df['casos'] = df['casos'].fillna({i: (0, 0.0) for i in df.index})
    df['obitos'] = df['obitos'].fillna({i: (0, 0.0) for i in df.index})

    dados = {
        'Casos confirmados': df.casos.to_list(),
        'Óbitos': df.obitos.to_list(),
    }
    return {
        'categories':  df.index.to_list(),
        'series': dados
    }

def get_casos_confirmado_proporcao_doencas_preexistentes(**kwargs):
    '''
    Proporção de casos confirmados e óbitos de Covid-19, por pacientes com doencas preexistentes no Município de Natal
    Retorna os dados desde a primeira notificação até a data data_boletim

    exemplo de uso: get_casos_confirmado_proporcao_distrito(timezone.now())

    :param data_boletim: indica a data maxíma para filtro dos dados.

    :return:
    Formato:
        (
        categories = [],
        data = {
        'Casos confirmados': [(quant, percentual),,,,,,,,, ]
        }
    '''
    def percentage(part, whole):
        return 100 * float(part) / float(whole)

    # data_inicial = Notificacao.objects.aggregate(min_data = Min('data'))['min_data']
    # data_final = kwargs.get('data_final', datetime.datetime.today())

    # dados_casos = get_casos(**kwargs)

    qs_default, total_positivos = _get_casos(**kwargs)

    dados = []
    qtd_diabetes = qs_default.filter(dados__diabetes="Sim").count()
    qtd_cardiacos = qs_default.filter(dados__doencas_cardiacas_cronicas="Sim").count()
    qtd_respiratorias = qs_default.filter(dados__doencas_respiratorias_cronicas_descompensadas="Sim").count()
    qtd_renais = qs_default.filter(dados__doencas_renais_cronicas_em_estagio_avancado_graus_3_4_ou_5="Sim").count()
    qtd_cromossomicas = qs_default.filter(dados__portador_de_doencas_cromossomicas_ou_estado_de_fragilidade_imunologica="Sim").count()
    dados.append((qtd_diabetes, percentage(qtd_diabetes, total_positivos)),)
    dados.append((qtd_cardiacos,  percentage(qtd_cardiacos, total_positivos)),)
    dados.append((qtd_respiratorias, percentage(qtd_respiratorias, total_positivos)),)
    dados.append((qtd_renais,  percentage(qtd_renais, total_positivos)),)
    dados.append((qtd_cromossomicas,  percentage(qtd_cromossomicas, total_positivos)),)

    dados_dict = {
        'Doenças Preexistentes': dados,
    }
    return {
        'categories':  ["Diabetes", "Doenças cardíacas", "Doenças respiratórias", "Doenças renais crônicas", "Doenças cromossômicas ou fragilidade imunológica"],
        'series': dados_dict
    }

def get_taxa_incidencia_acumulada(**kwargs): #Incidência por 100mil habitantes
    '''
    Novos casos da doença em uma população definida durante um período específico (um dia, por exemplo) dividido pela população em risco
    :param kwargs:
    :return:
    '''
    series_name = kwargs.get('series_name', None)
    field_bairro = kwargs.get('field_bairro', 'bairro')

    _series_name = []
    field_quant = '{}__municipio__quant_populacao'.format(field_bairro)
    if series_name:
        for serie_name in series_name:
            if '{}__distrito__nome'.format(field_bairro) in serie_name:
                field_quant = '{}__distrito__quant_populacao'.format(field_bairro)
            elif '{}__nome'.format(field_bairro) in serie_name:
                field_quant = '{}__quant_populacao'.format(field_bairro)

            _series_name.append(serie_name)
    _series_name.append(('Quant. População', field_quant))

    kwargs['filter'] = kwargs.get('filter', {'dados__resultado_do_teste': 'Positivo'})
    kwargs['fields_annotate'] = _get_field_annotate_padrao(**kwargs)
    kwargs['series_name'] = _series_name
    kwargs['field_date'] = kwargs.get('field_date', 'data')
    kwargs['qs'] = kwargs.get('qs', DEFAULT_QS_CASOS)

    qs, total_casos = _get_qs(**kwargs)

    if qs.count() == 0:
        return _tratar_retorno_dados(**kwargs)

    df = pd.DataFrame(qs)
    df.dropna(inplace=True)
    df['valor'] = (df['valor'] / df[field_quant] * 100000).round(2)
    df.drop(field_quant, axis=1, inplace=True)

    kwargs['df'] = df
    kwargs['series_name'] = series_name
    return _tratar_retorno_dados(**kwargs)

def get_taxa_prevalencia(**kwargs):
    '''
    a taxa de prevalência é definida como o número de casos existentes de uma doença ou outro evento de saúde dividido pelo número de pessoas de uma população em tempo especificado.
    Cada indivíduo é observado em uma única oportunidade, quando se constata sua situação quanto ao evento de interesse.

    https://www.scielo.br/scielo.php?script=sci_arttext&pid=S1806-37132020000300151&lng=en&nrm=iso&tlng=pt

    :param kwargs:
    :return:
    '''
    return get_taxa_incidencia_acumulada()

def get_taxa_letalidade(**kwargs):
    quant_casos = 0
    kwargs['series_name'] = kwargs.get('series_name', [])
    acumulado = kwargs.get('acumulado', False)
    original_series_name = kwargs['series_name']

    #Tratamento para obter os dados de casos confirmados
    kwargs['filter'] = kwargs.get('filter', {'dados__resultado_do_teste': 'Positivo'})
    kwargs['exclude'] = {'bairro': None, }
    kwargs['field_date'] = 'data'
    kwargs['qs'] = kwargs.get('qs', DEFAULT_QS_CASOS)
    kwargs['fields_annotate'] = _get_field_annotate_padrao(**kwargs)

    qs, total_casos = _get_qs(**kwargs)

    if not isinstance(qs, dict):
        df_casos = pd.DataFrame(qs)
        df_casos['quant_casos'] = df_casos['valor']
        try:
            df_casos['data'] = pd.to_datetime(df_casos['data'])
            df_casos.drop('extra_quant', axis=1, inplace=True)
        except:
            pass
        df_casos.drop('valor', axis=1, inplace=True)

        series_values_names = _get_series_values_names(original_series_name)
        df_casos = df_casos.set_index(series_values_names)
    else:
        quant_casos = qs['valor']

    #Tratamento para obter os dados de óbitos
    kwargs['filter'] = {'confirmado_covid19': True,}
    kwargs['exclude'] = None
    kwargs['field_date'] = 'data_do_obito'
    kwargs['qs'] = DEFAULT_QS_OBITOS

    SERIES_NAME_VALUE_PARSE = {
        'data': 'data_do_obito',
        'bairro__nome': 'bairro__nome',
        'bairro__distrito__nome': 'bairro__distrito__nome'
    }
    series_name = []
    for serie_name in original_series_name:
        series_name.append((serie_name[0], SERIES_NAME_VALUE_PARSE[serie_name[1]]))
    kwargs['series_name'] = series_name
    kwargs['fields_annotate'] = _get_field_annotate_padrao(**kwargs)

    qs, total_casos = _get_qs(**kwargs)

    if not isinstance(qs, dict):
        df_obitos = pd.DataFrame(qs)
        if not df_obitos.empty:
            df_obitos['quant_obitos'] = df_obitos['valor']
            df_obitos.drop('valor', axis=1, inplace=True)
            try:
                df_obitos['data_do_obito'] = pd.to_datetime(df_obitos['data_do_obito'])
                df_obitos.drop('extra_quant', axis=1, inplace=True)
            except:
                pass

            series_values_names = _get_series_values_names(kwargs['series_name'])
            df_obitos = df_obitos.set_index(series_values_names)

            #Tratamento para unir os dados de casos e óbitos e calcular a taxa de letalidade
            df = pd.concat([df_casos, df_obitos], axis=1)
        else:
            df = df_casos
            df['quant_obitos'] = 0

        if acumulado:
            df.fillna(method='ffill', inplace=True)
        df.fillna(0, inplace=True)

        df['valor'] = (df['quant_obitos'] / df['quant_casos'] * 100).fillna(0.0).round(2)
        df.drop('quant_obitos', axis=1, inplace=True)
        df.drop('quant_casos', axis=1, inplace=True)

        df.reset_index(inplace=True)

        try:
            df.rename(columns={'index': original_series_name[0][1]}, inplace=True)
            df.rename(columns={'level_0': original_series_name[0][1],
                               'level_1': original_series_name[1][1]},
                      inplace=True)
        except:
            pass

        kwargs['df'] = df
        kwargs['series_name'] = original_series_name
        return _tratar_retorno_dados(**kwargs)
    else:
        quant_obitos = qs['valor']
        return {'valor': round(quant_obitos / quant_casos * 100,2)}


def get_taxa_mortalidade(**kwargs):
    '''
    A taxa de mortalidade refere à proporção de óbitos em relação à população em determinado espaço geográfico no tempo considerado.

    https://www.paho.org/hq/index.php?option=com_content&view=article&id=14402:health-indicators-conceptual-and-operational-considerations-section-2&Itemid=0&showall=1&lang=pt

    :param kwargs:
    :return:
    '''
    kwargs['filter'] = {'confirmado_covid19': True}
    kwargs['field_date'] = kwargs.get('field_date', 'data_do_obito')
    kwargs['qs'] = DEFAULT_QS_OBITOS
    kwargs['field_bairro'] =  'bairro'
    return  get_taxa_incidencia_acumulada(**kwargs)

# def get_letalidade(**kwargs):
#     kwargs['filter'] = {'dados__resultado_do_teste':'Positivo'}
#     qs_casos, total_casos = _get_casos(**kwargs)
#     kwargs['filter'] = None
#     qs_obitos, total_casos = _get_obitos(**kwargs)
#     # total_obitos = get_num_obitos(**kwargs)['valor']#obitido da planilha de óbitos
#     total_obitos = get_obitos(**kwargs)['valor']
#     return {'valor': round((total_obitos / total_casos_confirmados) * 100,2)}

def get_percentual_ocupacao_leitos_fixo(**kwargs):
    #Retorna dados fixos obtidos da planilha em 09/07/2020
    return {'categories': ['UPA ESPERANÇA', 'UPA CIDADE SATÉLITE', 'UPA PAJUÇARA', 'UPA POTENGI', 'HOSPITAL DOS PESCADORES'],
  'series': {'DISPONÍVEIS':   [(10.0, 10.0), (70.0, 70.0), (60.0, 60.0),  (30.0, 30.0), (0, 0.0)],
	         'OCUPADOS': [(90.0, 90.0), (30.0, 30.0), (40.0, 40.0),  (70.0, 70.0), (100.0, 100.0)]}}

#tabela
#População, casos novos última semana, casos acumulados, casos acumulados 100mil habitantes, óbitos novos última semana, óbitos acumulados, óbitos acumulados 100mil habitantes
#incidência/100mil hab, mortalidade/100mil hab
def get_casos_e_obitos_por_bairro(**kwargs):
    kwargs['filter'] = {'dados__resultado_do_teste':'Positivo'}
    kwargs['series_name'] = (('casos', 'bairro__nome'),)
    dados_casos = get_casos(**kwargs)

    kwargs['filter'] = {'confirmado_covid19': True}
    kwargs['series_name'] = (('obitos', 'bairro__nome'),)
    dados_obitos = get_obitos(**kwargs)

    df_obitos = pd.DataFrame({'obitos':pd.Series(dados_obitos['series']['obitos'], index=dados_obitos['categories'])})
    df_casos = pd.DataFrame({'casos': pd.Series(dados_casos['series']['casos'], index=dados_casos['categories'])})
    df = pd.concat([df_obitos, df_casos], axis=1)
    df = df.fillna(0).astype(int).sort_index()
    dados = {
        'Casos confirmados': df.casos.to_list(),
        'Óbitos': df.obitos.to_list(),
    }
    return {
        'categories':  df.index.to_list(),
        'series': dados
    }

def get_recuperados(**kwargs):
    kwargs['filter'] = {'dados__resultado_do_teste': 'Positivo'}
    data_final = kwargs['data_final']
    data_14dias_antes = data_final - datetime.timedelta(days=14)

    qs, total_casos = _get_casos(**kwargs)

    dados = qs.annotate(
        data_sintomas=Coalesce('data_do_inicio_dos_sintomas', 'data'),
    ).aggregate(
        quant_total = Count('pk'),
        quant_quarentena=Count('pk', filter=Q(data_sintomas__range=(data_14dias_antes, data_final))),
        quant_internados=Count('pk', filter=Q(paciente_internado__tipo=PacienteInternacao.INTERNADO)),
    )
    kwargs['filter'] = {'confirmado_covid19': True}
    dados_obitos = get_obitos(**kwargs)

    quant_recuperados = dados['quant_total'] - dados['quant_quarentena'] - dados['quant_internados'] - dados_obitos['valor']
    return {'valor': quant_recuperados}

def get_isolamento(**kwargs):
    kwargs['filter'] = {'dados__resultado_do_teste': 'Positivo'}
    data_final = kwargs['data_final']
    data_14dias_antes = data_final - datetime.timedelta(days=14)
    kwargs['data_inicial'] = data_14dias_antes
    kwargs['field_date'] = kwargs.get('field_date', 'data_sintomas')

    qs = DEFAULT_QS_CASOS.all()
    qs = qs.annotate(data_sintomas=Coalesce('data_do_inicio_dos_sintomas', 'data'),)

    kwargs['qs'] = qs

    return get_casos(**kwargs)


# SELECT
# data,
# -- "base_municipio"."nome",
# COUNT("notificacoes_notificacao"."numero"),
# --COUNT("notificacoes_notificacao"."numero") OVER (PARTITION BY data) as quant
# --ROUND(((COUNT("notificacoes_notificacao"."numero") / ("base_municipio"."quant_populacao")::double precision) * 100000)::numeric, 2) AS "valor"
# -- cume_dist() over (partition by "base_municipio"."nome" order by data)
# SUM(COUNT("notificacoes_notificacao"."numero")) OVER (ORDER BY data
#      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) t1,
# SUM(COUNT("notificacoes_notificacao"."numero")) OVER (ORDER BY data
#      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) t2,
# SUM(COUNT("notificacoes_notificacao"."numero")) OVER (ORDER BY data
# RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) t3,
# SUM(COUNT("notificacoes_notificacao"."numero")) OVER (PARTITION BY data) as t9
#
# FROM "notificacoes_notificacao"
# INNER JOIN "base_bairro" ON ("notificacoes_notificacao"."bairro_id" = "base_bairro"."id")
# LEFT OUTER JOIN "base_municipio" ON ("base_bairro"."municipio_id" = "base_municipio"."codigo_ibge")
#
# WHERE ("notificacoes_notificacao"."tipo_motivo_desativacao" IS NULL
# 	   AND "notificacoes_notificacao"."data" BETWEEN '2020-02-09' AND '2020-07-20'
# 	   AND ("notificacoes_notificacao"."dados" -> 'resultado_do_teste') = '"Positivo"'
# 	   AND NOT ("notificacoes_notificacao"."bairro_id" IS NULL))
# GROUP BY "notificacoes_notificacao"."data"
# ORDER BY "notificacoes_notificacao"."data"
# --("base_municipio"."quant_populacao")::double precision