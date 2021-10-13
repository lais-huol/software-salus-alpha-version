import json
import json
import logging
import os
import pandas as pd
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.crypto import get_random_string
from sentry_sdk import capture_exception

from base.model_csv import qs_to_local_csv
from base.models import Bairro, Municipio, Distrito, HabitacoesBairro, EstabelecimentoSaude, AssociacaoBairro, \
    AssociacaoNomeEstabelecimentoSaude, AssociacaoOperadorCNES, Usuario, UnidadeFederativa

# https://www.ilovepdf.com/pt/pdf_para_excel

# with open('load_initial_data.log', 'w'):
#     pass
#
# logging.basicConfig(filename='load_initial_data.log',
#                     format='%(levelname)s;%(asctime)s;%(message)s',
#                     datefmt='%d/%m/%Y %I:%M:%S %p',
#                     level = logger.info)

logger = logging.getLogger(__name__)

#  for nome, nome_bairro in AssociacaoBairro.objects.values_list('nome', 'bairro__nome').order_by('nome'): print(nome, '->', nome_bairro)
# AssociacaoBairro.objects.all().delete()

def processar_bairros(filename, dados_distritos):
    df = pd.read_csv(filename, delimiter=';')
    municipio, created = Municipio.objects.get_or_create(
        codigo_ibge='240810',
        codigo_ibge_estado='24',
        nome='Natal'

    )
    bairros_parse = {
        'Mãe Luíza': 'Mãe Luiza',
        'Nordeste': 'Bairro Nordeste',
    }
    dados = {}
    contador = 0
    for index, nome in df['Bairro'].items():
        try:
            distrito = dados_distritos[nome.upper()]
        except:
            try:
                distrito = dados_distritos[bairros_parse[nome].upper()]
            except:
                pass
        bairro, created = Bairro.objects.get_or_create(
            nome=nome.upper(),
            municipio=municipio,
            distrito=distrito
        )
        contador += 1
        dados[nome.upper()] = bairro
    logger.debug('Importados {} Bairro.'.format(contador))
    return dados

def processar_distritos(filename):
    df = pd.read_csv(filename, delimiter=';')
    municipio, created = Municipio.objects.get_or_create(
        codigo_ibge='240810',
        codigo_ibge_estado='24',
        nome='Natal'

    )
    dados = {}
    contador = 0
    for index, row in df.iterrows():
        distrito, created = Distrito.objects.get_or_create(
            municipio=municipio,
            nome=row['DISTRITO']
        )
        try:
            dados[row['BAIRRO'].upper()] = distrito
            contador += 1
        except:
            pass
    logger.debug('Importados {} Distrito.'.format(contador))
    return dados

def processar_habitacoes_bairros(filename, dados_bairro):
    df = pd.read_csv(filename, delimiter=';', keep_default_na=False)
    dados = {}
    contador = 0
    for index, row in df.iterrows():
        nome_bairro = row['bairro'].upper()
        nome = row['nome'].upper()
        habitacoes, created = HabitacoesBairro.objects.get_or_create(
            nome=nome,
            bairro = dados_bairro[nome_bairro],
            tipo = row['tipo']
            )
        dados[nome] = dados_bairro[nome_bairro]
        contador += 1
    logger.debug('Importados {} HabitacoesBairro.'.format(contador))
    return dados

def importar_municipio_bairro_limbo():
    municipio, created = Municipio.objects.get_or_create(
        codigo_ibge='999999',
        codigo_ibge_estado='99',
        nome='Outro'

    )

    distrito, created = Distrito.objects.get_or_create(
        municipio=municipio,
        nome='Outro'
    )

    bairro, created = Bairro.objects.get_or_create(
        nome='OUTRO'.upper(),
        municipio=municipio,
        distrito=distrito
    )

# def exportar_ceps():
#     '''
#     Exporta os dados de cep para um arquivo CSV
#     :return:
#     '''
#     with open('ceps.csv', mode='w') as csv_file:
#         csv_writer = csv.writer(csv_file, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
#         csv_writer.writerow(['cep', 'dados_cep'])
#         qs = Notificacao.objects.filter(dados_cep__cep__isnull=False)
#         qs = qs.values('dados_cep__cep', 'dados_cep').distinct()
#         for cep, dados_cep in qs.values_list('dados_cep__cep', 'dados_cep'):
#             cep = re.sub('[.-]', '', cep)
#             csv_writer.writerow([cep, json.dumps(dados_cep, ensure_ascii=False)])

