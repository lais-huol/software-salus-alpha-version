from django.conf import settings
from django.core.management import BaseCommand

from base.alertas import Alerta
from base.caches import ControleCache
from base.extracao.rest_laiscep import recuperar_ceps
from base.extracao.scraping_imd import get_censo_leitos, baixar_pdf_censo_leitos_
from notificacoes.models import PacienteInternacao


class Command(BaseCommand):
    help = 'Carrega dados iniciais'

    def handle(self, *args, **kwargs):
        ControleCache.ceps().reset()
        ceps = recuperar_ceps()


