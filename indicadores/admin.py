from django.contrib import admin
from . import models
# Register your models here.
from .forms import ModeloPainelForm


class ModeloBoletimEpidemiologicoAdmin(admin.ModelAdmin):
  form = ModeloPainelForm


admin.site.register(models.ModeloPainel, ModeloBoletimEpidemiologicoAdmin)
admin.site.register(models.ModeloAplicacao)
