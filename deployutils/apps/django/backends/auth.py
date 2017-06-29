# Copyright (c) 2017, Djaodjin Inc.
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

from __future__ import absolute_import

import logging, random, six

from django.conf import settings as django_settings
from django.contrib.auth.backends import RemoteUserBackend
from django.contrib.auth import get_user_model


LOGGER = logging.getLogger(__name__)


class ProxyUserBackend(RemoteUserBackend):

    users = {}

    def create_user(self, session_data):
        user = None
        username = session_data['username']
        UserModel = get_user_model() #pylint:disable=invalid-name
        if ('django.contrib.auth.backends.ModelBackend'
            in django_settings.AUTHENTICATION_BACKENDS):
            LOGGER.warning(
                "attempt to load User(username='%s') from database.", username)
            try:
                #pylint:disable=protected-access
                user = UserModel._default_manager.get_by_natural_key(username)
            except UserModel.DoesNotExist:
                LOGGER.warning("'%s' is not in database.", username)
        else:
            user = UserModel(
                id=random.randint(1, (1 << 64) - 1), username=username)
        if user is not None:
            LOGGER.debug("add User(id=%d, username=%s) to cache.",
                user.id, user.username)
            self.users[user.id] = user

    def authenticate(self, remote_user):
        """
        The username passed as ``remote_user`` is considered trusted.  This
        method simply returns the ``User`` object with the given username.
        """
        if not remote_user:
            return
        username = self.clean_username(remote_user)
        for user in six.itervalues(self.users):
            LOGGER.debug("match %s with User(id=%d, username=%s)",
                username, user.id, user.username)
            if user.username == username:
                return user
        return None

    def get_user(self, user_id):
        return self.users.get(user_id, None)
