OBJS = socket_mmi.cpp

-include $(OBJS:.cpp=.d)

installdir = $(pkglibdir)/python/Plugins/Extensions/SocketMMI

install_PYTHON = \
	socketmmi.so

socketmmi.so: socket_mmi.cpp socket_mmi.h
	$(CXX) $(CPPFLAGS) -MD $(CXXFLAGS) $(DEFS) -I$(top_srcdir)/include \
	-Wall -W $(OBJS) -shared -fPIC -Wl,-soname,socketmmi.so -o socketmmi.so \
	$(LDFLAGS)

all: socketmmi.so

CLEANFILES = socketmmi.so socketmmi.d
