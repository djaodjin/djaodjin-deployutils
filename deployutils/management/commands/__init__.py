# Copyright (c) 2013, The DjaoDjin Team
#   All rights reserved.
#
#   Redistribution and use in source and binary forms, with or without
#   modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of DjaoDjin nor the names of its contributors may
#       be used to endorse or promote products derived from this software
#       without specific prior written permission.
#
#   THIS SOFTWARE IS PROVIDED BY The DjaoDjin Team ''AS IS'' AND ANY
#   EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#   WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
#   DISCLAIMED. IN NO EVENT SHALL The DjaoDjin Team LLC BE LIABLE FOR ANY
#   DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
#   (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#   LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
#   ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
#   SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import logging, os, subprocess, sys

import fabric.api as fab
from optparse import make_option
from django.core.management.base import BaseCommand

import deployutils.settings as settings

LOGGER = logging.getLogger(__name__)


class ResourceCommand(BaseCommand):
    """Commands intended to interact with the resources server directly."""

    option_list = BaseCommand.option_list + (
        make_option('-n',
            action='store_true',
            dest='no_execute',
            default=False,
            help='Print but do not execute'),
        )

    def __init__(self):
        BaseCommand.__init__(self)
        self.webapp = os.path.basename(
            os.path.dirname(os.path.abspath(sys.argv[0])))
        self.path = os.path.join(settings.DEPLOYED_WEBAPP_ROOT, self.webapp)

    def handle(self, *args, **options):
        settings.DRY_RUN = options['no_execute']
        fab.env.use_ssh_config = True


class DeployCommand(ResourceCommand):
    """Commands intended to interact with the deployed servers."""

    args = '[host ...]'

    def __init__(self):
        ResourceCommand.__init__(self)

    def handle(self, *args, **options):
        ResourceCommand.handle(self, *args, **options)
        logging.basicConfig(level=logging.DEBUG, format="%(message)s")
        logging.info("-" * 72)
        if len(args) > 0:
            fab.env.hosts = args
        else:
            fab.env.hosts = settings.DEPLOYED_SERVERS

def build_assets():
    """Call django_assets ./manage.py assets build if the app is present."""
    try:
        from webassets.script import GenericArgparseImplementation
        from django_assets.env import get_env
        prog = "%s assets" % os.path.basename(sys.argv[0])
        impl = GenericArgparseImplementation(
            env=get_env(), log=LOGGER, no_global_options=True, prog=prog)
        impl.run_with_argv(["build"])
    except ImportError:
        pass

def download(host, path):
    """download resources from a stage server."""
    shell_command([
            '/usr/bin/rsync',
            '-thrRvz', '--rsync-path', '/usr/bin/rsync',
            '%s:%s/./htdocs' % (host, path), '.'])


def shell_command(cmd):
    """Run a shell command."""
    if cmd[0] == '/usr/bin/rsync':
        if settings.DRY_RUN:
            cmd = [ cmd[0], '-n' ] + cmd[1:]
        LOGGER.info('run: %s', ' '.join(cmd))
        subprocess.check_call(cmd)
    else:
        LOGGER.info('run: %s', ' '.join(cmd))
        if not settings.DRY_RUN:
            subprocess.check_call(cmd)


def upload(host, path):
    """upload resources to a stage server."""
    # -O omit to set mod times on directories to avoid permissions error.
    shell_command([
            '/usr/bin/rsync',
            '--exclude', '.git', '--exclude', '*~', '--exclude', '.DS_Store',
            '--exclude', 'static/css', '--exclude', 'static/js',
            '-pOthrRvz', '--rsync-path', '/usr/bin/rsync',
            'htdocs', '%s:%s' % (host, path) ])

