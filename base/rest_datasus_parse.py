import copy
import logging
import re

from base.extracao.rest_datasus import get_profissional, get_estabelecimento_saude_detalhe
from base.models import AssociacaoOperadorCNES
from base.utils import get_native_data_now

logger = logging.getLogger(__name__)

def _get_estabelecimento_saude(dados):
    from base.models import EstabelecimentoSaude
    bairro = dados['bairro']

    municipio = None
    if bairro:
        municipio = bairro.municipio

    save_data = {
        'nome': dados['nome'],
        'municipio': municipio,
        'bairro': bairro,
        'email': dados['email'],
        'telefone': dados['telefone'],
    }

    estabelecimento_saude, created = EstabelecimentoSaude.objects.get_or_create(
        codigo_cnes=dados['cnes'], defaults=save_data
    )
    if not created:
        estabelecimento_saude, updated = EstabelecimentoSaude.objects.update_or_create(
            codigo_cnes=dados['cnes'], defaults=save_data
        )
    return estabelecimento_saude

def get_usuario(cpf, dados_padrao):
    from base.models import Usuario, PerfilEstabelecimentoSaude

    cpf = re.sub('[^0-9]', '', cpf)
    dados = get_profissional(cpf)

    if not dados:
        return None
    logger.debug('Processando profissionais de saúde do cnes;{}'.format(cpf))


    dados_unidade = copy.deepcopy(dados['vinculos'][0])
    dados_unidade.update(dados_padrao)

    estabelecimento_saude = dados_padrao['estabelecimento_saude']
    codigo_ibge = 'coMun'
    codigo_cnes = 'cnes'
    if estabelecimento_saude is None:
        estabelecimento_saude = get_estabelecimento_saude(codigo_cnes, codigo_ibge)

    if estabelecimento_saude is None:
        return None

    save_data = {
        'cpf': cpf,
        'nome': dados_padrao['nome'],
        'email': dados_padrao['email'],
        'telefone': '' if dados_padrao['telefone'] is None else dados_padrao['telefone'],
        'dados_cnes_datasus': dados,
        'dados_cnes_atualizados_em': get_native_data_now()
    }

    usuario, created = Usuario.objects.get_or_create(
        cpf=cpf, defaults=save_data
    )
    if not created:
        usuario, updated = Usuario.objects.update_or_create(
            cpf=cpf, defaults=save_data
        )
    logger.debug('Usuario criado;{}'.format(cpf))

    try:
        PerfilEstabelecimentoSaude.objects.get_or_create(usuario=usuario, estabelecimento_saude=estabelecimento_saude)
    except:
        pass

    return usuario

def get_estabelecimento_saude(codigo_cnes, cpf=''):
    from base.models import EstabelecimentoSaude
    cpf = re.sub('[^0-9]', '', cpf)
    dados = None
    try:
        estabelecimento_saude = None
        if codigo_cnes and len(codigo_cnes) == 7:
            filter = {'codigo_cnes': codigo_cnes}
            qs = EstabelecimentoSaude.objects.filter(codigo_cnes=codigo_cnes)
            estabelecimento_saude = qs[0]
        else:
            qs = AssociacaoOperadorCNES.objects.filter(cpf=cpf)
            estabelecimento_saude = qs[0].estabelecimento_saude

        if estabelecimento_saude and estabelecimento_saude.dados_cnes:
            return estabelecimento_saude
    except:
        pass

    if codigo_cnes and len(codigo_cnes) == 7:
        dados = get_estabelecimento_saude_detalhe(codigo_cnes)

    if dados is None:
        dados_vinculos = get_profissional(cpf)
        try:
            codigo_cnes = dados_vinculos['vinculos'][0]['cnes']
            dados = get_estabelecimento_saude_detalhe(codigo_cnes)
        except Exception as err:
            logger.warning('Erro ao obter vínculo CNES, erro {}, dados: {}'.format(err.args[0], dados_vinculos))
    if not dados:
        return None
    logger.debug('Processado estabelecimento de saúde;{}'.format(dados))

    save_data = {
        'dados_cnes': dados,
        'cpf_operador': cpf,
        'data_extracao': get_native_data_now(),
    }
    estabelecimento_saude, created = EstabelecimentoSaude.objects.update_or_create(
        codigo_cnes=dados['cnes'], defaults=save_data
    )
    return estabelecimento_saude

