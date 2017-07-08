# Copyright (c) 2017, Djaodjin Inc.
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

#pylint: disable=no-name-in-module,unused-import,import-error

try:
    from django.template.base import DebugLexer
except ImportError: # django < 1.8
    from django.template.debug import DebugLexer as BaseDebugLexer

    class DebugLexer(BaseDebugLexer):

        def __init__(self, template_string):
            super(DebugLexer, self).__init__(template_string, origin=None)


class DjangoTemplate(object):

    @property
    def template_builtins(self):
        from django.template.base import builtins
        return builtins

    @property
    def template_libraries(self):
        from django.template.base import libraries
        return libraries


def get_html_engine():
    try:
        from django.template import engines
        from django.template.utils import InvalidTemplateEngineError
        try:
            return engines['html'], None, None
        except InvalidTemplateEngineError:
            engine = engines['django'].engine
            return engine, engine.template_libraries, engine.template_builtins
    except ImportError: # django < 1.8
        return DjangoTemplate()


try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError: # django < 1.11
    class MiddlewareMixin(object):
        pass
