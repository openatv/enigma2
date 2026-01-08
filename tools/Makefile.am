bin_SCRIPTS = enigma2.sh
lib_LTLIBRARIES = libopen.la

initddir = $(sysconfdir)/init.d
initd_SCRIPTS = netrestarter

AM_CFLAGS = -DLIBC_SO=\"$(base_libdir)/libc.so.6\"

libopen_la_SOURCES = libopen.c
libopen_la_LIBADD = @LIBDL_LIBS@

EXTRA_DIST = enigma2.sh.in netrestarter
