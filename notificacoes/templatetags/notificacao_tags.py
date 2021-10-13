import re
from datetime import datetime

from django import template
from urllib.parse import urlencode

import json

from notificacoes.models import TipoFonteDados

register = template.Library()




@register.filter
def tipo_fonte_dados(value):
    tipo_fonte_dados = {x: y for x, y in TipoFonteDados.__dict__['TIPO']}
    return tipo_fonte_dados[value]
