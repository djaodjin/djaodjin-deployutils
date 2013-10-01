# -*- Makefile -*-

-include $(buildTop)/share/dws/prefix.mk

srcDir      ?= .

install::
	cd $(srcDir) && python ./setup.py install
