#!/usr/bin/env python
# Copyright (c) 2022, Djaodjin Inc.
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

import argparse, configparser, inspect, json, logging, os, sys

import requests

from deployutils import __version__
from deployutils.copy import download_theme, shell_command, upload_theme


LOGGER = logging.getLogger(__name__)
CONFIG = configparser.ConfigParser()
CONFIG_FILENAME = None
DEFAULT_API_ENDPOINT = "https://api.djaodjin.com"


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
            argspec = inspect.signature(func)
            positionals = []
            short_opts = set([])
            for arg in argspec.parameters.values():
                if arg.default == inspect.Parameter.empty:
                    positionals += [arg]
                else:
                    param_name = arg.name.replace('_', '-')
                    short_opt = param_name[0]
                    if not (param_name.startswith('no') or
                        (short_opt in short_opts)):
                        opts = ['-%s' % short_opt, '--%s' % param_name]
                    else:
                        opts = ['--%s' % param_name]
                    short_opts |= set([short_opt])
                    if isinstance(arg.default, list):
                        parser.add_argument(*opts, action='append')
                    elif isinstance(arg.default, dict):
                        parser.add_argument(*opts, type=json.loads)
                    elif arg.default is False:
                        parser.add_argument(*opts, action='store_true')
                    elif arg.default is not None:
                        parser.add_argument(*opts, default=arg.default)
                    else:
                        parser.add_argument(*opts)
            if positionals:
                for arg in positionals[:-1]:
                    parser.add_argument(arg.name)
                parser.add_argument(positionals[-1].name, nargs='*')


def filter_subcommand_args(func, options):
    """
    Filter out all options which are not part of the function *func*
    prototype and returns a set that can be used as kwargs for calling func.
    """
    kwargs = {}
    sig = inspect.signature(func)
    for arg in sig.parameters.values():
        if arg.name in options:
            kwargs.update({arg.name: getattr(options, arg.name)})
    return kwargs


def get_project(project=""):
    updated = False
    if not project:
        for section in CONFIG.sections():
            src_path = CONFIG[section].get('src_path', None)
            if src_path and os.path.samefile(src_path, os.getcwd()):
                project = section
                break
        if not project:
            project = os.path.basename(os.getcwd())
            custom_name = input(
                "Please enter the name of the project.\n"\
                "By default a project is hosted at *project*.djaoapp.com\n"\
                "(project defaults to %s): " % project)
            if custom_name:
                project = custom_name
    if project not in CONFIG.sections():
        CONFIG.add_section(project)

    src_path = CONFIG[project].get('src_path', None)
    if not src_path or not os.path.samefile(src_path, os.getcwd()):
        CONFIG.set(project, 'src_path', os.getcwd())
        updated = True

    return project, updated


def get_project_account(project="", account=""):
    project, updated = get_project(project=project)

    if not account:
        account = CONFIG[project].get('account', None)
    if not account:
        account = project
        custom_account = input(
            "Please enter the account project '%s' belongs to\n"\
            "(default to %s): " % (project, account))
        if custom_account:
            account = custom_account

    if not CONFIG[project].get('account', None):
        CONFIG.set(project, 'account', account)
        updated = True

    return project, account, updated


def get_project_connect(project, base_url="", api_key=""):
    """
    Required base_url and api_key to connect to the URL endpoint.
    """
    updated = False
    if project not in CONFIG.sections():
        CONFIG.add_section(project)

    if not base_url:
        base_url = CONFIG[project].get('base_url', None)
    if not base_url:
        domain = '%s.djaoapp.com' % project
        custom_domain = input("Please enter the domain for project '%s'\n"\
            "(default to: %s): " % (project, domain))
        if custom_domain:
            domain = custom_domain
        base_url = "https://%s" % domain
    if not CONFIG[project].get('base_url', None):
        CONFIG.set(project, 'base_url', base_url)
        updated = True

    if not api_key:
        api_key = CONFIG[project].get('api_key', None)
    if not api_key:
        api_key = input("Please enter an API Key for %s\n"\
            "(see https://www.djaodjin.com/docs/faq/#api-keys for help): "
            % base_url)
    if not CONFIG[project].get('api_key', None):
        CONFIG.set(project, 'api_key', api_key)
        updated = True

    return base_url, api_key, updated


def get_project_config(project="", base_url="", api_key=""):
    project, updated = get_project(project)
    base_url, api_key, updated_connect = get_project_connect(
        project, base_url=base_url, api_key=api_key)

    return project, base_url, api_key, (updated or updated_connect)


def save_config(config=None, config_filename=None):
    if not config_filename:
        config_filename = CONFIG_FILENAME
    if not config:
        config = CONFIG
    if not os.path.exists(os.path.dirname(config_filename)):
        os.makedirs(os.path.dirname(config_filename))
    with open(config_filename, 'w') as config_file:
        config.write(config_file)
    sys.stdout.write("saved configuration in %s\n" % config_filename)


