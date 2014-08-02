Upload resources
================

Images and other media resources occuppy an order of magnitute more disk space
than code. A git repository is not appropriate to store these encoded binary
data files. CSS and Javascript assets served in production are often cached,
bundled and minified versions of the source code in the repository.

The ``upload_resources`` command compiles the CSS and Javascript assets into
a htdocs/static/cache/ directory at the root of our Django project. Then
the command uploads those cached assets together with images and other static
resources stored in an htdocs/ directory at the root of our Django project
to a remote machine.

.. image:: upload_resources.*

Configuration
-------------

Add a ``DEPLOYUTILS_RESOURCES_REMOTE_LOCATION`` variable to the settings.py.
Example::

    $ git diff settings.py
    +DEPLOYUTILS_RESOURCES_REMOTE_LOCATION = "git@dev.example.com:/var/www/example"


Disk storage
------------

When the ``DEPLOYUTILS_RESOURCES_REMOTE_LOCATION`` matches a path that can be
interpreted by rsync, the underlying rsync command will be used to copy files
to the remote location.


S3 Storage
----------

When the ``DEPLOYUTILS_RESOURCES_REMOTE_LOCATION`` starts with s3://, the files
will be uploaded to the specified s3 bucket.

Reminder:
We must have an AWS account and have created an S3 bucket in
order to do that. Furthermore the S3 bucket must be configured to be
web accessible if we either want to serve the resources directly.

Assuming we have an AWS account, we follow these (one-time) steps
to create our bucket::

    # Install the aws command line tools
    $ pip install awscli

    # Create ~/.boto config file
    $ vi ~/.boto
    [Credentials]
    aws_access_key_id = _YOUR_AWS_ACCESS_KEY_ID_
    aws_secret_access_key = _YOUR_AWS_SECRET_ACCESS_KEY_

    # create an S3 bucket matching our project
    $ aws s3api create-bucket --bucket example

    $ vi example-bucket-policy.json
    {  "Version":"2012-10-17",
       "Statement":[{
          "Sid":"AddPerm",
          "Effect":"Allow",
          "Principal": "*",
          "Action":["s3:GetObject"],
          "Resource":["arn:aws:s3:::example/*"]
       }]
    }
    $ aws s3api put-bucket-policy --bucket example \
         --policy file://example-bucket-policy.json

To then upload resources to S3 is easy. Set
``DEPLOYUTILS_RESOURCES_REMOTE_LOCATION`` to the bucket and run
the ``upload_resources`` command::

    $ git diff settings.py
    +DEPLOYUTILS_RESOURCES_REMOTE_LOCATION = 's3://_example_'

    $ python manage.py upload_resources

    # Check we can read the uploaded resource
    $ wget https://_example_.s3.amazonaws.com/_example.png_
