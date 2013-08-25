# -*- Makefile -*-

srcDir        := .

-include $(shell dws context)
-include $(buildTop)/share/dws/prefix.mk

install::
	cd $(srcDir) && python ./setup.py install