def exportar_associacoes_bairro():
    qs = AssociacaoBairro.objects.all()
    qs_to_local_csv(qs, fields=['nome', 'bairro__nome'])


def exportar_associacoes_operadores():
    qs = AssociacaoOperadorCNES.objects.all()
    qs_to_local_csv(qs, fields=['cpf',
                                'estabelecimento_saude__codigo_cnes',
                                'dados'])


def exportar_associacoes_nomes_estabelecimento_cnes(path_dir_fixtures):
    qs = AssociacaoNomeEstabelecimentoSaude.objects.all()
    qs_to_local_csv(qs, fields=['nome',
                                'estabelecimento_saude__codigo_cnes',
                                'estabelecimento_saude__dados_cnes__CO_MUNICIPIO_GESTOR'
                                ],
                    path=path_dir_fixtures,
                    filename='associacaonomeestabelecimentosaude.csv')


def processar_associacoes_operadores(filename):
    df = pd.read_csv(filename, delimiter=',')
    contador = 0
    for index, row in df.iterrows():
        estabelecimento = None
        try:
            estabelecimento = EstabelecimentoSaude.objects.get(codigo_cnes= str(int(row['estabelecimento_saude__codigo_cnes'])))
        except:
            pass

        save_data = {
            'dados': row['dados'],
            'estabelecimento_saude': estabelecimento
        }
        AssociacaoOperadorCNES.objects.get_or_create(
            cpf=str(str(row['cpf'])), defaults=save_data)
        contador += 1
    logger.debug('Importados {} AssociacaoOperadorCNES.'.format(contador))


def processar_estabelecimento_saude(filename):
    df = pd.read_csv(filename, delimiter=';', index_col='CO_CNES')
    dados_cnes = json.loads(df.to_json(orient='index'))
    contador = 0
    for codigo_cnes, dados in dados_cnes.items():
        #Salva somente estabelecimentos de Natal
        if dados['CO_ESTADO_GESTOR'] == 24:
            save_data = {
                'dados_cnes': dados,
                'data_extracao': timezone.now()
            }
            estabelecimento_saude, created = EstabelecimentoSaude.objects.update_or_create(
                    codigo_cnes=codigo_cnes, defaults=save_data)
            contador += 1
    logger.debug('Importados {} EstabelecimentoSaude.'.format(contador))

    cnes_nao_importados= []
    for estabelecimento in EstabelecimentoSaude.objects.all():
        try:
            estabelecimento.dados_cnes['NO_FANTASIA']
        except KeyError as e:
            cnes_nao_importados.append(estabelecimento.codigo_cnes)
            capture_exception(e)
            logger.debug('ERROR, não encontrado chave NO_FANTASIA cnes {}'.format(estabelecimento.codigo_cnes))
    EstabelecimentoSaude.objects.filter(codigo_cnes__in=cnes_nao_importados).delete()

def processar_associacoes_bairro(filename):
    dados_bairro = {}
    for bairro in Bairro.objects.all():
        dados_bairro[bairro.nome] = bairro

    df = pd.read_csv(filename, delimiter=',')
    dados = {}
    contador = 0
    for index, row in df.iterrows():
        bairro = dados_bairro[row['bairro__nome']]
        save_data = {
            'bairro': bairro,
        }
        associacao_bairro, created = AssociacaoBairro.objects.get_or_create(
            nome=row['nome'], defaults=save_data
        )
        contador += 1
    logger.debug('Importados {} AssociacaoBairro.'.format(contador))
    return dados

def processar_associacoes_nomes_estabelecimento(filename):
    df = pd.read_csv(filename, delimiter=',')
    contador = 0
    for index, row in df.iterrows():
        save_data = {
            'nome': row['nome'],
            # 'estabelecimento_saude': estabelecimento_saude,
        }
        AssociacaoNomeEstabelecimentoSaude.objects.get_or_create(
            codigo_cnes=str(row['codigo_cnes']), defaults=save_data
        )
        contador += 1
    logger.debug('Importados {} AssociacaoNomeEstabelecimentoSaude.'.format(contador))


