DjaoDjin deployutils
====================

This Python module enables a Django or Flask project to seamlessly integrate
behind the [HTTP session manager reverse proxy](https://github.com/djaodjin/djaoapp).
It will replace the default ``django.contrib.sessions``
and ``AUTHENTICATION_BACKENDS`` to decode sessions forwarded to your project
by the HTTP session manager.

Tested with

- **Python:** 3.7, **Django:** 2.2 ([LTS](https://www.djangoproject.com/download/)), **Django Rest Framework:** 3.12
- **Python:** 3.7, **Django:** 4.0 (latest), **Django Rest Framework:** 3.12
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


    $ virtualenv _installTop_
    $ cd _installTop_
    $ source bin/activate
    $ git clone https://github.com/djaodjin/djaodjin-deployutils.git
    $ cd djaodjin-deployutils
    $ pip install -r testsite/requirements.txt


Create the credentials file with a ``DJAODJIN_SECRET_KEY`` and the empty db.


    $ make initdb


Run the web application


    $ python manage.py runserver


Browse to http://localhost:8000



Bonus commands
--------------

Commands to upload/download resources
-------------------------------------


    $ python manage.py download_resources
    $ python manage.py upload_resources


Not all assets are stored under source control. Images, videos, etc. are
better kept outside the git repository. These two commands are used to
download the extra resources into the webapp htdocs/ directory from
the stage server and upload them from the webapp htdocs/ directory to
the stage server respectively.


Fetch/merge from the remote git repository and downlad the extra resources
from the stage server.

Using configuration files from a S3 bucket
------------------------------------------


    $ python manage.py upload_configs --location s3://__example__ credentials site.conf
