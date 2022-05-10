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

from __future__ import unicode_literals

import dateutil, dateutil.relativedelta
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.utils.dateparse import parse_datetime

from ....helpers import datetime_or_now, start_of_day, update_context_urls
from .. import settings
from ..compat import gettext_lazy as _, six
from ..templatetags.deployutils_prefixtags import site_url


class Account(object):

    def __init__(self, fields, lookup_field=None):
        self.fields = fields
        self.lookup_field = lookup_field if lookup_field else 'slug'

    def __getattr__(self, field_name):
        return self.fields.get(field_name, None)

    def __str__(self):
        return str(self.fields[self.lookup_field])


class AccessiblesMixin(object):
    """
    Profiles accessibles by the ``request.user`` as defined
    in the session passed by the DjaoDjin proxy.
    """
    MANAGER = 'manager'
    redirect_roles = None

    @property
    def accessible_plans(self):
        if not hasattr(self, '_accessible_plans'):
            self._accessible_plans = set([plan['slug']
                for plan in self.get_accessible_plans(self.request)])
        return self._accessible_plans

    @property
    def accessible_profiles(self):
        if not hasattr(self, '_accessible_profiles'):
            self._accessible_profiles = set([org['slug']
                for org in self.get_accessible_profiles(self.request)])
        return self._accessible_profiles

    def get_redirect_roles(self, request):
        #pylint:disable=unused-argument
        return self.redirect_roles

    @staticmethod
    def get_accessible_plans(request, profile=None, at_time=None):
        """
        Returns the list of plans that appear under at least one subscription
        of a profile the `request.user` has a role on.
        """
        #pylint:disable=too-many-nested-blocks
        plans = {}
        for accessible_profiles in six.itervalues(request.session.get(
                'roles', {})):
            for accessible_profile in accessible_profiles:
                if not profile or profile == accessible_profile.get('slug'):
                    for subscription in accessible_profile.get(
                            'subscriptions', []):
                        subscription_ends_at = subscription.get('ends_at')
                        if (not at_time or
                            at_time < datetime_or_now(subscription_ends_at)):
                            plan_key =  subscription.get('plan')
                            plan = {'slug': plan_key}
                            if plan_key not in plans:
                                plans.update({plan_key: plan})
        return plans.values()

    @staticmethod
    def get_accessible_profiles(request, roles=None):
        """
        Returns the list of *dictionnaries* for which the accounts are
        accessibles by ``request.user`` filtered by ``roles`` if present.
        """
        results = []
        for role_name, accessible_profiles in six.iteritems(request.session.get(
                'roles', {})):
            if roles is None or role_name in roles:
                results += accessible_profiles
        return results

    def get_context_data(self, **kwargs):
        context = super(AccessiblesMixin, self).get_context_data(**kwargs)
        urls = {'profiles': []}
        for account in self.get_accessible_profiles(self.request,
                        self.get_redirect_roles(self.request)):
            urls['profiles'] += [{
                'location': site_url('/profile/%s/' % account['slug']),
                'printable_name': account.get('printable_name',
                    account.get('slug'))}]
        update_context_urls(context, urls)
        return context

    def get_managed(self, request):
        """
        Returns the list of *dictionnaries* for which the accounts are
        managed by ``request.user``.
        """
        return self.get_accessible_profiles(request, roles=[self.MANAGER])

    @property
    def managed_accounts(self):
        """
        Returns a list of account *slugs* for ``request.user`` is a manager
        of the account.
        """
        return [org['slug'] for org in self.get_accessible_profiles(
            self.request, roles=[self.MANAGER])]

    def manages(self, account):
        """
        Returns ``True`` if the ``request.user`` is a manager for ``account``.
        ``account`` will be converted to a string and compared
        to a profile slug.
        """
        account_slug = str(account)
        for accessible_profile in self.request.session.get(
                'roles', {}).get(self.MANAGER, []):
            if account_slug == accessible_profile['slug']:
                return True
        return False


