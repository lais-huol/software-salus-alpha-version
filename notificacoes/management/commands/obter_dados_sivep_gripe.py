import json
from django.core.files.base import ContentFile, File
from django.core.management.base import BaseCommand
from django.utils import timezone
from zipfile import ZipFile, BadZipFile

from base.caches import ControleCache
from base.utils import normalize_str
from indicadores.indicadores import *
import pandas as pd
from elasticsearch import Elasticsearch
import elasticsearch.helpers

from notificacoes.processar_notificacoes import ObterNotificacaoSivepGripeDBF

logger = logging.getLogger(__name__)
import os
import datetime
import glob
from dbfread import DBF
import pandas as pd
import logging
logger = logging.getLogger(__name__)


class RecordSivepGripe(object):
    def __init__(self, items):
        for (name, value) in items:
            setattr(self, name, value)

class Command(BaseCommand):
    def handle(self, *args, **options):
        dados_sivep = ObterNotificacaoSivepGripeDBF().processar()
        import sys; sys.exit()


        dir_media = os.path.join(settings.BASE_DIR, 'media')
        filename_path = os.path.join(dir_media, 'SRAGHOSPITALIZADO1129989_00.dbf')
        records = DBF(filename_path, recfactory=RecordSivepGripe, lowernames=True, encoding='iso-8859-1')
        # records = dict(list(DBF(filename_path, encoding='iso-8859-1')))

        dados = {}
        for record in records:
            dados[record.nu_notific] = record.__dict__

        df = pd.DataFrame.from_dict(dados, orient='index', columns=records.field_names)
        print('Total de registros: {}'.format(df.shape[0]))

        # for col in df.columns.to_list():
        #     print("'%s': {'campo': '%s', 'descricao': ''}," %(col, col) )


        #1 - filtar somente notificações que receberam alta por cura
        #df[df['evolucao'] == '1']

        #Filtro aplicado
        # evolução para 2 - óbitos,
        # residentes em Natal
        # classificação final 5 - SRAG por COVID-19
        df = df[(df['evolucao'] == '2') & (df['id_mn_resi'] == 'NATAL') & (df['classi_fin'] == '5')]

        #TODO: Túlio, o dataframe possuiu os óbitos COVID para Natal.


        print('Total de óbitos: {}'.format(df.shape[0]))
        for col in df.columns.to_list():
            print('<<<<<<<<<<<<<<<<<<<<<<<<<<<< {} -> {}'.format(col, len(df[col].unique())))
            if len(df[col].unique()) < 50:
                for v in df[col].unique():
                    print('{} -> {}'.format(v, df[df[col] == v][col].count()))

        # _obter_notificacao = ObterNotificacao(TipoArquivo.ESUSVE_ARQUIVO_CSV)
        # for nome_bairro in list(df['nm_bairro'].unique()):
        #     print(nome_bairro, _obter_notificacao.tratar_bairro(nome_bairro))
#'out_sor', 'tp_sor', 'sor_out', 'tp_am_sor', 'ds_an_out', 'pos_an_flu', 'an_sars2', 'lab_an', 'tomo_out'
#<<<<<<<<<<<<<<<<<<<<<<<<<<<< pcr_sars2
# 665
#1 713

#CLASSI_FIN

# df[df['classi_fin'] == v]['classi_fin'].count()


