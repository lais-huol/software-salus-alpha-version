# Generated by Django 3.0.6 on 2020-06-03 02:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0004_delete_pacienteinternacao'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssociacaoNomeEstabelecimentoSaude',
            fields=[
                ('codigo_cnes', models.CharField(max_length=7, primary_key=True, serialize=False, verbose_name='código CNES')),
                ('nome', models.CharField(max_length=255)),
                ('estabelecimento_saude', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='base.EstabelecimentoSaude')),
            ],
        ),
    ]