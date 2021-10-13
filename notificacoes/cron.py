
import requests
from django.conf import settings
from django_cron import CronJobBase, Schedule

from indicadores.paineis import PainelPublico
from notificacoes.processar_notificacoes import ObterNotificacaoEsusveAPI, ObterNotificacaoEsusveCSV
from .models import Notificacao, PacienteInternacao
import logging
logger = logging.getLogger(__name__)

class ProcessarNotificacoesAPICronJob(CronJobBase):
    RUN_AT_TIMES = ['06:00', '11:00', '17:00']
    RETRY_AFTER_FAILURE_MINS = 5

    schedule = Schedule(run_at_times=RUN_AT_TIMES, retry_after_failure_mins=RETRY_AFTER_FAILURE_MINS)
    code = 'notificacoes.ProcessarNotificacoesCronJob'

    def do(self):
        logger.debug("Iniciando processamento via API")
        obter_notificacao = ObterNotificacaoEsusveAPI(reprocessar=False)
        return str(obter_notificacao.processar())


class ProcessarNotificacoesCSVCronJob(CronJobBase):
    RUN_EVERY_MINS = 5
    RETRY_AFTER_FAILURE_MINS = 5

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS, retry_after_failure_mins=RETRY_AFTER_FAILURE_MINS)
    code = 'notificacoes.ProcessarNotificacoesCronJob'

    def do(self):
        logger.debug("Iniciando processamento via CSV")
        obter_notificacao = ObterNotificacaoEsusveCSV(reprocessar=False, qs_upload_importacao=None)
        return str(obter_notificacao.processar())


class ProcessarDadosCensoLeitosImdCronJob(CronJobBase):
    RUN_EVERY_MINS = 60
    RETRY_AFTER_FAILURE_MINS = 10

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS, retry_after_failure_mins=RETRY_AFTER_FAILURE_MINS)
    code = 'notificacoes.ProcessarDadosCensoLeitosImdCronJob'

    def do(self):
        mensagem = PacienteInternacao.processar_dados_censo_leitos_imd()
        return '\n'.join(mensagem)


class DefinirCnesReferenciaCronJob(CronJobBase):
    RUN_EVERY_MINS = 5

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'notificacoes.DefinirCnesReferenciaCronJob'

    def do(self):
        return 'Definidos CNES de referência de {} notificações'.format(Notificacao.definir_cnes_referencia())


class DefinirPessoaNaNotificacaoCronJob(CronJobBase):
    RUN_EVERY_MINS = 120

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'notificacoes.DefinirPessoaNaNotificacaoCronJob'

    def do(self):
        return 'Definidas pessoas de {} notificações'.format(Notificacao.definir_pessoa(api_sleep_time=1))


class CachePainelPublicoCronJob(CronJobBase):
    RUN_EVERY_MINS = 60

    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    code = 'notificacoes.CachePainelPublicoCronJob'

    def do(self):
        PainelPublico._reset_cache()
        url = 'http://{}/indicadores/painel_publico'.format(settings.ALLOWED_HOSTS[0])
        response = requests.get(url)
        return 'URL {} requisitada para forçar cache, response: {}'.format(url, response)
