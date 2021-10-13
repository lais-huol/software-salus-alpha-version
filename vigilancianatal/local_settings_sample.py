import logging
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'vigilancianatal',
        'USER': 'postgres',
        'PASSWORD': '',
        'HOST': '127.0.0.1',
        'PORT': '5432',
    }
}

ESUSVE_PATH = '/tmp/esus_ev.csv'
CEPS_PATH = '/dev/app/ceps'
REGULARN_PATH = '/dev/app/regula_rn_solicitacoes.json'

GOOGLE_API_KEY = 'INSIRA A CHAVE DE API'

# Sentry
DSN_DEV = 'https://9ae24f6f54744cb2a5988cddd7ddc04e@o84310.ingest.sentry.io/5265798'
DSN_PROD = 'https://0f7a54b559724210a3a55f009a935f50@o84310.ingest.sentry.io/5265822'
sentry_sdk.init(
    dsn=DSN_DEV,
    integrations=[DjangoIntegration()],

    # If you wish to associate users to errors (assuming you are using
    # django.contrib.auth) you may enable sending PII data.
    send_default_pii=True
)

BARRAMENTO_LAIS = {
    'url': 'http://barramento.lais.huol.ufrn.br/api/v2',
    'token': 'c40979a4d6d531755b1a2e53d0efe7a034835a89',
}
LOCALIZA_SUS = {
    'url': 'https://localizasus.lais.ufrn.br',
    'token': '2c07bd3770aa8c3f954cfc3efa9e96b7d64b422d',
}

AUTENTICACAO_CENSO = {
    'USUARIO': '',
    'SENHA': ''
}
AUTENTICACAO_API_ESUSVE = {
    'USUARIO': '',
    'SENHA': ''
}

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient'
        },
        'KEY_PREFIX': 'svigilancia'
    }
}

class SlowQueriesFilter(logging.Filter):
    """Filter slow queries and attach stack_info."""

    def filter(self, record):
        duration = record.duration
        if duration > 0.1:
            # Same as in _log for when stack_info=True is used.
            fn, lno, func, sinfo = logging.Logger.findCaller(None, True)
            record.stack_info = sinfo
            return True
        return False


class OnlyAppQueriesFilter(logging.Filter):
    def filter(self, record):
        sql_app = '"base_' in record.sql or '"notificacoes_' in record.sql or '"indicadores_' in record.sql
        if sql_app:
            return True
        return False

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'queries_above_300ms': {
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda record: record.duration > 0.3  # output slow queries only
        },
        'slow_queries': {
            '()': SlowQueriesFilter,
        },
        'app_queries': {
            '()': OnlyAppQueriesFilter,
        },

    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {funcName} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'standard': {
            'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/tmp/debug.log',
            'maxBytes': 10*(1024*1024), #10MB
            'backupCount': 2,
            'formatter': 'verbose',
        },
        'logfiledjango': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/tmp/django-db.log',
            # 'filename': os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "log", "logfile"),
            'maxBytes': 10*(1024*1024), #10MB
            'backupCount': 2,
            'formatter': 'standard',
            'filters': ['app_queries']
        },
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'DEBUG',
            'formatter': 'verbose',
        },
        'file_django': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/tmp/django.log',
            'formatter': 'verbose',
        },

    },
    'loggers': {
        'base': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
        'indicadores': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
        'notificacoes': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },

        'django.db': {
            'handlers': ['logfiledjango'],
            'level': 'DEBUG',
            'propagate': False
        }

    }
}