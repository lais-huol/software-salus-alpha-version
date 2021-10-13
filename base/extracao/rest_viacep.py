# -*- coding: utf-8 -*-
import logging
import re
import requests

logger = logging.getLogger(__name__)

token = None
URL = 'https://viacep.com.br/ws'
REQUEST_CONNECTION_TIMEOUT = 5
REQUEST_READ_TIMEOUT = 30

#abdo do huol, cpf 24609455072


def get_cep(cep):
    cep = re.sub('[.-]', '', cep)
    try:
        url = URL + '/{}/json'.format(cep)
        logger.debug('Obtendo dados de CEP ({}): Fonte {} ...'.format(cep, url))
        response = requests.get(url,
                                timeout=(REQUEST_CONNECTION_TIMEOUT, REQUEST_READ_TIMEOUT))
        return response.json()
    except Exception as err:
        mensagem_de_erro = '''status_code = %s
                                url = %s'
                                content = %s
                               ''' % ('', url, str(err.args[0]))
        logger.warning(mensagem_de_erro)
    return {}
