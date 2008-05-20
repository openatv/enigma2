socketmmi.so: socket_mmi.cpp socket_mmi.h
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(DEFS) -I$(top_srcdir)/include -Wall -W socket_mmi.cpp -shared -fPIC -Wl,-soname,socketmmi.so -o socketmmi.so $(LDFLAGS)

all: socketmmi.so

CLEANFILES = socketmmi.so
