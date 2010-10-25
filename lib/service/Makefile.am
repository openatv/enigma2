AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

noinst_LTLIBRARIES = libenigma_service.la

libenigma_service_la_SOURCES = \
	listboxservice.cpp service.cpp servicemp3.cpp servicedvb.cpp servicefs.cpp \
	event.cpp servicedvbrecord.cpp
	
