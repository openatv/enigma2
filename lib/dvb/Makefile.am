SUBDIRS = lowlevel

INCLUDES = \
	-I$(top_srcdir)/include

noinst_LIBRARIES = libenigma_dvb.a

libenigma_dvb_a_SOURCES = dvb.cpp demux.cpp frontend.cpp esection.cpp db.cpp \
	sec.cpp scan.cpp crc32.cpp pmt.cpp decoder.cpp eit.cpp rotor_calc.cpp \
	epgcache.cpp dvbtime.cpp metaparser.cpp volume.cpp tstools.cpp pvrparse.cpp \
	pesparse.cpp teletext.cpp radiotext.cpp subtitle.cpp

