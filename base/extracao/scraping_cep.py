# -*- coding: utf-8 -*-

import re
from bs4 import BeautifulSoup
from base.extracao.utils import page_get

import logging
logger = logging.getLogger(__name__)


token = None
URL = 'http://www.buscacep.correios.com.br/sistemas/buscacep/resultadoBuscaEndereco.cfm'
REQUEST_CONNECTION_TIMEOUT = 5
REQUEST_READ_TIMEOUT = 30

#abdo do huol, cpf 24609455072

HEADERS = {
'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
'Accept-Encoding': 'gzip, deflate',
'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
'Cache-Control': 'max-age=0',
'Connection': 'keep-alive',
'Content-Length': '13',
'Content-Type': 'application/x-www-form-urlencoded',
'Cookie': 'CFID=Z16c97xp1nfat85vel35thx6qc0x7tyryg54wwfrh1nlek21mq-99730854; CFTOKEN=Z16c97xp1nfat85vel35thx6qc0x7tyryg54wwfrh1nlek21mq-15cc09a7a5180d46-D52E9FE4-0F4A-F01A-2EAE1855E215CF51; JSESSIONID=87CE01C85D1CECCE48DBB40887DD7338.cfusion01; ssvbr0326_buscacep=sac2093_cep; ssvbr0326_www2=sac2844; opEueMonUID=u_l3z9re67tikalk1gny; CFGLOBALS=urltoken%3DCFID%23%3D99730854%26CFTOKEN%23%3D15cc09a7a5180d46%2DD52E9FE4%2D0F4A%2DF01A%2D2EAE1855E215CF51%26jsessionid%23%3D87CE01C85D1CECCE48DBB40887DD7338%2Ecfusion01%23lastvisit%3D%7Bts%20%272020%2D05%2D24%2018%3A09%3A35%27%7D%23hitcount%3D3%23timecreated%3D%7Bts%20%272020%2D05%2D24%2018%3A09%3A12%27%7D%23cftoken%3D15cc09a7a5180d46%2DD52E9FE4%2D0F4A%2DF01A%2D2EAE1855E215CF51%23cfid%3D99730854%23; CFGLOBALS=urltoken%3DCFID%23%3D99730854%26CFTOKEN%23%3D15cc09a7a5180d46%2DD52E9FE4%2D0F4A%2DF01A%2D2EAE1855E215CF51%26jsessionid%23%3D87CE01C85D1CECCE48DBB40887DD7338%2Ecfusion01%23lastvisit%3D%7Bts%20%272020%2D05%2D24%2018%3A09%3A35%27%7D%23hitcount%3D3%23timecreated%3D%7Bts%20%272020%2D05%2D24%2018%3A09%3A12%27%7D%23cftoken%3D15cc09a7a5180d46%2DD52E9FE4%2D0F4A%2DF01A%2D2EAE1855E215CF51%23cfid%3D99730854%23',
'Host': 'www.buscacep.correios.com.br',
'Origin': 'http://www.buscacep.correios.com.br',
'Referer': 'http://www.buscacep.correios.com.br/sistemas/buscacep/buscaEndereco.cfm',
'Upgrade-Insecure-Requests': '1',
'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36'
}

def get_cep(cep):
    cep = re.sub('[.-]', '', cep)
    if cep is None or len(cep) != 8:
        return None

    dados_form = {
        'CEP': cep,
    }
    url = URL
    logger.debug('Obtendo dados de CEP ({}): Fonte {} ...'.format(cep, URL))
    try:
        response = page_get('POST',
                            url = url,
                            data=dados_form,
                            verify=False,
                            headers=HEADERS,
                            timeout=(REQUEST_CONNECTION_TIMEOUT, REQUEST_READ_TIMEOUT),
                            allow_redirects=False)

        if response is not None:
            dados = {}
            soup = BeautifulSoup(response.content, "html.parser")
            tables = soup.findChildren('table')
            try:
                my_table = tables[0]
            except:
                return {}
            rows = my_table.findChildren(['td', 'tr'])
            for row in rows[1:]:
                cells = row.findChildren('td')
                cidade, uf = cells[2].text.replace('\xa0', '').split('/')
                dados = {
                     'uf': uf,
                     'cep': cells[3].text.replace('\xa0', ''),
                     'gia': '',
                     'ibge': '',
                     'bairro': cells[1].text.replace('\xa0', ''),
                     'unidade': '',
                     'localidade': cidade,
                     'logradouro': cells[0].text.replace('\xa0', ''),
                     'complemento': ''}
                logger.debug('Obtido CEP; {}'.format(dados))
                return dados
    except Exception as err:
        mensagem_de_erro = '''status_code = %s
                                url = %s'
                                content = %s
                               ''' % ('', url, str(err.args[0]))
        logger.warning(mensagem_de_erro)
    return {}
