import json
import os

import logging
import re
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.cache import cache
from pathlib import Path
from requests_html import HTMLSession
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

URL = 'https://leitoscovidrn.saude.rn.gov.br/leitos'
REQUEST_CONNECTION_TIMEOUT = 5
REQUEST_READ_TIMEOUT = 30

def get_censo_leitos(usuario, senha):
    # return json.loads(cache.get('imd_dados'))
    logger.info('Obtendo dados do censo leitos covid: Fonte {} ...'.format(URL))

    def processar_internacoes(session, unidades_ids):
        mensagem_de_retorno = []
        dados = []
        contador = 0
        for nome, id in unidades_ids.items():
            logger.debug('Processando {} ...'.format(URL + '/leito/listar/{}'.format(id)))
            destabelecimento = {}
            destabelecimento['unidade'] = nome
            destabelecimento['id'] = id
            destabelecimento['pacientes'] = []
            response = session.get(url=URL + '/leito/listar/{}'.format(id),
                                   timeout=(REQUEST_CONNECTION_TIMEOUT, REQUEST_READ_TIMEOUT))
            soup = BeautifulSoup(response.content, "html.parser")
            rows = soup.findAll('tr')
            for row in rows:
                cells = row.findChildren('td')
                if cells:
                    try:
                        dado = {'leito': '',
                                'tipo_de_leito': cells[1].find('p')['title'],
                                'nome_do_paciente': cells[2].span.string.strip(),
                                'idade': cells[3].string,
                                'diagnostico': cells[4].find('img')['title'],
                                'ti': ' cells[5].string',
                                'municipio': cells[6].string,
                                'data_de_admissao': cells[4].string,
                                }
                        contador += 1
                        destabelecimento['pacientes'].append(dado)
                    except AttributeError:
                        pass
            mensagem_de_retorno.append('{} - lidos: {}'.format(nome, len(destabelecimento['pacientes'])))
            dados.append(destabelecimento)

        mensagem_de_retorno.append('FIM DO PROCESSAMENTO DE INTERNAÇÕES - TOTAL PROCESSADOS: {}'.format(contador))
        return dados, mensagem_de_retorno

    def processar_obitos(session, unidades_ids):
        mensagem_de_retorno = []
        dados = []
        logger.debug('Processando {} ...'.format(URL + '/unidadesaude/listarobitos'))
        response = session.get(url=URL + '/unidadesaude/listarobitos',
                               timeout=(REQUEST_CONNECTION_TIMEOUT, REQUEST_READ_TIMEOUT))
        soup = BeautifulSoup(response.content, "html.parser")

        destabelecimento = {}
        rows = soup.findAll('tr')
        contador = 0
        for row in rows:
            cells = row.findChildren('td')
            if cells:
                nome_unidade = cells[3].string.strip()
                if destabelecimento.get(nome_unidade, None) is None:
                    destabelecimento[nome_unidade] = {}
                    destabelecimento[nome_unidade]['pacientes'] = []

                destabelecimento[nome_unidade]['unidade'] = nome_unidade

                try:
                    destabelecimento[nome_unidade]['id'] = unidades_ids[cells[3].string]
                except KeyError:
                    mensagem_de_retorno.append('Estabelecimento {} sem id associado'.format(nome_unidade))
                    destabelecimento[nome_unidade]['id'] = None

                dado = {'leito': '',
                        'tipo_de_leito': '',
                        'nome_do_paciente': str(cells[0].text).replace('\n', ''),
                        'idade': cells[1].text,
                        'diagnostico': cells[2].find('img')['title'],
                        'ti': '',
                        'municipio': '',
                        'data_de_liberacao': cells[4].string,
                        }
                contador += 1
                destabelecimento[nome_unidade]['pacientes'].append(dado)

        for k, v in destabelecimento.items():
            dados.append(v)

        mensagem_de_retorno.append('FIM DO PROCESSAMENTO DE ÓBITOS - TOTAL PROCESSADOS: {}'.format(contador))

        return dados, mensagem_de_retorno

    dados_form = {
        'username': usuario,
        'password': senha
    }
    url = URL + '/login'
    session = HTMLSession()
    session.post(
        url=url,
        data=dados_form,
        verify=False,
        timeout=(REQUEST_CONNECTION_TIMEOUT, REQUEST_READ_TIMEOUT))



    #Cria dicoinários onde a chave é o nome do estabelecimento de saúde e o valor é o id correspondente.
    response = session.get(url=URL + '/unidadesaude/dashboardunidade',
                           timeout=(REQUEST_CONNECTION_TIMEOUT, REQUEST_READ_TIMEOUT))
    soup = BeautifulSoup(response.content, "html.parser")
    my_table = soup.find(id='dataTable')
    rows = my_table.findChildren(['th', 'tr'])

    unidades_ids = {}
    for row in rows:
        cells = row.findChildren('td')
        nome_unidade = None
        for cell in cells:
            value = cell.string
            if value:
                nome_unidade = value
            try:
                id_estabelecimento = re.findall('[0-9]+', cell.a['onclick'])[0]
                unidades_ids[nome_unidade] = id_estabelecimento
            except:
                pass

    dados = []
    dados, mensagem_de_retorno = processar_internacoes(session, unidades_ids)
    dados_obitos, mensagem_de_retorno_obitos = processar_obitos(session, unidades_ids)
    dados.extend(dados_obitos)
    mensagem_de_retorno.extend(mensagem_de_retorno_obitos)

    # cache.set('imd_dados', json.dumps(dados), None)

    # with open('censo_leitos_imd.json', 'w') as fp:
    #     json.dump(dados, fp)
    return dados, mensagem_de_retorno


