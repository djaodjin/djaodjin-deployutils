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

0.11.0

  * makes `manages_broker` a property (breaking change)
  * fixes missing get_context_data
  * adds message about env variables override

[previous release notes](changelog)
