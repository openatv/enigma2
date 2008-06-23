OBJS := servicedvd.cpp

-include $(OBJS:.cpp=.d)

servicedvd.so:
	$(CXX) $(CPPFLAGS) -MD $(CXXFLAGS) $(DEFS) -I$(top_srcdir)/include \
	-Wall -W $(OBJS) -shared -fPIC -Wl,-soname,servicedvd.so -o servicedvd.so \
	$(LDFLAGS) -ldreamdvd

all: servicedvd.so

CLEANFILES = servicedvd.so servicedvd.d
