import sys
import unicodedata
from time import time

import calendar
import datetime
import difflib
import importlib
import jellyfish
import json
import logging
import pandas as pd
import re
import threading
from datetime import date, timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import mail_admins
from django.db import connection
from django.db.models import Q, QuerySet, Func, Sum
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.utils.timezone import make_aware, utc, is_aware
from epiweeks import Week, Year
from functools import lru_cache
from io import BytesIO
from json import JSONDecoder
from json import JSONEncoder
from rest_framework.renderers import JSONRenderer

logger = logging.getLogger(__name__)


def get_native_data_now():
    naive_datetime = datetime.datetime.now()
    aware_datetime = make_aware(naive_datetime)
    return aware_datetime


def levenshtein_distance(word, words, default_rate=0.85, default_distance=3):
    words_similar = difflib.get_close_matches(word, words)
    word_like = None
    weight = 0
    rate = 1
    for sw in words_similar:
        distance = jellyfish.levenshtein_distance(word, sw)
        rate = jellyfish.jaro_similarity(word, sw)
        if rate > default_rate or distance < default_distance:
            if rate > weight:
                word_like = sw
                weight = rate
    if word_like is None:
        for sw in words_similar:
            logger.debug(
                'Similaridade descartada; {}; {}; {}; {}'.format(word, sw, jellyfish.jaro_similarity(word, sw),
                                                                 jellyfish.levenshtein_distance(word, sw)))
    else:
        logger.debug(
            'Similaridade encontrada; {}; {}; {}; [{}]'.format(word, word_like, rate, ';'.join(words_similar)))
    return (word_like or word, rate)


def dict_compare(d1, d2):
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    intersect_keys = d1_keys.intersection(d2_keys)
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o: (d1[o], d2[o]) for o in intersect_keys if d1[o] != d2[o]}
    same = set(o for o in intersect_keys if d1[o] == d2[o])
    return added, removed, modified, same


@lru_cache(maxsize=10)
def normalize_keys(keys):
    normalized_keys = []
    for key in keys:
        new_key = re.sub('[^A-Za-z0-9_]+', '', unicodedata.normalize('NFKD', key.replace(' ', '_').lower()))
        normalized_keys.append(new_key)
    return normalized_keys

def normalize_str(str):
    return re.sub('[^A-Za-z0-9_]+', '', unicodedata.normalize('NFKD', str.replace(' ', '_').lower()))

class JSONModelFormMixin(object):
    """
    Mixin para ser usado juntamente com forms.ModelForm para salvar form fields específicos no model JSONField.

    Uso:

        class NotificacaoForm(JSONModelFormMixin, forms.ModelForm):
            idade = forms.IntegerField()

            class Meta:
                model = Notificacao
                fields = []
                json_form_fields = ['idade']

    """

    def get_json_model_field_value(self):
        return getattr(self, self.model_json_field_name, dict())

    def __init__(self, *args, **kwargs):
        self.json_form_fields = self.Meta.json_form_fields
        self.model_json_field_name = kwargs.pop('model_json_field_name')
        super(JSONModelFormMixin, self).__init__(*args, **kwargs)
        json_model_field_value = self.get_json_model_field_value()
        for field in self.json_form_fields:
            if json_model_field_value.get(field):
                self.fields[field].initial = json_model_field_value.get(field)

    def save(self, *args, **kwargs):
        json_model_field_value = self.get_json_model_field_value()
        for json_form_field in self.json_form_fields:
            val = self.cleaned_data[json_form_field]
            json_model_field_value[json_form_field] = val

        # Usa o JSONRenderer do rest_framework para serializar tipos como o date, depois converte
        # para dict porque é exigido pelo model JSONField
        json_model_field_value = json.loads(JSONRenderer().render(json_model_field_value))

        setattr(self.instance, self.model_json_field_name, json_model_field_value)
        return super(JSONModelFormMixin, self).save(*args, **kwargs)


def get_idade(data_nascimento):
    return (date.today() - data_nascimento) // timedelta(days=365.2425)


