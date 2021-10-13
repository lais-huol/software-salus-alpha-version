import logging

from base.extracao.rest_barramento import get_json_estabelecimento
from base.models import Municipio, Bairro, EstabelecimentoSaude

logger = logging.getLogger(__name__)


def get_estabelecimento_saude(codigo_cnes):
    dados = get_json_estabelecimento(codigo_cnes)
    if not dados:
        return None
    logger.debug('Processando unidade de saúde do barramento...;{}'.format(codigo_cnes))

    municipio = None
    try:
        dados_municipio = dados['municipio']
        municipio, created = Municipio.objects.get_or_create(codigo_ibge=dados_municipio['codigo'],
                                                             codigo_ibge_estado=dados_municipio['unidade_federativa'][
                                                                 'codigo'],
                                                             nome=dados_municipio['nome'])
    except:
        pass

    bairro = None
    try:
        bairro, created = Bairro.objects.get_or_create(nome=dados['bairro'],
                                                       municipio=municipio)

    except:
        pass

    try:
        save_data = {
            'nome': dados['nome'],
            'municipio': municipio,
            'bairro': bairro,
            'email': dados['email'],
            'telefone': dados['telefone'],
        }
    except:
        return None

    estabelecimento_saude = None
    estabelecimento_saude, created = EstabelecimentoSaude.objects.get_or_create(
        codigo_cnes=dados['cnes'], defaults=save_data
    )
    if not created:
        estabelecimento_saude, updated = EstabelecimentoSaude.objects.update_or_create(
            codigo_cnes=dados['cnes'], defaults=save_data
        )
    logger.debug('Unidade de saude criada;{}'.format(codigo_cnes))
    return estabelecimento_saude
