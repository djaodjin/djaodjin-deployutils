# Copyright (c) 2018, Djaodjin Inc.
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

from __future__ import absolute_import
from __future__ import unicode_literals

import logging, os, re, shutil, subprocess, sys, zipfile

from django.conf import settings as django_settings
from django.contrib.staticfiles.templatetags.staticfiles import do_static
from django.template.base import (Parser, NodeList,
    TOKEN_TEXT, TOKEN_VAR, TOKEN_BLOCK, TOKEN_COMMENT, TemplateSyntaxError)
from django.template.context import Context
from django.utils.encoding import force_text
from django.utils import six
from django_assets.templatetags.assets import assets

from ...compat import DebugLexer, get_html_engine
from .....copy import shell_command
from . import ResourceCommand, get_template_search_path

LOGGER = logging.getLogger(__name__)


class URLRewriteWrapper(object):

    def __init__(self, file_obj, path_prefix=None):
        self.wrapped = file_obj
        self.path_prefix = path_prefix

    def write(self, text):
        if self.path_prefix:
            text = text.replace(
                '="/static', '="/%s/static' % self.path_prefix)
        return self.wrapped.write(text)


class Template(object):

    def __init__(self, engine):
        self.engine = engine


class AssetsParser(Parser):

    def __init__(self, tokens, dest_stream,
                 libraries=None, builtins=None, origin=None):
        #pylint:disable=too-many-arguments
        super(AssetsParser, self).__init__(tokens,
            libraries=libraries, builtins=builtins, origin=origin)
        self.dest_stream = dest_stream
        self.context = Context()
        engine, _, _ = get_html_engine()
        self.context.template = Template(engine)

    def parse_through(self, parse_until=None):
        if parse_until is None:
            parse_until = []
        nodelist = NodeList()
        while self.tokens:
            token = self.next_token()
            if six.PY2:
                contents = token.contents.encode('utf8')
            else:
                contents = token.contents
            if token.token_type == TOKEN_TEXT:
                self.dest_stream.write(contents)
            elif token.token_type == TOKEN_VAR:
                self.dest_stream.write("{{%s}}" % contents)
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
                        assets_string = str(
                            assets(self, token).render(self.context))
                        self.dest_stream.write(assets_string)
                    except TemplateSyntaxError as err:
                        if hasattr(self, 'error'):
                            raise self.error(token, err)
                        # Django < 1.8
                        elif not self.compile_function_error(token, err):
                            raise
                elif command == 'static':
                    self.dest_stream.write(
                        do_static(self, token).render(self.context))
                else:
                    self.dest_stream.write("{%% %s %%}" % contents)
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
    This command considers everything in ``STATIC_ROOT`` to be a resource.

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

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('--app_name', action='store', dest='app_name',
            default=django_settings.APP_NAME,
            help='overrides the destination site name')
        parser.add_argument('--path_prefix', action='store',
            dest='path_prefix', default=None,
            help='Adds a prefix to all URLs for static assets')
        parser.add_argument('--build_dir',
            action='store', dest='build_dir', default=None,
            help='set the directory root where temporary files are created.')
        parser.add_argument('--install_dir',
            action='store', dest='install_dir', default=None,
            help='set the directory root where output files are created.')
        parser.add_argument('--exclude', action='append', dest='excludes',
            default=[], help='exclude specified templates directories')
        parser.add_argument('--include', action='append', dest='includes',
            default=[], help='include specified templates directories'\
                ' (after excludes have been applied)')

    def handle(self, *args, **options):
        app_name = options['app_name']
        zip_path = package_theme(app_name,
            install_dir=options['install_dir'],
            build_dir=options['build_dir'],
            excludes=options['excludes'],
            includes=options['includes'],
            path_prefix=options['path_prefix'])
        sys.stdout.write('package built: %s\n' % zip_path)


