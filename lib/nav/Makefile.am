AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

noinst_LIBRARIES = libenigma_nav.a

libenigma_nav_a_SOURCES = \
	core.cpp \
	pcore.cpp

navincludedir = $(pkgincludedir)/lib/nav
navinclude_HEADERS = \
	core.h \
	pcore.h
