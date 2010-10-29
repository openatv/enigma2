AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

noinst_LIBRARIES = libenigma_mmi.a

libenigma_mmi_a_SOURCES = \
	mmi_ui.cpp

mmiincludedir = $(pkgincludedir)/lib/mmi
mmiinclude_HEADERS = \
	mmi_ui.h
