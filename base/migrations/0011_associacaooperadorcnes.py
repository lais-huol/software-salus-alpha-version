# Generated by Django 3.0.7 on 2020-06-04 14:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0010_auto_20200604_0324'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssociacaoOperadorCNES',
            fields=[
                ('cpf', models.CharField(max_length=11, primary_key=True, serialize=False, verbose_name='CPF')),
                ('estabelecimento_saude', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='base.EstabelecimentoSaude')),
            ],
        ),
    ]