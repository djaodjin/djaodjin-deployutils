Integration with Django
=======================

Update your settings.py


    +from deployutils.configs import load_config

     BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    +APP_NAME = os.path.basename(BASE_DIR)

    +update_settings(sys.modules[__name__],
        load_config(APP_NAME, 'credentials', verbose=True))

     INSTALLED_APPS = (
         'django.contrib.admin',
         'django.contrib.auth',
         'django.contrib.contenttypes',
         'django.contrib.sessions',
         'django.contrib.messages',
         'django.contrib.staticfiles',
    +    'deployutils.apps.django',
     )

     MIDDLEWARE_CLASSES = (
         'django.middleware.security.SecurityMiddleware',
    -    'django.contrib.sessions.middleware.SessionMiddleware',
    +    'deployutils.apps.django.middleware.SessionMiddleware',
         'django.middleware.common.CommonMiddleware',
         'django.middleware.csrf.CsrfViewMiddleware',
         'django.contrib.auth.middleware.AuthenticationMiddleware',
     )

    +AUTHENTICATION_BACKENDS = (
    +    'deployutils.apps.django.backends.auth.ProxyUserBackend',
    +)

    # Session settings
    +SESSION_ENGINE = 'deployutils.apps.django.backends.encrypted_cookies'

    +DEPLOYUTILS = {
    +    # Hardcoded mockups here.
    +    'MOCKUP_SESSIONS': {
    +        'donny': {
    +          'username': 'donny',
    +          'roles': {
    +            'manager': [{
    +               'slug': 'testsite', 'printable_name': 'Testsite'}]}},
    +    },
    +    'ALLOWED_NO_SESSION': (
    +        STATIC_URL, reverse_lazy('login'),)
    +}


Create a ``credentials`` file that contains the ``DJAODJIN_SECRET_KEY``.
(You can also pass ``DJAODJIN_SECRET_KEY`` as a shell environment variable.)


    $ cat ./credentials
    # Authentication for djaodjin firewall
    DJAODJIN_SECRET_KEY = "__your_secret_key__"


(for stand-alone testing) Add the mockup views in urls.py


     urlpatterns = [
     ...
    +    url(r'^', include('deployutils.apps.django.mockup.urls')),
     ...
     ]