def calculateAge(birthDate):
    today = date.today()
    age = today.year - birthDate.year - ((today.month, today.day) < (birthDate.month, birthDate.day))
    return age


def background(func):
    def backgrnd_func(*args, **kwargs):
        th = threading.Thread(target=func, args=args, kwargs=kwargs)
        th.daemon = True
        th.start()

    return backgrnd_func


def elapsed_time(func):
    def elapsed_func(*args, **kwargs):
        t1 = time()
        return_fun = func(*args, **kwargs)
        t2 = time()
        logger.debug('{}, elapsed time: {}'.format(func.__name__, t2 - t1))
        return return_fun

    return elapsed_func


def run_async(func):
    """
        run_async(func)
            function decorator, intended to make "func" run in a separate
            thread (asynchronously).
            Returns the created Thread object

            E.g.:
            @run_async
            def task1():
                do_something

            @run_async
            def task2():
                do_something_too

            t1 = task1()
            t2 = task2()
            ...
            t1.join()
            t2.join()
    """
    from threading import Thread
    from functools import wraps

    @wraps(func)
    def async_func(*args, **kwargs):
        func_hl = Thread(target=func, args=args, kwargs=kwargs)
        func_hl.start()
        return func_hl

    return async_func


def users_with_perm(app_dot_codename):
    """
    app_dot_codename: "app.perm_codename".
    """
    app_label, codename = app_dot_codename.split('.')
    return get_user_model().objects.filter(
        Q(is_superuser=True) |
        Q(groups__permissions__content_type__app_label=app_label, groups__permissions__codename=codename) |
        Q(user_permissions__content_type__app_label=app_label, user_permissions__codename=codename)).distinct()


def serialize_dict(dic):
    return json.loads(JSONRenderer().render(dic))


def delta_date(d, now=None):
    if not isinstance(d, datetime.datetime):
        d = datetime.datetime(d.year, d.month, d.day)
    if now and not isinstance(now, datetime.datetime):
        now = datetime.datetime(now.year, now.month, now.day)

    now = now or datetime.datetime.now(utc if is_aware(d) else None)

    delta = now - d

    # Deal with leapyears by subtracing the number of leapdays
    leapdays = calendar.leapdays(d.year, now.year)
    if leapdays != 0:
        if calendar.isleap(d.year):
            leapdays -= 1
        elif calendar.isleap(now.year):
            leapdays += 1
    delta -= timedelta(leapdays)
    return delta


def send_password_reset_link(user):
    # Nota: o import deve estar aqui para evitar erro:
    # django.core.exceptions.ImproperlyConfigured: AUTH_USER_MODEL refers to model 'base.Usuario' that has not been installed
    from django.contrib.auth.forms import PasswordResetForm
    form = PasswordResetForm(data={'email': user.email})
    if form.is_valid():
        request = HttpRequest()
        request.META['SERVER_NAME'] = settings.ALLOWED_HOSTS[0]
        request.META['SERVER_PORT'] = '80'
        form.save(request=request)


def digits(txt):
    """
    Keep only digits in txt.

    >>> digits('15-12/1985.')
    >>> '15121985'
    """
    if txt:
        return re.sub('\D', '', txt)
    return txt


def qs_to_csv_response_postres(qs, filename):
    sql, params = qs.query.sql_with_params()
    sql = f"COPY ({sql}) TO STDOUT WITH (FORMAT CSV, HEADER, DELIMITER E',')"
    filename = f'{filename}-{timezone.now():%Y-%m-%d_%H-%M-%S}.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename={filename}'
    with connection.cursor() as cur:
        sql = cur.mogrify(sql, params)
        cur.copy_expert(sql, response)
    return response


def qs_to_csv_response(qs:QuerySet, filename, mapping=None):
    df = pd.DataFrame.from_records(qs)
    date_columns = [x for x in df.columns if 'data' in x.lower()]
    for dc in date_columns:
        df[dc] = pd.to_datetime(df[dc], utc=True, errors='raise')
        df[dc] = df[dc].dt.strftime("%d/%m/%Y")
    if mapping:
        df.rename(columns=mapping, inplace=True)

    filename = f'{filename}-{timezone.now():%Y-%m-%d_%H-%M-%S}.csv'
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename={filename}'
    df.to_csv(path_or_buf=response, encoding='latin1', date_format='%d/%m/%Y')
    return response


