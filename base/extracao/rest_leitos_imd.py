import json
import requests
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


URL = 'https://leitoscovidrn.saude.rn.gov.br/api/rest'
REQUEST_CONNECTION_TIMEOUT = 5
REQUEST_READ_TIMEOUT = 30
HEADERS = {
'tokenAutorizacao': '15b2ee656422ac1e8c51058af600692b288f3ccc5676b631335330df4123e374',
}

def get_leitos_lista_geral():
    '''
    Lista de todos pacientes internados e óbitos e o timestamp do relatório
    Formato
    {
        'internados: [
            {
              "diagnostico": "COVID-19 CONFIRMADO",
              "id": 0,
              "internacao_admiss\u00e3o": "10/06/2020",
              "internacao_liberacao": null,
              "internacao_motivo_liberacao": null,
              "leito_ativo": true,
              "leito_cod_referencia": "7",
              "leito_motivo_bloqueio": null,
              "leito_situacao_leito": "OCUPADO",
              "leito_tipo_leito": "ENFERMARIA",
              "paciente_data_nascimento": "28/01/1977",
              "paciente_municipio_codigo": "11205",
              "paciente_municipio_nome": "Santa Cruz",
              "paciente_nome": "ROMUALDO LOURENCO CONFESSOR",
              "requisicao_gal": "",
              "unidade_ativo": true,
              "unidade_nome": "HOSPITAL REGIONAL DE SANTA CRUZ",
              "unidade_tipo": "MUNICIPAL"
            },
        'obitos': [
        ]
        'altas': [
        ]
    }

    :return:
    '''
    try:
        url = URL + '/listaGeral'
        print('Obtendo dados censo leitos imd - {}'.format(url))
        response = requests.get(url,
                                headers=HEADERS,
                                timeout=(REQUEST_CONNECTION_TIMEOUT, REQUEST_READ_TIMEOUT))
        # with open('imd_listaGeral.json', 'w') as fp:
        #     json.dump(response.json(), fp, indent=4)
        return response.json()
    except Exception as err:
        mensagem_de_erro = '''status_code = %s
                                url = %s'
                                content = %s
                               ''' % ('', url, str(err.args[0]))
        raise Exception(mensagem_de_erro)
    return {}

def get_relatorio_ocupacao_leitos():
    '''
    Lista da ocupação dos leitos de todas as unidade em uma única lista.
    Formato:
        {
          "timestamp": "24/06/2020 19:18:47",
            "unidades": [
                {
                  "ativo": true,
                  "contato_enfermeiro": "",
                  "contato_medico": "",
                  "data_criacao": null,
                  "data_modificacao": null,
                  "demi_intensiva_confirmado": 6,
                  "demi_intensiva_descartado": 0,
                  "demi_intensiva_suspeito": 4,
                  "demi_intensiva_total": 19,
                  "email": null,
                  "id": 1,
                  "municipio": "Caic\u00f3",
                  "nome": "HOSPITAL REGIONAL TELECILA FREITAS FONTES (CAIC\u00d3/RN) SERID\u00d3",
                  "outros_confirmado": 7,
                  "outros_descartado": 0,
                  "outros_suspeito": 3,
                  "outros_total": 15,
                  "qnt_epi": null,
                  "qnt_respiradores": null,
                  "qnt_respiradores_disponiveis": null,
                  "soma_demi_intesiva": 10,
                  "soma_outros": 10,
                  "soma_uti": 9,
                  "tipo_unidade_saude": "ESTADUAL",
                  "uti_confirmado": 7,
                  "uti_descartado": 0,
                  "uti_suspeito": 2,
                  "uti_total": 11,
                  "vagas_demi_intesiva": 9,
                  "vagas_outros": 5,
                  "vagas_uti": 2
                },
            ]
        }


    :return:
    '''
    try:
        url = URL + '/relatorioOcupacaoLeitos'
        response = requests.get(url,
                                headers=HEADERS,
                                timeout=(REQUEST_CONNECTION_TIMEOUT, REQUEST_READ_TIMEOUT))
        return response.json()
    except Exception as err:
        mensagem_de_erro = '''status_code = %s
                                url = %s'
                                content = %s
                               ''' % ('', url, str(err.args[0]))
        raise Exception(mensagem_de_erro)
    return {}

def get_relatorio_ocupacao_leitos_tipos_unidade():
    '''
    Lista da ocupação dos leitos de todas as unidades por tipo
    :return:
    '''
    try:
        url = URL + '/relatorioOcupacaoLeitosTiposUnidade'
        response = requests.get(url,
                                headers=HEADERS,
                                timeout=(REQUEST_CONNECTION_TIMEOUT, REQUEST_READ_TIMEOUT))
        return response.json()
    except Exception as err:
        mensagem_de_erro = '''status_code = %s
                                url = %s'
                                content = %s
                               ''' % ('', url, str(err.args[0]))
        raise Exception(mensagem_de_erro)
    return {}

