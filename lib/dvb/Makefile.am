SUBDIRS = lowlevel

AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

noinst_LIBRARIES = libenigma_dvb.a

libenigma_dvb_a_SOURCES = \
	crc32.cpp \
	db.cpp \
	decoder.cpp \
	demux.cpp \
	dvb.cpp \
	dvbtime.cpp \
	eit.cpp \
	epgcache.cpp \
	esection.cpp \
	frontend.cpp \
	metaparser.cpp \
	pesparse.cpp \
	pmt.cpp \
	pvrparse.cpp \
	radiotext.cpp \
	rotor_calc.cpp \
	scan.cpp \
	sec.cpp \
	subtitle.cpp \
	teletext.cpp \
	tstools.cpp \
	volume.cpp

dvbincludedir = $(pkgincludedir)/lib/dvb
dvbinclude_HEADERS = \
	crc32.h \
	db.h \
	decoder.h \
	demux.h \
	dvb.h \
	dvbtime.h \
	eit.h \
	epgcache.h \
	esection.h \
	frontend.h \
	frontendparms.h \
	idemux.h \
	idvb.h \
	isection.h \
	list.h \
	metaparser.h \
	pesparse.h \
	pmt.h \
	pvrparse.h \
	radiotext.h \
	rotor_calc.h \
	scan.h \
	sec.h \
	specs.h \
	subtitle.h \
	teletext.h \
	tstools.h \
	volume.h
