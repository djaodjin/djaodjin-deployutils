# Copyright (c) 2017, DjaoDjin inc.
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

"""
Session Store for encrypted cookies.
"""

from __future__ import absolute_import

from datetime import datetime, timedelta
from importlib import import_module
import logging

from django.conf import settings as django_settings
from django.contrib.sessions.middleware import SessionMiddleware \
    as BaseMiddleware
from django.core.exceptions import PermissionDenied
from django.db import connections

from . import settings
from .compat import MiddlewareMixin
from .thread_local import clear_cache, set_request


LOGGER = logging.getLogger(__name__)


class SessionMiddleware(BaseMiddleware):

    def process_request(self, request):
        engine = import_module(django_settings.SESSION_ENGINE)
        session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME, None)
        request.session = engine.SessionStore(session_key)
        if not session_key:
            found = False
            for path in settings.ALLOWED_NO_SESSION:
                if request.path.startswith(str(path)):
                    found = True
                    break
            if not found:
                LOGGER.debug("%s not found in %s", request.path,
                    [str(url) for url in settings.ALLOWED_NO_SESSION])
                raise PermissionDenied("No DjaoDjin session key")
        # trigger ``load()``
        _ = request.session._session #pylint: disable=protected-access



class RequestLoggingMiddleware(MiddlewareMixin):

    @staticmethod
    def process_request(request):
        clear_cache()
        set_request(request)

    @staticmethod
    def process_response(request, response):
        nb_queries = 0
        duration = timedelta()
        for connection in connections.all():
            nb_queries += len(connection.queries)
            for query in connection.queries:
                convert = datetime.strptime(query['time'], "%S.%f")
                duration += timedelta(
                    0, convert.second, convert.microsecond)
                    # days, seconds, microseconds
        LOGGER.info("%s %s %d %s for %d SQL queries",
            request.method, request.get_full_path(),
            response.status_code, duration, nb_queries,
            extra={'request': request, 'nb_queries': nb_queries,
                'queries_duration': str(duration)})
        return response
