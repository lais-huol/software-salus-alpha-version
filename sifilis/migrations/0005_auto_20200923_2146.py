# Generated by Django 3.0.10 on 2020-09-24 00:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sifilis', '0004_auto_20200923_2146'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='planoterapeutico',
            unique_together={('nome', 'medicamento', 'orientacao', 'qtd_doses', 'invervalo_entre_doses_em_horas', 'prazo_extra_em_horas')},
        ),
    ]
