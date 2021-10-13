import base64
import zlib
import json

from django.utils.safestring import mark_safe


def compress_string_zlib_base64(value, level=6):
    from django.core.serializers.json import DjangoJSONEncoder
    json_str = mark_safe(json.dumps(value, cls=DjangoJSONEncoder))
    json_compressed = zlib.compress(json_str.encode(), level=level)
    return base64.encodebytes(json_compressed).decode('ascii').replace('\n', '')
