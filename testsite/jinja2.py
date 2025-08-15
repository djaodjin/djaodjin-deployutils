# Copyright (c) 2025, DjaoDjin inc.
# see LICENSE

from __future__ import absolute_import

from django.conf import settings
from deployutils.apps.django_deployutils.templatetags import (
    deployutils_prefixtags, deployutils_extratags)
from jinja2.sandbox import SandboxedEnvironment as Jinja2Environment


def environment(**options):
    # If we don't force ``auto_reload`` to True, in DEBUG=0, the templates
    # would only be compiled on the first edit.
    options.update({'auto_reload': True, 'cache_size': 0})
    env = Jinja2Environment(**options)
    # Generic filters to render templates
    env.filters['asset'] = deployutils_prefixtags.asset
    env.filters['site_url'] = deployutils_prefixtags.site_url
    env.filters['messages'] = deployutils_extratags.messages
    env.filters['wraplines'] = deployutils_extratags.wraplines
    if settings.DEBUG:
        env.globals.update({
            'ASSETS_DEBUG': settings.ASSETS_DEBUG,
        })

    return env
