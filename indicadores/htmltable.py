import datetime
import json
import uuid

from django.conf import settings
from jinja2 import PackageLoader, Environment

CONTENT_FILENAME = "content.html"

pl = PackageLoader('indicadores', 'templates/tables')
jinja2_env = Environment(lstrip_blocks=True, trim_blocks=True, loader=pl)

template_content = jinja2_env.get_template(CONTENT_FILENAME)


class HTMLTable():
    def __init__(self, id, **kwargs):
        self.id = id
        self.cols = []
        self.rows = []

        if kwargs.get('classes', None):
            self.table_classes = kwargs['classes']
        if kwargs.get('cols', None):
            self.cols = kwargs['cols']

    def set_rows(self, rows):
        self.rows = rows

    def add_rows(self, rows):
        self.rows.extend(rows)

    def buildcontent(self):
        context = self.__dict__
        return template_content.render(**context)