def baixar_pdf_censo_leitos_(usuario, senha):
    logger.info('Baixando pdf do censo leitos covid: Fonte {} ...'.format(URL))
    dados_form = {
        'username': usuario,
        'password': senha
    }
    url = URL + '/login'
    session = HTMLSession()
    session.post(
        url=url,
        data=dados_form,
        verify=False,
        timeout=(REQUEST_CONNECTION_TIMEOUT, REQUEST_READ_TIMEOUT))

    response = session.get(url=URL + '/unidadesaude/dashboardunidade',
                           timeout=(REQUEST_CONNECTION_TIMEOUT, REQUEST_READ_TIMEOUT))
    soup = BeautifulSoup(response.content, "html.parser")
    my_table = soup.find(id='dataTable')
    rows = my_table.findChildren(['th', 'tr'])

    unidades_ids = {}
    for row in rows:
        cells = row.findChildren('td')
        nome_unidade = None
        for cell in cells:
            value = cell.string
            if value:
                nome_unidade = value
            try:
                id_estabelecimento = re.findall('[0-9]+', cell.a['onclick'])[0]
                unidades_ids[nome_unidade] = id_estabelecimento
            except:
                pass

    #baixar os pdfs
    urls = [
        'https://leitoscovidrn.saude.rn.gov.br/leitos/unidadesaude/relatorioObitosCOVID',
        'https://leitoscovidrn.saude.rn.gov.br/leitos/unidadesaude/relatorioExameInsetivoSemi',
        'https://leitoscovidrn.saude.rn.gov.br/leitos/unidadesaude/relatorioExamesEnfermariaEExtra'
    ]
    dados_form = []
    dados_form.append('_unidadesSaude=1')
    for id in unidades_ids.values():
        dados_form.append('unidadesSaude={}'.format(id))
    dados_form = '&'.join(dados_form)

    paths_dos_arquivos = []
    for url in urls:
        response = session.post(url=url, headers = {'Content-Type': 'application/x-www-form-urlencoded',}, data=dados_form, stream = True)
        nome_arquivo = os.path.join(settings.MEDIA_ROOT, '{}.pdf'.format(url.split('/')[-1]))
        logger.debug('Baixando arquivo {}'.format(nome_arquivo))
        paths_dos_arquivos.append(nome_arquivo)
        filename = Path(nome_arquivo)
        filename.write_bytes(response.content)

    return paths_dos_arquivos



