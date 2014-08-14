# Copyright (c) 2014, Djaodjin Inc.
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

import datetime, fnmatch, inspect, logging, os, re, subprocess

from django.db import models
from django.core.exceptions import ImproperlyConfigured
from south.migration import Migrations
from south.management.commands import schemamigration, migrate

import deployutils.settings as settings
from deployutils.management.commands import (
    ResourceCommand, download, shell_command)
from deployutils.management.commands.install_theme import install_theme


LOGGER = logging.getLogger(__name__)


class SchemaMigration(schemamigration.Command):

    def error(self, message, code=1):
        """
        Override the error method to avoid a brutal sys.exit
        """
        raise RuntimeError(message)


class Command(ResourceCommand):
    help = "Fetch latest code and resources from the stage machine."

    def handle(self, *args, **options):
        if len(args) > 0:
            up_commit = args[0]
        else:
            up_commit = 'master'
        try:
            repo_path = os.getcwd()
            last_up_commit, up_commit = fetch_changes(repo_path, up_commit)
            # Fetch resources which are not stored under source control
            download(settings.RESOURCES_REMOTE_LOCATION)
            install_theme(settings.INSTALLED_TEMPLATES_ROOT,
                settings.RESOURCES_ROOT)
            migrate_all()
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
        shell_command([gitexe, 'pull'])
        last_up_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'])
        shell_command([gitexe, 'checkout', up_commit])
        up_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'])
        new_sources_timestamp = sources_latest_timestamp('.')
        if old_sources_timestamp < new_sources_timestamp:
            with open('.timestamp', 'w') as up_commit_file:
                up_commit_file.write(up_commit)
    finally:
        os.chdir(prevcwd)
    return last_up_commit, up_commit


def is_model_class(cls):
    return inspect.isclass(cls) and issubclass(cls, models.Model)


def migrate_all():
    """
    Create schema migrations for all apps specified in INSTALLED_APPS,
    then run a migrate command.
    """
    if not 'south' in settings.INSTALLED_APPS:
        print "'south' is not in INSTALLED_APPS, no migration done."
        return
    schema_cmd = SchemaMigration()
    initial_apps = []
    auto_apps = [] #pylint: disable=unused-variable
    for app in [app for app in settings.INSTALLED_APPS if app != 'south']:
        try:
            app_module = models.get_app(app)
            clsmembers = inspect.getmembers(app_module, is_model_class)
            if len(clsmembers) > 0:
                migrations_dir = os.path.join(
                    os.path.dirname(app_module.__file__), 'migrations')
                if os.path.isdir(migrations_dir):
                    schema_cmd.handle(app, auto=True)
                    found = False
                    for migration_file in os.listdir(migrations_dir):
                        if (re.match(r'^\d\d\d\d', migration_file)
                            and not migration_file.startswith('0001_initial')):
                            found = True
                            break
                    if found:
                        auto_apps += [app]
                    else:
                        initial_apps += [app]
                else:
                    schema_cmd.handle(app, initial=True)
                    initial_apps += [app]
            else:
                print("warning: App %s does not seem to contain any Model" %
                    app)
        except OSError, err:
            print "error: App %s, %s" % (app, err)
        except RuntimeError, err:
            print "warning: App %s, %s" % (app, err)
        except ImproperlyConfigured:
            print "warning: App %s does not seem to contain a models.py" % app

    # Clear the cached Migrations instances now that we have more of them.
    Migrations._clear_cache() #pylint: disable=no-member,protected-access
    migrate_cmd = migrate.Command()
    for app in initial_apps:
        print "initial migrate for %s" % app
        migrate_cmd.handle(app, fake=True)
    print "MIGRATE ALL!"
    migrate_cmd.handle()

