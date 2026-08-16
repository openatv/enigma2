#ifndef __lib_driver_ehotplug_socket_h
#define __lib_driver_ehotplug_socket_h

#include <lib/python/connections.h>

#ifndef SWIG
#include <string>
#include <list>

class eSocketNotifier;
template<class T> class ePtr;

#endif

class eHotplugSocket
{
#ifndef SWIG
	static eHotplugSocket *instance;
	int m_listenfd;
	const char *m_sockpath;
	ePtr<eSocketNotifier> m_listensn;

	struct Conn {
		int fd;
		std::string buffer;
		ePtr<eSocketNotifier> sn;
	};
	std::list<Conn *> m_conns;

	void onAccept(int what);
	void onData(int what, Conn *c);
	void closeConn(Conn *c);
#endif
public:
	PSignal1<void, const char *> dataReceived;
#ifndef SWIG
	eHotplugSocket();
	~eHotplugSocket();
#endif
	static eHotplugSocket *getInstance();
};

#endif
