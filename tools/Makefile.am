bin_SCRIPTS = enigma2.sh
lib_LTLIBRARIES = libopen.la

CFLAGS += -DLIBC_SO=\"$(base_libdir)/libc.so.6\"

libopen_la_SOURCES = libopen.c
libopen_la_LIBADD = @LIBDL_LIBS@

EXTRA_DIST = enigma2.sh.in
