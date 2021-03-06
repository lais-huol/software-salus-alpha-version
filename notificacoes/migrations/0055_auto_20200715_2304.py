# Generated by Django 3.0.7 on 2020-07-16 02:04

import django.contrib.postgres.fields.jsonb
from django.db import migrations
from django.db.models import Count


def remove_duplicatas(apps, schema_editor):
    HistoricoNotificacaoAtualizacao = apps.get_model("notificacoes", "HistoricoNotificacaoAtualizacao")
    qs = HistoricoNotificacaoAtualizacao.objects.values('dados_esusve_atualizados_em__date', 'notificacao').annotate(
        quant=Count('id')).filter(quant__gt=1)
    for h in qs:
        HistoricoNotificacaoAtualizacao.objects.filter(notificacao=h['notificacao']).first().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0054_historiconotificacaoatualizacao_dados_alterado'),
    ]

    operations = [
        migrations.RunPython(remove_duplicatas),
        migrations.RemoveField(
            model_name='historiconotificacaoatualizacao',
            name='dados_esusve_alterado',
        ),
        migrations.AlterField(
            model_name='historiconotificacaoatualizacao',
            name='dados_alterado',
            field=django.contrib.postgres.fields.jsonb.JSONField(default={}),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name='historiconotificacaoatualizacao',
            unique_together={('notificacao', 'data')},
        ),
        migrations.RemoveField(
            model_name='historiconotificacaoatualizacao',
            name='dados_esusve_atualizados_em',
        ),
    ]
