# Copyright (c) 2022, DjaoDjin inc.
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
Mockup login URL used in testing.
"""

from django.views.generic import TemplateView

from .api import LoginAPIView, ProfileDetailAPIView, TimersAPIView
from .views import SigninView
from ..compat import re_path


USERNAME_PAT = r'[\w.@+-]+'
SLUG_PAT = r'[a-zA-Z0-9_\-\+\.]+'

urlpatterns = [
    re_path(r'^api/timer/', TimersAPIView.as_view(), name='api_timer'),
    re_path(r'^api/profile/(?P<profile>%s)/' % SLUG_PAT,
        ProfileDetailAPIView.as_view(), name='api_profile'),
    re_path(r'^api/auth/', LoginAPIView.as_view(), name='api_login'),
    re_path(r'^users/(?P<user>%s)/' % USERNAME_PAT,
        TemplateView.as_view(template_name='users/index.html'),
        name='users_profile'),
    re_path(r'^login/$', SigninView.as_view(), name='login'),
]
