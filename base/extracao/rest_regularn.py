import json
import os
from django.conf import settings
import pandas as pd

import logging
logger = logging.getLogger(__name__)

URL = 'http://regulacao.saude.rn.gov.br/'

def get_solicitacoes():
    logger.info('Obtendo dados RegulaRN: Fonte {} ...'.format(URL))
    filename = os.path.join(settings.REGULARN_PATH)
    with open(filename) as f:
        dados = json.loads(f.read())
    return dados


