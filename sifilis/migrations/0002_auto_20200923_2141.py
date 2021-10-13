# Generated by Django 3.0.10 on 2020-09-24 00:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sifilis', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cid',
            options={'ordering': ['codigo']},
        ),
        migrations.AlterModelOptions(
            name='medicamento',
            options={'ordering': ['nome', 'solucao', 'metodo']},
        ),
        migrations.AlterModelOptions(
            name='planoterapeutico',
            options={'ordering': ['nome'], 'verbose_name': 'Plano Terapêutico', 'verbose_name_plural': 'Planos Terapêuticos'},
        ),
        migrations.AlterField(
            model_name='planoterapeutico',
            name='nome',
            field=models.CharField(max_length=255, verbose_name='Nome'),
        ),
    ]
