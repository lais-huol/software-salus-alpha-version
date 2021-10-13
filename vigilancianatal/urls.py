from django.apps import apps
from django.conf import settings
from django.conf.urls import url
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.views.generic import RedirectView
from notifications import urls as notifications_urls

urlpatterns = [
    path('accounts/', include('django.contrib.auth.urls')),
    path('admin/', admin.site.urls),
    path('api/', include('api.urls', namespace='api')),
    path('base/', include('base.urls', namespace='base')),
    path('indicadores/', include('indicadores.urls', namespace='indicadores')),
    path('', RedirectView.as_view(url=reverse_lazy('indicadores:inicio'), permanent=False)),
    url('^inbox/notifications/', include(notifications_urls, namespace='notifications')),
    path('djrichtextfield/', include('djrichtextfield.urls')),
    path("admin/", include('loginas.urls')),
    path("administracao/", include('administracao.urls', namespace='administracao')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

for app in settings.MODULE_APPS:
    App = apps.get_app_config(app)
    name = App.name
    urlpatterns.append(path(f'{name}/', include(f'{name}.urls', namespace=name)),)


def trigger_error(request):
    division_by_zero = 1 / 0


urlpatterns += [path('sentry-debug/', trigger_error)]
