# Generated by Django 3.0.7 on 2020-08-24 17:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0031_auto_20200824_1325'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pessoafisica',
            name='nome',
            field=models.CharField(default='', max_length=80),
            preserve_default=False,
        ),
    ]
