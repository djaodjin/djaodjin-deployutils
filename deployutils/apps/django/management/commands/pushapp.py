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

import logging, subprocess

import fabric.api as fab

from ... import settings
from .....copy import shell_command, upload
from . import DeployCommand, build_assets


LOGGER = logging.getLogger(__name__)


class Command(DeployCommand):
    help = "[Hotfix] Push local code and resources to deployed servers."

    def handle(self, *args, **options):
        DeployCommand.handle(self, *args, **options)
        build_assets()
        status = subprocess.check_output(['git', 'status', '--porcelain'])
        if not status:
            sha1 = subprocess.check_output(['git', 'rev-parse', 'HEAD'])
        else:
            sha1 = "??"
        with open('.timestamp', 'w') as timestamp_file:
            timestamp_file.write(sha1)
        for host in fab.env.hosts:
            fab.env.host_string = host
            pushapp(self.webapp, self.deployed_path, sha1)


@fab.task
def pushapp(webapp, webapp_path, sha1):
    remote_location = '%s:%s' % (fab.env.host_string, webapp_path)
    # Directories under htdocs/ are not under source control
    # except for static/css and static/js.
    shell_command([
            '/usr/bin/rsync',
            '--copy-links', '--exclude', '.git', '--exclude', 'htdocs/*',
            '--exclude', 'img/', #'--exclude', '*.pyc',
            '--exclude', '.DS_Store', '--exclude', '*~',
            '-pthrRvz', '--rsync-path', '/usr/bin/rsync', '--delete',
            '.', './htdocs/static/css', './htdocs/static/js',
            remote_location])
    upload(remote_location, prefix=settings.MULTITIER_RESOURCES_ROOT,
        dry_run=settings.DRY_RUN)
    LOGGER.info("pushapp %s %s %s", webapp, fab.env.host_string, sha1)
