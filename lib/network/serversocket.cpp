#include <lib/network/serversocket.h>

bool eServerSocket::ok()
{
	return okflag;
}

void eServerSocket::notifier(int)
{
	int clientfd, clientlen;
	struct sockaddr_in client_addr;

	eDebug("[SERVERSOCKET] incoming connection!");

	clientlen=sizeof(client_addr);
	clientfd=accept(getDescriptor(),
			(struct sockaddr *) &client_addr,
			(socklen_t*)&clientlen);
	if(clientfd<0)
		eDebug("[SERVERSOCKET] error on accept()");

	newConnection(clientfd);
}

eServerSocket::eServerSocket(int port, eMainloop *ml): eSocket(ml)
{
	struct sockaddr_in serv_addr;

	serv_addr.sin_family=AF_INET;
	serv_addr.sin_addr.s_addr=INADDR_ANY;
	serv_addr.sin_port=htons(port);

	okflag=1;
	int val=1;
	
	setsockopt(getDescriptor(), SOL_SOCKET, SO_REUSEADDR, &val, 4);

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

eServerSocket::~eServerSocket()
{
#if 0
	eDebug("[SERVERSOCKET] destructed");
#endif
}
