# Generated by Django 3.0.7 on 2020-06-10 15:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0016_monitoramento_pessoa'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificacao',
            name='numero_gal',
            field=models.CharField(max_length=12, null=True, verbose_name='requisição do GAL'),
        ),
    ]
