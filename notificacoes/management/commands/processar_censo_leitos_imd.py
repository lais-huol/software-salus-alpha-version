import datetime
import logging
from django.conf import settings
from django.core.management import BaseCommand

from base.alertas import Alerta
from base.extracao.scraping_imd import get_censo_leitos, baixar_pdf_censo_leitos_
from notificacoes.models import PacienteInternacao

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Carrega dados iniciais'

    def handle(self, *args, **kwargs):
        mensagem_retorno = PacienteInternacao.processar_dados_censo_leitos_imd()
        logger.debug(mensagem_retorno)

