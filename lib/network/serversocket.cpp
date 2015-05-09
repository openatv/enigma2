#include <errno.h>
#include <lib/network/serversocket.h>
#include <arpa/inet.h>

bool eServerSocket::ok()
{
	return okflag;
}

void eServerSocket::notifier(int)
{
	int clientfd, clientlen;
	struct sockaddr_in6 client_addr;
	char straddr[INET6_ADDRSTRLEN];

#ifdef DEBUG_SERVERSOCKET
	eDebug("[SERVERSOCKET] incoming connection!");
#endif

	clientlen=sizeof(client_addr);
	clientfd=accept(getDescriptor(),
			(struct sockaddr *) &client_addr,
			(socklen_t*)&clientlen);
	if(clientfd<0)
		eDebug("[SERVERSOCKET] error on accept()");

	inet_ntop(AF_INET6, &client_addr.sin6_addr, straddr, sizeof(straddr));
	strRemoteHost=straddr;
	newConnection(clientfd);
}

eServerSocket::eServerSocket(int port, eMainloop *ml): eSocket(ml, AF_INET6)
{
	struct sockaddr_in6 serv_addr;
	strRemoteHost = "";

	bzero(&serv_addr, sizeof(serv_addr));
	serv_addr.sin6_family=AF_INET6;
	serv_addr.sin6_addr=in6addr_any;
	serv_addr.sin6_port=htons(port);

	okflag=1;
	int val=1;
	int v6only=0;

	setsockopt(getDescriptor(), SOL_SOCKET, SO_REUSEADDR, &val, sizeof(val));
	setsockopt(getDescriptor(), IPPROTO_IPV6, IPV6_V6ONLY, &v6only, sizeof(v6only));

	if(bind(getDescriptor(),
		(struct sockaddr *) &serv_addr,
		sizeof(serv_addr))<0)
	{
		eDebug("[SERVERSOCKET] ERROR on bind() (%m)");
		okflag=0;
	}
	listen(getDescriptor(), 0);

	rsn->setRequested(eSocketNotifier::Read);
}

eServerSocket::eServerSocket(std::string path, eMainloop *ml) : eSocket(ml, AF_LOCAL)
{
	struct sockaddr_un serv_addr;
	strRemoteHost = "";

	memset(&serv_addr, 0, sizeof(serv_addr));
	serv_addr.sun_family = AF_LOCAL;
	strcpy(serv_addr.sun_path, path.c_str());

	okflag=1;

	unlink(path.c_str());
#if HAVE_LINUXSOCKADDR
	if(bind(getDescriptor(),
	(struct sockaddr *) &serv_addr,
	strlen(serv_addr.sun_path) + sizeof(serv_addr.sun_family))<0)
#else
	if(bind(getDescriptor(),
		(struct sockaddr *) &serv_addr,
		sizeof(serv_addr))<0)
#endif
	{
		eDebug("[SERVERSOCKET] ERROR on bind() (%m)");
		okflag=0;
	}
	listen(getDescriptor(), 0);

	rsn->setRequested(eSocketNotifier::Read);
}

eServerSocket::~eServerSocket()
{
#if 0
	eDebug("[SERVERSOCKET] destructed");
#endif
}

int eServerSocket::bind(int sockfd, struct sockaddr *addr, socklen_t addrlen)
{
	int result;
	while (1)
	{
		if ((result = ::bind(sockfd, addr, addrlen)) < 0 && errno == EINTR) continue;
		break;
	}
	return result;
}

int eServerSocket::listen(int sockfd, int backlog)
{
	int result;
	while (1)
	{
		if ((result = ::listen(sockfd, backlog)) < 0 && errno == EINTR) continue;
		break;
	}
	return result;
}

int eServerSocket::accept(int sockfd, struct sockaddr *addr, socklen_t *addrlen)
{
	int result;
	while (1)
	{
		if ((result = ::accept(sockfd, addr, addrlen)) < 0 && errno == EINTR) continue;
		break;
	}
	return result;
}
