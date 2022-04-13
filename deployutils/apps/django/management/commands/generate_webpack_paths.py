# Copyright (c) 2022, DjaoDjin inc.
# see LICENSE

import logging, json, os, sys

from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.staticfiles.finders import get_finders

LOGGER = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate paths for webpack to find node modules in Django apps"

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('-o', '--output',
            action='store', dest='output', default="webpack-conf-paths.json",
         help='Name of the config file where paths webpack will use are stored')


    def handle(self, *args, **options):

        # Lists all search paths for static assets.
        node_modules = []
        ign = apps.get_app_config('staticfiles').ignore_patterns
        for finder in get_finders():
            for _, storage in finder.list(ign):
                search_path = storage.path('')
                if not search_path in node_modules:
                    node_modules += [search_path]
        venv = os.path.dirname(os.path.dirname(sys.executable))
        node_modules += [
            os.path.join(venv, 'lib', 'node_modules')
        ]

        # Where webpack meta files are stored
        configs = {
            'assets_cache_path': str(settings.BASE_DIR),
            'node_modules': node_modules,
        }
        if hasattr(settings, 'WEBPACK_LOADER_STATS_FILE'):
            configs.update({
                'webpack_loader_stats_path': os.path.dirname(
                    settings.WEBPACK_LOADER_STATS_FILE),
                'webpack_loader_stats_filename': os.path.basename(
                    settings.WEBPACK_LOADER_STATS_FILE)
            })

        output = options.get('output')
        with open(output, 'w') as file_d:
            file_d.write(json.dumps(configs, indent=2))
        self.stdout.write('dumped config paths to %s' % output)
