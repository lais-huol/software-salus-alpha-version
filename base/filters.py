from base.models import Bairro
from notificacoes.models import Notificacao
import django_filters


class BairroFilter(django_filters.FilterSet):
    class Meta:
        model = Bairro
        fields = ['nome', 'municipio', ]

class NotificacaoFilter(django_filters.FilterSet):
    class Meta:
        model = Notificacao
        fields = ['bairro', ]