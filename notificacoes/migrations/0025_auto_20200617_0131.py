# Generated by Django 3.0.7 on 2020-06-17 04:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0024_auto_20200617_0001'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificacao',
            name='data',
            field=models.DateField(null=True, verbose_name='Data da Notificação'),
        ),
    ]