def qs_to_xlsx_response(qs:QuerySet, filename, mapping=None):
    df = pd.DataFrame.from_records(qs)
    date_columns = [x for x in df.columns if 'data' in x.lower()]
    for dc in date_columns:
        try:
            df[dc] = pd.to_datetime(df[dc], errors='ignore', infer_datetime_format=True, utc=True).dt.strftime("%d/%m/%Y")
        except:
            pass
    if mapping:
        df.rename(columns=(mapping), inplace=True)

    with BytesIO() as b:
        # Use the StringIO object as the filehandle.
        writer = pd.ExcelWriter(b, engine='xlsxwriter')
        df.to_excel(writer, sheet_name='Sheet1')
        writer.save()
        filename = f'{filename}-{timezone.now():%Y-%m-%d_%H-%M-%S}.xlsx'
        response = HttpResponse(b.getvalue(), content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = f'attachment; filename={filename}'
        return response


@run_async
def enviar_email_de_erro(err, mensagem, assunto=None):
    try:
        if assunto is None:
            assunto = u'ERROR %s' % str(err.args[0])
        mail_admins(subject=assunto,
                    message=mensagem,
                    fail_silently=False)
    except:
        raise


class DataExtenso:
    JANEIRO = 'Janeiro'
    FEVEREIRO = 'Fevereiro'
    MARCO = 'Março'
    ABRIL = 'Abril'
    MAIO = 'Maio'
    JUNHO = 'Junho'
    JULHO = 'Julho'
    AGOSTO = 'Agosto'
    SETEMBRO = 'Setembro'
    OUTUBRO = 'Outubro'
    NOVEMBRO = 'Novembro'
    DEZEMBRO = 'Dezembro'

    SEGUNDA = 0
    TERCA = 1
    QUARTA = 2
    QUINTA = 3
    SEXTA = 4
    SABADO = 5
    DOMINGO = 6

    def __init__(self, data):
        self.data = data

    def _get_choices(self):
        return [
            [1, DataExtenso.JANEIRO],
            [2, DataExtenso.FEVEREIRO],
            [3, DataExtenso.MARCO],
            [4, DataExtenso.ABRIL],
            [5, DataExtenso.MAIO],
            [6, DataExtenso.JUNHO],
            [7, DataExtenso.JULHO],
            [8, DataExtenso.AGOSTO],
            [9, DataExtenso.SETEMBRO],
            [10, DataExtenso.OUTUBRO],
            [11, DataExtenso.NOVEMBRO],
            [12, DataExtenso.DEZEMBRO],
        ]

    @classmethod
    def get_choices(cls):
        return cls()._get_choices()

    def data_extenso(self, fmt='%d de {} de %Y'):
        '''
        s[s.find('{')+1:+s.find('}')]
        Exemplo
        '%d de {M} de %Y'  -> 03 de Dezembro de 2020
        '%d de {m} de %Y'  -> 03 de dezembro de 2020
        '%d de {MM} de %Y'  -> 03 de DEZEMBRO de 2020
        '%d-{m:3}-> 03-dez
        :param fmt:
        :return:
        '''
        #{D:02}d {H:02}h {M:02}m {S:02}s
        meses_choice = self._get_choices()
        parse = fmt[fmt.find('{') + 1 : fmt.find('}')].split(':')
        fmt = fmt[0:fmt.find('{')] + '{' + fmt[fmt.find('}'):]

        if parse[0] == 'M':
            mes_ext = meses_choice[self.data.month-1][1].upper()
        elif parse[0] == 'm':
            mes_ext = meses_choice[self.data.month-1][1]
        else:
            mes_ext = meses_choice[self.data.month-1][1]

        if len(parse) > 1:
            mes_ext = mes_ext[:int(parse[1])]
        return str(self.data.strftime(fmt)).format(mes_ext)

    def get_mes(self):
        numero = self.data.month
        for id, nome in self._get_choices():
            if int(id) == int(numero):
                return nome
        return 'Desconhecido'

    def get_numero(self, mes):
        return self.data.month


class ToDate(Func):
    function = 'TO_DATE'
    template = '%(function)s(%(expressions)s, %(format)s)'


class AgeYear(Func):
    function = 'AGE'
    template = 'EXTRACT(YEAR FROM %(function)s(%(expressions)s))::INTEGER'

    class CastWeek():
        def __init__(self, week):
            self.week = week

        def ano(self):
            return self.week.year

        def semana(self):
            return self.week.week

class Round(Func):
    function = 'ROUND'
    template='%(function)s(%(expressions)s::numeric, 2)'

class SumCount(Sum):
    template = '%(function)s(Count(%(distinct)s%(expressions)s))'


class DataSemana():

    def __init__(self, ano, semana):
        self.ano = ano
        self.semana = semana

    def get_periodo(self, semana_a_considerar=(0,0)):
        _semana = Week(self.ano, self.semana, system='cdc')
        semana_de = _semana + min(semana_a_considerar)
        semana_ate = _semana + max(semana_a_considerar)
        return (semana_de.startdate(), semana_ate.enddate())

    def get_semanas(self, semana_a_considerar=(0,0)):
        _semana = Week(self.ano, self.semana, system='cdc')
        semana_de = _semana + min(semana_a_considerar)
        semana_ate = _semana + max(semana_a_considerar)
        return (semana_de, semana_ate)

    def get_data_inicial(self):
        return self.get_periodo()[0]

    def get_data_final(self):
        return self.get_periodo()[1]

    @classmethod
    def get_semana(cls, data):
        week = Week.fromdate(data, system='cdc')
        return DataSemana(week.year, week.week)

    @classmethod
    def get_semanas_ano(cls, ano):
        total_semanas = Year(ano).totalweeks()
        return ['{}/{}'.format(semana, ano) for semana in range(1, total_semanas)]


def to_date(data_str):
    data = None
    if data_str:
        if data_str.find('T') > 0 and len(data_str) == 24:
            data = datetime.datetime.strptime(data_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        elif data_str.find('-') > 0:
            data = datetime.datetime.strptime(data_str, '%Y-%m-%d')
        elif data_str.find('/') > 0:
            if len(data_str) == 10:
                data = datetime.datetime.strptime(data_str, '%d/%m/%Y')
            elif len(data_str) == 8:
                data = datetime.datetime.strptime(data_str, '%d/%m/%y')
        else:
            return None
    return data


class DateTimeDecoder(json.JSONDecoder):
    def __init__(self, *args, **kargs):
        JSONDecoder.__init__(self, object_hook=self.dict_to_object,
                             *args, **kargs)

    def dict_to_object(self, _data):
        if '__type__' not in _data:
            return _data
        _type = _data.pop('__type__')
        module = importlib.import_module(_type.split('.')[0])
        try:
            func = getattr(module, _type.split('.')[1])
            dateobj = func.fromisoformat(_data['value'])
            return dateobj
        except:
            _data['__type__'] = _type
            return _data


class DateTimeEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return {
                 '__type__': '{0}.{1}'.format(obj.__class__.__module__,obj.__class__.__name__),
                 'value': obj.isoformat()
            }

        elif isinstance(obj, datetime.timedelta):
            return {
                 '__type__': type(obj).__name__,
                 'value': (datetime.datetime.min + obj).time().isoformat()
            }
        return super(DateTimeEncoder, self).default(obj)


def csv_to_json(path_csv_file):
    """
    :param path_csv_file: path do arquivo csv
    :return: Json com dados do arquivo csv
    """
    import csv
    import json
    json_data = None
    with open(path_csv_file) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    return json.dumps(rows)


def get_size(obj, seen=None):
    """Recursively finds size of objects"""
    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)
    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, '__dict__'):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])
    return size
