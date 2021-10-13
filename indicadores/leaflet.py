import datetime
import json
import uuid

from django.conf import settings
from jinja2 import PackageLoader, Environment

CONTENT_FILENAME = "content.html"
PAGE_FILENAME = "page.html"

pl = PackageLoader('indicadores', 'templates/leaflet')
jinja2_env = Environment(lstrip_blocks=True, trim_blocks=True, loader=pl)

template_content = jinja2_env.get_template(CONTENT_FILENAME)


class RawJavaScriptText:
    def __init__(self, jstext):
        self._jstext = jstext

    def get_jstext(self):
        return self._jstext


class RawJsJSONEncoder(json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        json.JSONEncoder.__init__(self, *args, **kwargs)
        self._replacement_map = {}

    def default(self, o):
        if isinstance(o, RawJavaScriptText):
            key = uuid.uuid4().hex
            self._replacement_map[key] = o.get_jstext()
            return key
        else:
            return json.JSONEncoder.default(self, o)

    def encode(self, o):
        result = json.JSONEncoder.encode(self, o)
        for k, v in self._replacement_map.items():
             result = result.replace('"%s"' % (k,), v)
        return result


class Leaflet():
    def __init__(self, id, opts_base_map=None, **kwargs):
        self.id = id
        self.access_token = settings.MAPBOX_ACCESS_TOKEN
        self.container_extras = []
        self.opts = {'id_container': id}
        self.opts_base_map = {
            'attribution': '&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>, ©<a href="https://www.mapbox.com/">Mapbox</a>',
            'maxZoom': 18,
            'id': 'mapbox/streets-v11',
            'tileSize': 512,
            'zoomOffset': -1,
            'accessToken': self.access_token
        }
        self.container_title = kwargs.get('container_title', '')
        self.exibir_titulo = kwargs.get('exibir_titulo', True)
        self.titulo = ''
        self.exibir_identificador = kwargs.get('exibir_titulo', False)

        if kwargs.get('legend_heatmap', None):
            self.add_heatmap_legend()
        if opts_base_map:
            self.opts_base_map.update(opts_base_map)
        self.opts['js_base_map_opts'] = self.opts_base_map


    def add_heatmap_legend(self):
        self.container_extras.append(f'<div id="legend_{self.id}" class="legend-area"><p class="legend-text">Intensidade</p>'
                                     f'<span id="legend_min_{self.id}" class="legend-min"></span><span '
                                     f'class="legend-max" id="legend_max_{self.id}"></span>'
                                     f'<img id="legend_grad_{self.id}" style="width:100%"></div>')

    def set_heatmap_data(self, data):
        self.opts['heatmap_data'] = data

    def buildcontainer(self):
        container_pre = ''
        if self.exibir_titulo:
            container_pre = f'<p class="leaflet-title text-center">{self.titulo}</p>'
        content_extras = ''.join(self.container_extras)
        return f'{container_pre}<div id="{self.id}" class="map">{content_extras}</div>'

    def buildcontent(self):
        context = {key: json.dumps(value, cls=RawJsJSONEncoder) for key, value in self.opts.items()}
        return template_content.render(**context)
