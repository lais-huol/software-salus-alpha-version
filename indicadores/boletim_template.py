from jinja2 import Environment, meta, BaseLoader

from indicadores.enums import TipoConteudoVisualizacao


def format_datetime(value, format='%d/%m/%Y'):
    return value.strftime(format)


def format_decimal(value):
    if float(value).is_integer():
        return "{:,d}".format(int(value)).replace(",", "X").replace(".", ",").replace("X", ".")
    else:
        return "{:,.2f}".format(value).replace(",", "X").replace(".", ",").replace("X", ".")



def _get_filters():
    return {
        'data': format_datetime,
        'decimal': format_decimal,
    }


def get_env():
    env = Environment(
        loader=BaseLoader,
        variable_start_string='%%#',
        variable_end_string='#%%',
    )
    env.filters.update(_get_filters())
    return env


def get_vars(env, conteudo):
    parsed_content = env.parse(conteudo)
    variables = meta.find_undeclared_variables(parsed_content)

    return list(variables)


def preparar_contexto_painel(visualizacoes):
    scripts = []
    contexto = {}
    for chave, visualizacao in visualizacoes.items():
        if visualizacao is not None:
            tipo, conteudo = visualizacao.get('tipo'), visualizacao.get('conteudo')
            if tipo == TipoConteudoVisualizacao.GRAFICO or tipo == TipoConteudoVisualizacao.MAPA:
                container, script = conteudo
                scripts.append(script)
                contexto[chave] = container
            if tipo == TipoConteudoVisualizacao.VALOR:
                try:
                    contexto[chave] = conteudo['valor']
                except KeyError:
                    contexto[chave] = 0

            if tipo == TipoConteudoVisualizacao.TABELA:
                contexto[chave] = conteudo
    return contexto, scripts
