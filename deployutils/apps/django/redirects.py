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
Helpers to redirect based on session.
"""

from django import http
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.views.generic import RedirectView
from django.views.generic.base import ContextMixin, TemplateResponseMixin

from .compat import six
from .mixins import AccessiblesMixin
from .templatetags.deployutils_prefixtags import site_url
from ...helpers import update_context_urls


def _get_accept_list(request):
    http_accept = request.META.get('HTTP_ACCEPT', '*/*')
    return [item.strip() for item in http_accept.split(',')]


def _insert_url(request, redirect_field_name=REDIRECT_FIELD_NAME,
                inserted_url=None):
    '''Redirects to the *inserted_url* before going to the orginal
    request path.'''
    # This code is pretty much straightforward
    # from contrib.auth.user_passes_test
    path = request.build_absolute_uri()
    # If the login url is the same scheme and net location then just
    # use the path as the "next" url.
    login_scheme, login_netloc = six.moves.urllib.parse.urlparse(
        inserted_url)[:2]
    current_scheme, current_netloc = six.moves.urllib.parse.urlparse(path)[:2]
    if ((not login_scheme or login_scheme == current_scheme) and
        (not login_netloc or login_netloc == current_netloc)):
        path = request.get_full_path()
    # As long as *inserted_url* is not None, this call will redirect
    # anything (i.e. inserted_url), not just the login.
    return redirect_to_login(path, inserted_url, redirect_field_name)


def redirect_or_denied(request, inserted_url,
                       redirect_field_name=REDIRECT_FIELD_NAME, descr=None):
    http_accepts = _get_accept_list(request)
    if ('text/html' in http_accepts
        and isinstance(inserted_url, six.string_types)):
        return _insert_url(request, redirect_field_name=redirect_field_name,
                           inserted_url=inserted_url)
    if descr is None:
        descr = ""
    raise PermissionDenied(descr)



class AccountRedirectView(AccessiblesMixin, TemplateResponseMixin, ContextMixin,
                          RedirectView):
    """
    Find the ``Account`` associated with the request user
    and return the URL that contains the profile slug
    to redirect to.
    """

    account_url_kwarg = 'profile'
    template_name = 'saas/profile_redirects.html'
    permanent = False
    create_more = False
    create_on_none = True
    new_account_url = site_url('/users/roles/accept/') # i.e. reverse(
                                         # 'saas_role_implicit_grant_accept')

    def get_new_account_url(self, *args, **kwargs):
        kwargs.update({
            self.account_url_kwarg: 'PATTERN-%s' % self.account_url_kwarg})
        next_url = self.get_redirect_url(
            *args, **kwargs).replace('PATTERN-%s' % self.account_url_kwarg,
            ':%s' % self.account_url_kwarg)
        return '%s?%s=%s' % (self.new_account_url,
            REDIRECT_FIELD_NAME, next_url)

    def get(self, request, *args, **kwargs):
        candidates = self.get_accessible_profiles(
            request, self.get_redirect_roles(request))
        count = len(candidates)
        if count == 0:
            if self.create_on_none:
                url = self.get_new_account_url(*args, **kwargs)
                if self.permanent:
                    return http.HttpResponsePermanentRedirect(url)
                return http.HttpResponseRedirect(url)
            raise http.Http404("No account")
        if count == 1 and not self.create_more:
            profile = candidates[0]
            kwargs.update({self.account_url_kwarg: profile['slug']})
            return super(AccountRedirectView, self).get(
                request, *args, **kwargs)
        redirects = []
        for org in candidates:
            kwargs.update({self.account_url_kwarg: org['slug']})
            url = self.get_redirect_url(*args, **kwargs)
            slug = org.get('slug', "")
            print_name = org.get('printable_name', slug)
            redirects += [{'profile': {
                'slug': slug, 'printable_name': print_name},
                'home_url': url}]
        kwargs.update({
            self.account_url_kwarg: 'PATTERN-%s' % self.account_url_kwarg})
        context = self.get_context_data(**kwargs)
        context.update({'redirects': {'results': redirects},
            'next': self.get_redirect_url(*args, **kwargs).replace(
                'PATTERN-%s' % self.account_url_kwarg,
                ':%s' % self.account_url_kwarg)})
        update_context_urls(context, {
            'api_candidates': site_url("/api/accounts/profiles"),
            'user': {
                'api_accessibles':
                  site_url("/api/users/%s/accessibles" % str(request.user)),
                'api_profile_create':
                  site_url("/api/users/%s/profiles" % str(request.user)),
                'accessibles': site_url("/users/%s/roles/" % str(request.user))
            },
        })
        return self.render_to_response(context)
