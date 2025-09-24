# Copyright (c) 2025, Djaodjin Inc.
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

import logging, os, re, shutil, subprocess, zipfile

from django.conf import settings as django_settings
from django.template.backends.jinja2 import Jinja2 as Jinja2DjangoTemplates
from django.utils._os import safe_join
from jinja2.lexer import Lexer

from . import settings
from .compat import force_str, get_html_engine, six
from .templatetags.deployutils_prefixtags import asset
from ...copy import shell_command


LOGGER = logging.getLogger(__name__)

STATE_VARIABLE_BEGIN = 5


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


def get_template_search_path(app_name=None):
    template_dirs = []
    if app_name:
        candidate_dir = os.path.join(
            settings.MULTITIER_THEMES_DIR, app_name, 'templates')
        if os.path.isdir(candidate_dir):
            template_dirs += [candidate_dir]
    # Django 1.8+
    for loader in getattr(django_settings, 'TEMPLATES', []):
        for dir_path in loader['DIRS']:
            if dir_path not in template_dirs:
                template_dirs += [dir_path]
    # Previous Django versions
    for field_name in ['TEMPLATE_DIRS', 'TEMPLATES_DIRS']:
        for candidate in list(getattr(django_settings, field_name, [])):
            if not candidate in template_dirs:
                template_dirs += [candidate]
    return template_dirs


def init_build_and_install_dirs(app_name, build_dir=None, install_dir=None):
    if not build_dir:
        build_dir = os.path.join(os.getcwd(), 'build')
    if not install_dir:
        install_dir = os.getcwd()
    build_dir = os.path.join(
        os.path.normpath(os.path.abspath(build_dir)), app_name)
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    os.makedirs(build_dir)
    install_dir = os.path.normpath(os.path.abspath(install_dir))
    if not os.path.isdir(install_dir):
        os.makedirs(install_dir)
    return build_dir, install_dir


def package_assets(app_name, build_dir,
                   excludes=None, includes=None):
    #pylint:disable=unused-argument,too-many-locals
    resources_dest = os.path.join(build_dir, 'public')

    # Copy local resources (not under source control) to resources_dest.
    exclude_args = ['--exclude', '*~', '--exclude', '.DS_Store',
        '--exclude', '.webassets-cache']
    if excludes:
        for pat in excludes:
            exclude_args += ['--exclude', pat]
    app_static_root = django_settings.STATIC_ROOT
    assert app_static_root is not None and app_static_root
    # When app_static_root ends with the static_url, we will want
    # to insert the app_name prefix.
    root_idx = len(app_static_root)
    orig_static_url = django_settings.STATIC_URL
    static_url_parts = orig_static_url.strip('/').split('/')
    path_parts = app_static_root.strip('/').split('/')
    root_idx = 0
    for path_part, url_part in zip(reversed(path_parts),
                                   reversed(static_url_parts)):
        if path_part != url_part:
            break
        root_idx += 1
    if root_idx:
        app_static_root = os.path.sep + os.path.join(*path_parts[:-root_idx])
    if not app_static_root.endswith(os.path.sep):
        app_static_root = app_static_root + os.path.sep
        # static_url is required per-Django to start and ends with a '/'
        # (i.e. '/static/').
        # If we have a trailing '/', rsync will copy the content
        # of the directory instead of the directory itself.
    cmdline_root = ['/usr/bin/rsync'] + exclude_args + [
        '-az', '--safe-links', '--rsync-path', '/usr/bin/rsync']
    if False and includes:
        # XXX includes should add back excluded content to match
        # the `package_theme` implementation.
        for include in includes:
            include_static_root = safe_join(app_static_root, include)
            if os.path.exists(include_static_root):
                include_parts = include.strip('/').split('/')
                if len(include_parts) > 1:
                    include_resources_dest = safe_join(
                        resources_dest, os.path.join(*include_parts[:-1]))
                if not os.path.exists(include_resources_dest):
                    os.makedirs(include_resources_dest)
                cmdline = cmdline_root + [
                    include_static_root, include_resources_dest]
                shell_command(cmdline)
    else:
        cmdline = cmdline_root + [app_static_root, resources_dest]
        shell_command(cmdline)


def package_theme(app_name, build_dir,
                  excludes=None, includes=None, path_prefix=None,
                  template_dirs=None):
    """
    Package resources and templates for a multi-tier environment
    into a zip file.

    Templates are pre-compiled into ``*build_dir*/*app_name*/templates``.
    Compilation means {% assets '*path*' %} and {% static '*path*' %} tags
    are replaced by their compiled expression.
    """
    #pylint:disable=too-many-locals,too-many-arguments
    templates_dest = os.path.join(build_dir, 'templates')
    # override STATIC_URL to prefix APP_NAME.
    orig_static_url = django_settings.STATIC_URL
    if (app_name != settings.APP_NAME
        and not django_settings.STATIC_URL.startswith('/' + app_name)):
        django_settings.STATIC_URL = '/' + app_name + orig_static_url
    if not os.path.exists(templates_dest):
        os.makedirs(templates_dest)
    if template_dirs is None:
        template_dirs = get_template_search_path(app_name)
    for template_dir in template_dirs:
        if not os.path.isdir(template_dir):
            continue
        # The first of template_dirs usually contains the most specialized
        # templates (ie. the ones we truely want to install).
        if (templates_dest
            and not os.path.samefile(template_dir, templates_dest)):
            install_templates(template_dir, templates_dest,
                excludes=excludes, includes=includes, path_prefix=path_prefix)
    django_settings.STATIC_URL = orig_static_url


