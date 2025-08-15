# -*- Makefile -*-

-include $(buildTop)/share/dws/prefix.mk

srcDir        ?= .
installTop    ?= $(if $(VIRTUAL_ENV),$(VIRTUAL_ENV),$(abspath $(srcDir))/.venv)
binDir        ?= $(installTop)/bin
libDir        ?= $(installTop)/lib
objDir        ?= ./build
CONFIG_DIR    ?= $(installTop)/etc/testsite
RUN_DIR       ?= $(abspath $(srcDir))

installDirs   ?= install -d
installFiles  ?= install -p -m 644
DOCKER        ?= docker
PYTHON        := python
PIP           := pip
TWINE         := twine

ASSETS_DIR    ?= $(srcDir)/testsite/static
DB_NAME       ?= $(RUN_DIR)/db.sqlite

$(info Path to python executable (i.e. PYTHON) while running make: $(shell which $(PYTHON)))

MANAGE        := TESTSITE_SETTINGS_LOCATION=$(CONFIG_DIR) RUN_DIR=$(RUN_DIR) $(PYTHON) manage.py

# Django 1.7,1.8 sync tables without migrations by default while Django 1.9
# requires a --run-syncdb argument.
# Implementation Note: We have to wait for the config files to be installed
# before running the manage.py command (else missing SECRECT_KEY).
RUNSYNCDB     = $(if $(findstring --run-syncdb,$(shell cd $(srcDir) && $(MANAGE) migrate --help 2>/dev/null)),--run-syncdb,)

APP_NAME    = testsite
APP_VERSION = $(shell $(MANAGE) shell -c 'from django.conf import settings ; print(settings.APP_VERSION)' 2>/dev/null)


install::
	cd $(srcDir) && $(PIP) install .


install-conf:: $(DESTDIR)$(CONFIG_DIR)/credentials \
                $(DESTDIR)$(CONFIG_DIR)/gunicorn.conf


dist::
	$(PYTHON) -m build
	$(TWINE) check dist/*
	$(TWINE) upload dist/*


build-assets: $(ASSETS_DIR)/cache/app-$(APP_VERSION).js

$(ASSETS_DIR)/cache/app-$(APP_VERSION).js: $(srcDir)/testsite/static/js/app.js
	$(installDirs) $(dir $@)
	$(installFiles) $< $@


clean:: clean-dbs
	[ ! -f $(srcDir)/package-lock.json ] || rm $(srcDir)/package-lock.json
	find $(srcDir) -name '__pycache__' -exec rm -rf {} +
	find $(srcDir) -name '*~' -exec rm -rf {} +

clean-dbs:
	[ ! -f $(DB_NAME) ] || rm $(DB_NAME)


doc:
	$(installDirs) build/docs
	cd $(srcDir) && DJAODJIN_SECRET_KEY=`$(PYTHON) -c 'import sys ; from random import choice ; sys.stdout.write("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789") for i in range(50)]))'` sphinx-build -b html ./docs $(PWD)/build/docs


initdb: clean-dbs
	$(installDirs) $(dir $(DB_NAME))
	cd $(srcDir) && $(MANAGE) migrate $(RUNSYNCDB) --noinput


# !!! Attention !!!
# You will need to run `make initdb` before running `package-docker` in order
# to create the dummy db.sqilte file to package.
package-docker: build-assets
	cd $(srcDir) && $(DOCKER) build $(DOCKER_OPTS) .

# we remove the build directory to make sure we don't have extra files remaining
# when we excluded them in the package_theme command line. We also insures
# we are not removing important directories in the src tree by running
# the condition: `[ "$(abspath $(objDir))" != "$(abspath $(srcDir))" ]`.
package-theme: build-assets
	[ "$(abspath $(objDir))" != "$(abspath $(srcDir))" ] && rm -rf $(objDir)/$(APP_NAME)
	cd $(srcDir) && DEBUG=0 FEATURES_REVERT_TO_DJANGO=0 \
		$(MANAGE) package_theme \
		--build_dir=$(objDir) --install_dir=$(srcDir)/dist


vendor-assets-prerequisites:


$(DESTDIR)$(CONFIG_DIR)/credentials: $(srcDir)/testsite/etc/credentials
	$(installDirs) $(dir $@)
	@if [ ! -f $@ ] ; then \
		sed \
		-e "s,\%(SECRET_KEY)s,`$(PYTHON) -c 'import sys ; from random import choice ; sys.stdout.write("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)]))'`," \
		-e "s,\%(DJAODJIN_SECRET_KEY)s,`$(PYTHON) -c 'import sys ; from random import choice ; sys.stdout.write("".join([choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^*-_=+") for i in range(50)]))'`," \
		$< > $@ ; \
	else \
		echo "warning: We are keeping $@ intact but $< contains updates that might affect behavior of the testsite." ; \
	fi


$(DESTDIR)$(CONFIG_DIR)/gunicorn.conf: $(srcDir)/testsite/etc/gunicorn.conf
	$(installDirs) $(dir $@)
	[ -f $@ ] || sed -e 's,%(RUN_DIR)s,$(RUN_DIR),' $< > $@


-include $(buildTop)/share/dws/suffix.mk

.PHONY: all check dist doc install build-assets vendor-assets-prerequisites
