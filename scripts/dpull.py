#!/usr/bin/env python

"""Fetch a git repository and restart the webapp service."""

import os, sys

__version__ = None

if __name__ == '__main__':
    webapp_path = sys.argv[1]
    os.chdir(webapp_path)
    python_executable = os.path.join(
        os.path.dirname(webapp_path), 'bin', 'python')
    cmd = [ python_executable, './manage.py', 'pullapp' ]
    sys.stderr.write('run: %s' % ' '.join(cmd))
    sys.exit(os.system(' '.join(cmd)))
