DjaoDjin deployutils
====================

This Django app contains the commands used to manage the process from
development to code in production at DjaoDjin.

Install
-------

1. Install deployutils into your virtualenv

    $ python setup.py install


2. Add _deployutils_ to the INSTALLED_APPS

3. Configure the DEPLOYUTILS variables in the project settings

* DRY_RUN                   Do not execute, just show the commands
* DEPLOYED_WEBAPP_ROOT      Directory on DEPLOYED_SERVERS where to find webapps
* DEPLOYED_SERVERS          List of Hostname/IP webapps are deployed to
* RESOURCES_MACHINE         URL to the resources not under source control
                            (ex: git@example.com)


Commands to upload/download resources
-------------------------------------

    $ python manage.py download_resources
    $ python manage.py upload_resources

Not all assets are stored under source control. Images, videos, etc. are
better kept outside the git repository. These two commands are used to
download the extra resources into the webapp htdocs/ directory from
the stage server and upload them from the webapp htdocs/ directory to
the stage server respectively.

Commands to setup on deployed servers
-------------------------------------

    $ python manage.py pullapp

Fetch/merge from the remote git repository and downlad the extra resources
from the stage server.


Commnands to deploy webapp
--------------------------

    $ python manage.py syncapp

This command will trigger a "python manage.py pullapp" on the deployed server.

Note that you will need to setup the deployed machine with appropriate
authentication.


    $ python manage.py pushapp

Sometimes you are trying to test a hotfix directly in production. To that
purpose *pushapp* will rsync the webapp directly from your dev system
to the production servers.


