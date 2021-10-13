# Generated by Django 3.0.6 on 2020-05-29 04:28

from django.conf import settings
import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
    ]

    operations = [
        migrations.CreateModel(
            name='Usuario',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('cpf', models.CharField(max_length=11, primary_key=True, serialize=False, verbose_name='CPF')),
                ('nome', models.CharField(max_length=255, verbose_name='nome completo')),
                ('email', models.EmailField(max_length=254, verbose_name='e-mail')),
                ('telefone', models.CharField(max_length=20)),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'usuário',
            },
        ),
        migrations.CreateModel(
            name='Bairro',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Distrito',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='EstabelecimentoSaude',
            fields=[
                ('codigo_cnes', models.CharField(max_length=7, primary_key=True, serialize=False, verbose_name='código CNES')),
                ('dados_cnes', django.contrib.postgres.fields.jsonb.JSONField()),
                ('data_extracao', models.DateTimeField(null=True)),
                ('cpf_operador', models.CharField(max_length=11, null=True, verbose_name='CPF do operador ESUS-VE')),
            ],
        ),
        migrations.CreateModel(
            name='Municipio',
            fields=[
                ('codigo_ibge', models.CharField(max_length=6, primary_key=True, serialize=False, verbose_name='código IBGE')),
                ('codigo_ibge_estado', models.CharField(max_length=2, verbose_name='código IBGE do estado')),
                ('nome', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='PerfilEstabelecimentoSaude',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('estabelecimento_saude', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='base.EstabelecimentoSaude')),
                ('usuario', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='perfil_estabelecimento', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='PerfilDistrito',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('distrito', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.Distrito')),
                ('usuario', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='perfil_distrito', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='HabitacoesBairro',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255)),
                ('tipo', models.CharField(choices=[['C', 'Conjunto Habitacionais'], ['L', 'Loteamento']], max_length=1, null=True)),
                ('bairro', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.Bairro')),
            ],
        ),
        migrations.AddField(
            model_name='distrito',
            name='municipio',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.Municipio'),
        ),
        migrations.AddField(
            model_name='bairro',
            name='distrito',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='base.Distrito'),
        ),
        migrations.AddField(
            model_name='bairro',
            name='municipio',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.Municipio'),
        ),
        migrations.CreateModel(
            name='AssociacaoBairro',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=255, unique=True)),
                ('bairro', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='base.Bairro')),
            ],
        ),
    ]
