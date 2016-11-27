"""
Django settings for deployutils testsite project.
"""

import os, sys

from django.core.urlresolvers import reverse_lazy
from deployutils import load_config


# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_NAME = os.path.basename(BASE_DIR)

load_config('credentials', sys.modules[__name__], APP_NAME, verbose=True,
    s3_bucket=os.getenv("SETTINGS_BUCKET", None),
    passphrase=os.getenv("SETTINGS_CRYPT_KEY", None))
load_config('site.conf', sys.modules[__name__], APP_NAME, verbose=True,
    s3_bucket=os.getenv("SETTINGS_BUCKET", None),
    passphrase=os.getenv("SETTINGS_CRYPT_KEY", None))

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
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'deployutils',
    'testsite'
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'logfile':{
            'level':'DEBUG',
            'class':'logging.StreamHandler',
        },
    },
    'loggers': {
        'deployutils': {
            'handlers': ['logfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
        # This is the root logger. Apparently setting the level has no effect
        # ... anymore?
        '': {
            'level': 'WARNING',
            'propagate': False,
        },
    },
}


# HTTP Pipeline
MIDDLEWARE_CLASSES = [
    'django.middleware.security.SecurityMiddleware',
    'deployutils.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

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
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
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
SESSION_ENGINE = 'deployutils.backends.encrypted_cookies'

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
    'deployutils.backends.auth.ProxyUserBackend',
)

DEPLOYUTILS = {
    # Hardcoded mockups here.
    'MOCKUP_SESSIONS': {
        'donny': {
            'username': 'donny',
            'roles': {
                'manager': [{'slug': 'testsite', 'full_name': 'Testsite'}]}},
    },
    'ALLOWED_NO_SESSION': [
        STATIC_URL,
        reverse_lazy('login'), reverse_lazy('registration_register'),
        reverse_lazy('index')]
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
