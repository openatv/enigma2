#include <sys/ioctl.h>
#include <asm/ioctls.h>
#include <unistd.h>
#include <errno.h>
#include <linux/serial.h>
#include <lib/network/socket.h>

void eSocket::close()
{
	if (writebuffer.empty())
	{
		int wasconnected=(mystate==Connection) || (mystate==Closing);
		rsn=0;
		if (socketdesc >= 0)
		{
			::close(socketdesc);
			socketdesc=-1;
		}
		mystate=Invalid;
		if (wasconnected)
			connectionClosed_();
	} else
	{
		mystate=Closing;
		rsn->setRequested(rsn->getRequested()|eSocketNotifier::Write);
	}
}

void eSocket::enableRead()
{
	if (rsn)
		rsn->setRequested(rsn->getRequested()|eSocketNotifier::Read);
}

void eSocket::disableRead()
{
	if (rsn)
		rsn->setRequested(rsn->getRequested()&~eSocketNotifier::Read);
}

void eSocket::inject(const char *data, int len)
{
	readbuffer.write(data, len);
	if (mystate == Connection)
		readyRead_();
}

std::string eSocket::readLine()
{
	int size=readbuffer.searchchr('\n');
	if (size == -1)
		return std::string();
	size++; // ich will auch das \n
	char buffer[size+1];
	buffer[size]=0;
	readbuffer.read(buffer, size);
	return std::string(buffer);
}

bool eSocket::canReadLine()
{
	return readbuffer.searchchr('\n') != -1;
}

int eSocket::bytesAvailable()
{
	return readbuffer.size();
}

int eSocket::readBlock(char *data, unsigned int maxlen)
{
	return readbuffer.read(data, maxlen);
}

int eSocket::bytesToWrite()
{
	return writebuffer.size();
}

int eSocket::state()
{
	return mystate;
}

int eSocket::setSocket(int s, int iss, eMainloop *ml)
{
	socketdesc=s;
	if (socketdesc < 0) return -1;
	issocket=iss;
	fcntl(socketdesc, F_SETFL, O_NONBLOCK);
	last_break = -1;

	rsn = 0;
	rsn=eSocketNotifier::create(ml, getDescriptor(),
		eSocketNotifier::Read|eSocketNotifier::Hungup);
	CONNECT(rsn->activated, eSocket::notifier);
	return 0;
}

void eSocket::notifier(int what)
{
	if ((what & eSocketNotifier::Read) && (mystate == Connection))
	{
		int bytesavail=256;
		if (issocket)
			if (ioctl(getDescriptor(), FIONREAD, &bytesavail)<0)
				eDebug("FIONREAD failed.\n");

		{
			if (issocket)
			{
				if (!bytesavail)  // does the REMOTE END has closed the connection? (no Hungup here!)
				{
					writebuffer.clear();
					close();
					return;
				}
			}
			else		// when operating on terminals, check for break
			{
				serial_icounter_struct icount;
				memset(&icount, 0, sizeof(icount));
				if (!ioctl(getDescriptor(), TIOCGICOUNT, &icount))
				{
					if (last_break == -1)
						last_break = icount.brk;
					else if (last_break != icount.brk)
					{
						last_break = icount.brk;
						readbuffer.fromfile(getDescriptor(), bytesavail);
						readbuffer.clear();
						writebuffer.clear();
						rsn->setRequested(rsn->getRequested()&~eSocketNotifier::Write);
						write(getDescriptor(), "BREAK!", 6);
						hangup();
						return;
					}
				}
				else
					eDebug("TIOCGICOUNT failed(%m)");
			}
			int r;
			if ((r=readbuffer.fromfile(getDescriptor(), bytesavail)) != bytesavail)
				if (issocket)
					eDebug("fromfile failed!");
			readyRead_();
		}
	} else if (what & eSocketNotifier::Write)
	{
		if ((mystate == Connection) || (mystate == Closing))
		{
			if (!writebuffer.empty())
			{
				bytesWritten_(writebuffer.tofile(getDescriptor(), 65536));
				if (writebuffer.empty())
				{
					rsn->setRequested(rsn->getRequested()&~eSocketNotifier::Write);
					if (mystate == Closing)
					{
						close();		// warning, we might get destroyed after close.
						return;
					}
				}
			} else
				eDebug("got ready to write, but nothin in buffer. strange.");
			if (mystate == Closing)
				close();
		} else if (mystate == Connecting)
		{
			mystate=Connection;
			rsn->setRequested(rsn->getRequested()&~eSocketNotifier::Write);

			int res;
			socklen_t size=sizeof(res);
			::getsockopt(getDescriptor(), SOL_SOCKET, SO_ERROR, &res, &size);
			if (!res)
				connected_();
			else
			{
				close();
				error_(res);
			}
		}
	} else if (what & eSocketNotifier::Hungup)
	{
		if (mystate == Connection || (mystate == Closing && issocket) )
		{
			writebuffer.clear();
			close();
		} else if (mystate == Connecting)
		{
			int res;
			socklen_t size=sizeof(res);
			::getsockopt(getDescriptor(), SOL_SOCKET, SO_ERROR, &res, &size);
			close();
			error_(res);
		}
	}
}

