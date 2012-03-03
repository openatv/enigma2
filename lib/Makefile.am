AUTOMAKE_OPTIONS = subdir-objects
SUBDIRS = python

AM_CPPFLAGS = \
	-I$(top_builddir) \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

noinst_LIBRARIES=
BUILT_SOURCES=
CLEANFILES=
EXTRA_DIST=

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
