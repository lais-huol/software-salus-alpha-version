from time import sleep

import requests

from base.utils import digits


def get_dados(cpf_ou_cns, sleep_time=0):
    """
    Retorna dados de um cidadão obtidos através do webservice do CNS
    :param cpf_ou_cns:
    :return: HTTP Status e content
    Response Content Example (fake):
    {'complemento': 'APTO',
     'cns': '708607049758986',
     'nome': 'JOÃO BLA',
     'bairro': 'NOVO BAIRRO',
     'cep': '5900000',
     'logradouro': 'MARIA BLA',
     'data_de_nascimento': '1980-10-02',
     'sexo': 'M',
     'nome_do_pai': 'MARIO DA SILVA',
     'cpf': '648.545.870-08',
     'numero': '80',
     'telefone': '+55-84-999006789',
     'tipo_de_logradouro': '008',
     'nome_da_mae': 'MARIA MEDEIROS',
     'uf': 'RN',
     'municipio': '240325'}
    """
    cpf_ou_cns = digits(cpf_ou_cns)
    try:
        if sleep_time:
            sleep(sleep_time)
        return requests.get(
            url='https://api.sabia.ufrn.br/cns/{}/'.format(cpf_ou_cns),
            headers={'Authorization': 'Token QZEXGoSJtxp4lN8PaGtu3CNvznIYDPSuAEBhgbNL'}
        ).json()
    except ValueError:
        return None
