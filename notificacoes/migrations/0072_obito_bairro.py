# Generated by Django 3.0.7 on 2020-08-24 17:24

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0032_auto_20200824_1424'),
        ('notificacoes', '0071_auto_20200824_1225'),
    ]

    operations = [
        migrations.AddField(
            model_name='obito',
            name='bairro',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='base.Bairro'),
        ),
    ]
