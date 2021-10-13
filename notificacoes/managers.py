from django.db import models
from django.db.models import Q


class NotificacoesAtivasManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(tipo_motivo_desativacao__isnull=True)


class NotificacoesPendentesManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(Q(pessoa__isnull=True)
                       | Q(bairro__isnull=True)
                       | Q(estabelecimento_saude__isnull=True)
                       | Q(dados__telefone_celular=None)
                       # | Q(numero_gal__isnull=True, dados__resultado_do_teste=None)
                       )
        qs = qs.filter(ativa=True)
        return qs


class NotificacoesAlteradasManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        qs = qs.filter(tipo_motivo_desativacao__isnull=True, dados_alterado__isnull=False)
        return qs


class NotificacoesSimilaresManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        sql = '''
            notificacoes_notificacao.numero IN (            
                select n.numero from notificacoes_notificacao n
                inner join 
                (
                    select 
                        dados -> 'data_da_notificacao' as data_da_notificacao,
                        dados -> 'nome_completo' as nome_completo, 
                        dados -> 'data_de_nascimento' as data_de_nascimento
                    from notificacoes_notificacao
                    group by
                        dados -> 'data_da_notificacao',
                        dados -> 'nome_completo', 
                        dados -> 'data_de_nascimento'
                    having count(numero) > 1
                ) as r
                on n.dados -> 'data_da_notificacao' = r.data_da_notificacao
                and n.dados -> 'nome_completo' = r.nome_completo 
                and n.dados -> 'data_de_nascimento' = r.data_de_nascimento 
            )             
            '''
        return qs.extra(where=[sql]).filter(tipo_motivo_desativacao__isnull=True, notificacao_principal__isnull=True)


class MonitoramentosAtivosManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(notificacao__tipo_motivo_desativacao__isnull=True)