int eSocket::writeBlock(const char *data, unsigned int len)
{
	int err=0;
	int w=len;
	if (issocket && writebuffer.empty())
	{
		int tw=::send(getDescriptor(), data, len, MSG_NOSIGNAL);
		if ((tw < 0) && (errno != EWOULDBLOCK))
	// don't use eDebug here because of a adaptive mutex in the eDebug call..
	// and eDebug self can cause a call of writeBlock !!
			printf("write: %m\n");
		if (tw < 0)
			tw = 0;
		data+=tw;
		len-=tw;
	}
	if (len && !err)
		writebuffer.write(data, len);

	if (!writebuffer.empty())
		rsn->setRequested(rsn->getRequested()|eSocketNotifier::Write);
	return w;
}

int eSocket::getDescriptor()
{
	return socketdesc;
}

int eSocket::connectToHost(std::string hostname, int port)
{
	sockaddr_in  serv_addr;
	struct hostent *server;
	int res;

	if (mystate == Invalid)
	{
		/* the socket has been closed, create a new socket descriptor */
		int s=socket(AF_INET, SOCK_STREAM, 0);
		mystate=Idle;
		setSocket(s, 1, mainloop);
	}

	if(socketdesc < 0){
		error_(errno);
		return(-1);
	}
	server=gethostbyname(hostname.c_str());
	if(server==NULL)
	{
		eDebug("can't resolve %s", hostname.c_str());
		error_(errno);
		return(-2);
	}
	bzero(&serv_addr, sizeof(serv_addr));
	serv_addr.sin_family=AF_INET;
	bcopy(server->h_addr, &serv_addr.sin_addr.s_addr, server->h_length);
	serv_addr.sin_port=htons(port);
	res=::connect(socketdesc, (const sockaddr*)&serv_addr, sizeof(serv_addr));
	if ((res < 0) && (errno != EINPROGRESS) && (errno != EINTR))
	{
		eDebug("can't connect to host: %s", hostname.c_str());
		close();
		error_(errno);
		return(-3);
	}
	if (res < 0)	// EINPROGRESS or EINTR
	{
		rsn->setRequested(rsn->getRequested()|eSocketNotifier::Write);
		mystate=Connecting;
	} else
	{
		mystate=Connection;
		connected_();
	}
	return(0);
}

eSocket::eSocket(eMainloop *ml, int domain): readbuffer(32768), writebuffer(32768), mainloop(ml)
{
	int s=socket(domain, SOCK_STREAM, 0);
#if 0
	eDebug("[SOCKET]: initalized socket %d", socketdesc);
#endif
	mystate=Idle;
	setSocket(s, 1, ml);
}

eSocket::eSocket(int socket, int issocket, eMainloop *ml): readbuffer(32768), writebuffer(32768), mainloop(ml)
{
	setSocket(socket, issocket, ml);
	mystate=Connection;
}

eSocket::~eSocket()
{
	if(socketdesc>=0)
	{
		::close(socketdesc);
	}
}

eUnixDomainSocket::eUnixDomainSocket(eMainloop *ml) : eSocket(ml, AF_LOCAL)
{
}

eUnixDomainSocket::eUnixDomainSocket(int socket, int issocket, eMainloop *ml) : eSocket(socket, issocket, ml)
{
}

eUnixDomainSocket::~eUnixDomainSocket()
{
}

int eUnixDomainSocket::connectToPath(std::string path)
{
	sockaddr_un serv_addr_un;
	int res;

	if (mystate == Invalid)
	{
		/* the socket has been closed, create a new socket descriptor */
		int s=socket(AF_LOCAL, SOCK_STREAM, 0);
		mystate=Idle;
		setSocket(s, 1, mainloop);
	}

	if(socketdesc < 0){
		error_(errno);
		return(-1);
	}
	bzero(&serv_addr_un, sizeof(serv_addr_un));
	serv_addr_un.sun_family = AF_LOCAL;
	strcpy(serv_addr_un.sun_path, path.c_str());
	res=::connect(socketdesc, (const sockaddr*)&serv_addr_un, sizeof(serv_addr_un));
	if ((res < 0) && (errno != EINPROGRESS) && (errno != EINTR))
	{
		close();
		error_(errno);
		return(-3);
	}
	if (res < 0)	// EINPROGRESS or EINTR
	{
		rsn->setRequested(rsn->getRequested()|eSocketNotifier::Write);
		mystate=Connecting;
	} else
	{
		mystate=Connection;
		connected_();
	}
	return(0);
}
