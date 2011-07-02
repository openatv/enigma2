AM_CPPFLAGS = \
	-I$(top_srcdir) \
	-I$(top_srcdir)/include \
	-include Python.h \
	-include $(top_builddir)/enigma2_config.h

noinst_LIBRARIES = libenigma_base.a

libenigma_base_a_SOURCES = \
	buffer.cpp \
	connection.cpp \
	console.cpp \
	ebase.cpp \
	eenv.cpp \
	eerror.cpp \
	elock.cpp \
	encoding.cpp \
	estring.cpp \
	etpm.cpp \
	freesatv2.cpp \
	filepush.cpp \
	init.cpp \
	ioprio.cpp \
	message.cpp \
	nconfig.cpp \
	rawfile.cpp \
	smartptr.cpp \
	thread.cpp \
	httpstream.cpp

EXTRA_DIST = \
	eenv.cpp.in

baseincludedir = $(pkgincludedir)/lib/base
baseinclude_HEADERS = \
	buffer.h \
	console.h \
	ebase.h \
	eenv.h \
	eerror.h \
	elock.h \
	encoding.h \
	eptrlist.h \
	estring.h \
	etpm.h \
	filepush.h \
	freesatv2.cpp \
	i18n.h \
	itssource.h \
	init.h \
	init_num.h \
	ioprio.h \
	message.h \
	nconfig.h \
	object.h \
	rawfile.h \
	ringbuffer.h \
	smartptr.h \
	thread.h \
	httpstream.h
