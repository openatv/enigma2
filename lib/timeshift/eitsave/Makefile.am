plugindir = $(libdir)/enigma2/python/Components

AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

plugin_LTLIBRARIES = eitsave.la

eitsave_la_SOURCES = \
	eitsave.cpp 

eitsave_la_LDFLAGS = \
	-avoid-version -module

install-data-hook:
	rm $(DESTDIR)$(libdir)/enigma2/python/Components/eitsave.*a
