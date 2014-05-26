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

__version__ = '0.1'

# Read environment variable first
def load_config(confname, module=None, verbose=False):
    """
    Given a path to a file, parse its lines in ini-like format, and then
    set them in the current namespace.

    Quiet by default. Set verbose to True to see the absolute path to the config
    files printed on stderr.
    """
    # todo: consider using something like ConfigObj for this:
    # http://www.voidspace.org.uk/python/configobj.html
    import os, re
    confpath = os.path.join(module.CONFIG_DIR, confname)
    if os.path.isfile(confpath):
        if verbose:
            import sys
            sys.stderr.write('config loaded from %s\n' % confpath)
        with open(confpath) as conffile:
            line = conffile.readline()
            while line != '':
                if not line.startswith('#'):
                    look = re.match(r'(\w+)\s*=\s*(.*)', line)
                    if look:
                        if 'LOCALSTATEDIR' in look.group(2):
                            value = look.group(2) \
                                % {'LOCALSTATEDIR': module.APP_ROOT + '/var'}
                        else:
                            value = look.group(2)
                        try:
                            # Once Django 1.5 introduced ALLOWED_HOSTS (a tuple
                            # definitely in the site.conf set), we had no choice
                            # other than using eval. The {} are here to restrict
                            # the globals and locals context eval has access to.
                            setattr(module,
                                    look.group(1).upper(), eval(value, {}, {}))
                        except StandardError:
                            raise
                line = conffile.readline()
        if module.DB_ENGINE.endswith('sqlite3'):
            module.DB_PATH = module.DB_FILENAME
        else:
            module.DB_PATH = module.DB_NAME
        for pathname in [module.LOG_FILE]:
            if not os.path.exists(pathname):
                if not os.path.exists(os.path.dirname(pathname)):
                    os.makedirs(os.path.dirname(pathname))
                with open(pathname, 'w') as _:
                    pass    # touch file
    elif verbose:
        import sys
        sys.stderr.write('warning: config file %s does not exist.\n' % confpath)
