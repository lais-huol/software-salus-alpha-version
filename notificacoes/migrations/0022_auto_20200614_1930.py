# Generated by Django 3.0.7 on 2020-06-14 22:30

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0021_notificacao_data'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='monitoramento',
            options={'ordering': ['-id']},
        ),
        migrations.AddField(
            model_name='monitoramento',
            name='data_de_investigacao',
            field=models.DateField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
