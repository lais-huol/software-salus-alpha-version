from datetime import datetime

from django import forms
from django.db.transaction import atomic

from . import models
from .models import TipoExame, Exame, TipoExameResultado, Relacionamento, Antecedente


class Passo1Form(forms.Form):
    cid = forms.ModelChoiceField(queryset=models.CID.objects.filter(planoterapeutico__cid__isnull=False).distinct(),
                                 empty_label='Escolha o CID')


class Passo2Form(forms.Form):

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.cid = kwargs.pop('cid')
        self.pessoa = kwargs.pop('pessoa')
        self.base_fields['plano_terapeutico'].queryset = models.PlanoTerapeutico.qs_visiveis(self.user).filter(cid=self.cid)
        super().__init__(*args, **kwargs)

    def save(self):
        models.PlanoTerapeuticoPaciente.objects.create(
            paciente=self.pessoa,
            plano_terapeutico=self.cleaned_data['plano_terapeutico']
        )

    plano_terapeutico = forms.ModelChoiceField(queryset=models.PlanoTerapeutico.objects.none())


class CadastrarPlanoEVincularAoPacienteForm(forms.ModelForm):

    class Meta:
        model = models.PlanoTerapeutico
        fields = ['nome', 'medicamento', 'orientacao', 'qtd_doses', 'invervalo_entre_doses_em_horas', 'prazo_extra_em_horas']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.cid = kwargs.pop('cid')
        self.pessoa = kwargs.pop('pessoa')
        super().__init__(*args, **kwargs)

    @atomic
    def save(self, **kwargs):
        self.instance.restrito_ao_usuario = self.user
        super().save(**kwargs)
        self.instance.cid.add(self.cid)
        models.PlanoTerapeuticoPaciente.objects.create(
            paciente=self.pessoa,
            plano_terapeutico=self.instance
        )


class RegistrarDoseForm(forms.Form):

    def __init__(self, *args, **kwargs):
        self.plano_terapeutico_paciente = kwargs.pop('plano_terapeutico_paciente')
        super().__init__(*args, **kwargs)

    def save(self):
        self.plano_terapeutico_paciente.registrar_dose(
            dose_aplicada_em=self.cleaned_data['dose_aplicada_em']
        )

    dose_aplicada_em = forms.DateTimeField(initial=datetime.now)
    confirmar = forms.BooleanField(label='Confirmar aplicação da dose?')

class ExamePasso1Form(forms.Form):
    tipoexame = forms.ModelChoiceField(queryset=TipoExame.objects,
                                 empty_label='Escolha o Tipo do Exame', label='Tipo do Exame')

class ExamePasso2Form(forms.ModelForm):

    class Meta:
        model = Exame
        fields = ('resultado', 'data_de_realizacao', 'observacoes')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.tipoexame = kwargs.pop('tipo_exame')
        self.pessoa = kwargs.pop('pessoa')
        self.base_fields['resultado'].queryset = TipoExameResultado.objects.filter(tipo_de_exame=self.tipoexame)
        super().__init__(*args, **kwargs)
        self.fields['observacoes'].required = False


class RelacionamentoForm(forms.ModelForm):
    cpf = forms.CharField(label='CPF', required=False)
    cns = forms.CharField(label='CNS', required=False)

    class Meta:
        model = Relacionamento
        fields = ('cpf', 'cns', 'tipo_de_relacionamento', )

    def clean(self):
        if not self.cleaned_data.get('cpf') and not self.cleaned_data.get('cns'):
            self.add_error('cpf', 'É preciso informar o CPF ou o CNS.')

class AntecedenteForm(forms.ModelForm):
    class Meta:
        model = Antecedente
        fields = ('cid', 'situacao')
