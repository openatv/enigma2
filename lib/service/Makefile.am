AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

AM_CXXFLAGS = \
	$(LIBXINE_CFLAGS)

noinst_LTLIBRARIES = libenigma_service.la

libenigma_service_la_SOURCES = \
	event.cpp \
	event.h \
	iservice.h \
	listboxservice.cpp \
	listboxservice.h \
	service.cpp \
	service.h \
	servicedvb.cpp \
	servicedvb.h \
	servicedvbrecord.cpp \
	servicedvbrecord.h \
	servicefs.cpp \
	servicefs.h \
	servicemp3.cpp \
	servicemp3.h

if HAVE_LIBXINE
libenigma_service_la_SOURCES += \
	servicexine.cpp \
	servicexine.h
endif
