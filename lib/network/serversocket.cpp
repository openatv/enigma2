#include <errno.h>
#include <lib/network/serversocket.h>
#include <arpa/inet.h>

bool eServerSocket::ok()
{
	return okflag;
}

void eServerSocket::notifier(int)
{
	int clientfd;
	socklen_t clientlen;
	struct sockaddr_storage client_addr;
	char straddr[INET6_ADDRSTRLEN];
	const void *address = 0;

#ifdef DEBUG_SERVERSOCKET
	eDebug("[eServerSocket] incoming connection!");
#endif

	memset(&client_addr, 0, sizeof(client_addr));
	clientlen=sizeof(client_addr);
	clientfd=accept(getDescriptor(),
			(struct sockaddr *) &client_addr,
			&clientlen);
	if(clientfd<0)
	{
		eDebug("[eServerSocket] error on accept() (%m)");
		return;
	}

	if (client_addr.ss_family == AF_INET6)
		address = &((struct sockaddr_in6 *)&client_addr)->sin6_addr;
	else if (client_addr.ss_family == AF_INET)
		address = &((struct sockaddr_in *)&client_addr)->sin_addr;

	if (address && inet_ntop(client_addr.ss_family, address, straddr, sizeof(straddr)))
		strRemoteHost=straddr;
	else
		strRemoteHost.clear();
	newConnection(clientfd);
}

eServerSocket::eServerSocket(int port, eMainloop *ml): eSocket(ml, AF_INET6), m_port(port)
{
	struct sockaddr_in6 serv_addr6;
	struct sockaddr_in serv_addr4;
	int family = AF_INET6;
	int bind_result = -1;
	int listen_result;
	strRemoteHost = "";
	okflag=0;
	int val=1;
	int v6only=0;

	/* Some legacy receivers ship kernels without IPv6.  Creating an AF_INET6
	 * socket then returns EAFNOSUPPORT/ENOSYS.  Keep the dual-stack listener
	 * where it is available, but fall back to IPv4 instead of operating on an
	 * invalid descriptor. */
	if (getDescriptor() < 0)
	{
		family = AF_INET;
		if (setSocket(::socket(AF_INET, SOCK_STREAM, 0), 1, ml) < 0)
		{
			eDebug("[eServerSocket] ERROR creating IPv4 socket for port %d (%m)", port);
			return;
		}
	}

	setsockopt(getDescriptor(), SOL_SOCKET, SO_REUSEADDR, &val, sizeof(val));
	if (family == AF_INET6)
	{
		setsockopt(getDescriptor(), IPPROTO_IPV6, IPV6_V6ONLY, &v6only, sizeof(v6only));
		bzero(&serv_addr6, sizeof(serv_addr6));
		serv_addr6.sin6_family=AF_INET6;
		serv_addr6.sin6_addr=in6addr_any;
		serv_addr6.sin6_port=htons(port);
		bind_result=bind(getDescriptor(),
			(struct sockaddr *) &serv_addr6, sizeof(serv_addr6));
	}
	else
	{
		bzero(&serv_addr4, sizeof(serv_addr4));
		serv_addr4.sin_family=AF_INET;
		serv_addr4.sin_addr.s_addr=htonl(INADDR_ANY);
		serv_addr4.sin_port=htons(port);
		bind_result=bind(getDescriptor(),
			(struct sockaddr *) &serv_addr4, sizeof(serv_addr4));
	}

	/* An IPv6 socket may exist while IPv6 bind is unavailable.  Retry the
	 * listener as IPv4 before giving up. */
	if (bind_result < 0 && family == AF_INET6)
	{
		eDebug("[eServerSocket] IPv6 bind on port %d failed (%m), trying IPv4", port);
		close();
		family = AF_INET;
		if (setSocket(::socket(AF_INET, SOCK_STREAM, 0), 1, ml) == 0)
		{
			setsockopt(getDescriptor(), SOL_SOCKET, SO_REUSEADDR, &val, sizeof(val));
			bzero(&serv_addr4, sizeof(serv_addr4));
			serv_addr4.sin_family=AF_INET;
			serv_addr4.sin_addr.s_addr=htonl(INADDR_ANY);
			serv_addr4.sin_port=htons(port);
			bind_result=bind(getDescriptor(),
				(struct sockaddr *) &serv_addr4, sizeof(serv_addr4));
		}
	}

	if (bind_result < 0)
	{
		eDebug("[eServerSocket] ERROR binding port %d (%m)", port);
		close();
		return;
	}
#if HAVE_HISILICON
	listen_result=listen(getDescriptor(), 10);
#else
	listen_result=listen(getDescriptor(), 0);
#endif
	if (listen_result < 0)
	{
		eDebug("[eServerSocket] ERROR listening on port %d (%m)", port);
		close();
		return;
	}

	okflag=1;
	if (rsn)
		rsn->setRequested(eSocketNotifier::Read);
}

eServerSocket::eServerSocket(std::string path, eMainloop *ml) : eSocket(ml, AF_LOCAL)
{
	struct sockaddr_un serv_addr;
	strRemoteHost = "";
	m_port = 0;

	memset(&serv_addr, 0, sizeof(serv_addr));
	serv_addr.sun_family = AF_LOCAL;
	strcpy(serv_addr.sun_path, path.c_str());

	okflag=0;
	m_port = 0;
	if (getDescriptor() < 0)
	{
		eDebug("[eServerSocket] ERROR creating local socket %s (%m)", path.c_str());
		return;
	}

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
		eDebug("[eServerSocket] ERROR on bind() (%m)");
		close();
		return;
	}
#if HAVE_HISILICON
	if (listen(getDescriptor(), 10) < 0)
#else
	if (listen(getDescriptor(), 0) < 0)
#endif
	{
		eDebug("[eServerSocket] ERROR on listen() (%m)");
		close();
		return;
	}

	okflag=1;
	if (rsn)
		rsn->setRequested(eSocketNotifier::Read);
}

eServerSocket::~eServerSocket()
{
#if 0
	eDebug("[eServerSocket] destructed");
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
