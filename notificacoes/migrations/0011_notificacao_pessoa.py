# Generated by Django 3.0.7 on 2020-06-04 06:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0010_auto_20200604_0324'),
        ('notificacoes', '0010_remove_notificacao_pessoa'),
    ]

    operations = [
        migrations.AddField(
            model_name='notificacao',
            name='pessoa',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='base.PessoaFisica'),
        ),
    ]
