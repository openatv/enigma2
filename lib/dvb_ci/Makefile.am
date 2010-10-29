AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

noinst_LIBRARIES = libenigma_dvb_ci.a

libenigma_dvb_ci_a_SOURCES = \
	dvbci.cpp \
	dvbci_appmgr.cpp \
	dvbci_camgr.cpp \
	dvbci_datetimemgr.cpp \
	dvbci_mmi.cpp \
	dvbci_resmgr.cpp \
	dvbci_session.cpp \
	dvbci_ui.cpp

dvbciincludedir = $(pkgincludedir)/lib/dvb_ci
dvbciinclude_HEADERS = \
	dvbci.h \
	dvbci_appmgr.h \
	dvbci_camgr.h \
	dvbci_datetimemgr.h \
	dvbci_mmi.h \
	dvbci_resmgr.h \
	dvbci_session.h \
	dvbci_ui.h
