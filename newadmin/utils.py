# -*- coding: utf-8 -*-

import base64
import json
import re
import pickle
from decimal import Decimal
import zlib
import sys
from django.apps import apps
from django.conf import settings

import requests
from django.contrib.humanize.templatetags.humanize import intcomma
from django.core.validators import EMPTY_VALUES
from django.db import models
from django import forms
from django.forms.utils import flatatt
from django.http import HttpResponse
from django.template.defaultfilters import floatformat
from django.template.loader import render_to_string
from django.utils.encoding import force_text
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from localflavor.br.forms import BRCPFField
from django.core.signing import TimestampSigner, Signer

phone_digits_re = re.compile(r'^(\d{2})[-\.]?(\d{4,5})[-\.]?(\d{4})$')


def decimal_to_money(value, precision=2):
    value = floatformat(value, precision)
    value, decimal = force_text(value).split('.')
    value = intcomma(value)
    value = value.replace(',', '.') + ',' + decimal
    return value


class MoneyFormWidget(forms.TextInput):
    def render(self, name, value, attrs=None):
        value = value or ''
        if isinstance(value, Decimal):
            value = decimal_to_money(str(value), 2)
        return super(MoneyFormWidget, self).render(name, value, attrs)


class MoneyFormField(forms.DecimalField):
    widget = MoneyFormWidget

    def clean(self, value):
        if value:
            value = value.replace('.', '').replace(',', '.')
        return super(MoneyFormField, self).clean(value)

    def widget_attrs(self, widget):
        return {'class': 'money'}


