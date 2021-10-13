from importlib import import_module

from django.apps import apps
from django.conf import settings

from base.templatetags.base_tags import get_branch_full
from django.utils.functional import lazy

def processor(request):
    return {
        'IMPORTAR_NOTIFICACOES_VIA_CSV': settings.IMPORTAR_NOTIFICACOES_VIA_CSV,
        'IMPORTAR_NOTIFICACOES_VIA_API': settings.IMPORTAR_NOTIFICACOES_VIA_API,
        'DEV': 'master' not in get_branch_full()
    }


def menus(request):
    def get_all_menus(request):
        from django.conf import settings
        widgets_list = []
        for app in settings.MODULE_APPS:
            try:
                mod = import_module(app+'.template_widgets')
                widgets_list.append(mod.menu)
            except ImportError:
                pass
            except AttributeError:
                pass
        return list(map(lambda w: lazy(w, str)(request), widgets_list))

    return {'menus': lazy(get_all_menus, list)(request)}


def active_apps(request):
    def get_apps():
        from django.conf import settings
        app_list = []
        for app in settings.MODULE_APPS:
            try:
                mod = import_module(app+'.apps')

                app_list.append(mod.__dict__)
            except ImportError:
                pass
            except AttributeError:
                pass
        return list(app_list)

    return {'apps': lazy(get_apps, list)}