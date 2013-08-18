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

import datetime, fnmatch, logging, os, subprocess

import deployutils.settings as settings
from deployutils.management.commands import (
    ResourceCommand, build_assets, download, shell_command)

LOGGER = logging.getLogger(__name__)


class Command(ResourceCommand):
    help = "Fetch latest code and resources from the stage machine."

    def handle(self, *args, **options):
        if len(args) > 0:
            up_commit = args[0]
        else:
            up_commit = 'master'
        try:
            last_up_commit, up_commit = fetch_changes(self.path, up_commit)
            # Fetch resources which are not stored under source control
            download(settings.RESOURCES_MACHINE, self.path)
            build_assets()
            LOGGER.info("pullapp %s %s (old: %s)",
                        self.webapp, up_commit, last_up_commit)
        except subprocess.CalledProcessError, err:
            LOGGER.exception(
                "syncapp %s caught exception: %s", self.webapp, err)


def sources_latest_timestamp(root_dir, file_pat='*.py'):
    """
    Returns the timestamp for the source file
    that was most recently modified.
    """
    latest_timestamp = None
    for root, _, filenames in os.walk(root_dir):
        for filename in fnmatch.filter(filenames, file_pat):
            mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(
                    os.path.join(root, filename)))
            if not latest_timestamp or latest_timestamp < mod_time:
                latest_timestamp = mod_time
    return latest_timestamp


def fetch_changes(repo_path, up_commit='master'):
    """
    Fetch latest changes from stage and touch .timestamp
    if any python sources have been modified.
    """
    last_up_commit = None
    prevcwd = os.getcwd()
    try:
        gitexe = 'git'
        os.chdir(repo_path)
        old_sources_timestamp = sources_latest_timestamp('.')
        shell_command([ gitexe, 'fetch', 'origin', 'master' ])
        last_up_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'])
        shell_command([ gitexe, 'checkout', up_commit ])
        up_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'])
        new_sources_timestamp = sources_latest_timestamp('.')
        if old_sources_timestamp < new_sources_timestamp:
            with open('.timestamp', 'w') as up_commit_file:
                up_commit_file.write(up_commit)
    finally:
        os.chdir(prevcwd)
    return last_up_commit, up_commit
