noinst_LIBRARIES += base/libenigma_base.a

base_libenigma_base_a_SOURCES = \
	base/buffer.cpp \
	base/cachedtssource.cpp \
	base/cfile.cpp \
	base/connection.cpp \
	base/console.cpp \
	base/e2avahi.cpp \
	base/ebase.cpp \
	base/eenv.cpp \
	base/eerror.cpp \
	base/eerroroutput.cpp \
	base/elock.cpp \
	base/encoding.cpp \
	base/estring.cpp \
	base/etpm.cpp \
	base/freesatv2.cpp \
	base/filepush.cpp \
	base/init.cpp \
	base/ioprio.cpp \
	base/message.cpp \
	base/nconfig.cpp \
	base/rawfile.cpp \
	base/smartptr.cpp \
	base/thread.cpp \
	base/httpstream.cpp \
	base/wrappers.cpp

EXTRA_DIST += \
	base/eenv.cpp.in

baseincludedir = $(pkgincludedir)/lib/base
baseinclude_HEADERS = \
	base/buffer.h \
	base/cachedtssource.h \
	base/cfile.h \
	base/console.h \
	base/e2avahi.h \
	base/ebase.h \
	base/eenv.h \
	base/eerror.h \
	base/eerroroutput.h \
	base/elock.h \
	base/encoding.h \
	base/eptrlist.h \
	base/estring.h \
	base/etpm.h \
	base/filepush.h \
	base/freesatv2.h \
	base/i18n.h \
	base/itssource.h \
	base/init.h \
	base/init_num.h \
	base/ioprio.h \
	base/message.h \
	base/nconfig.h \
	base/object.h \
	base/rawfile.h \
	base/ringbuffer.h \
	base/smartptr.h \
	base/thread.h \
	base/httpstream.h \
	base/wrappers.h
