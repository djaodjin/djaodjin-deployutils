# -*- Makefile -*-

srcDir      ?= .
buildTop    ?= .

-include $(buildTop)/share/dws/prefix.mk

install::
	cd $(srcDir) && python ./setup.py install
