#ifndef __serversocket_h
#define __serversocket_h

#include "socket.h"

class eServerSocket: public eSocket
{
	void notifier(int handle);
	int okflag;
	std::string strRemoteHost;
protected:
	virtual void newConnection(int socket) = 0;
	int startListening(struct addrinfo *addr);
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
};

#endif /* __serversocket_h */
