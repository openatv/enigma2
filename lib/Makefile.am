AUTOMAKE_OPTIONS = subdir-objects
SUBDIRS = dvb_ci gdi service driver nav gui python mmi network timeshift

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

