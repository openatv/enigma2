noinst_LIBRARIES += hbbtv/libenigma_hbbtv.a

hbbtv_libenigma_hbbtv_a_SOURCES = \
	hbbtv/hbbtv.cpp \
	hbbtv/oipfapplication.cpp \
	hbbtv/hbbtv_abi_exports.cpp

hbbtvincludedir = $(pkgincludedir)/lib/hbbtv
hbbtvinclude_HEADERS = \
	hbbtv/hbbtv.h \
	hbbtv/oipfapplication.h
