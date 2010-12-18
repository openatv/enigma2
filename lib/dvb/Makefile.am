SUBDIRS = lowlevel

AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h

noinst_LTLIBRARIES = libenigma_dvb.la

libenigma_dvb_la_SOURCES = dvb.cpp demux.cpp frontend.cpp esection.cpp db.cpp \
	sec.cpp scan.cpp crc32.cpp pmt.cpp decoder.cpp eit.cpp rotor_calc.cpp \
	epgcache.cpp dvbtime.cpp metaparser.cpp volume.cpp tstools.cpp pvrparse.cpp \
	pesparse.cpp teletext.cpp radiotext.cpp subtitle.cpp cahandler.cpp \
	fastscan.cpp cablescan.cpp
