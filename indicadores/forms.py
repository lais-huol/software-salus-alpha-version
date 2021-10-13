import datetime

from django import forms
from djrichtextfield.widgets import RichTextWidget

from base.utils import DataSemana
from indicadores import catalogo
from indicadores.paineis import PainelBoletim
from indicadores.models import ModeloPainel, ModeloAplicacao
from notificacoes.forms import DateInput


class ModeloPainelForm(forms.ModelForm):
    conteudo = forms.CharField(widget=RichTextWidget())

    def __init__(self, *args, **kwargs):
        super(ModeloPainelForm, self).__init__(*args, **kwargs)
        self.fields['conteudo'].widget.field_settings = {
            'toolbar': [
                {'name': 'clipboard',
                 'items': ['Templates','-', 'Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord', '-', 'Undo', 'Redo']},
                {'name': 'editing', 'items': ['Find', 'Replace', '-', 'SelectAll']},
                {'name': 'basicstyles',
                 'items': ['Bold', 'Italic', 'Underline', 'Strike', 'Subscript', 'Superscript', '-', 'CopyFormatting',
                           'RemoveFormat']},
                '/',
                {'name': 'paragraph',
                 'items': ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'Blockquote', 'CreateDiv',
                           '-',
                           'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock', '-', 'BidiLtr', 'BidiRtl']},
                {'name': 'links', 'items': ['Link', 'Unlink', 'Anchor']},
                {'name': 'insert',
                 'items': ['Image', 'Table', 'HorizontalRule', 'SpecialChar']},
                {'name': 'styles', 'items': ['Styles', 'Format', 'Font', 'FontSize']},
                {'name': 'colors', 'items': ['TextColor', 'BGColor']},
                {'name': 'tools', 'items': ['Maximize', 'ShowBlocks', '-', 'Source']},
            ],
            'mentions': [{
                'feed': list(catalogo.get_catalogo_indicadores().keys()),
                'marker': '#',
                'itemTemplate': '<li data-id="{id}"><strong>{name}</strong></li>',
                'outputTemplate': '%%{name}#%%',
                'minChars': 0
            }],
            'imagesPath': "CKEDITOR.getUrl(CKEDITOR.plugins.getPath('templates') + 'templates/images/')",
            'templates_replaceContent': False,
            'templates_files': ['/static/js/templates/boletim.js']

        }
    class Meta:
        model = ModeloPainel
        fields = '__all__'


class BoletimForm(forms.ModelForm):
    modelo = forms.ModelChoiceField(queryset=ModeloPainel.objects.filter(tipo='boletim'))
    numero_do_boletim = forms.IntegerField()
    data_do_boletim = forms.DateField(widget=DateInput, initial=datetime.date.today)
    semana_boletim = forms.ChoiceField(choices=[(None, '---------')]+list(zip(reversed(DataSemana.get_semanas_ano(2020))
                                                   , reversed(DataSemana.get_semanas_ano(2020)))), label='Semana/ano')

    class Meta:
        model = ModeloAplicacao
        fields = ['nome', 'data_do_boletim', 'semana_boletim', 'modelo']
