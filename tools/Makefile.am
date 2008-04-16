libopen.so.0.0: libopen.c
	$(CXX) -Wall -W libopen.c -O2 -nostartfiles -shared -fPIC -Wl,-soname,libopen.so.0 -o libopen.so.0.0 -ldl

all: libopen.so.0.0

CLEANFILES = libopen.so.0.0

install: all
	$(INSTALL) libopen.so.0.0 $(DESTDIR)/usr/lib
