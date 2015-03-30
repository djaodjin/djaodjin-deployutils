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

"""
Convenience module for access of deployutils app settings, which enforces
default settings when the main settings module does not contain
the appropriate settings.

In a production environment, the static resources (images, css, js) are served
directly by nginx from RESOURCES_ROOT. Furthermore the CMS pages are
served by one process while the app is served by another process. This requires
to install the templates from the app repo into the CMS template directory
(INSTALLED_TEMPLATES_ROOT) after the TemplateNodes related to the assets
pipeline have been resolved.
"""
from django.conf import settings

_SETTINGS = {
    'DRY_RUN': getattr(settings, 'DEPLOYUTILS_DRY_RUN', False),
    'DEPLOYED_WEBAPP_ROOT':getattr(settings, 'DEPLOYUTILS_DEPLOYED_WEBAPP_ROOT',
        '/var/www/%s' % settings.ALLOWED_HOSTS[0]),
    'DEPLOYED_SERVERS': getattr(settings, 'DEPLOYUTILS_DEPLOYED_SERVERS',
        (settings.ALLOWED_HOSTS[0],)),
    'INSTALLED_APPS': getattr(settings, 'DEPLOYUTILS_INSTALLED_APPS',
        settings.INSTALLED_APPS),
    'RESOURCES_ROOT': getattr(settings, 'DEPLOYUTILS_RESOURCES_ROOT',
        settings.BASE_DIR + '/htdocs/'),
    'INSTALLED_TEMPLATES_ROOT': getattr(settings,
        'DEPLOYUTILS_INSTALLED_TEMPLATES_ROOT',
        settings.TEMPLATE_DIRS[0]),
    'RESOURCES_REMOTE_LOCATION': getattr(settings,
        'DEPLOYUTILS_RESOURCES_REMOTE_LOCATION', None),
    'DENY_NO_SESSION': getattr(settings, 'DEPLOYUTILS_DENY_NO_SESSION', False),
    'SESSION_COOKIE_NAME': 'sessionid',
    'DJAODJIN_SECRET_KEY': getattr(settings, 'DJAODJIN_SECRET_KEY', None),
    'CONFIG_BUCKET': 'deployutils'
}
_SETTINGS.update(getattr(settings, 'DEPLOYUTILS', {}))


CONFIG_BUCKET = _SETTINGS.get('CONFIG_BUCKET')
DRY_RUN = _SETTINGS.get('DRY_RUN')
DENY_NO_SESSION = _SETTINGS.get('DENY_NO_SESSION')
DEPLOYED_WEBAPP_ROOT = _SETTINGS.get('DEPLOYED_WEBAPP_ROOT')
DEPLOYED_SERVERS = _SETTINGS.get('DEPLOYED_SERVERS')
INSTALLED_APPS = _SETTINGS.get('INSTALLED_APPS')
INSTALLED_TEMPLATES_ROOT = _SETTINGS.get('INSTALLED_TEMPLATES_ROOT')
RESOURCES_REMOTE_LOCATION = _SETTINGS.get('RESOURCES_REMOTE_LOCATION',
    'git@%s:%s' % (settings.ALLOWED_HOSTS[0], DEPLOYED_WEBAPP_ROOT))

RESOURCES_ROOT = _SETTINGS.get('RESOURCES_ROOT')
if not RESOURCES_ROOT.endswith('/'):
    RESOURCES_ROOT = RESOURCES_ROOT + '/'

SESSION_COOKIE_NAME = _SETTINGS.get('SESSION_COOKIE_NAME')
DJAODJIN_SECRET_KEY = _SETTINGS.get('DJAODJIN_SECRET_KEY')
