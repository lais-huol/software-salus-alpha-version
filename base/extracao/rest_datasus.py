# -*- coding: utf-8 -*-
import logging
import requests

logger = logging.getLogger(__name__)

token = None
URL = 'http://cnes.datasus.gov.br/services'
REQUEST_CONNECTION_TIMEOUT = 5
REQUEST_READ_TIMEOUT = 30

#abdo do huol, cpf 24609455072

HEADERS = {'Accept': 'application/json, text/plain, */*',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
    'Cookie': 'SESSION=!jtmhxi4QaW7bWM4UgDG4DL2PTm//xvVlX5dP1ZdWPmuEGdbKvL8Qvo2lCxdVPAlMKqlvq562qJK9rl0=',
    'Host': 'cnes.datasus.gov.br',
    'Referer': 'http://cnes.datasus.gov.br/pages/profissionais/consulta.jsp?search=03086223405',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36',
}

def get_token(cpf, cns=None):
    #params={'token': self.token_autenticacao, 'mes': self.mes_referencia}
    '''
    Response:
    [{"id":"D180AD7ADE80D9B3EFB5656BDB5D176E406B77C41FF3D4B6E7EF48DC5F767ED2",
    "nome":"SENEI DA ROCHA HENRIQUE",
    "cns":"980016278321292"}]
    :param cpf:
    :param cns:
    :return:
    '''
    HEADERS['Referer'] = 'http://cnes.datasus.gov.br/pages/profissionais/consulta.jsp?search={}'.format((cpf))
    url = URL + '/profissionais?cns=%s' % cns
    logger.debug('Obtendo dados de profissionais de saúde (CPF {}, CNS {}): Fonte {} ...'.format(cpf, cns, url))
    try:
        if cns is not None:
            response = requests.get(url,
                                    headers=HEADERS,
                                    timeout=(REQUEST_CONNECTION_TIMEOUT, REQUEST_READ_TIMEOUT),
                                    allow_redirects=False)
        else:
            response = requests.get(URL + '/profissionais?cpf=%s' %cpf,
                                    headers=HEADERS,
                                    timeout=(REQUEST_CONNECTION_TIMEOUT, REQUEST_READ_TIMEOUT),
                                    allow_redirects=False)
        if response and response.status_code != 404:
            json =response.json()
            if json:
                return json[0].get('id')
    except Exception as err:
        mensagem_de_erro = '''status_code = %s
                                    url = %s'
                                    content = %s
                                   ''' % ('', url, str(err.args[0]))
        logger.warning(mensagem_de_erro)
    return {}

#http://cnes.datasus.gov.br/services/profissionais?cns=207281426640003
def get_profissional(cpf, token=None):
    '''
    Exemplo de dicionário de retorno:
    {nome: "ABDIEL DE LIRA ROLIM", cns: "980016285837932", cnsMaster: "700405938890250", sexo: null,…}
    cns: "980016285837932"
    cnsMaster: "700405938890250"
    nome: "ABDIEL DE LIRA ROLIM"
    sexo: null
    vinculos: [
        {existe: "0", tpPre: "2", tpRes: "2", estado: "RN", tpSusNaoSus: "S", coMun: "240810", noMun: "NATAL",…}
        cbo: "225320"
        chAmb: 4
        chHosp: 0
        chOutros: 20
        cnes: "2409208"
        cnpj: "24365710001406"
        coMun: "240810"
        dsCbo: "MEDICO EM RADIOLOGIA E DIAGNOSTICO POR IMAGEM"
        dsNatJur: "AUTARQUIA FEDERAL"
        estado: "RN"
        existe: "0"
        natJur: "1104"
        noFant: "MATERNIDADE ESCOLA JANUARIO CICCO"
        noMun: "NATAL"
        subVinculo: "PROPRIO"
        tpGestao: "M"
        tpPre: "2"
        tpRes: "2"
        tpSusNaoSus: "S"
        vinculacao: "VINCULO EMPREGATICIO"
        vinculo: "EMPREGO PUBLICO"
        }
    ],
    '''
    if token is None:
        token = get_token(cpf)
    HEADERS['Referer'] = 'http://cnes.datasus.gov.br/pages/profissionais/consulta.jsp?search={}'.format(cpf)
    url = URL + '/profissionais/%s' %token
    try:
        response = requests.get(url,
                                headers=HEADERS,
                                timeout=(REQUEST_CONNECTION_TIMEOUT, REQUEST_READ_TIMEOUT),
                                allow_redirects=False)
        if response and response.status_code != 404:
            return response.json()
    except Exception as err:
        mensagem_de_erro = '''status_code = %s
                                url = %s'
                                content = %s
                               ''' % ('', url, str(err.args[0]))
        logger.warning(mensagem_de_erro)

    return {}

