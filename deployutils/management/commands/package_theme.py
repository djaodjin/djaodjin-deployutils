# Copyright (c) 2015, Djaodjin Inc.
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

import logging, os, re, subprocess, zipfile
from optparse import make_option

from django.conf import settings as django_settings
from django.contrib.staticfiles.templatetags.staticfiles import do_static
from django.template.base import (Parser,
    TOKEN_TEXT, TOKEN_VAR, TOKEN_BLOCK, TOKEN_COMMENT, TemplateSyntaxError)
from django.template.context import Context
from django.template.debug import DebugLexer
from django.utils.encoding import force_text
from django_assets.templatetags.assets import assets

from deployutils import settings
from deployutils.management.commands import shell_command
from deployutils.management.commands import ResourceCommand, LOGGER

LOGGER = logging.getLogger(__name__)


class AssetsParser(Parser):

    def __init__(self, tokens, dest_stream):
        super(AssetsParser, self).__init__(tokens)
        self.dest_stream = dest_stream
        self.context = Context({})

    def parse_through(self, parse_until=None):
        if parse_until is None:
            parse_until = []
        nodelist = self.create_nodelist()
        while self.tokens:
            token = self.next_token()
            if token.token_type == TOKEN_TEXT:
                self.dest_stream.write(token.contents.encode('utf8'))
            elif token.token_type == TOKEN_VAR:
                self.dest_stream.write(
                    "{{%s}}" % token.contents.encode('utf8'))
            elif token.token_type == TOKEN_BLOCK:
                try:
                    command = token.contents.split()[0]
                except IndexError:
                    self.empty_block_tag(token)
                if command in parse_until:
                    # put token back on token list so calling
                    # code knows why it terminated
                    self.prepend_token(token)
                    return nodelist
                if command == 'assets':
                    try:
                        # XXX This should work but for some reason debug does
                        # not get propagated.
                        # Lost in webassets.bundle.resolve_contents
                        token.contents += ' debug=False'
                        compiled_result = assets(self, token)
                    except TemplateSyntaxError as err:
                        if not self.compile_function_error(token, err):
                            raise
                    self.dest_stream.write(compiled_result.render(self.context))
                elif command == 'static':
                    compiled_result = do_static(self, token)
                    self.dest_stream.write(compiled_result.render(self.context))
                else:
                    self.dest_stream.write(
                        "{%% %s %%}" % token.contents.encode('utf8'))
            elif token.token_type == TOKEN_COMMENT:
                pass


class Command(ResourceCommand):
    """
    Package resources and templates for a multi-tier environment
    into a zip file.

    Templates are pre-compiled into ``*build_dir*/*app_name*/templates``.
    Compilation means {% assets '*path*' %} and {% static '*path*' %} tags
    are replaced by their compiled expression.

    Resources are copied into ``*build_dir*/*app_name*/static``.
    Resources include CSS, JS, images and other files which can be accessed
    anonymously over HTTP and are necessary for the functionality of the site.
    This command considers everything in ``APP_STATIC_ROOT`` to be a resource.

    This command must be run with DEBUG=False and the cached assets must
    have been built before this command is invoked. They won't be rebuilt here.

    Example::

    $ DEBUG=0 python manage.py package_theme

    APP_NAME can be overriden with the ``--app_name`` command line flag.

    Example::

    $ ls
    templates/base.html
    $ python manage.py package_theme --app_name webapp
    $ ls build
    build/webapp/templates/base.html

    It is possible to exclude template files that match a regular expression.
    For more complex filters, it is possible to still include a subset
    of the excluded templates when they also match a secondary regular
    expression.

    Example::

    $ ls
    templates/base.html
    templates/skip/template.html
    templates/skip/deep/template.html
    $ python manage.py package_theme --exclude='skip/*' --include='skip/deep/*'
    $ ls build
    build/app_name/templates/base.html
    build/app_name/templates/skip/deep/template.html
    """
    help = "package templates and resources for a multitier setup."

    option_list = ResourceCommand.option_list + (
        make_option('--app_name', action='store', dest='app_name',
            default=settings.APP_NAME,
            help='overrides the destination site name'),
        make_option('--build_dir', action='store', dest='build_dir',
            default=None,
            help='set the directory root where output files are created.'),
        make_option('--excludes', action='append', dest='excludes',
            default=[], help='exclude specified templates directories'),
        make_option('--includes', action='append', dest='includes',
            default=[], help='include specified templates directories'\
                ' (after excludes have been applied)'),
        )

    def handle(self, *args, **options):
        app_name = options['app_name']
        package_theme(
            app_name, build_dir=options['build_dir'],
            excludes=options['excludes'],
            includes=options['includes'])


