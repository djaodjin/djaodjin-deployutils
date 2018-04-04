# Copyright (c) 2018, DjaoDjin inc.
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
Session Store for JWT tokens.
"""

from __future__ import absolute_import

import logging, json

from django.contrib.sessions.backends.signed_cookies import SessionStore \
    as SessionBase
from django.contrib.auth import (BACKEND_SESSION_KEY, HASH_SESSION_KEY,
    SESSION_KEY)
from jwt import encode, decode

from .... import crypt
from .. import settings
from .auth import ProxyUserBackend

LOGGER = logging.getLogger(__name__)


class SessionStore(SessionBase):

    def __init__(self, session_key=None):
        super(SessionStore, self).__init__(session_key=session_key)

    @property
    def data(self):
        return self._session

    @staticmethod
    def prepare(session_data={}, #pylint: disable=dangerous-default-value
                passphrase=None):
        """
        Returns *session_dict* as a base64 encrypted json string.

        """
        if passphrase is None:
            passphrase = settings.DJAODJIN_SECRET_KEY
        serialized = json.dumps(session_data, cls=crypt.JSONEncoder)
        return encode({'payload': serialized}, passphrase)

    def load(self):
        """
        We load the data from the key itself instead of fetching from
        some external data store. Opposite of _get_session_key(),
        raises BadSignature if signature fails.

        """
        session_data = {}
        try:
            session_text = decode(self.session_key,
                settings.DJAODJIN_SECRET_KEY)
            LOGGER.debug("session text: %s<%s>",
                session_text, session_text.__class__)
            session_data = json.loads(session_text.get('payload'))
            # We have been able to decode the session data, let's
            # create Users and session keys expected by Django
            # contrib.auth backend.
            if 'username' in session_data:
                backend = ProxyUserBackend()
                backend.create_user(session_data)
                user = backend.authenticate(session_data['username'])
                session_data[SESSION_KEY] = user.id
                session_data[BACKEND_SESSION_KEY] = "%s.%s" % (
                     backend.__class__.__module__, backend.__class__.__name__)
                session_data[HASH_SESSION_KEY] = user.get_session_auth_hash()
        except Exception as err: #pylint:disable=broad-except
            LOGGER.debug("Unable to decode session (%s)", err)
            return {}
        return session_data

    def _get_session_key(self):
        """
        Most session backends don't need to override this method, but we do,
        because instead of generating a random string, we want to actually
        generate a secure url-safe Base64-encoded string of data as our
        session key.
        """
        session_cache = getattr(self, '_session_cache', {})
        return self.prepare(session_cache)