COLUNAS = {
#Campos que consta no dicionário https://opendatasus.saude.gov.br/dataset/ae90fa8f-3e94-467e-a33f-94adbb66edf8/resource/8f571374-c555-4ec0-8e44-00b1e8b11c25/download/dicionario_de_dados_srag_hospitalizado_atual-sivepgripe.pdf
# Ficha sivep gripe http://189.28.128.100/sivep-gripe/Ficha_SIVEP_GRIPE_SRAG_Hospital.12.03.2020.pdf
#mas não há nos dados do DBF
# 'ID_CNS_SUS'
# NM_REFEREN
# DT_OBITO
#
#
#
#
#
#
#
#
#
'dt_res': {'campo': '', 'descricao': ''},
'res_igg': {'campo': '', 'descricao': 'Resultado da Sorologia para SARS-CoV-2'},
'res_igm': {'campo': '', 'descricao': 'Resultado da Sorologia para SARS-CoV-2'},
'res_iga': {'campo': '', 'descricao': 'Resultado da Sorologia para SARS-CoV-2'},
'nu_do': {'campo': '', 'descricao': 'Número da Declaraçãode Óbito'},
'nu_notific': {'campo': 'nu_notificacao', 'descricao': 'Número da Notificação'}, #Campo Chave
'dt_notific': {'campo': 'data_da_notificacao', 'descricao': 'Data de preenchimento da ficha de notificação.'}, #Campo Chave
'sem_not': {'campo': 'ds_semana_notificacao', 'descricao': 'Semana epidemiológica que o caso foi notificado.'},#Preenchida automaticamente, a partir da data de preenchimento (AAAASS)
'dt_sin_pri': {'campo': 'dt_diagnostico_sintoma', 'descricao': 'Data dos primeiros sintomas do caso de agravo agudo.'}, #Campo Obrigatório
'sem_pri': {'campo': '', 'descricao': ''},
'sg_uf_not': {'campo': 'co_uf_notificacao', 'descricao': 'Sigla da Unidade Federativa onde está localizada a unidade de saúde '}, #varchar2(2), Campo Obrigatório
'id_regiona': {'campo': '', 'descricao': ''},
'co_regiona': {'campo': '', 'descricao': ''},
'id_municip': {'campo': 'nu_municipio_notificacao', 'descricao': ''},  #NATAL
'co_mun_not': {'campo': 'co_municipio_notificacao', 'descricao': 'Código do município onde está localizada a unidade de saúde '},#varchar2(6) Campo Chave
'id_unidade': {'campo': 'nu_unidade_notificacao', 'descricao': 'Nome da unidade notificante'}, #Campo Obrigatório Preenchendo o código,
'co_uni_not': {'campo': 'co_unidade_notificacao', 'descricao': 'código cnes da unidade notificante'},
'nu_cpf': {'campo': 'cpf', 'descricao': 'cpf do paciente'},
'nm_pacient': {'campo': 'no_nome_paciente', 'descricao': 'Nome completo do paciente (sem abreviações)'}, #Campo Obrigatório
'cs_sexo': {'campo': 'tp_sexo', 'descricao': 'Sexo do paciente'}, #Campo Obrigatório s, M- Masculino F- Feminino I- Ignorado
'dt_nasc': {'campo': 'data_de_nascimento', 'descricao': 'Data de nascimento do paciente'}, #date dd/mm/aaaa , Campo Obrigatório
'nu_idade_n': {'campo': 'nu_idade', 'descricao': 'Idade informada pelo paciente quando não se sabe a data de nascimento.'}, #Campo Obrigatório, ex 58
'tp_idade': {'campo': 'nu_idade', 'descricao': ''}, #1-Dia; 2-Mês; 3-Ano
'cod_idade': {'campo': '', 'descricao': ''}, #ex 3058
'cs_gestant': {'campo': 'tp_gestante', 'descricao': 'Idade gestacional da paciente.'}, #Gestante 1. 1º Trimestre; 2. 2º Trimestre; 3. 3º Trimestre; 4. Idade gestacional ignorada; 5. Não; 6. Não se aplica
'cs_raca': {'campo': 'tp_raca_cor', 'descricao': 'raça declarada pela pessoa'}, #1- branca; 2- preta; 3- amarela; 4- parda; 5- indígena; 9 Ignorado
'cs_etinia': {'campo': '', 'descricao': ''},
'cs_escol_n': {'campo': 'tp_escolaridade', 'descricao': ''}, #0. Analfabeto; 1. Fundamental (1-9 anos); 2. Médio (1-3 anos); 3. Superior; 9. Ignorado; 10. Não se aplica
'nm_mae_pac': {'campo': 'no_nome_mae', 'descricao': 'Nome completo da mãe do paciente (sem abreviações)'},
'nu_cep': {'campo': 'nu_cep_residencia', 'descricao': 'CEP de residência do paciente'},
'id_pais': {'campo': 'nu_pais_residencia', 'descricao': 'País onde residia o paciente por ocasião da notificaçã'}, #BRASIL
'co_pais': {'campo': 'co_pais_residencia', 'descricao': ''}, #1-BRASIL
'sg_uf': {'campo': '', 'descricao': ''},
'id_rg_resi': {'campo': '', 'descricao': ''},
'co_rg_resi': {'campo': '', 'descricao': ''},
'id_mn_resi': {'campo': 'co_municipio_residencia', 'descricao': 'Código do município de residência do caso notificado'}, #Campo Obrigatório
'co_mun_res': {'campo': '', 'descricao': ''},
'nm_bairro': {'campo': 'no_bairro_residencia', 'descricao': 'Nome do bairro de residência'},
'nm_logrado': {'campo': 'no_logradouro_residencia', 'descricao': ''},
'nu_numero': {'campo': 'nu_residencia', 'descricao': 'Nº. do logradouro'},
'nm_complem': {'campo': 'ds_complemento_residencia', 'descricao': 'Complemento do logradouro '},
'nu_ddd_tel': {'campo': 'nu_ddd_residencia', 'descricao': 'DDD do telefone de  residência do paciente'},
'nu_telefon': {'campo': 'nu_telefone_residencia', 'descricao': 'Telefone de residência do paciente'},
'cs_zona': {'campo': 'tp_zona_residencia', 'descricao': 'Zona de residência do paciente por ocasião da notificação'}, #1. urbana; 2. rural; 3. periurbana; 9. ignorado
'surto_sg': {'campo': '', 'descricao': 'Caso é proveniente de surto de SG?'},
'nosocomial': {'campo': '', 'descricao': ''},# 1-Sim; 2-Não; 9-Ignorado
'ave_suino': {'campo': '', 'descricao': ''},
'febre': {'campo': '', 'descricao': ''},
'tosse': {'campo': '', 'descricao': ''},
'garganta': {'campo': '', 'descricao': ''},
'dispneia': {'campo': '', 'descricao': ''},
'desc_resp': {'campo': '', 'descricao': ''},
'saturacao': {'campo': '', 'descricao': ''},
'diarreia': {'campo': '', 'descricao': ''},
'vomito': {'campo': '', 'descricao': ''},
'outro_sin': {'campo': '', 'descricao': ''},
'outro_des': {'campo': '', 'descricao': ''},
'fator_risc': {'campo': '', 'descricao': ''},
'puerpera': {'campo': '', 'descricao': ''},
'cardiopati': {'campo': '', 'descricao': ''},
'hematologi': {'campo': '', 'descricao': ''},
'sind_down': {'campo': '', 'descricao': ''},
'hepatica': {'campo': '', 'descricao': ''},
'asma': {'campo': '', 'descricao': ''},
'diabetes': {'campo': '', 'descricao': ''},
'neurologic': {'campo': '', 'descricao': ''},
'pneumopati': {'campo': '', 'descricao': ''},
'imunodepre': {'campo': '', 'descricao': ''},
'renal': {'campo': '', 'descricao': ''},
'obesidade': {'campo': '', 'descricao': ''},
'obes_imc': {'campo': '', 'descricao': ''},
'out_morbi': {'campo': '', 'descricao': ''},
'morb_desc': {'campo': '', 'descricao': ''},
'vacina': {'campo': 'st_vacina_gripe', 'descricao': 'Se o paciente já foi vacinado ou não, contra gripe, após verificar documentação/caderneta'}, #1 Sim; 2 Não; 9 Ignorado
'dt_ut_dose': {'campo': '', 'descricao': ''},
'mae_vac': {'campo': '', 'descricao': ''},
'dt_vac_mae': {'campo': '', 'descricao': ''},
'm_amamenta': {'campo': '', 'descricao': ''},
'dt_doseuni': {'campo': '', 'descricao': ''},
'dt_1_dose': {'campo': '', 'descricao': ''},
'dt_2_dose': {'campo': '', 'descricao': ''},
'antiviral': {'campo': '', 'descricao': ''},
'tp_antivir': {'campo': '', 'descricao': ''},
'out_antiv': {'campo': '', 'descricao': 'Se o antiviral utilizado não foi Oseltamivir ou Zanamivir, informar qual antiviral foi utilizado.'}, #TAMIFLU, tamiflu, invermectina, ''
'dt_antivir': {'campo': '', 'descricao': ''},
'hospital': {'campo': '', 'descricao': 'O paciente foi internado?'},#1-Sim; 2-Não; 9-Ignorado
'dt_interna': {'campo': '', 'descricao': ''},
'sg_uf_inte': {'campo': 'co_uf_residencia', 'descricao': 'Sigla da Unidade Federada de residência do paciente'}, #Campo Obrigatório
'id_rg_inte': {'campo': '', 'descricao': ''},
'co_rg_inte': {'campo': '', 'descricao': 'Município onde está localizado a Unidade de Saúde onde o paciente internou.'},
'id_mn_inte': {'campo': '', 'descricao': 'código ibge 6 dígito do município onde está localizado a Unidade de Saúde onde o paciente internou.'},
'co_mu_inte': {'campo': '', 'descricao': ''},
'nm_un_inte': {'campo': '', 'descricao': ''},
'co_un_inte': {'campo': '', 'descricao': ''},
'uti': {'campo': '', 'descricao': 'O paciente foi internado em UTI?'}, #1-Sim; 2-Não; 9-Ignorado
'dt_entuti': {'campo': '', 'descricao': 'Data de entrada do paciente na unidade de Terapia intensiva (UTI).'},
'dt_saiduti': {'campo': '', 'descricao': 'Data em que o paciente saiu da Unidade de Terapia intensiva (UTI)'},
'suport_ven': {'campo': '', 'descricao': 'O paciente fez uso de suporte ventilatório?'}, #1-Sim, invasivo; 2-Sim;  não invasivo; 3-Não; 9-Ignorado
'raiox_res': {'campo': '', 'descricao': ''},
'raiox_out': {'campo': '', 'descricao': ''},
'dt_raiox': {'campo': '', 'descricao': ''},
'amostra': {'campo': 'foi_realizado_teste', 'descricao': 'Foi realizado coleta de amostra para realização de teste diagnóstico?'}, #1-Sim; 2-Não; 9-Ignorado
'dt_coleta': {'campo': 'data_da_coleta_do_teste', 'descricao': 'Data da coleta da amostra para realização do teste diagnóstico.'},
'tp_amostra': {'campo': '', 'descricao': 'Tipo da amostra clínica coletada para o teste diagnóstico.'}, #1-Secreção de Nasoorofaringe; 2-Lavado Broco-alveolar; 3-Tecido post-mortem; 4-Outra, qual?; 5-LCR; 9-Ignorado
'out_amost': {'campo': '', 'descricao': ''},
'requi_gal': {'campo': '', 'descricao': ''},
'pcr_resul': {'campo': '', 'descricao': 'Resultado do teste de RT-PCR/outro método por Biologia Molecular'}, #1-Detectável; 2-Não Detectável; 3-Inconclusivo; 4-Não Realizado; 5-Aguardando Resultado; 9-Ignorado
'dt_pcr': {'campo': '', 'descricao': ''},
'pos_pcrflu': {'campo': '', 'descricao': 'Resultado da RTPCR foi positivo para Influenza'}, #1-Sim; 2-Não; 9-Ignorado
'tp_flu_pcr': {'campo': '', 'descricao': ''},
'pcr_fluasu': {'campo': '', 'descricao': ''},
'fluasu_out': {'campo': '', 'descricao': ''},
'pcr_flubli': {'campo': '', 'descricao': ''},
'flubli_out': {'campo': '', 'descricao': ''},
'pos_pcrout': {'campo': '', 'descricao': ''},
'pcr_vsr': {'campo': '', 'descricao': ''},
'pcr_para1': {'campo': '', 'descricao': ''},
'pcr_para2': {'campo': '', 'descricao': ''},
'pcr_para3': {'campo': '', 'descricao': ''},
'pcr_para4': {'campo': '', 'descricao': ''},
'pcr_adeno': {'campo': '', 'descricao': ''},
'pcr_metap': {'campo': '', 'descricao': ''},
'pcr_boca': {'campo': '', 'descricao': ''},
'pcr_rino': {'campo': '', 'descricao': ''},
'pcr_outro': {'campo': '', 'descricao': ''},
'ds_pcr_out': {'campo': '', 'descricao': ''},
'lab_pcr': {'campo': '', 'descricao': ''},
'co_lab_pcr': {'campo': '', 'descricao': ''},
'classi_fin': {'campo': 'tp_classificacao_final', 'descricao': ''}, #Campo Obrigatório, 1-SRAG por Influenza; 2- SRAG por outros vírus respiratórios; 3- SRAG por outros; # agentes etiológicos; 4- SRAG não especificado
'dt_encerra': {'campo': 'data_de_encerramento', 'descricao': 'Data do encerramento da investigação do caso'},  #Campo Obrigatório
'classi_out': {'campo': '', 'descricao': ''},
'criterio': {'campo': 'tp_criterio_confirmacao', 'descricao': 'Indicar qual o critério de confirmação'}, #1. Laboratorial; 2. Clínico Epidemiológico; 3. Clínico; 4. Clínico Imagem
'evolucao': {'campo': 'evolucao_caso', 'descricao': 'Evolução do caso'}, #1-Cura; 2-Óbito; 9-Ignorado
'dt_evoluca': {'campo': 'data_evolucao', 'descricao': 'Data da alta ou do óbito '},
'observa': {'campo': '', 'descricao': ''},
'nome_prof': {'campo': '', 'descricao': 'Nome completo do profissional de saúde (sem abreviações) responsável pela notificação.'}, #
'reg_prof': {'campo': '', 'descricao': 'Número do conselho ou matrícula do profissional de saúde responsável pela notificação'}, #860.863 COREN'
'dt_digita': {'campo': 'data_cadastro', 'descricao': 'Data de inclusão do registro no sistema'},
'histo_vgm': {'campo': '', 'descricao': '- Paciente tem histórico de viagem internacional até 14 dias antes do início dos sintomas? '}, #1-Sim; 2-Não; 9-Ignorado
'pais_vgm': {'campo': '', 'descricao': ''},
'co_ps_vgm': {'campo': '', 'descricao': ''},
'lo_ps_vgm': {'campo': '', 'descricao': ''},
'dt_vgm': {'campo': '', 'descricao': ''},
'dt_rt_vgm': {'campo': '', 'descricao': ''},
'pcr_sars2': {'campo': '', 'descricao': 'Resultado diagnóstico do RTPCR para (SARS-CoV2).'},
'pac_cocbo': {'campo': '', 'descricao': ''},
'pac_dscbo': {'campo': '', 'descricao': 'Código CBO da ocupação profissional do paciente'},
'out_anim': {'campo': '', 'descricao': 'Informar o animal que o paciente teve contato se selecionado a opção 3.'},
'dor_abd': {'campo': '', 'descricao': 'Paciente apresentou dor abdominal?'}, #1-Sim; 2-Não; 9-Ignorado
'fadiga': {'campo': '', 'descricao': 'Paciente apresentou fadiga?'}, #1-Sim; 2-Não; 9-Ignorado
'perd_olft': {'campo': '', 'descricao': 'Paciente apresentou perda do olfato?'}, #1-Sim; 2-Não; 9-Ignorado
'perd_pala': {'campo': '', 'descricao': 'Paciente apresentou perda do paladar?'}, #1-Sim; 2-Não; 9-Ignorado
'tomo_res': {'campo': '', 'descricao': 'Informar o resultado da tomografia'}, #1-Tipico COVID-19; 2- Indeterminado COVID-19; 3- Atípico COVID-19; 4- Negativo para Pneumonia; 5- Outro; 6-Não realizado; 9-Ignorado
'tomo_out': {'campo': '', 'descricao': 'Informar o resultado da tomografia se selecionado a opção 5-Outro'},
'dt_tomo': {'campo': '', 'descricao': ''},
'tp_tes_an': {'campo': '', 'descricao': 'Tipo do teste antigênico que foi realizado.'}, #1-Imunofluorescência (IF); 2- Teste rápido antigênico
'dt_res_an': {'campo': '', 'descricao': 'Data do resultado do teste antigênico'},
'res_an': {'campo': '', 'descricao': 'Resultado do Teste Antigênico'}, #1-positivo; 2-Negativo; 3- Inconclusivo; 4-Não realizado; 5-Aguardando resultado; 9-Ignorado
'lab_an': {'campo': '', 'descricao': 'Laboratório que realizou o Teste antigênico'},
'co_lab_an': {'campo': '', 'descricao': 'código cnes do Laboratório que realizou o Teste antigênico'},
'pos_an_flu': {'campo': '', 'descricao': 'Resultado do Teste Antigênico que foi positivo para Influenza'}, #1-Sim; 2-Não; 9-Ignorado
'tp_flu_an': {'campo': '', 'descricao': ''},
'pos_an_out': {'campo': '', 'descricao': ''},
'an_sars2': {'campo': '', 'descricao': ''},
'an_vsr': {'campo': '', 'descricao': ''},
'an_para1': {'campo': '', 'descricao': ''},
'an_para2': {'campo': '', 'descricao': ''},
'an_para3': {'campo': '', 'descricao': ''},
'an_adeno': {'campo': '', 'descricao': ''},
'an_outro': {'campo': '', 'descricao': ''},
'ds_an_out': {'campo': '', 'descricao': 'Nome do outro vírus respiratório identificado pelo Teste Antigênico'},
'tp_am_sor': {'campo': '', 'descricao': ''},
'sor_out': {'campo': '', 'descricao': ''},
'dt_co_sor': {'campo': '', 'descricao': ''},
'tp_sor': {'campo': '', 'descricao': ''},
'out_sor': {'campo': '', 'descricao': ''},


}

