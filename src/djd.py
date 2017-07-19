#!/usr/bin/env python
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

"""
Command-line utillity to deploy to djaodjin
"""

import argparse, inspect, os, sys

from deployutils.copy import upload, download


__version__ = None


def build_subcommands_parser(parser, module):
    """
    Returns a parser for the subcommands defined in the *module*
    (i.e. commands starting with a 'pub_' prefix).
    """
    mdefs = module.__dict__
    keys = list(mdefs.keys())
    keys.sort()
    subparsers = parser.add_subparsers(help='sub-command help')
    for command in keys:
        if command.startswith('pub_'):
            func = module.__dict__[command]
            parser = subparsers.add_parser(command[4:], help=func.__doc__)
            parser.set_defaults(func=func)
            argspec = inspect.getargspec(func)
            flags = len(argspec.args)
            if argspec.defaults:
                flags = len(argspec.args) - len(argspec.defaults)
            if flags >= 1:
                for arg in argspec.args[:flags - 1]:
                    parser.add_argument(arg)
                parser.add_argument(argspec.args[flags - 1], nargs='*')
            short_opts = set([])
            for idx, arg in enumerate(argspec.args[flags:]):
                arg = arg.replace('_', '-')
                short_opt = arg[0]
                if not (arg.startswith('no') or (short_opt in short_opts)):
                    opts = ['-%s' % short_opt, '--%s' % arg]
                else:
                    opts = ['--%s' % arg]
                short_opts |= set([short_opt])
                if isinstance(argspec.defaults[idx], list):
                    parser.add_argument(*opts, action='append')
                elif isinstance(argspec.defaults[idx], dict):
                    parser.add_argument(*opts, type=json.loads)
                elif argspec.defaults[idx] is False:
                    parser.add_argument(*opts, action='store_true')
                elif argspec.defaults[idx] is not None:
                    parser.add_argument(*opts, default=argspec.defaults[idx])
                else:
                    parser.add_argument(*opts)


def filter_subcommand_args(func, options):
    """
    Filter out all options which are not part of the function *func*
    prototype and returns a set that can be used as kwargs for calling func.
    """
    kwargs = {}
    argspec = inspect.getargspec(func)
    for arg in argspec.args:
        if arg in options:
            kwargs.update({arg: getattr(options, arg)})
    return kwargs


def pub_download(args, location=None, prefix=""):
    """Download theme packages from the stage *location*.
    """
    download(location, remotes=args, prefix=prefix)


def pub_upload(args, location=None, prefix=""):
    """Upload theme packages to the stage *location*.
    """
    upload(location, remotes=args, prefix=prefix)


def main(args):
    """
    Main Entry Point
    """
    try:
        import __main__
        parser = argparse.ArgumentParser(
            usage='%(prog)s [options] command\n\nVersion\n  %(prog)s version '
            + str(__version__),
            formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument('--version', action='version',
                            version='%(prog)s ' + str(__version__))
        build_subcommands_parser(parser, __main__)

        if len(args) <= 1:
            parser.print_help()
            return 1

        options = parser.parse_args(args[1:])
        # Filter out options with are not part of the function prototype.
        func_args = filter_subcommand_args(options.func, options)
        options.func(**func_args)

    except RuntimeError as err:
        LOGGER.error(err)
        return err.code


if __name__ == '__main__':
    main(sys.argv)
