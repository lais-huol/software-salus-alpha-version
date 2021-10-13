from django.apps import AppConfig

icon = 'icons/sifilis.png'
title = 'Sífilis: gestor de casos'
url_pessoa = 'sifilis:listar_por_pessoa'


class SifilisConfig(AppConfig):
    name = 'sifilis'
