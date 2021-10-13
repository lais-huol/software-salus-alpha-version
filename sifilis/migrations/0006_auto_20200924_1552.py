# Generated by Django 3.0.10 on 2020-09-24 18:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sifilis', '0005_auto_20200923_2146'),
    ]

    operations = [
        migrations.AlterField(
            model_name='planoterapeuticopaciente',
            name='situacao',
            field=models.CharField(choices=[('Em andamento', 'em andamento'), ('Finalizado', 'finalizado'), ('Suspenso', 'suspenso')], default='Em andamento', max_length=255, verbose_name='Situação'),
        ),
    ]