def processar_municipios(filename_municipios, filename_populacao):
    #codigo_uf;nome_uf;municipio_id;municipio_codigo_ibge;municipio_nome
    df_municipios = pd.read_csv(filename_municipios, delimiter=';', dtype={'municipio_id': str, 'uf_codigo': str, 'municipio_codigo':str})
    df_populacao = pd.read_csv(filename_populacao, delimiter=';',
                                dtype={'uf_codigo': str, 'municipio_id': str, 'populacao': str})

    df = pd.merge(left=df_municipios, right=df_populacao, left_on='municipio_id', right_on='municipio_id')
    dados = {}
    contador = 0
    for index, row in df.iterrows():
        contador += 1
        estado, created = UnidadeFederativa.objects.get_or_create(codigo_ibge=row['uf_codigo'],
                                                                  defaults={
                                                                  'sigla': row['uf_sigla'],
                                                                  'nome': row['uf_nome']
                                                                  })
        try:
            valor = int(row['populacao'].replace('.', ''))
        except:
            valor = int(row['populacao'].split('(')[0].replace('.', ''))
        Municipio.objects.get_or_create(
                codigo_ibge = row['municipio_codigo'][:6],
                defaults= {
                    'codigo_ibge_estado': row['uf_codigo'],
                    'nome': row['municipio_nome'],
                    'estado': estado,
                    'quant_populacao': valor
                }
        )

    logger.debug('Importados {} Municípios.'.format(contador))
    return dados

def processar_populacao(filename, cls):
    df = pd.read_csv(filename, delimiter=';',
                               dtype={'nome': str, 'pop18':int})

    dados = {}
    contador = 0
    for index, row in df.iterrows():
        contador += 1
        quant = row['pop18']
        nome = row['nome'].upper()
        cls.objects.filter(nome=nome).update(quant_populacao=quant)
    logger.debug('Atualizando quantidades populacionais de {} {}.'.format(contador, cls.__name__))
    return dados

def processar_ufs(filename):
    #[{"coUF":"12","siglaUF":"AC","noUF":"Acre","coRegiaoGeografica":"1","noRegiaoGeografica":"Norte"}
    df = pd.read_json(filename)
    dados = {}
    contador = 0
    for index, row in df.iterrows():
        contador += 1
        UnidadeFederativa.objects.update_or_create(
                codigo_ibge = row['coUF'],
                defaults= {
                    'sigla': row['siglaUF'],
                    'nome': row['noUF'],
                }
        )
    logger.debug('Importados {} Municípios.'.format(contador))
    return dados



class Command(BaseCommand):
    help = 'Processar arquivos auxiliares'

    def handle(self, *args, **kwargs):
        importar_municipio_bairro_limbo()

        path_dir_fixtures = os.path.join(settings.BASE_DIR, 'base/fixtures')

        filename = os.path.join(path_dir_fixtures, 'ufs.json')
        processar_ufs(filename)

        filename = os.path.join(path_dir_fixtures, 'municipios.csv')
        filename_populacao = os.path.join(path_dir_fixtures, 'municipios_populacao.csv')
        processar_municipios(filename, filename_populacao)

        exportar_associacoes_nomes_estabelecimento_cnes(path_dir_fixtures)

        filename = os.path.join(path_dir_fixtures, 'associacao_nomes_estabelecimento.csv')
        processar_associacoes_nomes_estabelecimento(filename)

        filename = os.path.join(path_dir_fixtures, 'distritos.csv')
        dados_distritos = processar_distritos(filename)

        filename = os.path.join(path_dir_fixtures, 'distritos_populacoes.csv')
        processar_populacao(filename, Distrito)

        filename = os.path.join(path_dir_fixtures, 'bairros.csv')
        dados_bairro = processar_bairros(filename, dados_distritos)

        filename = os.path.join(path_dir_fixtures, 'bairros_populacoes.csv')
        processar_populacao(filename, Bairro)

        filename = os.path.join(path_dir_fixtures, 'habitacoes.csv')
        processar_habitacoes_bairros(filename, dados_bairro)

        filename = os.path.join(path_dir_fixtures, 'associacaobairro.csv')
        processar_associacoes_bairro(filename)

        filename = os.path.join(path_dir_fixtures, 'tb_estabelecimentos_rn.csv')
        processar_estabelecimento_saude(filename)

        filename = os.path.join(path_dir_fixtures, 'associacaooperadorcnes.csv')
        processar_associacoes_operadores(filename)


        # FIXME: retirar código quando sair do ambiente dev
        if not Usuario.objects.exists():
            su_cpf = '12345678909'
            su_password = get_random_string()
            Usuario.objects.create_superuser(cpf=su_cpf, nome='Super User', email='root@example.net', password=su_password)
            print('Superusercriado! username: {}, senha: {}'.format(su_cpf, su_password))

