# Copyright (c) 2025, DjaoDjin inc.
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
Mockup APIs used in stand-alone development.
"""
from __future__ import unicode_literals

import json, logging
from importlib import import_module

from django.conf import settings as django_settings
from django.http import Http404
from rest_framework import generics, renderers, serializers, status
from rest_framework.response import Response
import jwt

from .. import settings
from ..compat import is_authenticated, six
from ....helpers import as_timestamp, datetime_or_now

LOGGER = logging.getLogger(__name__)


class CredentialsSerializer(serializers.Serializer):
    """
    All secrets can be optional during authentication such that we are able to
    raise a `ValidationError` when the authentication should proceed through
    a SSO provider for a particular user.
    """
    username = serializers.CharField(required=True,
        help_text="Username to identify the account")

    # If we define those fields in a Mixin, they don't show up
    # in the API documentation.
    password = serializers.CharField(required=False, write_only=True,
        style={'input_type': 'password'},
        help_text="Password of the user making the HTTP request")
    otp_code = serializers.IntegerField(required=False, write_only=True,
        style={'input_type': 'password'},
        help_text="One-time code. This field will be checked against"\
            " an expected code when multi-factor authentication (MFA)"\
            " is enabled.")
    email_code = serializers.IntegerField(required=False, write_only=True,
        style={'input_type': 'password'},
        help_text="Email verification code.")
    phone_code = serializers.IntegerField(required=False, write_only=True,
        style={'input_type': 'password'},
        help_text="Phone verification code.")

    class Meta:
        fields = ('username', 'password', 'otp_code',
            'email_code', 'phone_code')


    def create(self, validated_data):
        raise RuntimeError('`create()` should not be called.')

    def update(self, instance, validated_data):
        raise RuntimeError('`update()` should not be called.')



class LoginAPIView(generics.CreateAPIView):
    """
    Authenticates a user

    Returns a JSON Web Token that can be used in HTTP requests that require
    authentication.
    """
    schema = None
    serializer_class = CredentialsSerializer
    renderer_classes = (renderers.JSONRenderer,)

    def create_token(self, user_payload, expires_at=None):
        if not expires_at:
            exp = (as_timestamp(datetime_or_now())
                + self.request.session.get_expiry_age())
        else:
            exp = as_timestamp(expires_at)
        user_payload.update({'exp': exp})
        token = jwt.encode(user_payload,
            settings.DJAODJIN_SECRET_KEY,
            settings.JWT_ALGORITHM)
        try:
            token = token.decode('utf-8')
        except AttributeError:
            # PyJWT==2.0.1 already returns an oject of type `str`.
            pass
        return Response({'token': token}, status=status.HTTP_201_CREATED)

    def get(self, request, *args, **kwargs):
        if not is_authenticated(request):
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        user_payload = settings.MOCKUP_SESSIONS[request.user.username]
        return self.create_token(user_payload)

    def post(self, request, *args, **kwargs):
        engine = import_module(django_settings.SESSION_ENGINE)
        session_store = engine.SessionStore()
        #pylint:disable=protected-access
        user_payload = settings.MOCKUP_SESSIONS[request.data['username']]
        session_store._session_key = session_store.prepare(
            user_payload,
            settings.DJAODJIN_SECRET_KEY)
        session_store.modified = True
        self.request.session = session_store
        return self.create_token(user_payload)


class ProfileDetailAPIView(generics.RetrieveAPIView):

    schema = None

    def get(self, request, *args, **kwargs):
        profile_slug = self.kwargs.get('profile')
        for _, session_data in six.iteritems(settings.MOCKUP_SESSIONS):
            for _, role_data in six.iteritems(session_data.get('roles', {})):
                for profile in role_data:
                    if profile.get('slug') == profile_slug:
                        return Response(profile)
        raise Http404


class TimersAPIView(generics.CreateAPIView):

    schema = None

    def post(self, request, *args, **kwargs):
        # request.data is like {'display_timedelta': 135,
        #     'request_id': 'c78b2f42-95d6-130d-2627-66f8b03913e8'}
        LOGGER.info("timedelta:JS: %s", json.dumps(request.data))
        return Response([request.data['display_timedelta'], args, kwargs])
