noinst_LIBRARIES += network/libenigma_network.a

network_libenigma_network_a_SOURCES = \
	network/serversocket.cpp \
	network/socket.cpp

networkincludedir = $(pkgincludedir)/lib/network
networkinclude_HEADERS = \
	network/serversocket.h \
	network/socket.h
