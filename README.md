DjaoDjin deployutils
====================

This Python module enables a Django or Flask project to seamlessly integrate
behind the [HTTP session manager reverse proxy](https://github.com/djaodjin/djaoapp).
It will replace the default ``django.contrib.sessions``
and ``AUTHENTICATION_BACKENDS`` to decode sessions forwarded to your project
by the HTTP session manager.

Tested with

- **Python:** 3.7, **Django:** 3.2 ([LTS](https://www.djangoproject.com/download/)), **Django Rest Framework:** 3.12
- **Python:** 3.10, **Django:** 4.0 (latest), **Django Rest Framework:** 3.12
- **Python:** 2.7, **Django:** 1.11 (legacy), **Django Rest Framework:** 3.9.4

[More technical documentation](https://djaodjin.com/docs/technical/)

Install
-------

Install deployutils into your environment


    $ pip install djaodjin-deployutils

See the steps to [integrate with a Django project](docs/deploy-django.rst).


Development
-----------

Clone the repository in a virtualenv and install the prerequisites


    $ python3 -m .venv
    $ source .venv/bin/activate
    $ pip install -r testsite/requirements.txt


Create the credentials file with a ``DJAODJIN_SECRET_KEY`` and the empty db.


    $ make initdb


Run the web application


    $ python manage.py runserver


Browse to http://localhost:8000

Release Notes
=============

Tested with

- **Python:** 3.7, **Django:** 3.2 ([LTS](https://www.djangoproject.com/download/))
- **Python:** 3.10, **Django:** 4.2 (latest)
- **Python:** 2.7, **Django:** 1.11 (legacy) - use testsite/requirements-legacy.txt

0.10.9

  * enables using `get_accessible_profiles` without deriving from Mixin
  * adds `manages_broker` as a shortcut

[previous release notes](changelog)
