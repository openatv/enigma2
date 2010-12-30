AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

plugindir = $(pkglibdir)/python/Plugins/Extensions/DVDPlayer

plugin_LTLIBRARIES = servicedvd.la

servicedvd_la_SOURCES = \
	servicedvd.cpp \
	servicedvd.h

servicedvd_la_LDFLAGS = -avoid-version -module
