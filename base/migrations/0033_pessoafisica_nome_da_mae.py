# Generated by Django 3.0.7 on 2020-08-26 21:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0032_auto_20200824_1424'),
    ]

    operations = [
        migrations.AddField(
            model_name='pessoafisica',
            name='nome_da_mae',
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
