# Copyright (c) 2015, Djaodjin Inc.
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

import os, re, sys

from django.conf import settings as django_settings
from deployutils.management.commands import ResourceCommand


class Command(ResourceCommand):
    help = "Display an inheritance tree through ``extends`` of templates."

    def handle(self, *args, **options):
        self.edges = []
        for template_dir in django_settings.TEMPLATE_DIRS:
            self._load_templates(
                template_dir, template_roots=django_settings.TEMPLATE_DIRS)
        for edge in self.edges:
            print edge
        self._roots()
        self._create_tree()

    def _roots(self):
        sources = set([])
        targets = set([])
        for edge in self.edges:
            sources |= set([edge[0]])
            targets |= set([edge[1]])
        roots = targets - sources
        print "XXX roots: " + str(roots)

    def _create_tree(self):
        roots = {}
        while len(self.edges) > 0:
            # Find leaf nodes
            sources = set([])
            targets = set([])
            for edge in self.edges:
                sources |= set([edge[0]])
                targets |= set([edge[1]])
            leafs = sources - targets
            # build deepest level
            level = {}
            remains = []
            for edge in self.edges:
                if edge[0] in leafs:
                    if not edge[1] in level:
                        level[edge[1]] = []
                    level[edge[1]] += [edge[0]]
                else:
                    remains += [edge]
            print "XXX level=%s" % str(level)
            print "XXX remains=%s" % '\n'.join([str(r) for r in remains])
            deeper_level = roots
            roots = {}
            used = set([])
            for root, leafs in level.iteritems():
                if not root in roots:
                    roots[root] = []
                for leaf in leafs:
                    if leaf in deeper_level:
                        roots[root] += [{leaf: deeper_level[leaf]}]
                        used |= set([leaf])
                    else:
                        roots[root] += [leaf]
            print "XXX USED: %s" % str(used)
            for root, leafs in deeper_level.iteritems():
                if not root in used:
                    if not root in roots:
                        roots[root] = leafs
                    else:
                        roots[root] += leafs
            print "XXX ROOTS: " + str(roots)
            self.edges = remains
            print "---------------------------------------"
        print roots.keys()


    def _load_templates(self, template_dir, template_roots=None):
        for pathname in os.listdir(template_dir):
            template_name = os.path.join(template_dir, pathname)
            if os.path.isfile(template_name):
                with open(template_name) as source:
                    template_string = source.readline()
                    look = re.match(r'{% extends "(\S+)" %}', template_string)
                    if look:
                        found = False
                        for root in template_roots:
                            if not root.endswith(os.sep):
                                root += os.sep
                            if template_name.startswith(root):
                                found = True
                                self.edges += [(template_name.replace(root, ''),
                                    look.group(1))]
                                break
                        if not found:
                            sys.stderr.write(
                                'unable to find "%s" in template roots %s',
                                template_name, template_roots)

            elif os.path.isdir(template_name):
                self._load_templates(template_name, template_roots)
