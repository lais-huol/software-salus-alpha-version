import logging
import requests

logger = logging.getLogger(__name__)

def page_get(http_method_type, url, **kwargs):

    try:
        if http_method_type == 'GET':
            response = requests.get(url, **kwargs)
            if response.status_code == 200:
                return response
            else:
                mensagem_de_erro = '''status_code = %s
                                    url = %s'
                                    content = %s
                                   ''' % (response.status_code, url, response.text)
                logger.warning(mensagem_de_erro)
                return None
        elif http_method_type == 'POST':
            response = requests.post(url, **kwargs)
            status_code = response.status_code
            if status_code == 200:
                return response
            else:
                mensagem_de_erro = '''status_code = %s
                                    url = %s'
                                    content = %s
                                   ''' % (response.status_code, url, response.text)
                logger.warning(mensagem_de_erro)
                return None
        else:
            raise RuntimeError('http method type %s not implemented' %http_method_type)
    except Exception as err:
        mensagem_de_erro = '''status_code = %s
                            url = %s'
                            content = %s
                           ''' % ('', url, str(err.args[0]))
        logger.warning(mensagem_de_erro)
    return None
