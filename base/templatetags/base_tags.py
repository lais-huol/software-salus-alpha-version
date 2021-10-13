import re
from datetime import datetime

from django import template
from urllib.parse import urlencode

from base.alertas import Alerta
from base.utils import delta_date

import json

numeric_test = re.compile("^\d+$")
register = template.Library()


@register.filter
def getattribute(value, arg):
    """Gets an attribute of an object dynamically from a string name"""
    if hasattr(value, arg):
        return getattr(value, arg)
    try:
        return value[arg]
    except (KeyError, TypeError):
        return ''


@register.filter
def get(value, arg):
    """Gets an attribute of an object dynamically from a string name"""
    return value[arg]


@register.filter
def getornone(value, arg):
    """Gets an attribute of an object dynamically from a string name"""
    try:
        return value[arg]
    except KeyError:
        return None

@register.filter
def asdate(value):
    """Gets an attribute of an object dynamically from a string name"""
    try:
        if value is not None and isinstance(value, str) and 'T' in value:
            return datetime.strptime(value.split('T')[0], '%Y-%m-%d')
        elif  value is not None and isinstance(value, str) and len(value)==10 and '-' in value:
            return datetime.strptime(value, '%Y-%m-%d')
        return datetime.strptime(value, '%d/%m/%Y')
    except ValueError:
        return value
    except TypeError:
        return ''

@register.filter
def asdays(value: datetime):
    try:
        delta = delta_date(value)
        dias = delta.days
        return f'{dias} dia{"s" if dias!=1 else ""}'
    except AttributeError:
        return value


@register.filter
def sincehours(value: datetime):
    delta = delta_date(value)
    return int(delta.seconds/3600)


@register.filter
def notification_action_url(notification):
    return Alerta.get_action_url(notification)


@register.filter
def notification_actor_title(notification):
    if notification.actor_content_type.model == 'contenttype':
        return notification.actor.model_class()._meta.verbose_name_plural
    return str(notification.actor)


@register.filter()
def split(value, arg):
    return value.split(arg)

@register.simple_tag()
def slice_by_find(value, arg, arg2):
    if arg2 == 'prior':
        return value[:value.find(arg)]
    elif arg2 == 'next':
        return value[value.find(arg)+1:]


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    query = context['request'].GET.copy()
    query.update(kwargs)
    return urlencode(query)


@register.simple_tag
def get_last_commit():
    import subprocess
    return subprocess.check_output(["git", 'log', '-n1', '--format=format:"%h"']).decode().strip().replace("\"", "")


@register.simple_tag
def get_branch():
    import subprocess
    return subprocess.check_output(["git", 'log', '-n1', '--format=format:"%D"']).decode().strip().replace("\"", "").split('/')[-1]


@register.simple_tag
def get_branch_full():
    import subprocess
    return subprocess.check_output(["git", 'log', '-n1', '--format=format:"%D"']).decode().strip().replace("\"", "")

@register.filter
def asjson(value):
    return json.dumps(value)

@register.simple_tag
def is_app_installed(app):
  from django.apps import apps
  return apps.is_installed(app)
