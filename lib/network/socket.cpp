#include <sys/ioctl.h>
#include <asm/ioctls.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>
#include <string.h>
#include <linux/serial.h>
#include <lib/network/socket.h>

void eSocket::close()
{
	if (writebuffer.empty())
	{
		int wasconnected = (mystate == Connection) || (mystate == Closing);
		rsn = 0;
		if (socketdesc >= 0)
		{
			::close(socketdesc);
			socketdesc = -1;
		}
		mystate = Invalid;
		if (wasconnected)
			connectionClosed_();
	} else
	{
		mystate = Closing;
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

int eSocket::setSocket(int s, int iss)
{
	socketdesc = s;
	if (socketdesc < 0) return -1;
	issocket = iss;
	fcntl(socketdesc, F_SETFL, O_NONBLOCK);
	last_break = -1;

	rsn = 0;
	rsn = eSocketNotifier::create(mainloop, getDescriptor(),
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
				eDebug("[eSocket] FIONREAD failed.\n");

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
					eDebug("[eSocket] TIOCGICOUNT failed: %m");
			}
			int r;
			if ((r=readbuffer.fromfile(getDescriptor(), bytesavail)) != bytesavail)
				if (issocket)
					eDebug("[eSocket] fromfile failed!");
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
				eDebug("[eSocket] got ready to write, but nothin in buffer. strange.");
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
		if ((tw < 0) && (errno != EWOULDBLOCK)) {
	// don't use eDebug here because of a adaptive mutex in the eDebug call..
	// and eDebug self can cause a call of writeBlock !!
			struct timespec tp;
			clock_gettime(CLOCK_MONOTONIC, &tp);
			fprintf(stderr, "<%6lu.%06lu> [eSocket] write: %m\n", tp.tv_sec, tp.tv_nsec/1000);
		}
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

int eSocket::connect(struct addrinfo *addr)
{
	int res;
	struct addrinfo *ptr = addr;
	close();
	for (ptr = addr; ptr != NULL; ptr = ptr->ai_next)
	{
		if (setSocket(socket(ptr->ai_family, ptr->ai_socktype, ptr->ai_protocol), 1) < 0)
		{
			/* No need to close, setSocket only fails when socket() already failed */
			continue;
		}
		mystate = Idle;

		res = ::connect(socketdesc, ptr->ai_addr, ptr->ai_addrlen);
		if ((res < 0) && (errno != EINPROGRESS) && (errno != EINTR))
		{
			error_(errno);
			close(); /* Release and disconnect the notifier */
			continue;
		}
		if (res < 0)	// EINPROGRESS or EINTR
		{
			rsn->setRequested(rsn->getRequested() | eSocketNotifier::Write);
			mystate = Connecting;
			return 0;
		}
		else
		{
			mystate = Connection;
			connected_();
			return 1;
		}
	}
	return -1;
}

int eSocket::connectToHost(std::string hostname, int port)
{
	int res;
	struct addrinfo *addr = NULL;
	struct addrinfo hints;
	char portnumber[16];

	memset(&hints, 0, sizeof(hints));
	hints.ai_family = AF_UNSPEC; /* both ipv4 and ipv6 */
	hints.ai_socktype = SOCK_STREAM;
	hints.ai_protocol = 0; /* any */
#ifdef AI_ADDRCONFIG
	hints.ai_flags = AI_NUMERICSERV | AI_ADDRCONFIG; /* only return ipv6 if we have an ipv6 address ourselves, and ipv4 if we have an ipv4 address ourselves */
#else
	hints.ai_flags = AI_NUMERICSERV; /* AI_ADDRCONFIG is not available */
#endif
	snprintf(portnumber, sizeof(portnumber), "%d", port);

	if ((res = getaddrinfo(hostname.c_str(), portnumber, &hints, &addr)) || !addr)
	{
		eDebug("[eSocket] can't resolve %s (getaddrinfo: %s)", hostname.c_str(), gai_strerror(res));
		return -2;
	}

	res = connect(addr);
	if (res < 0)
	{
		eDebug("[eSocket] can't connect to host: %s", hostname.c_str());
	}
	freeaddrinfo(addr);
	return res;
}

eSocket::eSocket(eMainloop *ml): readbuffer(32768), writebuffer(32768), mainloop(ml)
{
	socketdesc = -1;
	mystate = Invalid;
}

eSocket::eSocket(int socket, int issocket, eMainloop *ml): readbuffer(32768), writebuffer(32768), mainloop(ml)
{
	setSocket(socket, issocket);
	mystate = Connection;
}

eSocket::~eSocket()
{
	if (socketdesc >= 0)
	{
		::close(socketdesc);
		socketdesc = -1;
	}
}

eUnixDomainSocket::eUnixDomainSocket(eMainloop *ml) : eSocket(ml)
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
	int res;
	struct sockaddr_un serv_addr_un;
	struct addrinfo addr;

	memset(&serv_addr_un, 0, sizeof(serv_addr_un));
	serv_addr_un.sun_family = AF_LOCAL;
	strcpy(serv_addr_un.sun_path, path.c_str());

	memset(&addr, 0, sizeof(addr));
	addr.ai_family = AF_LOCAL;
	addr.ai_socktype = SOCK_STREAM;
	addr.ai_protocol = 0; /* any */
	addr.ai_addr = (struct sockaddr *)&serv_addr_un;
	addr.ai_addrlen = sizeof(serv_addr_un);

	res = connect(&addr);
	return res;
}
