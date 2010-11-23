AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

noinst_LIBRARIES = libenigma_components.a

libenigma_components_a_SOURCES = \
	file_eraser.cpp \
	scan.cpp

componentsincludedir = $(pkgincludedir)/lib/components
componentsinclude_HEADERS = \
	file_eraser.h \
	scan.h
