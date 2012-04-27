AUTOMAKE_OPTIONS = subdir-objects

AM_CPPFLAGS = \
	-I$(top_builddir) \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

# initialize these, to be filled with targets in the included files
noinst_LIBRARIES=
plugin_LTLIBRARIES=
BUILT_SOURCES=
CLEANFILES=
EXTRA_DIST=
noinst_PYTHON=
nobase_install_PYTHON=
installdir = $(pkglibdir)
plugindir = $(libdir)/enigma2/python/Components
pluginexecdir = $(libdir)/enigma2/python/Components
pluginexec_PROGRAMS=

include actions/Makefile.inc
include base/Makefile.inc
include components/Makefile.inc
include dvb/Makefile.inc
include dvb_ci/Makefile.inc
include gdi/Makefile.inc
include service/Makefile.inc
include driver/Makefile.inc
include nav/Makefile.inc
include gui/Makefile.inc
include mmi/Makefile.inc
include network/Makefile.inc
include python/Makefile.inc
include timeshift/Makefile.inc

# Build the subdirs without parallellism
SUBDIRS = python
