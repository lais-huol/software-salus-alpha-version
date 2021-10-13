from django.apps import AppConfig
from django.urls import reverse_lazy

icon = 'icons/covid.png'
title = 'Notificações COVID'
url_pessoa = 'notificacoes:listar_por_pessoa'

class NotificacoesConfig(AppConfig):
    name = 'notificacoes'

    def ready(self):
        pass
