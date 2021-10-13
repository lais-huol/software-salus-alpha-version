# Generated by Django 3.0.7 on 2020-07-08 14:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0026_remove_estabelecimentosaude_cpf_operador'),
        ('notificacoes', '0043_auto_20200707_1505'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificacao',
            name='municipio_ocorrencia',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='municipio_ocorrencia', to='base.Municipio', verbose_name='Município de ocorrência da Notificação'),
        ),
        migrations.AddField(
            model_name='notificacao',
            name='municipio_residencia',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='municipio_residencia', to='base.Municipio', verbose_name='Município de residência'),
        ),
        migrations.AddField(
            model_name='notificacao',
            name='tipo_motivo_desativacao',
            field=models.PositiveIntegerField(choices=[[0, 'Município de residência externo'], [1, 'Evolução do caso igual a cancelado'], [2, 'Nome completo vazio'], [3, 'Notificação repetida'], [4, 'Notificação similar'], [5, 'Bairro outros']], null=True),
        ),
        migrations.CreateModel(
            name='HistoricoNotificacaoAssociacaoBairroOutros',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('confirmado', models.BooleanField(default=False)),
                ('bairro', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.Bairro')),
                ('notificacao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='notificacoes.Notificacao')),
            ],
        ),
    ]