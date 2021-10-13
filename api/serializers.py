from rest_framework import serializers, fields
from rest_framework.relations import PrimaryKeyRelatedField

from base.models import Bairro
from notificacoes.models import Notificacao, AssociacaoNomeEstabelecimentoSaude


class DistritoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bairro
        fields = (
            'nome', 'municipio'
        )


class BairroSerializer(serializers.ModelSerializer):
    distrito = DistritoSerializer()

    class Meta:
        model = Bairro
        fields = (
            'nome', 'distrito', 'municipio'
        )


class NotificacaoSerializer(serializers.ModelSerializer):
    bairro = BairroSerializer()

    class Meta:
        model = Notificacao
        fields = (
            'numero', 'dados', 'bairro', 'resultado_teste'
        )


class NotificacaoGALSerializer(serializers.ModelSerializer):
    numero_gal = fields.CharField(min_length=12, max_length=12)

    class Meta:
        model = Notificacao
        fields = (
            'numero_gal',
        )


class AssociacaoNomeEstabelecimentoSaudeSerializer(serializers.ModelSerializer):
    codigo_cnes = fields.CharField(min_length=7, max_length=7)

    class Meta:
        model = AssociacaoNomeEstabelecimentoSaude
        fields = (
            'codigo_cnes', 'nome'
        )
