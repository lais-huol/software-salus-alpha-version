import datetime
import logging
import pandas as pd
import numpy as np

from base.caches import ControleCache
from base.models import Bairro, HabitacoesBairro, AssociacaoBairro
from base.utils import DataExtenso, DataSemana
from indicadores.management.commands.processar_dados_auxiliares import Command
from notificacoes.models import Notificacao, TipoArquivo
from notificacoes.processar_notificacoes import _ObterNotificacaoEsusve

logger = logging.getLogger(__name__)

if not ControleCache.obitos_planilha().exists():
    processar_dados_auxiliares = Command()
    processar_dados_auxiliares.handle()

def covert_data_apresentacao(data_do_obito):
    return DataExtenso(data_do_obito).data_extenso('%d-{m:3}')


def convert_data_min(data_do_obito):
    week = DataSemana.get_semana(data_do_obito)._get_week()
    data_min = week.startdate()
    dia_semana = DataExtenso.TERCA
    return data_min + datetime.timedelta(days=dia_semana - data_min.weekday())


def _get_df(**kwargs):
    data_inicial = kwargs.get('data_inicial', None)
    data_final = kwargs.get('data_final', None)
    semana_boletim = kwargs.get('semana_boletim', None)
    ano_boletim = kwargs.get('ano_boletim', None)

    df = ControleCache.obitos_planilha().get()
    df =  df.dropna(subset=['data_do_obito'])

    df['data_min'] = df['data_do_obito'].apply(convert_data_min)

    mask = (df['data_do_obito'] > pd.Timestamp(data_inicial)) & (df['data_do_obito'] <= pd.Timestamp(data_final))
    return df.loc[mask]


def get_num_obitos(**kwargs):
    df = ControleCache.obitos_planilha().get()
    count_row = df.shape[0]
    return {'valor': count_row}


def get_obitos_semanas(**kwargs):
    df = _get_df(**kwargs)

    if kwargs.get('acumulado', False):
        dfgroup = df['data_min'].value_counts(ascending=True)
        dfgroup = dfgroup.sort_index()
        dfgroup = dfgroup.cumsum().fillna(0)
        dfgroup = dfgroup.reset_index()
        dfgroup.rename(columns={'index': 'data_min', 'data_min': 'count'}, inplace=True)
        dfgroup.sort_values(by=['data_min'], inplace=True)
    else:
        dfgroup = df.groupby('data_min')['data_min'].agg(['count'])
        dfgroup = dfgroup.reset_index()
    # dfgroup['data_min'] = pd.to_datetime(dfgroup['data_min'])
    dfgroup['data_do_obito_apresentacao'] = dfgroup['data_min'].apply(covert_data_apresentacao)
    return  {'categories': dfgroup['data_do_obito_apresentacao'].to_list(),
             'series': {'Óbitos Confirmados': dfgroup['count'].to_list()}}

def get_obitos_dias(**kwargs):
    df = _get_df(**kwargs)
    if kwargs.get('acumulado', False):
        dfgroup = df['data_do_obito'].value_counts(ascending=True)
        dfgroup = dfgroup.sort_index()
        dfgroup = dfgroup.cumsum().fillna(0)
        dfgroup = dfgroup.reset_index()
        dfgroup.rename(columns={'index': 'data_do_obito', 'data_do_obito': 'count'}, inplace=True)
        dfgroup.sort_values(by=['data_do_obito'], inplace=True)
    else:
        dfgroup = df.groupby('data_do_obito')['data_do_obito'].agg(['count'])
        dfgroup = dfgroup.reset_index()
    # dfsum['data_min'] = pd.to_datetime(dfsum['data_min'])
    dfgroup['data_do_obito_apresentacao'] = dfgroup['data_do_obito'].apply(covert_data_apresentacao)
    return  {'categories': dfgroup['data_do_obito_apresentacao'].to_list(),
             'series': {'Óbitos Confirmados': dfgroup['count'].to_list()}}

def get_faixa_idade():
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


def get_obitos_sexo_e_idade(**kwargs):
    #https://www.bitdegree.org/learn/pandas-groupby
    df =  _get_df(**kwargs)  #.query('idade==40 or idade==60')
    try:
        df['idade'].astype(int)
    except ValueError:
        df = df.dropna(subset=['idade'])
        df['idade'] = df['idade'].astype(int)

    bins = pd.cut(df['idade'], [0, 1, 5, 10, 20, 40, 60, 70, 80, 200], right=False)
    dfg = df.groupby([bins, 'sexo'])['idade'].agg(['count']).reset_index()
    dfg = dfg.pivot('idade', 'sexo').reset_index()
    dfg.columns = dfg.columns.droplevel()

    dfgp = dfg[['HOMENS', 'MULHERES']].apply(lambda c: c / c.sum() * 100).round(2).fillna(0)
    dfgp.rename(columns={'HOMENS': 'percentual_homens', 'MULHERES': 'percentual_mulheres'}, inplace=True)
    dfquant = pd.concat([dfg, dfgp], axis=1)
    #dfquant.iloc[:, [0]] # dfquant[dfquant.columns[0]]

    #preparando dados para retorno

    categorias = dfquant[dfquant.columns[0]].replace(get_faixa_idade()).to_list()
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


def _get_distritos(nomes_de_bairros):
    obter_notificacao = _ObterNotificacaoEsusve(TipoArquivo.ESUSVE_ARQUIVO_CSV)
    dbairros = {}
    for nome_bairro in nomes_de_bairros:

        bairro = obter_notificacao._get_bairro(nome_bairro)
        if bairro:
            dbairros[nome_bairro] = bairro.distrito.nome
        else:
            raise Exception('bairro {} não encontrado, por favor realize a assoicação'.format(nome_bairro))
    return dbairros

def get_obitos_por_distrito(** kwargs):
    df = _get_df(**kwargs)
    nomes_de_bairros = df.groupby('bairro')['bairro'].agg(['count']).reset_index()['bairro'].to_list()
    ddistritos = _get_distritos(nomes_de_bairros)
    # df['distrito'] = df['bairro'].apply(_get_distrito)

    df['distrito'] = df['bairro'].replace(ddistritos)
    df = df[df['distrito'].notna()]
    dfg = df.groupby('distrito')['distrito'].agg(['count']).reset_index()
    dfg['percentual'] =  dfg[['count']].apply(lambda c: c / c.sum() * 100).round(2).fillna(0)

    subset = dfg[['count', 'percentual']]
    dados_obitos = [tuple(x) for x in subset.to_numpy()]

    return {'categories': dfg['distrito'].to_list(),
            'series': {'obitos': dados_obitos}}

