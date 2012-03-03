AUTOMAKE_OPTIONS = subdir-objects
<<<<<<< HEAD
=======
SUBDIRS = dvb_ci gdi service driver nav gui python mmi network
>>>>>>> parent of 7a3c4ad... Non-recursive makefile part 2

AM_CPPFLAGS = \
	-I$(top_builddir) \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

# initialize these, to be filled with targets in the included files
noinst_LIBRARIES=
BUILT_SOURCES=
CLEANFILES=
EXTRA_DIST=
noinst_PYTHON=
nobase_install_PYTHON=
installdir = $(pkglibdir)

include actions/Makefile.inc
include base/Makefile.inc
include components/Makefile.inc
include dvb/Makefile.inc
<<<<<<< HEAD
include dvb_ci/Makefile.inc
include gdi/Makefile.inc
include service/Makefile.inc
include driver/Makefile.inc
include nav/Makefile.inc
include gui/Makefile.inc
include mmi/Makefile.inc
include network/Makefile.inc
include python/Makefile.inc

# Build the subdirs without parallellism
SUBDIRS = python timeshift
=======
>>>>>>> parent of 7a3c4ad... Non-recursive makefile part 2
