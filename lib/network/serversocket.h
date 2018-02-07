#ifndef __serversocket_h
#define __serversocket_h

#include "socket.h"

class eServerSocket: public eSocket
{
	void notifier(int handle);
	int okflag;
	std::string strRemoteHost;
	int m_port;
protected:
	virtual void newConnection(int socket)=0;
	int bind(int sockfd, struct sockaddr *addr, socklen_t addrlen);
	int listen(int sockfd, int backlog);
	int accept(int sockfd, struct sockaddr *addr, socklen_t *addrlen);
public:
	/* INET serversocket constructor */
	eServerSocket(int port, eMainloop *ml);
	/* UNIX serversocket constructor */
	eServerSocket(std::string path, eMainloop *ml);
	virtual ~eServerSocket();
	bool ok();
	std::string RemoteHost() { return strRemoteHost;}
	int Port() { return m_port; }
};

#endif /* __serversocket_h */
