# Generated by Django 3.0.7 on 2020-07-29 20:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0026_remove_estabelecimentosaude_cpf_operador'),
    ]

    operations = [
        migrations.AlterField(
            model_name='associacaobairro',
            name='bairro',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='base.Bairro'),
        ),
        migrations.AlterField(
            model_name='habitacoesbairro',
            name='bairro',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='base.Bairro'),
        ),
    ]