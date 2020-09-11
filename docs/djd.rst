Deploying to production
=======================

Assets are Plain-Old-Data (POD) files that need to be transferred from
the server to the client browser, i.e. typically Javascript files (.js)
and CSS layout files (.css).

Setting up a workspace
----------------------

The first step is to retrieve an API key from the site project. To do that
visit the user profile for an admin (i.e. profile manager) of the site
you created
(ex: https://*mysite*.djaoapp.com/users/*myprofile*/) and create an API Key.

Then on the command line run:

```
$ pip install djaodjin-deployutils
$ djd init
saved configuration in $HOME/.djd/credentials
```

Deploying a theme
-----------------

Assuming the production .js and .css bundles are compiled into a directory
called dist/themes/public and the theme templates are located in a directory
called dist/themes/templates:

```
$ djd upload dist/themes/
```

Deploying a Docker container
----------------------------

First you will need to build and upload the container to a Docker repository.
For example, if you are using the Docker container repository feature from GitHub:

```
$ docker login docker.pkg.github.com -u *USERNAME* -p *TOKEN*
$ docker build .
Successfully built *IMAGE_ID*
$ docker tag *IMAGE_ID* docker.pkg.github.com/*USERNAME*/*mysite*/*mysite*:*TAG_NAME*
```

Once the container is built and uploaded, to deploy it, run:

```
$ djd deploy
```
