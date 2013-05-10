noinst_LIBRARIES += dvb_ci/libenigma_dvb_ci.a

dvb_ci_libenigma_dvb_ci_a_SOURCES = \
	dvb_ci/dvbci.cpp \
	dvb_ci/dvbci_appmgr.cpp \
	dvb_ci/dvbci_camgr.cpp \
	dvb_ci/dvbci_datetimemgr.cpp \
	dvb_ci/dvbci_mmi.cpp \
	dvb_ci/dvbci_resmgr.cpp \
	dvb_ci/dvbci_session.cpp \
	dvb_ci/dvbci_ui.cpp

dvbciincludedir = $(pkgincludedir)/lib/dvb_ci
dvbciinclude_HEADERS = \
	dvb_ci/dvbci.h \
	dvb_ci/dvbci_appmgr.h \
	dvb_ci/dvbci_camgr.h \
	dvb_ci/dvbci_datetimemgr.h \
	dvb_ci/dvbci_mmi.h \
	dvb_ci/dvbci_resmgr.h \
	dvb_ci/dvbci_session.h \
	dvb_ci/dvbci_ui.h