def ssh_reverse_tunnel(args, base_url, api_key, prefix=None):
    """
    Creates the SSH reverse tunnel
    """
    local_port = 8000
    remote_port = local_port
    remote_host = 'git@'
    shell_command(['ssh', '-fnNT',
        '-R', '*:%(remote_port)d:localhost:%(local_port)d' % {
            'local_port': local_port, 'remote_port': remote_port},
        remote_host])


def pub_deploy(args, project="", account="", api_key=""):
    """Deploy a container for a project.
    """
    base_url, api_key, updated = get_project_connect(
        'djaodjin',
        base_url=DEFAULT_API_ENDPOINT,
        api_key=api_key)
    project, account, updated = get_project_account(
        project=project, account=account)
    if updated:
        save_config()

    api_container_url = \
        "%(base_url)s/api/containers/%(organization)s/apps/%(app)s/" % {
            'base_url': base_url,
            'organization': str(account),
            'app': str(project)}
    data = None
    container_location = args[0] if args else None
    if container_location:
        data = {'location': container_location}
    resp = requests.post(api_container_url, data=data, auth=(api_key, ""))
    LOGGER.info("POST %s returns %d %s",
        api_container_url, resp.status_code, resp.text)


def pub_download(args, project="", base_url="", api_key="",
                 templates_only=False):
    """Download a theme package for a project.
  --templates-only    download templates only,
                      skip assets.
    """
    project, base_url, api_key, updated = get_project_config(
        project=project, base_url=base_url, api_key=api_key)
    if updated:
        save_config()
    download_theme(args, base_url, api_key, prefix=project,
        templates_only=templates_only)


def pub_init(args, project="", account="", base_url="",
             api_key="", dj_api_key=""):
    """Initialize the API keys and URLs used to upload
a project theme or deploy its container.
    """
    #pylint:disable=too-many-arguments,unused-argument
    _, _, updated = get_project_connect(
        'djaodjin',
        base_url=DEFAULT_API_ENDPOINT,
        api_key=dj_api_key)
    project, account, updated_next = get_project_account(
        project=project, account=account)
    updated |= updated_next
    project, base_url, api_key, updated_next = get_project_config(
        project=project, base_url=base_url, api_key=api_key)
    updated |= updated_next
    if updated:
        save_config()


def pub_tunnel(args, project="", base_url="", api_key=""):
    """SSH Reverse tunnel to a project.
    """
    project, base_url, api_key, updated = get_project_config(
        project=project, base_url=base_url, api_key=api_key)
    if updated:
        save_config()
    ssh_reverse_tunnel(args, base_url, api_key, prefix=project)


def pub_upload(args, project="", base_url="", api_key="", templates_only=False):
    """Upload a theme package (or directory) for a project.
    """
    project, base_url, api_key, updated = get_project_config(
        project=project, base_url=base_url, api_key=api_key)
    if updated:
        save_config()
    upload_theme(args, base_url, api_key, prefix=project,
        templates_only=templates_only)


def main(args):
    """
    Main Entry Point
    """
    global CONFIG_FILENAME
    try:
        parser = argparse.ArgumentParser(
            usage='%(prog)s [options] command\n\nVersion\n  %(prog)s version '
            + str(__version__),
            formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument('--version', action='version',
                            version='%(prog)s ' + str(__version__))
        parser.add_argument(
            '--endpoint', action='store',
            default=DEFAULT_API_ENDPOINT,
            help='API endpoint to call')
        parser.add_argument(
            '--project', action='store',
            default=None,
            help='Project being managed')
        parser.add_argument(
            '--config', action='store',
            default=os.path.join(os.getenv('HOME'), '.djd', 'credentials'),
            help='configuration file')
        build_subcommands_parser(parser, sys.modules[__name__])

        if len(args) <= 1:
            parser.print_help()
            return 1

        options = parser.parse_args(args[1:])
        CONFIG_FILENAME = options.config
        sys.stdout.write("read configuration from %s\n" % CONFIG_FILENAME)
        CONFIG.read(CONFIG_FILENAME)
        for section in CONFIG.sections():
            LOGGER.debug("[%s]", section)
            for key, val in CONFIG.items(section):
                if key.endswith('_key'):
                    LOGGER.debug("%s = *****", key)
                else:
                    LOGGER.debug("%s = %s", key, val)

        # Filter out options which are not part of the function prototype.
        func_args = filter_subcommand_args(options.func, options)
        return options.func(**func_args)

    except RuntimeError as err:
        LOGGER.error(err)
        return err.code


def cli_main():
    logging.basicConfig(level='INFO')
    main(sys.argv)


if __name__ == '__main__':
    cli_main()
