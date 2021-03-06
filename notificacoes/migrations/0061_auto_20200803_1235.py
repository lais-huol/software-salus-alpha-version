# Generated by Django 3.0.7 on 2020-08-03 15:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0060_auto_20200720_2312'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificacao',
            name='data_do_encerramento',
            field=models.DateField(null=True, verbose_name='Data do Encerramento'),
        ),
        migrations.AddField(
            model_name='notificacao',
            name='encerrada_em',
            field=models.DateTimeField(null=True, verbose_name='Encerrada em'),
        ),
        migrations.AddField(
            model_name='notificacao',
            name='encerrada_motivo',
            field=models.PositiveIntegerField(choices=[[1, 'Cura'], [2, 'Óbito']], null=True, verbose_name='Motivo do Encerramento'),
        ),
        migrations.AddField(
            model_name='notificacao',
            name='encerrada_observacoes',
            field=models.TextField(null=True, verbose_name='Observações do Encerramento'),
        ),
        migrations.AddField(
            model_name='notificacao',
            name='encerrada_por',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL, verbose_name='Encerrado por'),
        ),
        migrations.AlterField(
            model_name='notificacao',
            name='tipo_motivo_desativacao',
            field=models.PositiveIntegerField(choices=[[1, 'Município de residência externo'], [2, 'Evolução do caso igual a cancelado'], [3, 'motivo desconhecido'], [8, 'Nome completo vazio'], [4, 'Notificação repetida'], [5, 'Notificação similar'], [6, 'Bairro outros'], [7, 'Associações de bairro pertecente a outros, mas localidade obtida do CEP pertence a cidade']], null=True),
        ),
    ]
