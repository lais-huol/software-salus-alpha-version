# Generated by Django 3.0.7 on 2020-07-13 20:07

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0050_auto_20200711_2132'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricoNotificacaoAtualizacao',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dados_esusve_alterado', django.contrib.postgres.fields.jsonb.JSONField(default=None, null=True)),
                ('dados_esusve_atualizados_em', models.DateTimeField(null=True)),
                ('notificacao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='notificacoes.Notificacao')),
            ],
            options={
                'verbose_name': 'Histórico de atualização de notificação',
                'verbose_name_plural': 'Históricos de atualizações de notificações',
                'unique_together': {('notificacao', 'dados_esusve_atualizados_em')},
            },
        ),
    ]