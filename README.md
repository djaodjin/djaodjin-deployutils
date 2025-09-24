DjaoDjin deployutils
====================

This repository contains the code for the command line tool and modules
to seamlessly integrate an appplication with DjaoDjin's
[HTTP session manager proxy](https://github.com/djaodjin/djaoapp).

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

    # When using Django integration
    $ make build-assets


Create the credentials file with a ``DJAODJIN_SECRET_KEY`` and the empty db.


    $ make initdb


Run the web application


    $ python manage.py runserver


Browse to http://localhost:8000

Release Notes
=============

Tested with

- **Python:** 3.10, **Django:** 4.2 ([LTS](https://www.djangoproject.com/download/))
- **Python:** 3.12, **Django:** 5.2 (next)
- **Python:** 3.9, **Django:** 3.2 (legacy)

0.14.1

 * uses settings.ASSETS_CDN when packaging theme templates
 * presents manage.py commands in a separate django_deployutils section
 * adds mockup to retrieve user profile API

[previous release notes](changelog)
