import csv
import os

from django.conf import settings

from sifilis.models import CID, PlanoTerapeutico, Medicamento, TipoExame, TipoExameResultado


def importar_dados_iniciais():

    horas_por_unidade = {
        'hora': 1,
        'dia': 24,
        'semana': 24*7,
    }

    cids = csv.DictReader(open(os.path.join(settings.BASE_DIR, 'sifilis/dados_iniciais/cids_sifilis.csv'), 'r'))
    for i in cids:
        CID.objects.get_or_create(codigo=i['codigo'], nome=i['nome'])

    planos = csv.DictReader(
        open(os.path.join(settings.BASE_DIR, 'sifilis/dados_iniciais/plano_terapeutico.csv'), 'r'),
    )
    for i in planos:
        medicamento, _ = Medicamento.objects.get_or_create(
            nome=i['medicamento'],
            solucao=i['solucao'],
            metodo=i['metodo'],
        )
        invervalo_entre_doses_em_horas = int(i['intervalo_doses']) * horas_por_unidade[i['und_intervalo_doses']]
        prazo_extra_em_horas = int(i['prazo_extra']) * horas_por_unidade[i['und_prazo']]
        obj, _ = PlanoTerapeutico.objects.get_or_create(
            nome=i['tratamento'],
            medicamento=medicamento,
            orientacao=i['orientacao'],
            qtd_doses=i['qtde_doses'],
            invervalo_entre_doses_em_horas=invervalo_entre_doses_em_horas,
            prazo_extra_em_horas=prazo_extra_em_horas,
        )
        obj.cid.add(CID.objects.get(codigo=i['cid']),)

    tipos_exame = csv.DictReader(open(os.path.join(settings.BASE_DIR, 'sifilis/dados_iniciais/tipos_exame.csv'), 'r'))
    for i in tipos_exame:
        TipoExame.objects.get_or_create(nome=i['titulo'])

    resultados_exame = csv.DictReader(open(os.path.join(settings.BASE_DIR, 'sifilis/dados_iniciais/resultados_tipos_exame.csv'), 'r'))
    for i in resultados_exame:
        TipoExameResultado.objects.get_or_create(nome=i['descricao'], tipo_de_exame_id=i['tipo_exame_id'])
