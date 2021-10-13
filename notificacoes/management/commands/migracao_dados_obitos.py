from django.conf import settings
from django.core.management.base import BaseCommand

from django.apps.registry import apps
from base.rest_cns import get_dados
from base.utils import normalize_str
from notificacoes.models import TipoArquivo
from notificacoes.processar_notificacoes import ObterNotificacao

Bairro = apps.get_model('base', 'Bairro')
Municipio = apps.get_model('base', 'Municipio')
PessoaFisica = apps.get_model('base', 'PessoaFisica')
Obito = apps.get_model('notificacoes', 'Obito')
Notificacao = apps.get_model('notificacoes', 'Notificacao')



def importar_obitos_pacientes_internados():
    # We can't import the Person model  as it may be a newer
    # version than this migration expects. We use the historical version.
    qs_notificacoes_desfecho_obito = Notificacao.objects.filter(paciente_internado__tipo='O', paciente_internado__data_do_obito__isnull=False)

    print("QTD Notificações [ÓBITOS] com Pessoa Física {}".format(
        qs_notificacoes_desfecho_obito.filter(pessoa__isnull=False).count()))
    print("QTD Notificacões [ÓBITOS] sem Pessoa Física {}".format(
        qs_notificacoes_desfecho_obito.filter(pessoa__isnull=True).count()))

    qtd_registros_obitos_criados_com_pessoa_existente = 0
    qtd_registros_obitos_criados_sem_pessoa_existente = 0
    for notificacao in qs_notificacoes_desfecho_obito.filter(pessoa__isnull=False):
        registro_obito, criado = Obito.objects.update_or_create(pessoa=notificacao.pessoa,
                                                                data_do_obito=notificacao.paciente_internado.data_do_obito,
                                                                resultado_do_teste_covid_19= notificacao.paciente_internado.resultado_do_teste_covid_19,
                                                                )
        if criado:
            qtd_registros_obitos_criados_com_pessoa_existente += 1
            print("O registro de óbito id {} referente ao paciente {} foi criado".format(registro_obito.id, registro_obito.pessoa.nome))


    for notificacao in qs_notificacoes_desfecho_obito.filter(pessoa__isnull=True):
        print("O paciente {} NÃO tem Pessoa Fisica - CPF {} CNS {}".format(notificacao.dados.get("nome_completo"),  notificacao.dados.get("cpf"), notificacao.dados.get("cns")))
        cpf = notificacao.dados.get("cpf")
        cns = notificacao.dados.get("cns")
        dados_resposta_webservice_cns = None
        if cpf:
            dados_resposta_webservice_cns = get_dados(cpf)
        elif cns:
            dados_resposta_webservice_cns = get_dados(cns)

        if dados_resposta_webservice_cns:
            municipio_codigo_ibge = dados_resposta_webservice_cns.get("municipio", None)
            cpf = dados_resposta_webservice_cns.get("cpf")
            dados_pessoa = {"cep": dados_resposta_webservice_cns.get("cep", None),
                            "cns": dados_resposta_webservice_cns.get("cns"),
                            "cpf": cpf,
                            "sexo": dados_resposta_webservice_cns.get("sexo", None),
                            "email": None,
                            "bairro": dados_resposta_webservice_cns.get("bairro", None),
                            "logradouro": dados_resposta_webservice_cns.get("logradouro", None),
                            "complemento": dados_resposta_webservice_cns.get("complemento", None),
                            "nome": dados_resposta_webservice_cns.get("nome", None),
                            "telefone_celular": dados_resposta_webservice_cns.get("telefone", None),
                            "data_de_nascimento": dados_resposta_webservice_cns.get("data_de_nascimento", None),
                            "telefone_de_contato": dados_resposta_webservice_cns.get("telefone", None),
                            "municipio_de_residencia": Municipio.get_nome_by_ibge(codigo_ibge=municipio_codigo_ibge),
                            "municipio_cod_ibg": municipio_codigo_ibge,
                            "numero_res": dados_resposta_webservice_cns.get("numero", "sn")}


            if PessoaFisica.objects.filter(cpf=''.join(filter(str.isdigit, cpf))).exists():
                pessoa_fisica = PessoaFisica.objects.get(cpf=''.join(filter(str.isdigit, cpf)))
            else:
                pessoa_fisica, created = PessoaFisica.objects.update_or_create(cpf=''.join(filter(str.isdigit, cpf)), **dados_pessoa)

            if pessoa_fisica:
                registro_obito, obito_criado = Obito.objects.update_or_create(pessoa=pessoa_fisica,
                                                                        data_do_obito=notificacao.paciente_internado.data_do_obito,
                                                                        resultado_do_teste_covid_19=notificacao.paciente_internado.resultado_do_teste_covid_19
                                                                        )
                if obito_criado:
                    qtd_registros_obitos_criados_sem_pessoa_existente += 1
                    print("O registro de óbito id {} referente ao paciente {} foi criado".format(registro_obito.id,
                                                                                                 registro_obito.pessoa.nome))

    print("FIM")
    print("Foram criados {} registros de Óbitos para pacientes que JÁ POSSUIA PessoaFisica".format(qtd_registros_obitos_criados_com_pessoa_existente))
    print("Foram criados {} registros de PessoaFisica e Óbitos para pacientes que NÃO POSSUIA PessoaFisica".format(qtd_registros_obitos_criados_sem_pessoa_existente))


def atualizar_bairro_do_obito():
    _obter_notificacao = ObterNotificacao(TipoArquivo.ESUSVE_ARQUIVO_CSV)
    def get_bairro (dados_pessoa):
        nome = dados_pessoa['dados_monitoramento'].get('bairro')
        if dados_pessoa['dados_monitoramento']:
            if nome and (not dados_pessoa['notificacao__bairro__nome'] \
                    or normalize_str(nome) != normalize_str(dados_pessoa['notificacao__bairro__nome'])):
                cache_bairro = _obter_notificacao.tratar_bairro(nome)
                if cache_bairro and cache_bairro['nome'] != settings.BAIRRO_OUTROS:
                    return Bairro(pk=cache_bairro['pk'])

        if dados_pessoa['notificacao__bairro__pk'] and dados_pessoa['notificacao__bairro__nome'] != settings.BAIRRO_OUTROS:
            return Bairro(pk=dados_pessoa['notificacao__bairro__pk'])

        cache_bairro = _obter_notificacao.tratar_bairro(nome)
        if cache_bairro and cache_bairro['nome'] != settings.BAIRRO_OUTROS:
            return Bairro(pk=cache_bairro['pk'])
        return None

    qs = PessoaFisica.objects.filter(obito__isnull=False).values()
    for dados_pessoa in qs:
        bairro = get_bairro(dados_pessoa)
        Obito.objects.filter(pk=dados_pessoa['obito__pk']).update(bairro=bairro)



class Command(BaseCommand):
   def handle(self, *args, **kwargs):
       importar_obitos_pacientes_internados()
       atualizar_bairro_do_obito()
