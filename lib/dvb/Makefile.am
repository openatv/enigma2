SUBDIRS = lowlevel

AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

noinst_LTLIBRARIES = libenigma_dvb.la

libenigma_dvb_la_SOURCES = \
	crc32.cpp \
	crc32.h \
	db.cpp \
	db.h \
	decoder.cpp \
	decoder.h \
	demux.cpp \
	demux.h \
	dvb.cpp \
	dvb.h \
	dvbtime.cpp \
	dvbtime.h \
	eit.cpp \
	eit.h \
	epgcache.cpp \
	epgcache.h \
	esection.cpp \
	esection.h \
	frontend.cpp \
	frontend.h \
	frontendparms.h \
	idemux.h \
	idvb.h \
	isection.h \
	list.h \
	metaparser.cpp \
	metaparser.h \
	pesparse.cpp \
	pesparse.h \
	pmt.cpp \
	pmt.h \
	pvrparse.cpp \
	pvrparse.h \
	radiotext.cpp \
	radiotext.h \
	rotor_calc.cpp \
	rotor_calc.h \
	scan.cpp \
	scan.h \
	sec.cpp \
	sec.h \
	specs.h \
	subtitle.cpp \
	subtitle.h \
	teletext.cpp \
	teletext.h \
	tstools.cpp \
	tstools.h \
	volume.cpp \
	volume.h
