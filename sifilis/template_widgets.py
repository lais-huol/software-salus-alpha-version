from django.template.loader import render_to_string


def menu(request):
    return render_to_string('sifilis/widgets/menu.html')


