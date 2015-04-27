noinst_LIBRARIES += nav/libenigma_nav.a

nav_libenigma_nav_a_SOURCES = \
	nav/core.cpp \
	nav/pcore.cpp

navincludedir = $(pkgincludedir)/lib/nav
navinclude_HEADERS = \
	nav/core.h
