# Generated by Django 3.0.7 on 2020-08-24 12:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0069_merge_20200824_0926'),
    ]

    operations = [
        migrations.AlterField(
            model_name='uploadimportacao',
            name='tipo',
            field=models.PositiveIntegerField(choices=[[0, 'ESUS-VE NOTIFICA CSV'], [1, 'ESUS-VE NOTIFICA API'], [2, 'SIVEP GRIPE DBF'], [3, 'SIVEP GRIPE API']], default=0),
        ),
    ]