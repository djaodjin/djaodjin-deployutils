# Copyright (c) 2014, DjaoDjin Inc.
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

"""
Function to load site and credentials config files
"""
import os, re, sys

__version__ = '0.2'

from deployutils import crypt

# Read environment variable first
#pylint: disable=too-many-arguments,too-many-locals,too-many-statements
def load_config(confname, module, app_name,
                prefix='etc', verbose=False, skip_s3=True, passphrase=None):
    """
    Given a path to a file, parse its lines in ini-like format, and then
    set them in the current namespace.

    Quiet by default. Set verbose to True to see the absolute path to the config
    files printed on stderr.
    """
    content = None
    if not skip_s3:
        try:
            import boto
            bucket_name = '%s-deployutils' % app_name
            try:
                conn = boto.connect_s3()
                bucket = conn.get_bucket(bucket_name)
                key = bucket.get_key(confname)
                content = key.get_contents_as_string()
                if verbose:
                    sys.stderr.write('config loaded from %s in S3 bucket %s\n'
                        % (confname, bucket_name))
            except (boto.exception.NoAuthHandlerFound,
                    boto.exception.S3ResponseError) as _:
                pass
        except ImportError:
            pass

    # We cannot find a deployutils S3 bucket. Let's look on the filesystem.
    if not content:
        candidates = []
        app_config_dir = ('%s_CONFIG_DIR' % app_name).upper()
        if app_config_dir in os.environ:
            candidate = os.path.join(os.environ[app_config_dir], confname)
            if os.path.isfile(candidate):
                candidates += [candidate]
        if 'VIRTUAL_ENV' in os.environ:
            candidate = os.path.join(
                    os.environ['VIRTUAL_ENV'], prefix, app_name, confname)
            if os.path.isfile(candidate):
                candidates += [candidate]
        candidate = os.path.join(
            os.path.dirname(os.path.dirname(sys.executable)),
            prefix, app_name, confname)
        if os.path.isfile(candidate):
            candidates += [candidate]
        candidate = '/%s/%s/%s' % (prefix, app_name, confname)
        if os.path.isfile(candidate):
            candidates += [candidate]
        if len(candidates) > 0:
            confpath = candidates[0]
            if verbose:
                sys.stderr.write('config loaded from %s\n' % confpath)
            with open(confpath, 'rb') as conffile:
                content = conffile.read()
        else:
            content = None
            sys.stderr.write(
                'warning: config %s was not found.\n' % confname)

    if content:
        if passphrase:
            lines = crypt.decrypt(content, passphrase).split('\n')
        else:
            lines = content.split('\n')

        # We used to parse the file line by line. Once Django 1.5
        # introduced ALLOWED_HOSTS (a tuple that definitely belongs
        # to the site.conf set), we had no choice other than resort
        # to eval(value, {}, {}).
        # We are not resorting to import conf module yet but that
        # might be necessary once we use dictionary configs for some
        # of the apps...
        # todo: consider using something like ConfigObj for this:
        # http://www.voidspace.org.uk/python/configobj.html
        for line in lines:
            if not line.startswith('#'):
                look = re.match(r'(\w+)\s*=\s*(.*)', line)
                if look:
                    if 'LOCALSTATEDIR' in look.group(2):
                        value = look.group(2) \
                            % {'LOCALSTATEDIR': module.APP_ROOT + '/var'}
                    else:
                        value = look.group(2)
                    try:
                        setattr(module,
                                look.group(1).upper(), eval(value, {}, {}))
                    except StandardError:
                        raise
        if hasattr(module, 'LOG_FILE'):
            for pathname in [module.LOG_FILE]:
                if not os.path.exists(pathname):
                    if not os.path.exists(os.path.dirname(pathname)):
                        os.makedirs(os.path.dirname(pathname))
                    with open(pathname, 'w') as _:
                        pass    # touch file
                sys.stderr.write('logging app messages in %s\n' % pathname)
