# Generated by Django 3.0.7 on 2020-07-06 22:18

from django.db import migrations, models
import django.db.models.deletion

def cria_unidade_federativa(apps, schema_editor):
    UnidadeFederativa = apps.get_model('base', 'UnidadeFederativa')

    UnidadeFederativa.objects.create(codigo_ibge='24', nome='Rio Grande do Norte')
    UnidadeFederativa.objects.create(codigo_ibge='99', nome='OUTROS')


def municipio_set_estado_outros(apps, schema_editor):
    Municipio = apps.get_model('base', 'Municipio')
    UnidadeFederativa = apps.get_model('base', 'UnidadeFederativa')

    estado = UnidadeFederativa.objects.get(codigo_ibge='99')
    Municipio.objects.filter(codigo_ibge='999999').update(estado=estado)


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0023_auto_20200630_2029'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnidadeFederativa',
            fields=[
                ('codigo_ibge', models.CharField(max_length=2, primary_key=True, serialize=False, verbose_name='código IBGE')),
                ('nome', models.CharField(max_length=255)),
            ],
        ),
        migrations.RunPython(cria_unidade_federativa),
        migrations.AddField(
            model_name='municipio',
            name='estado',
            field=models.ForeignKey(default=24, on_delete=django.db.models.deletion.CASCADE, to='base.UnidadeFederativa'),
            preserve_default=False,
        ),
        migrations.RunPython(municipio_set_estado_outros)
    ]