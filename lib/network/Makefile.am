AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

noinst_LIBRARIES = libenigma_network.a

libenigma_network_a_SOURCES = \
	httpd.cpp \
	http_dyn.cpp \
	http_file.cpp \
	http.cpp \
	serversocket.cpp \
	socket.cpp

networkincludedir = $(pkgincludedir)/lib/network
networkinclude_HEADERS = \
	httpd.h \
	http_dyn.h \
	http_file.h \
	http.h \
	serversocket.h \
	socket.h
