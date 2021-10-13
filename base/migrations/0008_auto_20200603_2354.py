# Generated by Django 3.0.7 on 2020-06-04 02:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0007_merge_20200603_2302'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pessoafisica',
            name='cns',
            field=models.CharField(max_length=15, null=True, unique=True, verbose_name='CNS'),
        ),
        migrations.AlterField(
            model_name='pessoafisica',
            name='cpf',
            field=models.CharField(max_length=11, null=True, unique=True, verbose_name='CPF'),
        ),
    ]