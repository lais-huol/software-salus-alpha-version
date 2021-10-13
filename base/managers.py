from django.conf import settings
from django.db import models


class BairrosAtivosManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(municipio__codigo_ibge=settings.CODIGO_IBGE_MUNICIPIO_BASE)


class DistritosAtivosManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(municipio__codigo_ibge=settings.CODIGO_IBGE_MUNICIPIO_BASE)


class MunicipiosAtivosManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(codigo_ibge=settings.CODIGO_IBGE_MUNICIPIO_BASE)
