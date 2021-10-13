# Generated by Django 3.0.7 on 2020-09-01 13:21
import django
from django.db import migrations, models

def atualizar_fks(apps, schema_editor):
    Notificacao = apps.get_model('notificacoes', 'Notificacao')
    HistoricoNotificacaoAtualizacao = apps.get_model('notificacoes', 'HistoricoNotificacaoAtualizacao')
    HistoricoNotificacaoAssociacaoBairroOutros = apps.get_model('notificacoes', 'HistoricoNotificacaoAssociacaoBairroOutros')
    Monitoramento = apps.get_model('notificacoes', 'Monitoramento')

    print('Criando cache para fazer o mapeando do pk')
    mapeamento_pk = {}
    for numero, id in Notificacao.objects.values_list('numero', 'id'):
        mapeamento_pk[numero] = id  # map old primary keys to new

    print('Atualizando fk HistoricoNotificacaoAtualizacao.notificacao')
    for fk_model in HistoricoNotificacaoAtualizacao.objects.all():
        if fk_model.notificacao_id:
            fk_model.notificacao_id = mapeamento_pk[fk_model.notificacao_id]
            fk_model.save()

    print('Atualizando fk HistoricoNotificacaoAssociacaoBairroOutros.notificacao')
    for fk_model in HistoricoNotificacaoAssociacaoBairroOutros.objects.all():
        if fk_model.notificacao_id:
            fk_model.notificacao_id = mapeamento_pk[fk_model.notificacao_id]
            fk_model.save()

    print('Atualizando fk Monitoramento.notificacao')
    for fk_model in Monitoramento.objects.all():
        if fk_model.notificacao_id:
            fk_model.notificacao_id = mapeamento_pk[fk_model.notificacao_id]
            fk_model.save()

    print('Atualizando fk Notificacao.notificacao_principal')
    for fk_model in Notificacao.objects.all():
        if fk_model.notificacao_principal_id:
            fk_model.notificacao_principal_id = mapeamento_pk[fk_model.notificacao_principal_id]
            fk_model.save()

class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0077_notificacao_id'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificacao',
            name='id',
            field=models.IntegerField(default=0, unique=True),
        ),
        # remove as foreign key constraint
        migrations.AlterField(
            model_name='HistoricoNotificacaoAtualizacao',
            name='notificacao',
            field=models.ForeignKey(to='notificacoes.Notificacao', on_delete=django.db.models.deletion.CASCADE, blank=True, null=True, db_constraint=False)
        ),
        migrations.AlterField(
            model_name='HistoricoNotificacaoAssociacaoBairroOutros',
            name='notificacao',
            field=models.ForeignKey(to='notificacoes.Notificacao', on_delete=django.db.models.deletion.CASCADE, blank=True, null=True, db_constraint=False)
        ),
        migrations.AlterField(
            model_name='Monitoramento',
            name='notificacao',
            field=models.ForeignKey(to='notificacoes.Notificacao', on_delete=django.db.models.deletion.CASCADE, blank=True, null=True, db_constraint=False)
        ),
        migrations.AlterField(
            model_name='Notificacao',
            name='notificacao_principal',
            field=models.ForeignKey(to='notificacoes.Notificacao', on_delete=django.db.models.deletion.SET_NULL, blank=True, null=True, db_constraint=False)
        ),
        #Atualiza as referências
        migrations.RunPython(atualizar_fks),

        # atualiza campo  varchar para integer, exclui index
        migrations.AlterField(
            model_name='HistoricoNotificacaoAtualizacao',
            name='notificacao',
            field=models.IntegerField()
        ),
        migrations.AlterField(
            model_name='HistoricoNotificacaoAssociacaoBairroOutros',
            name='notificacao',
            field=models.IntegerField()
        ),
        migrations.AlterField(
            model_name='Monitoramento',
            name='notificacao',
            field=models.IntegerField()
        ),
        migrations.AlterField(
            model_name='Notificacao',
            name='notificacao_principal',
            field=models.IntegerField(blank=True, null=True)
        ),

    ]