def package_theme(app_name, install_dir=None, build_dir=None,
                  excludes=None, includes=None, path_prefix=None):
    #pylint:disable=too-many-locals,too-many-arguments
    if not build_dir:
        build_dir = os.path.join(os.getcwd(), 'build')
    if not install_dir:
        install_dir = os.getcwd()
    build_dir = os.path.join(
        os.path.normpath(os.path.abspath(build_dir)), app_name)
    install_dir = os.path.normpath(os.path.abspath(install_dir))
    templates_dest = os.path.join(build_dir, 'templates')
    resources_dest = os.path.join(build_dir, 'public')
    # override STATIC_URL to prefix APP_NAME.
    orig_static_url = django_settings.STATIC_URL
    if (app_name != django_settings.APP_NAME
        and not django_settings.STATIC_URL.startswith('/' + app_name)):
        django_settings.STATIC_URL = '/' + app_name + orig_static_url
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)
    if not os.path.exists(templates_dest):
        os.makedirs(templates_dest)
    template_dirs = get_template_search_path(app_name)
    for template_dir in template_dirs:
        # The first of template_dirs usually contains the most specialized
        # templates (ie. the ones we truely want to install).
        if (templates_dest
            and not os.path.samefile(template_dir, templates_dest)):
            install_templates(template_dir, templates_dest,
                excludes=excludes, includes=includes, path_prefix=path_prefix)

    # Copy local resources (not under source control) to resources_dest.
    excludes = ['--exclude', '*~', '--exclude', '.DS_Store',
        '--exclude', '.webassets-cache']
    app_static_root = django_settings.STATIC_ROOT
    assert app_static_root is not None and app_static_root
    # When app_static_root ends with the static_url, we will want
    # to insert the app_name prefix.
    static_root_parts = app_static_root.split(os.sep)
    root_parts_idx = len(static_root_parts)
    root_idx = len(app_static_root)
    found = False
    for url_part in reversed(orig_static_url.split('/')):
        found = True # With ``break`` later on to default to False
                     # when zero iteration.
        if url_part:
            root_parts_idx = root_parts_idx - 1
            root_idx = root_idx - len(static_root_parts[root_parts_idx]) - 1
            if url_part != static_root_parts[root_parts_idx]:
                found = False
                break
    if found:
        app_static_root = os.path.join(
            app_static_root[:root_idx], django_settings.STATIC_URL[1:-1])
        # static_url is required per-Django to start and ends with a '/'
        # (i.e. '/static/').
        # If we have a trailing '/', rsync will copy the content
        # of the directory instead of the directory itself.
    shell_command(['/usr/bin/rsync']
        + excludes + ['-az', '--safe-links', '--rsync-path', '/usr/bin/rsync']
        + [app_static_root, resources_dest])
    if not os.path.isdir(install_dir):
        os.makedirs(install_dir)
    zip_path = os.path.join(install_dir, '%s.zip' % app_name)
    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        fill_package(zip_file, os.path.dirname(build_dir), prefix=app_name)
    return zip_path

def fill_package(zip_file, srcroot, prefix=''):
    for pathname in os.listdir(os.path.join(srcroot, prefix)):
        pathname = os.path.join(prefix, pathname)
        full_path = os.path.join(srcroot, pathname)
        if os.path.isfile(full_path):
            zip_file.write(full_path, pathname)
        if os.path.isdir(full_path):
            fill_package(zip_file, srcroot, prefix=pathname)


def install_templates(srcroot, destroot, prefix='', excludes=None,
                      includes=None, path_prefix=None):
    #pylint:disable=too-many-arguments
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
        if os.path.isfile(source_name) and not os.path.exists(dest_name):
            # We don't want to overwrite specific theme files by generic ones.
            with open(source_name) as source:
                template_string = source.read()
            try:
                template_string = force_text(template_string)
                lexer = DebugLexer(template_string)
                tokens = lexer.tokenize()
                if not os.path.isdir(os.path.dirname(dest_name)):
                    os.makedirs(os.path.dirname(dest_name))
                from django.template.backends.django import DjangoTemplates
                _, libraries, builtins = get_html_engine()
                with open(dest_name, 'w') as dest:
                    parser = AssetsParser(tokens,
                        URLRewriteWrapper(dest, path_prefix),
                        libraries=libraries,
                        builtins=builtins,
                        origin=None)
                    parser.parse_through()
                cmdline = ['diff', '-u', source_name, dest_name]
                cmd = subprocess.Popen(cmdline, stdout=subprocess.PIPE)
                lines = cmd.stdout.readlines()
                cmd.wait()
                # Non-zero error codes are ok here. That's how diff
                # indicates the files are different.
                if lines:
                    verb = 'compile'
                else:
                    verb = 'install'
                sys.stdout.write("%s %s to %s\n" % (verb,
                    source_name.replace(
                        django_settings.BASE_DIR, '*APP_ROOT*'),
                    dest_name.replace(destroot,
                        '*MULTITIER_TEMPLATES_ROOT*')))
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
                excludes=excludes, includes=includes, path_prefix=path_prefix)
