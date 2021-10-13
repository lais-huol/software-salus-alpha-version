# Generated by Django 3.0.10 on 2020-09-23 18:21

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('base', '0036_auto_20200916_1028'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CID',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=255, unique=True, verbose_name='Código')),
                ('nome', models.CharField(max_length=255, unique=True, verbose_name='Nome')),
            ],
        ),
        migrations.CreateModel(
            name='Medicamento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255, unique=True, verbose_name='Nome')),
                ('solucao', models.CharField(max_length=255, verbose_name='Solução')),
                ('metodo', models.CharField(max_length=255, verbose_name='Método')),
            ],
        ),
        migrations.CreateModel(
            name='PlanoTerapeutico',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255, unique=True, verbose_name='Nome')),
                ('orientacao', models.TextField(verbose_name='Orientação')),
                ('qtd_doses', models.PositiveIntegerField(default=1)),
                ('invervalo_entre_doses_em_horas', models.PositiveIntegerField(default=0)),
                ('prazo_extra_em_horas', models.PositiveIntegerField(default=0)),
                ('cid', models.ManyToManyField(to='sifilis.CID')),
                ('medicamento', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='sifilis.Medicamento')),
                ('restrito_ao_usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Plano Terapêutico',
                'verbose_name_plural': 'Planos Terapêuticos',
                'unique_together': {('medicamento', 'qtd_doses', 'invervalo_entre_doses_em_horas', 'prazo_extra_em_horas')},
            },
        ),
        migrations.CreateModel(
            name='TipoExame',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255, unique=True, verbose_name='Nome')),
            ],
            options={
                'verbose_name': 'Tipo de Exame',
                'verbose_name_plural': 'Tipos de Exame',
            },
        ),
        migrations.CreateModel(
            name='TipoExameResultado',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255, verbose_name='Nome')),
                ('tipo_de_exame', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='sifilis.TipoExame')),
            ],
            options={
                'verbose_name': 'Possível Resultado para Tipo de Exame',
                'verbose_name_plural': 'Possíveis Resultados para Tipo de Exame',
                'unique_together': {('tipo_de_exame', 'nome')},
            },
        ),
        migrations.CreateModel(
            name='PlanoTerapeuticoPaciente',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('situacao', models.CharField(max_length=255, verbose_name='Situação')),
                ('paciente', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sifilis_planoterapeutico_set', to='base.PessoaFisica')),
                ('plano_terapeutico', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='sifilis.PlanoTerapeutico')),
            ],
        ),
        migrations.CreateModel(
            name='Exame',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_de_realizacao', models.DateTimeField(verbose_name='Data da realização')),
                ('observacoes', models.TextField(verbose_name='Observações')),
                ('paciente', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sifilis_exame_set', to='base.PessoaFisica')),
                ('resultado', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='sifilis.TipoExameResultado')),
            ],
        ),
        migrations.CreateModel(
            name='DoseAplicada',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('dose_aplicada_em', models.DateTimeField()),
                ('plano_terapeutico_paciente', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='sifilis.PlanoTerapeuticoPaciente')),
            ],
        ),
        migrations.CreateModel(
            name='Antecedente',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cid', models.ManyToManyField(to='sifilis.CID')),
                ('paciente', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='sifilis_antecedente_set', to='base.PessoaFisica')),
            ],
        ),
        migrations.CreateModel(
            name='Relacionamento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_de_relacionamento', models.CharField(max_length=255)),
                ('paciente', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='base.PessoaFisica')),
                ('pessoa', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='pessoanucleointimoset', to='base.PessoaFisica')),
            ],
            options={
                'unique_together': {('paciente', 'pessoa')},
            },
        ),
    ]