def fill_package(app_name, build_dir=None, install_dir=None):
    """
    Creates the theme package (.zip) from templates and optionally
    assets installed in the ``build_dir``.
    """
    zip_path = os.path.join(install_dir, '%s.zip' % app_name)
    with zipfile.ZipFile(zip_path, 'w') as zip_file:
        fill_package_zip(zip_file, os.path.dirname(build_dir), prefix=app_name)
    return zip_path


def fill_package_zip(zip_file, srcroot, prefix=''):
    for pathname in os.listdir(os.path.join(srcroot, prefix)):
        pathname = os.path.join(prefix, pathname)
        full_path = os.path.join(srcroot, pathname)
        if os.path.isfile(full_path):
            zip_file.write(full_path, pathname)
        if os.path.isdir(full_path):
            fill_package_zip(zip_file, srcroot, prefix=pathname)


def _list_templates(srcroot, prefix=''):
    """
    List all templates in srcroot
    """
    results = []
    for pathname in os.listdir(os.path.join(srcroot, prefix)):
        pathname = os.path.join(prefix, pathname)
        source_name = os.path.join(srcroot, pathname)
        if os.path.isfile(source_name):
            results += [pathname]
        elif os.path.isdir(source_name):
            if not source_name.endswith('jinja2'):
                results += _list_templates(srcroot, prefix=pathname)
    return results


def _install_jinja2_template(engine, template_string, source_name, dest_name):
    template_name = None
    tokens = Lexer(engine.env).tokeniter(template_string,
        template_name, filename=source_name)
    buffered_tokens = []
    state = None
    with open(dest_name, 'w') as dest:
        for token in tokens:
            if state is None:
                if token[1] == 'variable_begin':
                    state = STATE_VARIABLE_BEGIN
            elif state == STATE_VARIABLE_BEGIN:
                if token[1] == 'variable_end':
                    buffered_tokens += [token]
                    state = None
            if state is None:
                if buffered_tokens:
                    if len(buffered_tokens) == 5:
                        if (buffered_tokens[0][1] == 'variable_begin' and
                            buffered_tokens[3][1] == 'name' and
                            buffered_tokens[3][2] == 'asset'):
                            val = buffered_tokens[1][2]
                            if val and val[0] in ('"', "'"):
                                cached_asset = asset(val[1:-1])
                                dest.write(cached_asset)
                            buffered_tokens = []
                    if buffered_tokens:
                        dest.write("%s" % ''.join([token[2]
                            for token in buffered_tokens]))
                    buffered_tokens = []
                elif six.PY2:
                    dest.write("%s" % token[2].encode('utf-8'))
                else:
                    dest.write("%s" % str(token[2]))
            else:
                buffered_tokens += [token]
        if buffered_tokens:
            dest.write("%s" % ''.join([
                token[2] for token in buffered_tokens]))
            buffered_tokens = []
        dest.write("\n")


def install_templates(srcroot, destroot, prefix='', excludes=None,
                      includes=None, path_prefix=None):
    #pylint:disable=too-many-arguments,too-many-statements
    """
    Expand link to compiled assets all templates in *srcroot*
    and its subdirectories.
    """
    #pylint: disable=too-many-locals
    exclude_pats = [r'.*~', r'\.DS_Store']
    if excludes:
        exclude_pats += excludes
    if includes is None:
        includes = []
    if not os.path.exists(os.path.join(prefix, destroot)):
        os.makedirs(os.path.join(prefix, destroot))
    for pathname in _list_templates(srcroot):
        source_name = os.path.join(srcroot, pathname)
        dest_name = os.path.join(destroot, pathname)
        excluded = False
        for pat in exclude_pats:
            if re.search(pat, pathname):
                excluded = True
                break
        if excluded:
            for pat in includes:
                if re.search(pat, pathname):
                    excluded = False
                    break
        if excluded:
            LOGGER.debug("skip %s", source_name)
            continue
        LOGGER.debug("%s %s %s", "install" if (
            os.path.isfile(source_name) and not os.path.exists(dest_name)) else
            "pass", source_name, dest_name)
        if os.path.isfile(source_name) and not os.path.exists(dest_name):
            # We don't want to overwrite specific theme files by generic ones.
            with open(source_name) as source:
                template_string = source.read()
                if six.PY2 and hasattr(template_string, 'decode'):
                    template_string = template_string.decode('utf-8')
            try:
                template_string = force_str(template_string)
                if not os.path.isdir(os.path.dirname(dest_name)):
                    os.makedirs(os.path.dirname(dest_name))
                engine, unused_libraries, unused_builtins = get_html_engine()
                if isinstance(engine, Jinja2DjangoTemplates):
                    _install_jinja2_template(engine, template_string, source_name, dest_name)
                else:
                    raise RuntimeError("no packager for template engine '%s'" %
                        engine.__class__)

                lines = None
                cmdline = ['diff', '-u', source_name, dest_name]
                try:
                    with subprocess.Popen(
                            cmdline, stdout=subprocess.PIPE) as cmd:
                        lines = cmd.stdout.readlines()
                        cmd.wait()
                except AttributeError:
                    pass # Py2.7 Popen doesn't support context managers
                         # i.e. `__exit__` is undefined.
                # Non-zero error codes are ok here. That's how diff
                # indicates the files are different.
                if lines:
                    verb = 'compile'
                else:
                    verb = 'install'
                dest_multitier_name = dest_name.replace(destroot,
                        '*MULTITIER_TEMPLATES_ROOT*')
                LOGGER.debug("%s %s to %s", verb,
                    source_name.replace(
                        #py3.10: will be PosixPath
                        str(django_settings.BASE_DIR), '*APP_ROOT*'),
                    dest_multitier_name)
            except UnicodeDecodeError:
                LOGGER.warning("%s: Templates can only be constructed "
                    "from unicode or UTF-8 strings.", pathname)
