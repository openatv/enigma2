#include <errno.h>
#include <string.h>
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
	struct sockaddr client_addr;
	char straddr[INET6_ADDRSTRLEN];

#ifdef DEBUG_SERVERSOCKET
	eDebug("[eServerSocket] incoming connection!");
#endif

	clientlen = sizeof(client_addr);
	clientfd = accept(getDescriptor(), &client_addr, &clientlen);
	if (clientfd < 0)
	{
		eDebug("[eServerSocket] error on accept: %m");
		return;
	}

	if (client_addr.sa_family == AF_LOCAL)
	{
		strRemoteHost = "(local)";
	}
	else
	{
		strRemoteHost = inet_ntop(client_addr.sa_family, client_addr.sa_data, straddr, sizeof(straddr));
	}
	newConnection(clientfd);
}

eServerSocket::eServerSocket(int port, eMainloop *ml): eSocket(ml)
{
	int res;
	struct addrinfo *addr = NULL;
	struct addrinfo hints;
	char portnumber[16];

	okflag = 0;
	strRemoteHost = "";

	memset(&hints, 0, sizeof(hints));
	hints.ai_family = AF_UNSPEC; /* both ipv4 and ipv6 */
	hints.ai_socktype = SOCK_STREAM;
	hints.ai_protocol = 0; /* any */
#ifdef AI_ADDRCONFIG
	hints.ai_flags = AI_PASSIVE | AI_NUMERICSERV | AI_ADDRCONFIG; /* only return ipv6 if we have an ipv6 address ourselves, and ipv4 if we have an ipv4 address ourselves */
#else
	hints.ai_flags = AI_PASSIVE | AI_NUMERICSERV; /* AI_ADDRCONFIG is not available */
#endif
	snprintf(portnumber, sizeof(portnumber), "%d", port);

	if ((res = getaddrinfo(NULL, portnumber, &hints, &addr)) || !addr)
	{
		eDebug("[eServerSocket] getaddrinfo: %s", gai_strerror(res));
		return;
	}

	if (startListening(addr) >= 0)
	{
		okflag = 1;
		rsn->setRequested(eSocketNotifier::Read);
	}
	freeaddrinfo(addr);
}

eServerSocket::eServerSocket(std::string path, eMainloop *ml) : eSocket(ml)
{
	struct sockaddr_un serv_addr_un;
	struct addrinfo addr;

	okflag = 0;
	strRemoteHost = "";

	memset(&serv_addr_un, 0, sizeof(serv_addr_un));
	serv_addr_un.sun_family = AF_LOCAL;
	strcpy(serv_addr_un.sun_path, path.c_str());

	memset(&addr, 0, sizeof(addr));
	addr.ai_family = AF_LOCAL;
	addr.ai_socktype = SOCK_STREAM;
	addr.ai_protocol = 0; /* any */
	addr.ai_addr = (struct sockaddr *)&serv_addr_un;
	addr.ai_addrlen = sizeof(serv_addr_un);

	unlink(path.c_str());

	if (startListening(&addr) >= 0)
	{
		okflag = 1;
		rsn->setRequested(eSocketNotifier::Read);
	}
}

eServerSocket::~eServerSocket()
{
#ifdef DEBUG_SERVERSOCKET
	eDebug("[eServerSocket] destructed");
#endif
}

int eServerSocket::startListening(struct addrinfo *addr)
{
	struct addrinfo *ptr = addr;
	for (ptr = addr; ptr != NULL; ptr = ptr->ai_next)
	{
		if (setSocket(socket(ptr->ai_family, ptr->ai_socktype, ptr->ai_protocol), 1) < 0)
		{
			continue;
		}

		int val = 1;
		setsockopt(getDescriptor(), SOL_SOCKET, SO_REUSEADDR, &val, sizeof(val));

		if (bind(getDescriptor(), ptr->ai_addr, ptr->ai_addrlen) < 0)
		{
			eDebug("[eServerSocket] ERROR on bind: %m");
			close();
			continue;
		}
	}

	if (getDescriptor() < 0)
	{
		return -1;
	}

	if (listen(getDescriptor(), 0) < 0)
	{
		close();
		return -1;
	}
	return 0;
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
