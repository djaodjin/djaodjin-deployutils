# -*- Makefile -*-

-include $(buildTop)/share/dws/prefix.mk

srcDir        ?= .
installTop    ?= $(VIRTUAL_ENV)
binDir        ?= $(installTop)/bin

PYTHON        := $(binDir)/python

install::
	cd $(srcDir) && $(PYTHON) ./setup.py install --quiet

# prerequisite: pip install Sphinx
doc:
	cd $(srcDir) && sphinx-build -b html ./docs $(PWD)/docs
