Integration with Django
=======================

`DjaoApp <https://github.com/djaodjin/djaoapp>`_ handles accounts, billing
and access control. Other application HTTP requests have been setup
to be forwarded to the application logic server under specific conditions
(ex: authenticated user, active subscription, etc.).

To retrieve the session data, and authenticated user information, forwarded
by the DjaoApp HTTP proxy in the server-side Django application, start by
updating your `settings.py` as such:

.. code-block:: python

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

It will replace the default ``django.contrib.sessions``
and ``AUTHENTICATION_BACKENDS`` to decode sessions forwarded to your project
by the HTTP session proxy.

Create a ``credentials`` file that contains the ``DJAODJIN_SECRET_KEY``.
(You can also pass ``DJAODJIN_SECRET_KEY`` as a shell environment variable.)

.. code-block:: bash

    $ cat ./credentials
    # Authentication for djaodjin firewall
    DJAODJIN_SECRET_KEY = "__your_secret_key__"


(for stand-alone testing) Add the mockup views in urls.py

.. code-block:: python

     urlpatterns = [
     ...
    +    re_path(r'^', include('deployutils.apps.django.mockup.urls')),
     ...
     ]

Helper mixins
-------------

In the cases were you want to customize the user interface based on the
roles, organizations and subscriptions attached to a user, deployutils
provides a set of useful mixins that you can extend
in your `Views` in order to access the session data:

- `deployutils.apps.django.mixins.AccessiblesMixin <https://github.com/djaodjin/djaodjin-deployutils/blob/a72d73072c72a9538d87d3427d36fd59f1da2726/deployutils/apps/django/mixins.py#L38>`_ to test if a user has a specific role on an organization.
- `deployutils.apps.django.mixins.AccountMixin <https://github.com/djaodjin/djaodjin-deployutils/blob/a72d73072c72a9538d87d3427d36fd59f1da2726/deployutils/apps/django/mixins.py#L130>`_ to retrieve an account object associated to a slug parameter


we have seen previously that `request.user` is set automatically by
`deployutils.apps.django.middleware.SessionMiddleware`.
You can also access the raw session data by accessing it by key in
`request.session`. For example to retrieve the dictionnary of roles
for the authenticated user, use the following code:

.. code-block:: python

    roles = request.session.get('roles', {})


You can also add `deployutils.apps.django.mixins.AccessiblesMixin`
to your views and benefit from often used methods such as
`managed_accounts`, the list of all organizations managed
by the authenticated user. Example:

.. code-block:: python

    from django.views.generic import TemplateView
    from deployutils.apps.django.mixins import AccessiblesMixin

    class AppView(AccessiblesMixin, TemplateView):
    ...
        def get_context_data(self, *args, **kwargs):
            context = super(AppView, self).get_context_data(*args, **kwargs)
            context.update({'managed_accounts': self.managed_accounts})
            return context


Other methods available in the mixin are:

.. autoproperty:: deployutils.apps.django.mixins.AccessiblesMixin.accessible_plans
.. autoproperty:: deployutils.apps.django.mixins.AccessiblesMixin.accessible_profiles
.. automethod:: deployutils.apps.django.mixins.AccessiblesMixin.get_accessible_plans
.. automethod:: deployutils.apps.django.mixins.AccessiblesMixin.get_accessible_profiles
.. automethod:: deployutils.apps.django.mixins.AccessiblesMixin.get_managed
.. automethod:: deployutils.apps.django.mixins.AccessiblesMixin.has_role
.. autoproperty:: deployutils.apps.django.mixins.AccessiblesMixin.managed_accounts
.. automethod:: deployutils.apps.django.mixins.AccessiblesMixin.manages
.. autoproperty:: deployutils.apps.django.mixins.AccessiblesMixin.manages_broker
