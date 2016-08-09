# Copyright (c) 2016, DjaoDjin inc.
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
from django.conf import settings
from django.contrib.messages.api import get_messages
from django.forms import BaseForm

#pylint:disable=no-name-in-module,import-error
from django.utils.six.moves.urllib.parse import urljoin


register = template.Library()


@register.filter()
def asset(path):
    """
    *Mockup*: adds the appropriate url or path prefix.
    """
    return site_prefixed(path)


@register.filter()
def is_authenticated(request):
    return request.user.is_authenticated()


@register.filter()
def host(request):
    return request.get_host()


@register.filter()
def messages(obj):
    """
    Messages to be displayed to the current session.
    """
    if isinstance(obj, BaseForm):
        return obj.non_field_errors()
    return get_messages(obj)


@register.filter()
def site_prefixed(path):
    """
    *Mockup*: adds the path prefix when required.
    """
    if path is None:
        path = ''
    if settings.DEBUG and hasattr(settings, 'APP_NAME'):
        path_prefix = '/%s' % settings.APP_NAME
    else:
        path_prefix = ''
    if path:
        # We have an actual path instead of generating a prefix that will
        # be placed in front of static urls (ie. {{'pricing'|site_prefixed}}
        # insted of {{''|site_prefixed}}{{ASSET_URL}}).
        path_prefix += '/'
        if path.startswith('/'):
            path = path[1:]
    return urljoin(path_prefix, path)


@register.filter()
def url_profile(request): #pylint:disable=unused-argument
    """
    *Mockup*: access the user profile.
    """
    if hasattr(request, 'user') and request.user.is_authenticated():
        return site_prefixed("users/%s/" % request.user)
    return None


@register.filter()
def wraplines(text):
    text = str(text)
    line_length = 80
    text_length = len(text)
    nb_lines = text_length / line_length
    if text_length % line_length > 0:
        nb_lines += 1
    lines = [text[first * line_length:(first + 1) * line_length]
        for first in range(0, nb_lines)]
    return '\n'.join(lines)
