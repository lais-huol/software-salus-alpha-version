from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse_lazy
from notifications.signals import notify

from base.utils import users_with_perm


class Alerta(object):
    VERB_PROCESSAMENTO_CENSO_LEITOS_COVID_CONCLUIDO = 'Processamento Censo Leitos COVID Concluído. Há nomes de pacientes a serem associados.'
    VERB_NOVO_RESULTADO_GAL = 'Novo resultado GAL'
    VERB_NOMES_ESTABELECIMENTO_A_ASSOCIAR = 'Há nomes de estabelecimento a serem associados com código CNES.'
    VERB_NOMES_NOTIFICACAO_DEFINIR_PRINCIPAL = 'Há notificações semelhantes que precisam ser tratadas.'
    VERB_HA_NOTIFICACOES_ALTERADAS = 'Há Notificações alteradas.'
    VERB_PROCESSAMENTO_BASE_ESUSVE_CONCLUIDA = 'Processamento base ESUS-VE foi concluída.'
    VERB_PROCESSAMENTO_BASE_SIVEP_GRIPE_CONCLUIDA  = 'Processamento base SIVEP GRIPE foi concluída.'
    VERB_MONITORAMENTO_24H_NECESSARIO = 'Monitoramento 24h necessário'
    VERB_MONITORAMENTO_48H_NECESSARIO = 'Monitoramento 48h necessário'
    VERB_HA_NOTIFICACOES_COM_DATA_VAZIA = 'Notificação com data da notificação vazia.'
    VERB_HA_MONITORAMENTO_ENCERRADO_POR_OBITO = 'Há Monitoramento encerrado por Óbito.'
    VERB_NOVO_OBITO_PENDENTE_VALIDACAO = 'Novo Óbito pendente para Validar.'

    # Defina aqui a action_url para cada verb; caso o verb não esteja aqui, o action_url será
    # notification.action_object.get_absolute_url()
    VERBS_AND_ACTIONS_URLS = {
        VERB_PROCESSAMENTO_CENSO_LEITOS_COVID_CONCLUIDO: reverse_lazy('notificacoes:associar_pacientes'),
        VERB_NOMES_ESTABELECIMENTO_A_ASSOCIAR: reverse_lazy('notificacoes:associar_estabelecimentos'),
        VERB_NOMES_NOTIFICACAO_DEFINIR_PRINCIPAL: reverse_lazy('notificacoes:definir_principais'),
        VERB_PROCESSAMENTO_BASE_ESUSVE_CONCLUIDA: reverse_lazy('notificacoes:definir_principais'),
        VERB_HA_NOTIFICACOES_ALTERADAS: reverse_lazy('notificacoes:listar_alteradas'),
        VERB_NOVO_OBITO_PENDENTE_VALIDACAO: reverse_lazy('notificacoes:listar_obitos'),
    }

    @classmethod
    def send(cls, verb, recipient, sender=None, action_object=None):
        sender = sender or ContentType.objects.get_for_model(apps.get_model('notificacoes', 'notificacao'))
        notify.send(sender=sender, recipient=recipient, verb=verb, action_object=action_object)

    @classmethod
    def novo_resultado_gal(cls, obj_notificacao):
        for recipient in obj_notificacao.visivel_para():
            notify.send(sender=obj_notificacao, recipient=recipient, verb=cls.VERB_NOVO_RESULTADO_GAL,
                        action_object=obj_notificacao)

    @classmethod
    def notificacao_com_data_vazia(cls, obj_notificacao):
        #TODO: revisar - disponível apenas para o pefil vigilância
        for recipient in obj_notificacao.visivel_para():
            notify.send(sender=obj_notificacao, recipient=recipient, verb=cls.VERB_HA_NOTIFICACOES_COM_DATA_VAZIA,
                        action_object=obj_notificacao)

    @classmethod
    def processamento_censo_leitos_covid_concluido(cls):
        # TODO: revisar - disponível apenas para o pefil vigilância
        cls.send(verb=cls.VERB_PROCESSAMENTO_CENSO_LEITOS_COVID_CONCLUIDO,
                 recipient=users_with_perm('notificacoes.pode_associar_pacientes'))

    @classmethod
    def ha_nomes_estabelecimento_a_associar(cls):
        # TODO: revisar - disponível apenas para o pefil vigilância
        cls.send(verb=cls.VERB_NOMES_ESTABELECIMENTO_A_ASSOCIAR,
                 recipient=users_with_perm('notificacoes.pode_associar_estabelecimentos'))

    @classmethod
    def processamento_base_esusve_concluida(cls):
        # TODO: revisar - disponível apenas para o pefil vigilância
        cls.send(verb=cls.VERB_PROCESSAMENTO_BASE_ESUSVE_CONCLUIDA,
                 recipient=users_with_perm('notificacoes.pode_definir_notificacoes_principais'))

    @classmethod
    def processamento_base_sivep_gripe_concluida(cls):
        # TODO: revisar - disponível apenas para o pefil vigilância
        cls.send(verb=cls.VERB_PROCESSAMENTO_BASE_SIVEP_GRIPE_CONCLUIDA,
                 recipient=users_with_perm('notificacoes.pode_definir_notificacoes_principais'))

    @classmethod
    def ha_notificacoes_similares(cls):
        # TODO: revisar - disponível apenas para o pefil vigilância
        cls.send(verb=cls.VERB_NOMES_NOTIFICACAO_DEFINIR_PRINCIPAL,
                 recipient=users_with_perm('notificacoes.pode_definir_notificacoes_principais'))

    @classmethod
    def ha_notificacao_alterada(cls):
        # TODO: revisar - disponível apenas para o pefil vigilância
        # TODO: enviar para gestores dvs e usuários dvs
        from base.models import Usuario
        recipient_list = Usuario.objects.all()
        cls.send(verb=cls.VERB_HA_NOTIFICACOES_ALTERADAS, recipient=recipient_list)

    @classmethod
    def monitoramento_24h_necessario(cls, obj_notificacao):
        # TODO: revisar - disponível apenas para o pefil atenção básica
        recipient_list = obj_notificacao.visivel_para().exclude(perfil_distrito__isnull=True,
                                                                perfil_estabelecimento__isnull=True)
        for recipient in recipient_list:
            cls.send(verb=cls.VERB_MONITORAMENTO_24H_NECESSARIO, recipient=recipient)

    @classmethod
    def monitoramento_48h_necessario(cls, obj_notificacao):
        # TODO: revisar - disponível apenas para o pefil atenção básica
        recipient_list = obj_notificacao.visivel_para().exclude(perfil_distrito__isnull=True,
                                                                perfil_estabelecimento__isnull=True)
        for recipient in recipient_list:
            cls.send(verb=cls.VERB_MONITORAMENTO_48H_NECESSARIO, recipient=recipient)

    @classmethod
    def novo_obito_pendente_validacao(cls):
        cls.send(verb=cls.VERB_NOVO_OBITO_PENDENTE_VALIDACAO,
                 recipient=users_with_perm('notificacoes.pode_validar_obito'))

    @classmethod
    def get_action_url(cls, notification):
        if notification.verb in cls.VERBS_AND_ACTIONS_URLS:
            return cls.VERBS_AND_ACTIONS_URLS[notification.verb]
        if hasattr(notification.action_object, 'get_absolute_url'):
            return notification.action_object.get_absolute_url()
        return ''
