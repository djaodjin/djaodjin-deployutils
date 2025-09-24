# Copyright (c) 2023, DjaoDjin inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from django import template

from .. import settings
from ..compat import six, urljoin

register = template.Library()

URL_SEP = '/'


@register.filter()
def asset(path):
    """
    Static assets are often fetched from different locations in development and
    production environments. CSS/Javascript assets also go through different
    build workflows.

    To support the various scenarios, the `asset` template tag
    (i.e. `{{'/static/img/logo.png'|asset}}`) rewrites the path passed
    as parameter based on the `ASSETS_CDN` settings.

    As an example, we configure the project to serve all media files
    from an asset server in a production environment, while serving
    the media assets locally in a development environment.

    .. code-block::

        # templates/index.html
        <img src="{{'/static/img/logo.png'|asset}}">

    .. code-block::

        # testsite/settings.py
        ASSETS_CDN = {
            '/static/img/': 'https://www.example.com/static/img/'
        }

    When we add a compiled application `.js` file, we will want to introduce
    a unique versioning to bypass any caching issues when that file
    is deployed in production.

    .. code-block::

        # templates/base.html
        <script type="text/javascript" src="{{'/static/cache/app.js'|asset}}"></script>

    .. code-block::

        # testsite/settings.py
        + APP_VERSION = "1.0"
          ASSETS_CDN = {
        +    '/static/cache/app.js': '/static/cache/app-%s.js' % APP_VERSION,
             '/static/img/': 'https://www.djaodjin.com/static/img/'
          }

    If we intent to bypass the build workflow, and use source files directly
    in a development environment, we would modify the template file as such:

    .. code-block::

        # templates/base.html
        + {% if DEBUG %}
        + <script type="text/javascript" src="{{'/static/js/app.js'|asset}}"></script>
        + {% else %}
          <script type="text/javascript" src="{{'/static/cache/app.js'|asset}}"></script>
        + {% endif %}
    """
    path_parts = path.split(URL_SEP)
    for idx in range(len(path_parts), 0, -1):
        path_prefix = URL_SEP.join(path_parts[:idx])
        if path_prefix in settings.ASSETS_CDN:
            cdn_path = urljoin(settings.ASSETS_CDN[path_prefix],
                URL_SEP.join(path_parts[idx:]))
            return cdn_path
        path_prefix += URL_SEP
        if path_prefix in settings.ASSETS_CDN:
            cdn_path = urljoin(settings.ASSETS_CDN[path_prefix],
                URL_SEP.join(path_parts[idx:]))
            return cdn_path
    if settings.DEBUG and hasattr(settings, 'APP_NAME'):
        path_prefix = '/%s' % settings.APP_NAME
        if not path.startswith(path_prefix):
            cdn_path = urljoin(path_prefix, path)
            return cdn_path
    return path


@register.filter()
def site_url(request):
    """
    The `site_url` template tag mocks up the
    `multitier <https://github.com/djaodjin/djaodjin-multitier>`_ when
    sites are configured to use a path prefix.

    This is especially useful in development environments, both
    `djaoapp <https://github.com/djaodjin/djaoapp>`_ and multiple projects
    will run on `localhost`.
    """
    if isinstance(request, six.string_types):
        path = request
        if path is None:
            path = ''
        path_prefix = ''
        if settings.DEBUG and hasattr(settings, 'APP_NAME'):
            candidate = '/%s' % settings.APP_NAME
            if not path.startswith(candidate):
                path_prefix = candidate
        if path:
            # We have an actual path instead of generating a prefix that will
            # be placed in front of static urls (ie. {{'pricing'|site_url}}
            # insted of {{''|site_url}}{{ASSET_URL}}).
            path_prefix += '/'
            if path.startswith('/'):
                path = path[1:]
        return urljoin(path_prefix, path)
    return request.build_absolute_uri(location='/').rstrip('/')


@register.filter()
def site_prefixed(path):
    return site_url(path)
