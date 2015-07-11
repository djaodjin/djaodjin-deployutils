# Copyright (c) 2015, Djaodjin Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import getpass, mimetypes, os
from optparse import make_option

import boto
from django.conf import settings as django_settings
from django.core.management.base import BaseCommand

from deployutils import locate_config, crypt

class Command(BaseCommand):
    help = "Encrypt the configuration files and upload them to a S3 bucket."

    option_list = BaseCommand.option_list + (
        make_option('--bucket', action='store', dest='bucket',
            default='deployutils',
            help='Print but do not execute'),
        )

    def handle(self, *args, **options):
        #pylint: disable=too-many-locals
        default_acl = 'private'
        app_name = django_settings.APP_NAME
        passphrase = getpass.getpass('Passphrase:')
        conn = boto.connect_s3()
        bucket = conn.get_bucket(options['bucket'])
        for confname in args:
            if os.path.exists(confname):
                conf_path = confname
                confname = os.path.basename(confname)
            else:
                conf_path = locate_config(confname, app_name)
            content_type = mimetypes.guess_type(conf_path)[0]
            if content_type:
                headers = {'Content-Type': content_type}
            else:
                headers = {}
            content = None
            with open(conf_path) as conf_file:
                content = conf_file.read()
            encrypted = crypt.encrypt(content, passphrase)
            key = boto.s3.key.Key(bucket)
            key.name = '%s/%s' % (app_name, confname)
            key.set_contents_from_string(encrypted, headers,
                replace=True, policy=default_acl)
