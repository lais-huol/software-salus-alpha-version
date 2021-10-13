from django.core.management.base import BaseCommand
from django.utils import timezone
from memory_profiler import profile

from base.caches import ControleCache
from indicadores.indicadores import *
from notificacoes.models import Notificacao, UploadImportacao, TipoArquivo
from notificacoes.processar_notificacoes import ObterNotificacaoEsusveCSV, ObterNotificacaoEsusveAPI, \
    ObterNotificacaoSivepGripeDBF

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Reprocessar a última notificação'

    def add_arguments(self, parser):
        parser.add_argument('--refazer-ativas', action='store_true', help='Se incluso, refaz as notificações desativadas')
        parser.add_argument('--reprocessar', action='store_true', help='Se incluso, reprocessa o último arquivo independente do status processado')
        parser.add_argument('--sivep-gripe', action='store_true',
                            help='Processa os óbitos da base do SIVEP Gripe')

    def processar_notificacoes(cls, qs_upload_importacao=None, reprocessar=False):
        if qs_upload_importacao is None:
            qs_upload_importacao = UploadImportacao.objects.filter(processado=False).order_by('datahora')

        upload_importacao = None
        if qs_upload_importacao.exists():
            upload_importacao = qs_upload_importacao[0]

        if upload_importacao and upload_importacao.tipo == TipoArquivo.ESUSVE_ARQUIVO_CSV:
            obter_notificacao = ObterNotificacaoEsusveCSV(reprocessar, qs_upload_importacao)
        else:
            obter_notificacao = ObterNotificacaoEsusveAPI(reprocessar)
        obter_notificacao._cache_status_processamento.reset()
        return obter_notificacao.processar()

    def handle(self, *args, **options):
        # print(Notificacao.recuperar_notificacoes_similares())
        # Notificacao.processar_notificacoes_similares()
        # ControleCache.notificacoes_similares().remove(['202089887',])
        # informacoes_repetidas, ac, rc, snomes_chaves = Notificacao.recuperar_notificacoes_similares()
        # import ipdb; ipdb.set_trace()
        # Notificacao._desativar_notificacoes_iguais()
        # Notificacao.processar_notificacoes_alteradas(timezone.now().date())
        # import sys; sys.exit()

        # print(Notificacao.processar_csv())

        # Notificacao.recuperar_notificacoes_similares()
        # breakpoint()
        # Notificacao.definir_principais(numeros_requisicoes_principais = [['49953', '151971'], ['104621'], ['57575'], ['46086']])

        # ObterNotificacaoSivepGripeDBF()._processar_notificacoes_similares()
        # import sys; sys.exit()

        processar_sivep_gripe = options['sivep_gripe']
        refazer_ativas = options['refazer_ativas']
        reprocessar = options['reprocessar']

        if processar_sivep_gripe:
            obter_notificacao = ObterNotificacaoSivepGripeDBF()
            obter_notificacao._cache_status_processamento.reset()
            print(obter_notificacao.processar())
            import sys;sys.exit()

        qs_upload_importacao = UploadImportacao.objects.filter(processado=reprocessar).order_by('-datahora')

        if not qs_upload_importacao.exists():
            qs_upload_importacao = None
        resumo = self.processar_notificacoes(qs_upload_importacao=qs_upload_importacao, reprocessar=refazer_ativas)
        logger.debug(resumo)
