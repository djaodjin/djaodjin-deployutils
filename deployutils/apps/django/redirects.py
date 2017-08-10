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
Helpers to redirect based on session.
"""

from django import http
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.views.generic import RedirectView
from django.views.generic.base import TemplateResponseMixin

from .mixins import AccessiblesMixin


class AccountRedirectView(TemplateResponseMixin, AccessiblesMixin,
                          RedirectView):
    """
    Find the ``Account`` associated with the request user
    and return the URL that contains the organization slug
    to redirect to.
    """

    slug_url_kwarg = 'organization'
    template_name = 'saas/organization_redirects.html'
    permanent = False
    create_more = False
    create_on_none = True
    new_account_url = '/app/new/'
    redirect_roles = None

    def get(self, request, *args, **kwargs):
        candidates = self.get_accessibles(request, self.redirect_roles)
        count = len(candidates)
        if count == 0:
            if self.create_on_none:
                kwargs.update({
                    self.slug_url_kwarg: 'PATTERN-%s' % self.slug_url_kwarg})
                next_url = super(AccountRedirectView, self).get_redirect_url(
                *args, **kwargs).replace('PATTERN-%s' % self.slug_url_kwarg,
                    ':%s' % self.slug_url_kwarg)
                url = '%s?%s=%s' % (self.new_account_url,
                    REDIRECT_FIELD_NAME, next_url)
                if self.permanent:
                    return http.HttpResponsePermanentRedirect(url)
                else:
                    return http.HttpResponseRedirect(url)
            else:
                raise http.Http404("No account")
        if count == 1 and not self.create_more:
            organization = candidates[0]
            kwargs.update({self.slug_url_kwarg: organization['slug']})
            return super(AccountRedirectView, self).get(
                request, *args, **kwargs)
        redirects = []
        for org in candidates:
            kwargs.update({self.slug_url_kwarg: org['slug']})
            url = super(AccountRedirectView, self).get_redirect_url(
                *args, **kwargs)
            print_name = org['full_name'] if org['full_name'] else org['slug']
            redirects += [(url, print_name)]
        kwargs.update({self.slug_url_kwarg: 'PATTERN-%s' % self.slug_url_kwarg})
        context = {'redirects': redirects,
            'next': super(AccountRedirectView, self).get_redirect_url(
            *args, **kwargs).replace('PATTERN-%s' % self.slug_url_kwarg,
                ':%s' % self.slug_url_kwarg)}
        return self.render_to_response(context)
