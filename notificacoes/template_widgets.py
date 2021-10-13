from django.contrib.auth.context_processors import auth
from django.template.loader import render_to_string


def menu(request):
    return render_to_string('notificacoes/widgets/menu.html', auth(request))


