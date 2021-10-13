from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from notifications.admin import NotificationAdmin
from swapper import load_model

from .models import Usuario, Distrito, Bairro, AssociacaoBairro, HabitacoesBairro, Municipio, EstabelecimentoSaude, \
    AssociacaoNomeEstabelecimentoSaude, PerfilDistrito, PerfilAtencaoBasica, PerfilVigilancia, \
    PerfilAtencaoEspecializada, PerfilEstabelecimentoSaude, AssociacaoOperadorCNES


# Register your models here.


class UsuarioAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('cpf', 'password')}),
        (_('Personal info'), {'fields': ('nome', 'email', 'telefone')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('cpf', 'password1', 'password2'),
        }),
    )
    list_display = ('nome', 'cpf', 'email', 'date_joined', 'last_login')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('nome', 'cpf', 'email', 'telefone')
    ordering = ('nome',)
    filter_horizontal = ('groups', 'user_permissions',)
    change_form_template = 'loginas/change_form.html'


class PerfilAdmin(admin.ModelAdmin):
    list_display = ('usuario_nome', 'usuario_cpf')
    search_fields = ('usuario__nome', 'usuario__cpf')

    def usuario_nome(self, obj):
        return obj.usuario.nome
    usuario_nome.short_description = 'Usuário'

    def usuario_cpf(self, obj):
        return obj.usuario.cpf
    usuario_cpf.short_description = 'CPF'


class PerfilGestaoAdmin(PerfilAdmin):
    list_display = ('usuario_nome', 'usuario_cpf', 'municipio')
    search_fields = ('usuario__nome', 'usuario__cpf', 'municipio__nome')


class PerfilDistritoAdmin(PerfilAdmin):
    list_display = ('usuario_nome', 'usuario_cpf', 'distrito')
    search_fields = ('usuario__nome', 'usuario__cpf', 'distrito__nome')


class PerfilEstabelecimentoSaudeAdmin(PerfilAdmin):
    list_display = ('usuario_nome', 'usuario_cpf', 'estabelecimento_saude')
    search_fields = ('usuario__nome', 'usuario__cpf', 'estabelecimento_saude__codigo_cnes')


class AssociacaoBairroAdmin(admin.ModelAdmin):
    list_display = ('nome', 'bairro')
    search_fields = ('nome',)
    list_filter = ('bairro',)
    ordering = ('nome',)


class BairroAdmin(admin.ModelAdmin):
    list_display = ('nome', 'municipio', 'distrito')
    search_fields = ('nome',)
    list_filter = ('municipio','distrito')
    ordering = ('nome',)


class EstabelecimentoSaudeAdmin(admin.ModelAdmin):
    list_display = ('codigo_cnes', 'nome', 'bairro', 'municipio', 'data_extracao', 'dados_cnes')
    search_fields = ('codigo_cnes', 'dados_cnes__nome' )
    ordering = ('dados_cnes__nome',)


class AssociacaoOperadorCNESAdmin(admin.ModelAdmin):
    list_display = ('cpf', 'estabelecimento_saude', 'dados')
    search_fields = ('cpf', 'estabelecimento_saude__dados_cnes__NO_FANTASIA')

def action_notification_read(modeladmin, request, queryset):
    for notification in queryset:
        notification.mark_as_read()
action_notification_read.short_description = 'Definir como lidas notifications selecionadas '

Notification = load_model('notifications', 'Notification')
class AlertaAdmin(NotificationAdmin):
    raw_id_fields = ('recipient',)
    list_display = ('timestamp', 'verb', 'recipient', 'actor',
                    'unread')
    list_filter = ('verb', 'unread', 'timestamp', 'recipient')

    actions = [action_notification_read, ]

    def get_queryset(self, request):
        qs = super(AlertaAdmin, self).get_queryset(request)
        return qs.prefetch_related('actor')


admin.site.unregister(Notification)
admin.site.register(Notification, AlertaAdmin)
admin.site.register(AssociacaoNomeEstabelecimentoSaude)
admin.site.register(Usuario, UsuarioAdmin)
admin.site.register(Distrito)
admin.site.register(Bairro, BairroAdmin)
admin.site.register(PerfilVigilancia, PerfilGestaoAdmin)
admin.site.register(PerfilEstabelecimentoSaude, PerfilEstabelecimentoSaudeAdmin)
admin.site.register(PerfilAtencaoBasica, PerfilGestaoAdmin)
admin.site.register(PerfilAtencaoEspecializada, PerfilGestaoAdmin)
admin.site.register(PerfilDistrito, PerfilDistritoAdmin)
admin.site.register(AssociacaoBairro, AssociacaoBairroAdmin)
admin.site.register(HabitacoesBairro, AssociacaoBairroAdmin)
admin.site.register(Municipio)
admin.site.register(EstabelecimentoSaude, EstabelecimentoSaudeAdmin)
admin.site.register(AssociacaoOperadorCNES, AssociacaoOperadorCNESAdmin)

