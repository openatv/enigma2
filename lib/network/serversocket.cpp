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
	union // ugly workaround for sizeof(sockaddr) < sizeof(sockaddr_in6) issue
	{
		sockaddr sock;
		sockaddr_in sock_in;
		sockaddr_in6 sock_in6;
	} client_addr;

	char straddr[INET6_ADDRSTRLEN];

#ifdef DEBUG_SERVERSOCKET
	eDebug("[eServerSocket] incoming connection!");
#endif

	clientlen = sizeof(client_addr);
	clientfd = accept(getDescriptor(), &client_addr.sock, &clientlen);
	if (clientfd < 0)
	{
		eDebug("[eServerSocket] error on accept: %m");
		return;
	}

	switch(client_addr.sock.sa_family)
	{
		case(PF_LOCAL):
		{
			strRemoteHost = "(local)";
			break;
		}

		case(PF_INET):
		{
			strRemoteHost = inet_ntop(PF_INET, &client_addr.sock_in.sin_addr, straddr, sizeof(straddr));
			break;
		}

		case(PF_INET6):
		{
			static uint8_t ipv4_mapped_pattern[] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xff, 0xff };

			if(!memcmp(&client_addr.sock_in6.sin6_addr, ipv4_mapped_pattern, sizeof(ipv4_mapped_pattern)))
			{
				 // ugly hack to get real ipv4 address without the ::ffff:, inet_ntop doesn't have an option for it
				strRemoteHost = inet_ntop(PF_INET, (sockaddr_in *)&client_addr.sock_in6.sin6_addr.s6_addr[12], straddr, sizeof(straddr));
			}
			else
				strRemoteHost = inet_ntop(PF_INET6, &client_addr.sock_in6.sin6_addr, straddr, sizeof(straddr));

			break;
		}

		default:
		{
			strRemoteHost = "(error)";
			break;
		}
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
	struct addrinfo *ptr;

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