def package_theme(app_name, build_dir=None, excludes=None, includes=None):
    if not build_dir:
        build_dir = os.path.join(os.getcwd(), 'build')
    templates_dest = os.path.join(build_dir, app_name, 'templates')
    resources_dest = os.path.join(build_dir, app_name, 'public')
    # override STATIC_URL to prefix APP_NAME.
    orig_static_url = django_settings.STATIC_URL
    if not django_settings.STATIC_URL.startswith(
            '/' + settings.APP_NAME):
        django_settings.STATIC_URL = \
            '/' + settings.APP_NAME + orig_static_url
    if not os.path.exists(templates_dest):
        os.makedirs(templates_dest)
    template_dirs = [django_settings.TEMPLATE_DIRS[0]]
    candidate_dir = os.path.join(django_settings.TEMPLATE_DIRS[0], app_name)
    if os.path.isdir(candidate_dir):
        template_dirs += [candidate_dir]
    for template_dir in template_dirs:
        # The first TEMPLATE_DIRS usually contains the most specialized
        # templates (ie. the ones we truely want to install).
        if (templates_dest
            and not os.path.samefile(template_dir, templates_dest)):
            install_templates(template_dir, templates_dest,
                excludes=excludes, includes=includes)
    django_settings.STATIC_URL = orig_static_url

    # Copy local resources (not under source control) to resources_dest.
    excludes = ['--exclude', '*~', '--exclude', '.DS_Store']
    app_static_root = django_settings.APP_STATIC_ROOT
    if app_static_root[-1] == os.sep:
        # If we have a trailing '/', rsync will copy the content
        # of the directory instead of the directory itself.
        app_static_root = app_static_root[:-1]
    shell_command(['/usr/bin/rsync']
        + excludes + ['-az', '--safe-links', '--rsync-path', '/usr/bin/rsync']
        + [app_static_root, resources_dest])
    with zipfile.ZipFile(
            os.path.join(build_dir, '%s.zip' % app_name), 'w') as zip_file:
        fill_package(zip_file, build_dir, prefix=app_name)


def fill_package(zip_file, srcroot, prefix=''):
    for pathname in os.listdir(os.path.join(srcroot, prefix)):
        pathname = os.path.join(prefix, pathname)
        full_path = os.path.join(srcroot, pathname)
        if os.path.isfile(full_path):
            zip_file.write(full_path, pathname)
        if os.path.isdir(full_path):
            fill_package(zip_file, srcroot, prefix=pathname)


def install_templates(srcroot, destroot,
                      prefix='', excludes=None, includes=None):
    """
    Expand link to compiled assets all templates in *srcroot*
    and its subdirectories.
    """
    #pylint: disable=too-many-locals
    if not os.path.exists(os.path.join(prefix, destroot)):
        os.makedirs(os.path.join(prefix, destroot))
    for pathname in os.listdir(os.path.join(srcroot, prefix)):
        pathname = os.path.join(prefix, pathname)
        excluded = False
        for pat in excludes:
            if re.match(pat, pathname):
                excluded = True
                break
        if excluded:
            for pat in includes:
                if re.match(pat, pathname):
                    excluded = False
                    break
        if excluded:
            LOGGER.debug("skip %s", pathname)
            continue
        source_name = os.path.join(srcroot, pathname)
        dest_name = os.path.join(destroot, pathname)
        if os.path.isfile(source_name):
            with open(source_name) as source:
                template_string = source.read()
            try:
                template_string = force_text(template_string)
                lexer = DebugLexer(template_string, origin=None)
                tokens = lexer.tokenize()
                if not os.path.isdir(os.path.dirname(dest_name)):
                    os.makedirs(os.path.dirname(dest_name))
                with open(dest_name, 'w') as dest:
                    parser = AssetsParser(tokens, dest)
                    parser.parse_through()
                cmdline = ['diff', '-u', source_name, dest_name]
                cmd = subprocess.Popen(cmdline, stdout=subprocess.PIPE)
                lines = cmd.stdout.readlines()
                cmd.wait()
                # Non-zero error codes are ok here. That's how diff
                # indicates the files are different.
                if len(lines) > 0:
                    verb = 'compile'
                else:
                    verb = 'install'
                LOGGER.info("%s %s to %s", verb,
                    source_name.replace(
                        django_settings.BASE_DIR, '*APP_ROOT*'),
                    dest_name.replace(destroot,
                        '*MULTITIER_TEMPLATES_ROOT*'))
            except UnicodeDecodeError:
                LOGGER.warning("%s: Templates can only be constructed "
                    "from unicode or UTF-8 strings.", source_name)
        elif os.path.isdir(source_name):
            install_templates(srcroot, destroot, prefix=pathname,
                excludes=excludes, includes=includes)
