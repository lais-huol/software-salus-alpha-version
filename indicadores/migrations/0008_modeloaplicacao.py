# Generated by Django 3.0.7 on 2020-07-03 00:49

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('indicadores', '0007_auto_20200702_1202'),
    ]

    operations = [
        migrations.CreateModel(
            name='ModeloAplicacao',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255)),
                ('data', models.DateField()),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('dados', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True)),
                ('modelo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='indicadores.ModeloPainel')),
            ],
            options={
                'verbose_name_plural': 'modelos aplicados',
            },
        ),
    ]
