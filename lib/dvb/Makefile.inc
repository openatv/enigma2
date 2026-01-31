noinst_LIBRARIES += dvb/libenigma_dvb.a

dvb_libenigma_dvb_a_SOURCES = \
	dvb/cablescan.cpp \
	dvb/cahandler.cpp \
	dvb/crc32.cpp \
	dvb/csaengine.cpp \
	dvb/csasession.cpp \
	dvb/db.cpp \
	dvb/decoder.cpp \
	dvb/demux.cpp \
	dvb/dvb.cpp \
	dvb/dvbtime.cpp \
	dvb/eit.cpp \
	dvb/epgcache.cpp \
	dvb/epgchanneldata.cpp \
	dvb/epgtransponderdatareader.cpp \
	dvb/esection.cpp \
	dvb/fastscan.cpp \
	dvb/fbc.cpp \
	dvb/filepush.cpp \
	dvb/frontend.cpp \
	dvb/frontendparms.cpp \
	dvb/metaparser.cpp \
	dvb/opentv.cpp \
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
	dvb/rtspstreamserver.cpp \
	dvb/pmtparse.cpp \
	dvb/encoder.cpp \
	dvb/atsc.cpp \
	dvb/fcc.cpp \
	dvb/fccdecoder.cpp

dvbincludedir = $(pkgincludedir)/lib/dvb
dvbinclude_HEADERS = \
	dvb/cablescan.h \
	dvb/cahandler.h \
	dvb/crc32.h \
	dvb/csaengine.h \
	dvb/csasession.h \
	dvb/db.h \
	dvb/decoder.h \
	dvb/demux.h \
	dvb/dvb.h \
	dvb/dvbtime.h \
	dvb/eit.h \
	dvb/epgcache.h \
	dvb/epgchanneldata.h \
	dvb/epgtransponderdatareader.h \
	dvb/esection.h \
	dvb/fastscan.h \
	dvb/fbc.h \
	dvb/filepush.h \
	dvb/frontend.h \
	dvb/frontendparms.h \
	dvb/idemux.h \
	dvb/idvb.h \
	dvb/isection.h \
	dvb/list.h \
	dvb/metaparser.h \
	dvb/opentv.h \
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
	dvb/rtspstreamserver.h \
	dvb/pmtparse.h \
	dvb/encoder.h \
	dvb/atsc.h \
	dvb/fcc.h \
	dvb/fccdecoder.h

if DREAMNEXTGEN
dvbinclude_HEADERS += \
	dvb/alsa.h \
	dvb/decoders.h \
	dvb/ringbuffer.h \
	dvb/tsparser.h
endif
