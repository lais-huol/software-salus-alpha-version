import os

import redis
from django.contrib.messages import constants as messages
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse_lazy

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AMBIENTE_PROD = os.environ.get('BRANCH') == 'master'

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '8(t=b5msb1m8cka)b&@%w0b%ddp0ujmmm12zvolbo=p+c#e_($'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []
# ADMINS = [('Jailton', 'jailton.paiva@lais.huol.ufrn.br'),
#           ('Sedir', 'sedir.morais@lais.huol.ufrn.br'),
#           ('Túlio', 'tulio.paiva@lais.huol.ufrn.br')]

# Application definition

MODULE_APPS = [
    'notificacoes',
    'sifilis',
]

INSTALLED_APPS = [
    'newadmin',
    'api',
    'base',
    'indicadores',
    'administracao',
    *MODULE_APPS,

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django_extensions',
    'rest_framework',
    'rest_framework_datatables',
    'bootstrapform',
    'crispy_forms',
    'formtools',
    'notifications',
    'localflavor',
    'django_cron',
    'djrichtextfield',
    'loginas',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert-success',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert-danger',
}

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
        'rest_framework_datatables.renderers.DatatablesRenderer',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework_datatables.filters.DatatablesFilterBackend',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework_datatables.pagination.DatatablesPageNumberPagination',
    'PAGE_SIZE': 50,
}

AUTH_USER_MODEL = 'base.Usuario'

ROOT_URLCONF = 'vigilancianatal.urls'

TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [TEMPLATES_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'vigilancianatal.context_processors.menus',
                'vigilancianatal.context_processors.active_apps',
                'vigilancianatal.context_processors.processor',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'loginas.context_processors.impersonated_session_status',
            ],
        },
    },
]

CRISPY_TEMPLATE_PACK = 'bootstrap4'

WSGI_APPLICATION = 'vigilancianatal.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LOGIN_URL = reverse_lazy('base:login')
LOGIN_REDIRECT_URL = '/'

LOGOUT_URL = reverse_lazy('loginas-logout')
LOGOUT_REDIRECT_URL = '/'

LOGINAS_LOGOUT_REDIRECT_URL = reverse_lazy('admin:index')
CAN_LOGIN_AS = lambda request, target_user: request.user.is_superuser and not target_user.is_superuser
LOGINAS_USERNAME_FIELD = 'cpf'

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Recife'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'

STATIC_ROOT = os.path.join(BASE_DIR, 'static')

ESUSVE_PATH = ''
CEPS_PATH = ''

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

MEDIA_URL = '/media/'

DISTRITO_OUTROS = 'Outro'
BAIRRO_OUTROS = 'OUTRO'
CODIGO_IBGE_MUNICIPIO_BASE = '240810'
CODIGO_IBGE_UF_BASE = '24'
CODIGO_IBGE_OUTRO = '999999'

BARRAMENTO_LAIS = {
    'url': 'http://barramento.lais.huol.ufrn.br/api/v2',
    'token': 'f9675dce0838e02db5f70faecd023d7150ae61d6',
}

X_FRAME_OPTIONS = 'SAMEORIGIN'

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache', #django_redis
        # 'BACKEND': 'redis_cache.RedisCache', #django-redis-cache-2.1.1
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient'
        },
        'KEY_PREFIX': 'svigilancia'
    }
}

SELECT2_CACHE_BACKEND = 'default'
SELECT2_CACHE_PREFIX = 'select2'

cron_importar_notificacoes_via_api = 'notificacoes.cron.ProcessarNotificacoesAPICronJob'
cron_importar_notificacoes_via_csv = 'notificacoes.cron.ProcessarNotificacoesCSVCronJob'

if AMBIENTE_PROD:
    CRON_CLASSES = [
        cron_importar_notificacoes_via_api,
        'notificacoes.cron.ProcessarDadosCensoLeitosImdCronJob',
        'notificacoes.cron.DefinirCnesReferenciaCronJob',
        'notificacoes.cron.DefinirPessoaNaNotificacaoCronJob',
        'notificacoes.cron.CachePainelPublicoCronJob',
    ]
else:
    CRON_CLASSES = []

IMPORTAR_NOTIFICACOES_VIA_CSV = cron_importar_notificacoes_via_csv in CRON_CLASSES
IMPORTAR_NOTIFICACOES_VIA_API = cron_importar_notificacoes_via_api in CRON_CLASSES
if IMPORTAR_NOTIFICACOES_VIA_CSV and IMPORTAR_NOTIFICACOES_VIA_API:
    raise ImproperlyConfigured('Escolha {} ou {} para incluir em CRON_CLASSES'.format(
        cron_importar_notificacoes_via_api, cron_importar_notificacoes_via_csv
    ))


DJANGO_CRON_LOCK_BACKEND = 'django_cron.backends.lock.file.FileLock'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# TODO: retirar quando for para local_settings de produção
LOCALIZA_SUS = {
    'url': 'https://localizasus.lais.ufrn.br',
    'token': '2c07bd3770aa8c3f954cfc3efa9e96b7d64b422d',
}

DJRICHTEXTFIELD_CONFIG = {
    'js': ['//cdn.ckeditor.com/4.14.1/full-all/ckeditor.js', '/static/js/N1ED-editor/plugin.js'],
    'init_template': 'djrichtextfield/init/ckeditor.js',
    'settings': {  # CKEditor
        'format_tags': 'p;h1;h2;h3;h4',
        'width': 700,
        'disableNativeSpellChecker': False,
        'extraPlugins': "mentions,N1ED-editor",
    },
    'defaultLanguage': 'pt'
}

MAPBOX_ACCESS_TOKEN = 'pk.eyJ1Ijoic2VkaXIiLCJhIjoiY2s5dXFpNTVxMDRvNzNudWxuZXZxdjB2MCJ9.C6m6FyWhUH26_mFl5wrfPg'


try:
    from .local_settings import *
except ImportError:
    raise Exception("A local_settings.py file is required to run this project")
