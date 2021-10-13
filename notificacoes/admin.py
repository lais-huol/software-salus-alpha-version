from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from base.caches import ControleCache
from .models import Notificacao, UploadImportacao


class UploadImportacaoAdmin(admin.ModelAdmin):
    change_list_template = "admin/notificacoes/uploadimportacao/change_list.html"
    list_display = ('datahora', 'arquivo', 'usuario_nome', 'processado')
    search_fields = ('usuario', 'arquivo')
    ordering = ('-datahora',)

    def usuario_nome(self, obj):
        try:
            return obj.usuario.nome
        except:
            return ''
    usuario_nome.short_description = 'Usuário'



class NotificacaoEvento(SimpleListFilter):
    title = 'Evento'
    parameter_name = 'notificacoes'

    def lookups(self, request, model_admin):
        return (
            ('cep_vazio', 'CEP Vazios'),
            ('cep_nulos', 'CEP Nulos'),
            ('ativas_com_cnes_referencia_vazio', 'Ativas com CNES de Referência Vazio'),
            ('modificadas', 'Dados alterados'),
            ('modificadas_vazio', 'Dados alterados vazios'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'cep_vazio':
            return queryset.filter(dados_cep={})
        elif self.value() == 'cep_nulos':
            return queryset.filter(dados_cep__isnull=True)
        if self.value() == 'modificadas':
            return queryset.filter(dados_alterado__isnull=False)
        elif self.value() == 'modificadas_vazio':
            return queryset.filter(dados_alterado={})
        elif self.value() == 'ativas_com_cnes_referencia_vazio':
            return queryset.filter(estabelecimento_saude_referencia__isnull=True, ativa=True)
        return queryset


class NotificacaoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'ativa', 'pessoa', 'numero_gal', 'bairro', 'estabelecimento_saude',
                    'paciente_internado', 'notificacao_principal',
                    'ha_dados_alterado',
                    'dados_atualizados_em', 'dados_cep_atualizados_em')
    list_filter = (NotificacaoEvento,)
    search_fields = ('numero',)

    def ha_dados_alterado(self, obj):
        return obj.dados_alterado is not None
    ha_dados_alterado.short_description = 'Há dados alterado'


admin.site.register(Notificacao, NotificacaoAdmin)
admin.site.register(UploadImportacao, UploadImportacaoAdmin)

