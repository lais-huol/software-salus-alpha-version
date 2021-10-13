from django.contrib.postgres.fields import JSONField
from django.db import models
from djrichtextfield.models import RichTextField

from indicadores import boletim_template

CHOICE_BOLETIM = 'boletim'
CHOICE_SALA_SITUACAO = 'sala_situacao'
CHOICE_PUBLICO = 'publico'
CHOICE_OUTRO = 'outro'


class ModeloPainel(models.Model):
    CHOICES_TIPO = [
        (CHOICE_BOLETIM, 'Boletim'),
        (CHOICE_SALA_SITUACAO, 'Sala de situação'),
        (CHOICE_PUBLICO, 'Painél público'),
        (CHOICE_OUTRO, 'Outro'),
    ]

    nome = models.CharField(max_length=255)
    tipo = models.CharField(choices=CHOICES_TIPO, max_length=100, default=CHOICE_OUTRO)
    conteudo = RichTextField()

    def render(self, context):
        env = boletim_template.get_env()
        template = env.from_string(self.conteudo)

        return template.render(context)

    def vars(self):
        return boletim_template.get_vars(boletim_template.get_env(), self.conteudo)

    def __str__(self):
        return self.nome

    @property
    def esta_sendo_usado(self):
        usado = ModeloPainel.objects.filter(id=self.id).exclude(modeloaplicacao__isnull=True).count()
        return True if usado else False

    class Meta:
        verbose_name = 'modelo de painel'
        verbose_name_plural = 'modelos de painel'


class ModeloAplicacao(models.Model):
    nome = models.CharField(max_length=255)
    modelo = models.ForeignKey('ModeloPainel', on_delete=models.PROTECT)
    criado_em = models.DateTimeField(auto_now_add=True)
    dados = JSONField(null=True, blank=True)

    class Meta:
        verbose_name = 'modelo aplicado'
        verbose_name_plural = 'modelos aplicados'
