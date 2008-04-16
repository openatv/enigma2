servicedvd.so: servicedvd.cpp servicedvd.h
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(DEFS) -I$(top_srcdir)/include -Wall -W servicedvd.cpp -shared -fPIC -Wl,-soname,servicedvd.so -o servicedvd.so $(LDFLAGS) -ldreamdvd

all: servicedvd.so

CLEANFILES = servicedvd.so
