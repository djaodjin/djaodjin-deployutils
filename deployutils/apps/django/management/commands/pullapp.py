# Copyright (c) 2018, Djaodjin Inc.
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

import datetime, fnmatch, inspect, logging, os, re, shutil, subprocess, sys

from django.db import models
from django.core.exceptions import ImproperlyConfigured

from ... import settings
from .....copy import shell_command, download
from . import ResourceCommand
from .package_theme import package_theme


LOGGER = logging.getLogger(__name__)


try:
    #pylint: disable=import-error
    from south.management.commands import schemamigration

    class SchemaMigration(schemamigration.Command): #pylint: disable=no-init

        def error(self, message, code=1):
            #pylint: disable=unused-argument,no-self-use
            """
            Override the error method to avoid a brutal sys.exit
            """
            raise RuntimeError(message)

except ImportError: # South not present in virtualenv.
    pass


class Command(ResourceCommand):
    help = "Fetch latest code and resources from the stage machine."

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--app_name', action='store', dest='app_name',
            default=settings.APP_NAME,
            help='Override the name of the project')

    def handle(self, *args, **options):
        app_name = options['app_name']
        if args:
            up_commit = args[0]
        else:
            up_commit = 'master'
        try:
            repo_path = os.getcwd()
            last_up_commit, up_commit = fetch_changes(repo_path, up_commit)
            # Fetch resources which are not stored under source control
            download(settings.RESOURCES_REMOTE_LOCATION,
                prefix=settings.MULTITIER_RESOURCES_ROOT,
                dry_run=settings.DRY_RUN)
            migrate_all()
            # XXX moving towards deprecation?
            build_dir = os.path.join(os.getcwd(), 'build')
            package_theme(app_name, build_dir=build_dir)
            templates_dest = os.path.join(
                settings.MULTITIER_THEMES_DIR, app_name)
            resources_dest = os.path.join(
                settings.MULTITIER_RESOURCES_ROOT, app_name)
            shutil.copy(os.path.join(build_dir, app_name, 'templates'),
                templates_dest)
            shutil.copy(os.path.join(build_dir, app_name, 'static'),
                resources_dest)
            LOGGER.info("pullapp %s %s (old: %s)",
                        self.webapp, up_commit, last_up_commit)
        except subprocess.CalledProcessError as err:
            LOGGER.exception(
                "pullapp %s caught exception: %s", self.webapp, err)


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


def _south_migrate_all():
    if not 'south' in settings.INSTALLED_APPS:
        sys.stderr.write(
            "warning: 'south' is not in INSTALLED_APPS, no migration done.\n")
        return 0
    #pylint: disable=import-error,too-many-nested-blocks
    from south.migration import Migrations
    from south.management.commands import migrate
    schema_cmd = SchemaMigration()
    initial_apps = []
    auto_apps = [] #pylint: disable=unused-variable
    for app in [app for app in settings.INSTALLED_APPS if app != 'south']:
        try:
            app_module = models.get_app(app) #pylint: disable=no-member
                                             # South only used with Django < 1.7
            clsmembers = inspect.getmembers(app_module, is_model_class)
            if clsmembers:
                migrations_dir = os.path.join(
                    os.path.dirname(app_module.__file__), 'migrations')
                if os.path.isdir(migrations_dir):
                    schema_cmd.handle(app, auto=True)#pylint:disable=no-member
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
                    schema_cmd.handle( #pylint:disable=no-member
                        app, initial=True)
                    initial_apps += [app]
            else:
                sys.stderr.write(
                    "warning: App %s does not seem to contain any Model\n" %
                    app)
        except OSError as err:
            sys.stderr.write("error: App %s, %s\n" % (app, err))
        except RuntimeError as err:
            sys.stderr.write("error: App %s, %s\n" % (app, err))
        except ImproperlyConfigured:
            sys.stderr.write(
                "warning: App %s does not seem to contain a models.py\n" % app)

    # Clear the cached Migrations instances now that we have more of them.
    Migrations._clear_cache() #pylint: disable=no-member,protected-access
    migrate_cmd = migrate.Command()
    for app in initial_apps:
        sys.stderr.write("initial migrate for %s\n" % app)
        migrate_cmd.handle(app, fake=True)
    sys.stderr.write("MIGRATE ALL!\n")
    migrate_cmd.handle(no_initial_data=True)
    return 0


def migrate_all():
    """
    Create schema migrations for all apps specified in INSTALLED_APPS,
    then run a migrate command.
    """
    if 'south' in settings.INSTALLED_APPS:
        return _south_migrate_all()
    from django.core.management.commands import makemigrations, migrate
    schema_args = [sys.executable, 'makemigrations']
    for app in settings.INSTALLED_APPS:
        if not app.startswith('django'):
            schema_args += [app]
    schema_cmd = makemigrations.Command()
    schema_cmd.run_from_argv(schema_args)

    migrate_cmd = migrate.Command()
    sys.stderr.write("MIGRATE ALL!\n")
    return migrate_cmd.run_from_argv([sys.executable, 'migrate'])
