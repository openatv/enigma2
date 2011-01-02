AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

plugindir = $(pkglibdir)/python/Plugins/Extensions/SocketMMI

plugin_LTLIBRARIES = socketmmi.la

socketmmi_la_SOURCES = \
	socket_mmi.cpp \
	socket_mmi.h

socketmmi_la_LDFLAGS = -avoid-version -module
