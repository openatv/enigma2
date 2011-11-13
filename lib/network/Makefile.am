AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

noinst_LIBRARIES = libenigma_network.a

libenigma_network_a_SOURCES = \
	serversocket.cpp \
	socket.cpp

networkincludedir = $(pkgincludedir)/lib/network
networkinclude_HEADERS = \
	serversocket.h \
	socket.h
