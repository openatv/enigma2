#ifndef __serversocket_h
#define __serversocket_h

#include "socket.h"

class eServerSocket: public eSocket
{
	void notifier(int handle);		
	int okflag;
protected:
	virtual void newConnection(int socket)=0;
public:
	eServerSocket(int port, eMainloop *ml);
	virtual ~eServerSocket();
	bool ok();
};

#endif /* __serversocket_h */
