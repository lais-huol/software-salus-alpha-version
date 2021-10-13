from django import forms

from base.models import Distrito, Municipio, Bairro, HabitacoesBairro, AssociacaoBairro
from notificacoes.models import PacienteInternacao, Notificacao


class PacienteInternacaoForm(forms.ModelForm):
    nome_paciente = forms.CharField(label='Nome do paciente')
    # TODO Jailton é preciso uma função para retornar o queryset ou lista de notificações com dados próximos
    notificacao = forms.ModelChoiceField(queryset=Notificacao.ativas.all(), label='Notificação', required=False)

    def __init__(self, *args, **kwargs):
        super(PacienteInternacaoForm, self).__init__(*args, **kwargs)
        self.fields['nome_paciente'].widget.attrs['value'] = self.instance.dados_censo_leitos['paciente_nome']
        self.fields['nome_paciente'].widget.attrs['readonly'] = True
        notificacoes_proximas = self.instance.notificacao_set.all() | Notificacao.obter_notificacoes_por_data_nascimento(self.instance.data_de_nascimento_str)
        self.fields['notificacao'].queryset = notificacoes_proximas
        if self.instance.notificacao_set.count():
            self.fields['notificacao'].initial = self.instance.notificacao_set.first()

    def save(self, commit=True):
        self.instance.notificacao_set.all().update(paciente_internado=None)
        if self.cleaned_data['notificacao']:
            self.cleaned_data['notificacao'].paciente_internado = self.instance
            self.cleaned_data['notificacao'].save()
        return super(PacienteInternacaoForm, self).save()


    class Meta:
        model = PacienteInternacao
        fields = ['nome_paciente', 'notificacao']


class DistritoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['municipio'].queryset = Municipio.ativos.all()
        self.fields['municipio'].initial = Municipio.ativos.all()[0]
        self.fields['municipio'].widget.attrs['readonly'] = True

    class Meta:
        model = Distrito
        fields = '__all__'


class BairroForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['distrito'].queryset = Distrito.ativos.all()
        self.fields['municipio'].queryset = Municipio.ativos.all()
        self.fields['municipio'].initial = Municipio.ativos.all()[0]
        self.fields['municipio'].widget.attrs['readonly'] = True

    class Meta:
        model = Bairro
        fields = '__all__'


class HabitacaoForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bairro'].queryset = Bairro.ativos.all()

    class Meta:
        model = HabitacoesBairro
        fields = '__all__'


class AssociacaoBairroForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['bairro'].queryset = Bairro.ativos.all()
        self.fields['nome'].disabled = True

    class Meta:
        model = AssociacaoBairro
        fields = '__all__'
