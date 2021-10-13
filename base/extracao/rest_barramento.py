import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


TOKEN = settings.BARRAMENTO_LAIS['token']
URL = settings.BARRAMENTO_LAIS['url']
REQUEST_CONNECTION_TIMEOUT = 10
REQUEST_READ_TIMEOUT = 40


def acessar_servico(http_method_type, url, **kwargs):
    try:
        link = url
        if http_method_type == 'GET':
            js = []
            while True:
                response = requests.get(link, **kwargs)
                status_code = response.status_code
                if status_code == 200:
                    try:
                        #recupera o link para a próxima página, padrão &limit=1000&offset=1000
                        link = response.headers['link'].split(';')[0] #'rel="next",<None>; rel="prev",'
                        #remove o primeiro e o último caracter, ou seja, "<" e ">"
                        link = link[1:-1]
                        js.extend(response.json())
                        if 'None' in link:
                            break
                    except KeyError:
                        return response.json()
                else:
                    break
            if status_code == 200:
                return js
        elif http_method_type == 'POST':
            response = requests.post(url, **kwargs)
            status_code = response.status_code
            if status_code == 200:
                return response.json()
        else:
            raise RuntimeError('http method type %s not implemented' %http_method_type)
    except Exception as err:
        mensagem_de_erro = '''status_code = %s
                            url = %s'
                            content = %s
                           '''%('', url, str(err.args[0]))
        logger.warning(mensagem_de_erro)
    return {}


def get_json_estabelecimento(codigo_cnes):
    headers = {
           'Authorization': 'Token ' + TOKEN,
           'content-type' : 'application/json',
            'grant_type': 'Token ' + TOKEN,
           }
    url = URL + '/estabelecimentos/%s/?format=json&necessita_atualizar=False' %codigo_cnes
    logger.debug('Obtendo dados do estabelecimento de saúde (codigo cnes {}): Fonte {} ...'.format(codigo_cnes, URL))
    js = acessar_servico('GET',
                         url,
                         timeout=(REQUEST_CONNECTION_TIMEOUT, REQUEST_READ_TIMEOUT),
                         headers=headers,
                         verify=False,
                         allow_redirects=False)
    return js
# http://barramento.lais.huol.ufrn.br/api/v2/estabelecimentos/2654024/?format=json
# https://barramento.lais.huol.ufrn.br/api/v2/estabelecimentos/2654024/?format=json