class AccountMixin(AccessiblesMixin):
    """
    Mixin to use in views that will retrieve an account object (out of
    ``account_queryset``) associated to a slug parameter (``account_url_kwarg``)
    in the URL.
    The ``account`` property will be ``None`` if either ``account_url_kwarg``
    is ``None`` or absent from the URL pattern.
    """
    account_queryset = None
    account_lookup_field = None
    account_url_kwarg = None

    @property
    def account(self):
        if not hasattr(self, '_account'):
            self._account = None
            if (self.account_url_kwarg is not None
                and self.account_url_kwarg in self.kwargs):
                account_lookup_value = self.kwargs.get(self.account_url_kwarg)
                if self.account_queryset is None:
                    # There are no Model in the database backing an account.
                    # We entirely derive it from the the session token passed
                    # by the proxy.
                    for account in self.get_accessible_profiles(self.request):
                        if (account[self.account_lookup_field]
                            == account_lookup_value):
                            self._account = Account(account,
                                lookup_field=self.account_lookup_field)
                            break
                else:
                    if self.account_lookup_field is None:
                        raise ImproperlyConfigured(
                            "%(cls)s.account_lookup_field is None. Define "
                            "%(cls)s.account_lookup_field as the field used "
                            "to retrieve accounts in the database." % {
                                'cls': self.__class__.__name__
                            }
                        )
                    kwargs = {'%s__exact' % self.account_lookup_field:
                        account_lookup_value}
                    try:
                        self._account = self.account_queryset.filter(
                            **kwargs).get()
                    except self.account_queryset.model.DoesNotExist:
                        #pylint: disable=protected-access
                        raise Http404(_("No %(verbose_name)s found matching"\
                            " '%(account)s'") % {'verbose_name':
                            self.account_queryset.model._meta.verbose_name,
                            'account': account_lookup_value})
                if not self._account:
                    raise Http404(_("No account found matching '%(account)s'")
                        % {'account': account_lookup_value})
        return self._account

    def get_context_data(self, **kwargs):
        context = super(AccountMixin, self).get_context_data(**kwargs)
        context.update({self.account_url_kwarg: self.account})
        return context

    def get_reverse_kwargs(self):
        """
        List of kwargs taken from the url that needs to be passed through
        to ``get_success_url``.
        """
        if self.account_url_kwarg:
            return [self.account_url_kwarg]
        return []

    def get_url_kwargs(self, **kwargs):
        if not kwargs:
            kwargs = self.kwargs
        url_kwargs = {}
        for url_kwarg in self.get_reverse_kwargs():
            url_kwarg_val = kwargs.get(url_kwarg, None)
            if url_kwarg_val:
                url_kwargs.update({url_kwarg: url_kwarg_val})
        return url_kwargs


class ProviderMixin(AccountMixin):
    """
    Mixin that behaves like `AccountMixin` except it will default to the broker
    account instead of `None` when no account is found.
    """

    @property
    def account(self):
        if not hasattr(self, '_account'):
            self._account = super(ProviderMixin, self).account
            if self._account is None:
                kwargs = {
                    '%s__exact' % self.account_lookup_field: settings.APP_NAME
                }
                try:
                    self._account = self.account_queryset.filter(**kwargs).get()
                except self.account_queryset.model.DoesNotExist:
                    #pylint: disable=protected-access
                    raise Http404(
                        _("No %(verbose_name)s found matching '%(provider)s'") %
                        {'verbose_name':
                         self.account_queryset.model._meta.verbose_name,
                         'provider': settings.APP_NAME
                        })
        return self._account


class BeforeMixin(object):

    clip = True
    date_field = 'created_at'

    def cache_fields(self, request):
        self.ends_at = request.GET.get('ends_at', None)
        if self.clip or self.ends_at:
            if self.ends_at is not None:
                self.ends_at = parse_datetime(self.ends_at.strip('"'))
            self.ends_at = datetime_or_now(self.ends_at)

    def get_queryset(self):
        """
        Implements before date filtering on ``date_field``
        """
        kwargs = {}
        if self.ends_at:
            kwargs.update({'%s__lt' % self.date_field: self.ends_at})
        return super(BeforeMixin, self).get_queryset().filter(**kwargs)

    def get(self, request, *args, **kwargs): #pylint: disable=unused-argument
        self.cache_fields(request)
        return super(BeforeMixin, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(BeforeMixin, self).get_context_data(**kwargs)
        if self.ends_at:
            context.update({'ends_at': self.ends_at})
        return context


class DateRangeMixin(BeforeMixin):

    natural_period = dateutil.relativedelta.relativedelta(months=-1)

    def cache_fields(self, request):
        super(DateRangeMixin, self).cache_fields(request)
        self.start_at = None
        if self.ends_at:
            self.start_at = request.GET.get('start_at', None)
            if self.start_at:
                self.start_at = datetime_or_now(parse_datetime(
                    self.start_at.strip('"')))
            else:
                self.start_at = (
                    start_of_day(self.ends_at + self.natural_period)
                    + dateutil.relativedelta.relativedelta(days=1))

    def get_queryset(self):
        """
        Implements date range filtering on ``created_at``
        """
        kwargs = {}
        if self.start_at:
            kwargs.update({'%s__gte' % self.date_field: self.start_at})
        return super(DateRangeMixin, self).get_queryset().filter(**kwargs)

    def get_context_data(self, **kwargs):
        context = super(DateRangeMixin, self).get_context_data(**kwargs)
        if self.start_at:
            context.update({'start_at': self.start_at})
        return context
