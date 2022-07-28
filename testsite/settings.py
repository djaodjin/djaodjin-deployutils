"""
Django settings for deployutils testsite project.
"""

import logging, os, sys

from deployutils.apps.django.compat import reverse_lazy
from deployutils.configs import load_config, update_settings


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_NAME = os.path.basename(BASE_DIR)
RUN_DIR = os.getenv('RUN_DIR', os.getcwd())
DB_NAME = os.path.join(RUN_DIR, 'db.sqlite')
LOG_FILE = os.path.join(RUN_DIR, 'testsite-app.log')

update_settings(sys.modules[__name__],
    load_config(APP_NAME, 'credentials', 'site.conf', verbose=True,
        location=os.getenv("SETTINGS_LOCATION", None),
        passphrase=os.getenv("SETTINGS_CRYPT_KEY", None)))

if not hasattr(sys.modules[__name__], "SECRET_KEY"):
    from random import choice
    SECRET_KEY = "".join([choice(
        "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)])

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Installed apps
# --------------
if DEBUG:
    ENV_INSTALLED_APPS = (
        'debug_toolbar',
        'django_extensions',
        )
else:
    ENV_INSTALLED_APPS = tuple([])

INSTALLED_APPS = ENV_INSTALLED_APPS + (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'deployutils.apps.django',
    'testsite'
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'formatters': {
        'simple': {
            'format': 'X X %(levelname)s [%(asctime)s] %(message)s',
            'datefmt': '%d/%b/%Y:%H:%M:%S %z'
        },
        'json': {
            '()': 'deployutils.apps.django.logging.JSONFormatter',
            'format':
            'gunicorn.' + APP_NAME + '.app: [%(process)d] '\
                '%(log_level)s %(remote_addr)s %(http_host)s %(username)s'\
                ' [%(asctime)s] %(message)s',
            'datefmt': '%d/%b/%Y:%H:%M:%S %z',
            'replace': False,
            'whitelists': {
                'record': [
                    'nb_queries', 'queries_duration',
                    'charge', 'amount', 'unit', 'modified',
                    'customer', 'organization', 'provider'],
            }
        },
    },
    'handlers': {
        'db_log': {
            'level': 'DEBUG',
            'formatter': 'simple',
            'filters': ['require_debug_true'],
            'class':'logging.StreamHandler',
        },
        'log':{
            'level':'DEBUG',
            'formatter': 'json',
            'class':'logging.StreamHandler',
        },
    },
    'loggers': {
        'deployutils': {
            'level': 'DEBUG',
            'propagate': True,
        },
#        'django.db.backends': {
#           'handlers': ['db_log'],
#           'level': 'DEBUG',
#        },
        # This is the root logger. Apparently setting the level has no effect
        # ... anymore?
        '': {
            'handlers': ['log'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}
if logging.getLogger('gunicorn.error').handlers:
    LOGGING['handlers']['log'].update({
        'class':'logging.handlers.WatchedFileHandler',
        'filename': LOG_FILE
    })


# HTTP Pipeline
if DEBUG:
    MIDDLEWARE = tuple([
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    ])
else:
    MIDDLEWARE = ()

MIDDLEWARE += (
    'django.middleware.security.SecurityMiddleware',
    'deployutils.apps.django.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

MIDDLEWARE_CLASSES = MIDDLEWARE

ROOT_URLCONF = 'testsite.urls'
WSGI_APPLICATION = 'testsite.wsgi.application'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'testsite', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Static asset files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/
STATIC_URL = '/static/'


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DB_NAME,
    }
}

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [{'NAME':
    'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
}, {
    'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
}, {
    'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
}, {
    'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
}]


# Session settings
# ----------------
# The default session serializer switched to JSONSerializer in Django 1.6
# but just to be sure:
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'
SESSION_ENGINE = 'deployutils.apps.django.backends.encrypted_cookies'
#SESSION_ENGINE = 'deployutils.apps.django.backends.jwt_session_store'

# The Django Middleware expects to find the authentication backend
# before returning an authenticated user model.
# In django.contrib.auth.__init__.py:get_user, the following code
# will prevent us to use either our custom backend or the backup
# one if both are not specified in AUTHENTICATION_BACKENDS.
#
#    try:
#        user_id = request.session[SESSION_KEY]
#        backend_path = request.session[BACKEND_SESSION_KEY]
#    except KeyError, err:
#        pass
#    else:
#        if backend_path in settings.AUTHENTICATION_BACKENDS:
#            backend = load_backend(backend_path)
AUTHENTICATION_BACKENDS = (
    'deployutils.apps.django.backends.auth.ProxyUserBackend',
#    'django.contrib.auth.backends.RemoteUserBackend',
)

DEPLOYUTILS = {
    # Hardcoded mockups here.
    'MOCKUP_SESSIONS': {
        'donny': {
            'username': 'donny',
            'email': 'donny@example.com',
            'full_name': 'Donny Deploy',
            'roles': {
                'manager': [{
                    'slug': 'testsite', 'printable_name': 'Testsite'}]}},
    },
    'ALLOWED_NO_SESSION': [
        STATIC_URL,
        reverse_lazy('login'),
        reverse_lazy('index')],
    'BACKEND_SESSION_STORE': 'django.contrib.sessions.backends.db.SessionStore',
}

# User settings
# -------------
LOGIN_REDIRECT_URL = '/'

# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Debug toolbar
# -------------
DEBUG_TOOLBAR_PATCH_SETTINGS = False
DEBUG_TOOLBAR_CONFIG = {
    'JQUERY_URL': '/static/vendor/jquery.js',
    'SHOW_COLLAPSED': True,
    'SHOW_TEMPLATE_CONTEXT': True,
}

INTERNAL_IPS = ('127.0.0.1', '::1')
