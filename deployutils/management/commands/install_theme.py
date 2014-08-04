# Copyright (c) 2014, Djaodjin Inc.
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

import os, subprocess

from django.conf import settings as django_settings
from django.template.base import (Parser,
    TOKEN_TEXT, TOKEN_VAR, TOKEN_BLOCK, TOKEN_COMMENT, TemplateSyntaxError)
from django.template.context import Context
from django.template.debug import DebugLexer
from django.utils.encoding import force_text
from django_assets.templatetags.assets import assets

from deployutils import settings
from deployutils.management.commands import shell_command
from deployutils.management.commands import ResourceCommand, LOGGER


class AssetsParser(Parser):

    def __init__(self, tokens, dest_stream):
        super(AssetsParser, self).__init__(tokens)
        self.dest_stream = dest_stream

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
                        compiled_result = assets(self, token)
                    except TemplateSyntaxError as err:
                        if not self.compile_function_error(token, err):
                            raise
                    context = Context({})
                    self.dest_stream.write(compiled_result.render(context))
                else:
                    self.dest_stream.write(
                        "{%% %s %%}" % token.contents.encode('utf8'))
            elif token.token_type == TOKEN_COMMENT:
                pass


class Command(ResourceCommand):
    """
    Install templates with URLs to compiled assets, as well as
    static assets.
    The cached assets must have been built before this command
    is invoked. They won't be rebuilt here.
    """

    def handle(self, *args, **options):
        install_theme(settings.INSTALLED_TEMPLATES_ROOT,
            settings.RESOURCES_ROOT)


def install_theme(templates_dest, resources_dest):
    for template_dir in django_settings.TEMPLATE_DIRS:
        if (templates_dest
            and not os.path.samefile(template_dir, templates_dest)):
            install_templates(template_dir, templates_dest)
    # Copy local resources (not under source control) to resources_dest.
    excludes = ['--exclude', '*~', '--exclude', '.DS_Store']
    shell_command(['/usr/bin/rsync']
        + excludes + ['-az', '--rsync-path', '/usr/bin/rsync']
        + ['%s/' % django_settings.APP_STATIC_ROOT, resources_dest])


def install_templates(srcroot, destroot):
    """
    Expand link to compiled assets all templates in *srcroot*
    and its subdirectories.
    """
    #pylint: disable=too-many-locals
    if not os.path.exists(destroot):
        os.makedirs(destroot)
    for pathname in os.listdir(srcroot):
        source_name = os.path.join(srcroot, pathname)
        dest_name = os.path.join(destroot, pathname)
        if os.path.isfile(source_name):
            with open(source_name) as source:
                template_string = source.read()
            try:
                template_string = force_text(template_string)
                lexer = DebugLexer(template_string, origin=None)
                tokens = lexer.tokenize()
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
                    print "modified %s" % dest_name
            except UnicodeDecodeError:
                LOGGER.warning("%s: Templates can only be constructed "
                    "from unicode or UTF-8 strings.", source_name)
        elif os.path.isdir(source_name):
            install_templates(source_name, dest_name)
        else:
            print "skip %s" % source_name