class MoneyModelField(models.DecimalField):
    def __init__(self, *args, **kwargs):
        kwargs['max_digits'] = 11
        kwargs['decimal_places'] = 2
        super(MoneyModelField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': MoneyFormField}
        defaults.update(kwargs)
        return super(MoneyModelField, self).formfield(**defaults)


class DateWidget(forms.DateInput):
    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {"class": "date", "placeholder": "00/00/0000"}
        super(DateWidget, self).__init__(attrs)


class DateFormField(forms.DateField):
    input_formats = ('%d/%m/%Y',)
    widget = DateWidget


class DateTimeWidget(forms.DateTimeInput):
    def __init__(self, attrs=None):
        if attrs is None:
            attrs = {"class": "datetime", "placeholder": "00/00/0000 00:00"}
        super(DateTimeWidget, self).__init__(attrs)


class DateTimeFormField(forms.DateTimeField):
    input_formats = ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M')
    widget = DateTimeWidget


class CepModelField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 9
        super(CepModelField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {
            'min_length': 9,
            'widget': forms.TextInput(attrs={'class': 'cep', 'placeholder': '00000-000'})
        }
        defaults.update(kwargs)
        return super(CepModelField, self).formfield(**defaults)


class CpfFormField(BRCPFField):
    def __init__(self, max_length=14, min_length=14, *args, **kwargs):
        super(CpfFormField, self).__init__(max_length, min_length, *args, **kwargs)

    def widget_attrs(self, widget):
        attrs = super(CpfFormField, self).widget_attrs(widget)
        #attrs['class'] = 'cpf'
        attrs['placeholder'] = '000.000.000-00'
        return attrs

    def clean(self, value):
        # O `clean` foi sobrescrito para não permitir valores como '999.999.999.99',
        # pois o `BRCPFField` pega apenas os números para validar, desconsiderando traços e pontos
        super(CpfFormField, self).clean(value)
        if not self.required and not value:
            return value
        if not re.match('\d{3}.\d{3}.\d{3}-\d{2}', value):
            raise forms.ValidationError(u'O CPF deve estar no formato 999.999.999-99')
        return value


class CpfModelField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 14
        super(CpfModelField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': CpfFormField}
        defaults.update(kwargs)
        return super(CpfModelField, self).formfield(**defaults)


class DateModelField(models.DateField):
    def formfield(self, **kwargs):
        defaults = {'form_class': DateFormField}
        defaults.update(kwargs)
        return super(DateModelField, self).formfield(**defaults)


class DateTimeModelField(models.DateTimeField):
    def formfield(self, **kwargs):
        defaults = {'form_class': DateTimeFormField}
        defaults.update(kwargs)
        return super(DateTimeModelField, self).formfield(**defaults)


class PhoneNumberFormField(forms.CharField):
    # Nota: rescrevi o BRPhoneNumberField para herdar de CharField e poder
    # trabalhar com o max_length que vem do dbfield. O ``clean`` também foi
    # modificado para só permitir os formatos XX-XXXX-XXXX ou XX-XXXXX-XXXX.
    default_error_messages = {
        'invalid': u'Números de telefone devem estar num dos seguintes formatos: '
                   u'XX-XXXX-XXXX ou XX-XXXXX-XXXX.',
    }

    def clean(self, value):
        super(PhoneNumberFormField, self).clean(value)
        if value in EMPTY_VALUES:
            return ''
        m = phone_digits_re.search(value)
        if m:
            return '%s-%s-%s' % (m.group(1), m.group(2), m.group(3))
        raise forms.ValidationError(self.error_messages['invalid'])


class PhoneNumberModelField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 13
        super(PhoneNumberModelField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {
            'form_class': PhoneNumberFormField,
            'widget': forms.TextInput(attrs={'placeholder': '00-0000-0000'})
        }
        defaults.update(kwargs)
        return super(PhoneNumberModelField, self).formfield(**defaults)


class JsonResponse(HttpResponse):
    def __init__(self, data):
        content = json.dumps(data)
        HttpResponse.__init__(self, content=content,
                              content_type='application/json')


class ReCaptchaWidget(forms.widgets.Widget):

    class Media:
        js = ('https://www.google.com/recaptcha/api.js',)

    def render(self, name, value, attrs=None):
        return mark_safe(u'<div class="g-recaptcha" data-sitekey="%s"></div>' % settings.RECAPTHA_SITE_KEY)

    def value_from_datadict(self, data, files, name):
        return data.get(u'g-recaptcha-response')


class ReCaptchaField(forms.CharField):

    def __init__(self, *args, **kwargs):
        kwargs['label'] = u''
        self.widget = ReCaptchaWidget
        self.required = True
        return super(ReCaptchaField, self).__init__(*args, **kwargs)

    def get_remote_ip(self):
        f = sys._getframe()
        while f:
            if 'request' in f.f_locals:
                request = f.f_locals['request']
                if request:
                    remote_ip = request.META.get('REMOTE_ADDR', '')
                    forwarded_ip = request.META.get('HTTP_X_FORWARDED_FOR', '')
                    ip = remote_ip if not forwarded_ip else forwarded_ip
                    return ip
            f = f.f_back

    def clean(self, value):
        response = requests.post('https://www.google.com/recaptcha/api/siteverify',
                                 data=dict(secret=settings.RECAPTHA_SECRET_KEY,
                                           response=value,
                                           remoteip=self.get_remote_ip()))
        if not json.loads(response.text)['success']:
            raise forms.ValidationError(u'A verificação falhou. Por favor, tente novamente.')
        return value



def timeless_dump_qs(query):
    serialized_str = base64.b64encode(zlib.compress(pickle.dumps(query))).decode()
    signer = Signer()
    signed_data = signer.sign(serialized_str)
    payload = {'data': signed_data}
    return mark_safe(json.dumps(payload))

def timeless_load_qs_query(query):
    payload = json.loads(query)
    signer = Signer()
    signed_data = payload['data']
    data = signer.unsign(signed_data)
    return pickle.loads(zlib.decompress(base64.b64decode(data)))


def dumps_qs_query(query):
    serialized_str = base64.b64encode(zlib.compress(pickle.dumps(query))).decode()
    signer = TimestampSigner()
    signed_data = signer.sign(serialized_str)
    payload = {'data': signed_data}
    return mark_safe(json.dumps(payload))


def loads_qs_query(query):
    signer = TimestampSigner()
    payload = json.loads(query)
    signed_data = payload['data']
    data = signer.unsign(signed_data, max_age=settings.SIGNER_MAX_AGE)
    return pickle.loads(zlib.decompress(base64.b64decode(data)))


class ChainedSelectWidget(forms.Select):
    def render(self, name, value, attrs=None, choices=(), renderer=None):
        id_ = attrs['id']
        if not value:
            value = self.initial

        data = ""
        if self.qs_filter:
            data += ", qs_filter: '%s'" % self.qs_filter

        options = {}
        attrs['name'] = name
        if self.form_filters:
            if not isinstance(self.form_filters, (tuple, list)):
                raise ValueError('`form_filters` deve ser lista ou tupla')
            options['form_parameter_names'] = ','.join([i[0] for i in self.form_filters])
            options['django_filter_names'] = ','.join([i[1] for i in self.form_filters])

        context = dict(
            id=id_,
            url=self.url,
            initial=value,
            obj_value='id',
            obj_label=self.obj_label,
            empty_label=self.empty_label,
            data=data,
            options=options,
            qs_filter_params_map=self.qs_filter_params_map,
            control=timeless_dump_qs(self.queryset.all().query),
        )

        final_attrs = self.build_attrs(attrs)
        output = [format_html('<select{0}>', flatatt(final_attrs))]
        output.append('</select>')
        output.append(render_to_string('chainedselect_widget.html', context))
        return mark_safe('\n'.join(output))




class ChainedModelChoiceField(forms.ModelChoiceField):
    """
    Uma versão do forms.ModelChoiceField que trabalha de forma aninhada, onde ele é preenchido de acordo com uma escolha de outro "select".
    Keyword arguments:
       *obj_label:             Uma string com o label que deve ser colocado no option do select
        empty_label            Uma string a ser apresentada quando não tiver dados
        url:                   Uma string com a url de pesquisa. Ela deve retornar um Json e recebe os seguintes parametros: `request.POST` expected args: 'chained_attr', 'id', 'obj_label'
        qs_filter:             Uma query no formato string
                                 Exemplo: aluno__caracterizacao__isnull=False
        qs_filter_params_map   Um dict com parâmetros para o qs_fitler
                                 Exemplo: qs_filter='avaliadores_de_agendamentos=current_user'
                                          qs_filter_params_map    = {'current_user': tl.get_user().id},
      * form_filters           Uma lista de lista que tem 'Uma string com o nome do campo relacionado' e 'Uma string representado com o valor que deve colocar no filter'

    * parametros obrigatórios

    Exemplo:
        estado = forms.ModelChoiceField(Estado.object.all(), label=u'Estado')
        cidade = forms.ChainedModelChoiceFieldPlus(Cidade.objects.all(),
                                              label                = u'Cidade',
                                              empty_label          = u'Selecione o Estado',
                                              obj_label            = 'nome',
                                              form_filters         = [('estado', 'estado_id')]
                                              qs_filter            = 'estado__pais=pais'
                                              qs_filter_params_map = {'pais':1})
    """

    widget = ChainedSelectWidget

    def __init__(self, queryset, empty_label="---------", required=True, widget=None, label=None, initial=None, help_text=None, to_field_name=None, *args, **kwargs):
        try:
            obj_label = kwargs.pop('obj_label')
        except KeyError:
            raise KeyError('Parameter obj_label is required.')

        try:
            form_filters = kwargs.pop('form_filters')
        except KeyError:
            raise KeyError('Parameter form_filters is required.')

        qs_filter = kwargs.pop('qs_filter', None)
        qs_filter_params_map = kwargs.pop('qs_filter_params_map', {})
        url = kwargs.pop('url', None)
        if not url:
            class_name = queryset.model.__name__
            class_module = queryset.model.__module__.split('.')[0]
            url = '/chained_select/%s/%s/' % (class_module, class_name)

        super().__init__(
            queryset, empty_label=empty_label, required=required, widget=widget, label=label, initial=initial, help_text=help_text, to_field_name=to_field_name, *args, **kwargs
        )

        self.widget.initial = initial
        self.widget.empty_label = empty_label
        self.widget.url = url
        self.widget.form_filters = form_filters
        self.widget.obj_label = obj_label
        self.widget.qs_filter = qs_filter
        self.widget.qs_filter_params_map = qs_filter_params_map
        self.widget.queryset = queryset


class ChainedMultipleSelectWidget(forms.SelectMultiple):
    def get_context(self, name, value, attrs=None, choices=()):
        id_ = attrs['id']
        if not value:
            value = self.initial

        if isinstance(value, list):
            value = map(int, value)

        data = ""
        if self.qs_filter:
            data += ", qs_filter: '%s'" % self.qs_filter

        options = {}
        if self.form_filters:
            if not isinstance(self.form_filters, (tuple, list)):
                raise ValueError('`form_filters` deve ser lista ou tupla')
            options['form_parameter_names'] = ','.join([i[0] for i in self.form_filters])
            options['django_filter_names'] = ','.join([i[1] for i in self.form_filters])

        return dict(id=id_,
                       url=self.url,
                       initial=value,
                       obj_value='id',
                       obj_label=self.obj_label,
                       data=data,
                       options=options,
                       qs_filter_params_map=self.qs_filter_params_map,
                       control=dumps_qs_query(self.queryset.all().query))

    def render(self, name, value, attrs=None, choices=()):
        context = self.get_context(name, value, attrs, choices)
        final_attrs = self.build_attrs(attrs, name=name)
        output = [format_html('<select multiple="multiple"{}>', flatatt(final_attrs)), '</select>',
                  render_to_string('chainedselect_widget.html', context)]
        return mark_safe('\n'.join(output))


class ChainedModelMultipleChoiceField(forms.ModelMultipleChoiceField):
    widget = ChainedMultipleSelectWidget

    def __init__(self, queryset, cache_choices=None,
                 required=True, widget=None, label=None, initial=None,
                 help_text='', *args, **kwargs):
        try:
            obj_label = kwargs.pop('obj_label')
        except KeyError:
            raise KeyError(u'Parameter obj_label is required.')

        try:
            form_filters = kwargs.pop('form_filters')
        except KeyError:
            raise KeyError(u'Parameter form_filters is required.')

        qs_filter = kwargs.pop('qs_filter', None)
        qs_filter_params_map = kwargs.pop('qs_filter_params_map', {})
        url = kwargs.pop('url', None)
        if not url:
            class_name = queryset.model.__name__
            class_module = queryset.model.__module__.split('.')[0]
            url = '/newadmin/chained_select/%s/%s/' % (class_module, class_name)

        super(ChainedModelMultipleChoiceField, self).__init__(
            queryset, cache_choices, required, widget, label, initial,
            help_text, *args, **kwargs)

        self.widget.initial = initial
        self.widget.url = url
        self.widget.form_filters = form_filters
        self.widget.obj_label = obj_label
        self.widget.qs_filter = qs_filter
        self.widget.qs_filter_params_map = qs_filter_params_map
        self.widget.queryset = queryset


