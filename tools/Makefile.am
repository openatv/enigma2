libopen: 
	$(CXX) -Wall -W libopen.c -O2 -nostartfiles -shared -fPIC -Wl,-soname,libopen.so.0 -o libopen.so.0.0 -ldl

all: libopen

install:
	$(INSTALL) libopen.so.0.0 $(DEST)/usr/lib
