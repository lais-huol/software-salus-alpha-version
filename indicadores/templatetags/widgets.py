import datetime
from django import template

register = template.Library()


@register.inclusion_tag('indicadores/widget_tag.html', takes_context=False)
def render_widget(cor, titulo, valor=None, icone=None, extras=None):
    return {
        'titulo': titulo,
        'valor': valor,
        'icone': icone,
        'cor': cor,
        'extras': extras,
    }
