Command line tool
=================

The command line tool, djd, helps deploy updates to a Website running
on `DjaoDjin <https://www.djaodjin.com>`_.

Setting up a workspace
----------------------

The first step is to retrieve API Key to connect the hosted Website
(ex: _ABC***123_) -
`How do I get my API Keys? <https://www.djaodjin.com/docs/faq/#api-keys>`_

Then on the command line run:

.. code-block:: bash

    $ pip install djaodjin-deployutils
    $ djd init
    saved configuration in $HOME/.djd/credentials


Deploying a theme
-----------------

Themes are composed of assets, Plain-Old-Data (POD) files that need to be
transferred from the server to the client browser, i.e. typically Javascript
files (.js) and CSS layout files (.css), and templates, HTML files served
by the Website.

Assuming the production .js and .css bundles are compiled into a directory
called dist/themes/public and the theme templates are located in a directory
called dist/themes/templates:

.. code-block:: bash

    $ djd upload dist/themes/


Deploying a Docker image
------------------------

Check that you have an image present on the image registry of your choice,
 and note the container image location.

Update the information to launch the image in your site's DjaoDjin Control
Panel.

- A container location, i.e. where the Docker image has been uploaded
  (ex: `ghcr.io/djaodjin/djaopsp/livedemo:main`)
- Authentication credentials for the Docker registry (if necessary)
- Runtime Environment variables (if any)

After you push a new image to the registry, deploy it to your Website
with the following command:

.. code-block:: bash

    $ djd deploy