def get_estabelecimento_saude(codigo_cnes):
    ''' Json de retorno
    [{id: "2408102653982", codigo_cnes: "2653982", noFantasia: "HUOL HOSPITAL UNIVERSITARIO ONOFRE LOPES",…}]
    0: {id: "2408102653982", codigo_cnes: "2653982", noFantasia: "HUOL HOSPITAL UNIVERSITARIO ONOFRE LOPES",…}
    atendeSus: "S"
    codigo_cnes: "2653982"
    gestao: "M"
    id: "2408102653982"
    natJuridica: "1"
    noEmpresarial: "UNIVERSIDADE FEDERAL DO RIO GRANDE DO NORTE"
    noFantasia: "HUOL HOSPITAL UNIVERSITARIO ONOFRE LOPES"
    noMunicipio: "NATAL"
    uf: "RN"
    '''
    HEADERS[
        'Referer'] = 'Referer: http://codigo_cnes.datasus.gov.br/pages/estabelecimentos/consulta.jsp?search={}'.format(
        codigo_cnes)
    url = URL + '/estabelecimentos?cnes={}'.format(codigo_cnes)
    logger.debug('Obtendo dados de estabelecimento de saúde (codigo cnes {}): Fonte {} ...'.format(codigo_cnes, url))
    try:
        response = requests.get(url,
                                headers=HEADERS,
                                timeout=(REQUEST_CONNECTION_TIMEOUT, REQUEST_READ_TIMEOUT),
                                allow_redirects=False)
        if response and response.status_code == 200:
            return response.json()
    except Exception as err:
        mensagem_de_erro = '''status_code = %s
                                url = %s'
                                content = %s
                               ''' % ('', url, str(err.args[0]))
        logger.warning(mensagem_de_erro)
    return {}


def get_estabelecimento_saude_detalhe(codigo_cnes, codigo_ibge=None):
    # Request URL: http'://cnes.datasus.gov.br/services/gestao
    # {"D":"DUPLA","E":"ESTADUAL","M":"MUNICIPAL"}
    # http://cnes.datasus.gov.br/services/natjur
    # {"1":"ADMINISTRAÇÃO PÚBLICA","2":"ENTIDADES EMPRESARIAIS","3":"ENTIDADES SEM FINS LUCRATIVOS","5":"ORGANIZAÇÕES INTERNACIONAIS/OUTRAS","4":"PESSOAS FÍSICAS"}
    # http://cnes.datasus.gov.br/services/estabelecimentos?cnes=2653982
    # Request URL: http://cnes.datasus.gov.br/services/estabelecimentos/240810 2653982

    ''' Json de retorno
        {id: "2408102653982", cnes: "2653982", noFantasia: "HUOL HOSPITAL UNIVERSITARIO ONOFRE LOPES",…}
        bairro: "PETROPOLIS"
        cep: "59012300"
        cnes: "2653982"
        cnpj: "24365710001317"
        coMotivoDesab: null
        cpfDiretorCln: "00937107476"
        dsMotivoDesab: null
        dsStpUnidade: null
        dsTpUnidade: "HOSPITAL GERAL"
        dtAtualizacao: "14/04/2020"
        dtAtualizacaoOrigem: "10/02/2003"
        dtCarga: "10/05/2020"
        dtExpAlvara: null
        id: "2408102653982"
        municipio: "240810"
        natJuridica: "1"
        natJuridicaMant: "1"
        noComplemento: null
        noEmpresarial: "UNIVERSIDADE FEDERAL DO RIO GRANDE DO NORTE"
        noFantasia: "HUOL HOSPITAL UNIVERSITARIO ONOFRE LOPES"
        noLogradouro: "AV NILO PECANHA"
        noMunicipio: "NATAL"
        nuAlvara: null
        nuCompDesab: null
        nuEndereco: "620"
        nuTelefone: "8433425000"
        nvDependencia: "3"
        orgExpAlvara: null
        regionalSaude: "007"
        tpGestao: "M"
        tpPessoa: "3"
        tpSempreAberto: "S"
        uf: "RN"
    '''
    HEADERS['Referer'] = 'http://cnes.datasus.gov.br/pages/estabelecimentos/consulta.jsp?search={}'.format(codigo_cnes)
    id = '{}{}'.format(codigo_ibge, codigo_cnes)
    url = URL + '/estabelecimentos/{}'
    try:
        if codigo_ibge is None:
            dados = get_estabelecimento_saude(codigo_cnes)
            if dados:
                id = dados[0]['id']
        url = url.format(id)

        response = requests.get(url,
                                headers=HEADERS,
                                timeout=(REQUEST_CONNECTION_TIMEOUT, REQUEST_READ_TIMEOUT),
                                allow_redirects=False)
        if response and response.status_code == 200:
            return response.json()
    except Exception as err:
        mensagem_de_erro = '''status_code = %s
                                url = %s'
                                content = %s
                               ''' % ('', url, str(err.args[0]))
        logger.warning(mensagem_de_erro)
    return {}
