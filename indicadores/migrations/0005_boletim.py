# Generated by Django 3.0.7 on 2020-07-02 13:53

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('indicadores', '0004_auto_20200702_0931'),
    ]

    operations = [
        migrations.CreateModel(
            name='Boletim',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255)),
                ('dados', django.contrib.postgres.fields.jsonb.JSONField()),
                ('modelo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='indicadores.ModeloPainel')),
            ],
        ),
    ]