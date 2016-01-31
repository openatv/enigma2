noinst_LIBRARIES += dvb/libenigma_dvb.a

dvb_libenigma_dvb_a_SOURCES = \
	dvb/cablescan.cpp \
	dvb/cahandler.cpp \
	dvb/crc32.cpp \
	dvb/db.cpp \
	dvb/decoder.cpp \
	dvb/demux.cpp \
	dvb/dvb.cpp \
	dvb/dvbtime.cpp \
	dvb/eit.cpp \
	dvb/epgcache.cpp \
	dvb/esection.cpp \
	dvb/fastscan.cpp \
	dvb/filepush.cpp \
	dvb/frontend.cpp \
	dvb/frontendparms.cpp \
	dvb/metaparser.cpp \
	dvb/pesparse.cpp \
	dvb/pmt.cpp \
	dvb/pvrparse.cpp \
	dvb/radiotext.cpp \
	dvb/rotor_calc.cpp \
	dvb/scan.cpp \
	dvb/sec.cpp \
	dvb/subtitle.cpp \
	dvb/teletext.cpp \
	dvb/tstools.cpp \
	dvb/volume.cpp \
	dvb/streamserver.cpp \
	dvb/pmtparse.cpp \
	dvb/encoder.cpp

if HAVE_AMLOGIC
dvb_libenigma_dvb_a_SOURCES += dvb/amldecoder.cpp
endif

dvbincludedir = $(pkgincludedir)/lib/dvb
dvbinclude_HEADERS = \
	dvb/cablescan.h \
	dvb/cahandler.h \
	dvb/crc32.h \
	dvb/db.h \
	dvb/decoder.h \
	dvb/demux.h \
	dvb/dvb.h \
	dvb/dvbtime.h \
	dvb/eit.h \
	dvb/epgcache.h \
	dvb/esection.h \
	dvb/fastscan.h \
	dvb/filepush.h \
	dvb/frontend.h \
	dvb/frontendparms.h \
	dvb/idemux.h \
	dvb/idvb.h \
	dvb/isection.h \
	dvb/list.h \
	dvb/metaparser.h \
	dvb/pesparse.h \
	dvb/pmt.h \
	dvb/pvrparse.h \
	dvb/radiotext.h \
	dvb/rotor_calc.h \
	dvb/scan.h \
	dvb/sec.h \
	dvb/specs.h \
	dvb/subtitle.h \
	dvb/teletext.h \
	dvb/tstools.h \
	dvb/volume.h \
	dvb/streamserver.h \
	dvb/pmtparse.h \
	dvb/encoder.h
if HAVE_AMLOGIC
dvbinclude_HEADERS += dvb/amldecoder.h
endif
