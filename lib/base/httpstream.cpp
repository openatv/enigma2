#include <cstdio>
#include <unistd.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <arpa/inet.h>
#include <netdb.h>

#include <vector>
#include <string>

#include <lib/base/httpstream.h>
#include <lib/base/eerror.h>

DEFINE_REF(eHttpStream);

eHttpStream::eHttpStream()
{
	streamSocket = -1;
}

eHttpStream::~eHttpStream()
{
	close();
}

int eHttpStream::select(int maxfd, fd_set *readfds, fd_set *writefds, fd_set *exceptfds, struct timeval *timeout)
{
	int retval;
	fd_set rset, wset, xset;
	timeval interval;

	/* make a backup of all fd_set's and timeval struct */
	if (readfds) rset = *readfds;
	if (writefds) wset = *writefds;
	if (exceptfds) xset = *exceptfds;
	if (timeout)
	{
		interval = *timeout;
	}
	else
	{
		/* make gcc happy... */
		timerclear(&interval);
	}

	while (1)
	{
		retval = ::select(maxfd, readfds, writefds, exceptfds, timeout);

		if (retval < 0)
		{
			/* restore the backup before we continue */
			if (readfds) *readfds = rset;
			if (writefds) *writefds = wset;
			if (exceptfds) *exceptfds = xset;
			if (timeout) *timeout = interval;
			if (errno == EINTR) continue;
			eDebug("eHttpStream::select error (%m)");
			break;
		}

		break;
	}
	return retval;
}

ssize_t eHttpStream::singleRead(int fd, void *buf, size_t count)
{
	int retval;
	while (1)
	{
		retval = ::read(fd, buf, count);
		if (retval < 0)
		{
			if (errno == EINTR) continue;
			eDebug("eHttpStream::singleRead error (%m)");
		}
		return retval;
	}
}

ssize_t eHttpStream::timedRead(int fd, void *buf, size_t count, int initialtimeout, int interbytetimeout)
{
	fd_set rset;
	struct timeval timeout;
	int result;
	size_t totalread = 0;

	while (totalread < count)
	{
		FD_ZERO(&rset);
		FD_SET(fd, &rset);
		if (totalread == 0)
		{
			timeout.tv_sec = initialtimeout/1000;
			timeout.tv_usec = (initialtimeout%1000) * 1000;
		}
		else
		{
			timeout.tv_sec = interbytetimeout / 1000;
			timeout.tv_usec = (interbytetimeout%1000) * 1000;
		}
		if ((result = select(fd + 1, &rset, NULL, NULL, &timeout)) < 0) return -1; /* error */
		if (result == 0) break;
		if ((result = singleRead(fd, ((char*)buf) + totalread, count - totalread)) < 0)
		{
			return -1;
		}
		if (result == 0) break;
		totalread += result;
	}
	return totalread;
}

ssize_t eHttpStream::readLine(int fd, char** buffer, size_t* bufsize)
{
	size_t i = 0;
	int result;
	while (1) 
	{
		if (i >= *bufsize) 
		{
			char *newbuf = (char*)realloc(*buffer, (*bufsize)+1024);
			if (newbuf == NULL)
				return -ENOMEM;
			*buffer = newbuf;
			*bufsize = (*bufsize) + 1024;
		}
		result = timedRead(fd, (*buffer) + i, 1, 3000, 100);
		if (result <= 0 || (*buffer)[i] == '\n')
		{
			(*buffer)[i] = '\0';
			return result <= 0 ? -1 : i;
		}
		if ((*buffer)[i] != '\r') i++;
	}
	return -1;
}

int eHttpStream::connect(const char *hostname, int port, int timeoutsec)
{
	int sd = -1;
	std::vector<struct addrinfo *> addresses;
	struct addrinfo *info = NULL;
	struct addrinfo hints;
	memset(&hints, 0, sizeof(hints));
	hints.ai_family = AF_UNSPEC; /* both ipv4 and ipv6 */
	hints.ai_socktype = SOCK_STREAM;
	hints.ai_protocol = 0; /* any */
#ifdef AI_ADDRCONFIG
	hints.ai_flags = AI_ADDRCONFIG; /* only return ipv6 if we have an ipv6 address ourselves, and ipv4 if we have an ipv4 address ourselves */
#else
	hints.ai_flags = 0; /* we have only IPV4 support, if AI_ADDRCONFIG is not available */
#endif
	char portstring[15];
	/* this is suboptimal, but the alternative would require us to mess with the memberdata of an 'abstract' addressinfo struct */
	snprintf(portstring, sizeof(portstring), "%d", port);
	if (getaddrinfo(hostname, portstring, &hints, &info) || !info) return -1;
	struct addrinfo *ptr = info;
	while (ptr)
	{
		addresses.push_back(ptr);
		ptr = ptr->ai_next;
	}

	for (unsigned int i = 0; i < addresses.size(); i++)
	{
		sd = ::socket(addresses[i]->ai_family, addresses[i]->ai_socktype, addresses[i]->ai_protocol);
		if (sd < 0) break;
		int flags;
		bool setblocking = false;
		if ((flags = fcntl(sd, F_GETFL, 0)) < 0)
		{
			::close(sd);
			sd = -1;
			continue;
		}
		if (!(flags & O_NONBLOCK))
		{
			/* set socket nonblocking, to allow for our own timeout on a nonblocking connect */
			flags |= O_NONBLOCK;
			if (fcntl(sd, F_SETFL, flags) < 0)
			{
				::close(sd);
				sd = -1;
				continue;
			}
			/* remember to restore O_NONBLOCK when we're connected */
			setblocking = true;
		}
		int connectresult;
		while (1)
		{
			connectresult = ::connect(sd, addresses[i]->ai_addr, addresses[i]->ai_addrlen);
			if (connectresult < 0)
			{
				if (errno == EINTR || errno == EINPROGRESS)
				{
					int error;
					socklen_t len = sizeof(error);
					timeval timeout;
					fd_set wset;
					FD_ZERO(&wset);
					FD_SET(sd, &wset);

					timeout.tv_sec = timeoutsec;
					timeout.tv_usec = 0;

					if (select(sd + 1, NULL, &wset, NULL, &timeout) <= 0) break;

					if (getsockopt(sd, SOL_SOCKET, SO_ERROR, &error, &len) < 0) break;

					if (error) break;
					/* we are connected */
					connectresult = 0;
					break;
				}
			}
			break;
		}
		if (connectresult < 0)
		{
			::close(sd);
			sd = -1;
			continue;
		}
		if (setblocking)
		{
			/* set socket blocking again */
			flags &= ~O_NONBLOCK;
			if (fcntl(sd, F_SETFL, flags) < 0)
			{
				::close(sd);
				sd = -1;
				continue;
			}
		}
		if (sd >= 0)
		{
#ifdef SO_NOSIGPIPE
			int val = 1;
			setsockopt(sd, SOL_SOCKET, SO_NOSIGPIPE, (char*)&val, sizeof(val));
#endif
			/* we have a working connection */
			break;
		}
	}
	freeaddrinfo(info);
	return sd;
}

ssize_t eHttpStream::write(int fd, const void *buf, size_t count)
{
	int retval;
	char *ptr = (char*)buf;
	size_t handledcount = 0;
	while (handledcount < count)
	{
		retval = ::write(fd, &ptr[handledcount], count - handledcount);

		if (retval == 0) return -1;
		if (retval < 0)
		{
			if (errno == EINTR) continue;
			eDebug("eHttpStream::write error (%m)");
			return retval;
		}
		handledcount += retval;
	}
	return handledcount;
}

int eHttpStream::open(const char *url)
{
	int port;
	std::string hostname;
	std::string uri = url;
	std::string request;
	size_t buflen = 1024;
	char *linebuf = NULL;
	int result;
	char proto[100];
	int statuscode = 0;
	char statusmsg[100];

	close();

	int pathindex = uri.find("/", 7);
	if (pathindex > 0) 
	{
		hostname = uri.substr(7, pathindex - 7);
		uri = uri.substr(pathindex, uri.length() - pathindex);
	} 
	else 
	{
		hostname = uri.substr(7, uri.length() - 7);
		uri = "";
	}
	int customportindex = hostname.find(":");
	if (customportindex > 0) 
	{
		port = atoi(hostname.substr(customportindex + 1, hostname.length() - customportindex - 1).c_str());
		hostname = hostname.substr(0, customportindex);
	} 
	else if (customportindex == 0) 
	{
		port = atoi(hostname.substr(1, hostname.length() - 1).c_str());
		hostname = "localhost";
	}
	else
	{
		port = 80;
	}
	streamSocket = connect(hostname.c_str(), port, 10);
	if (streamSocket < 0) goto error;

	request = "GET ";
	request.append(uri).append(" HTTP/1.1\r\n");
	request.append("Host: ").append(hostname).append("\r\n");
	request.append("Accept: */*\r\n");
	request.append("Connection: close\r\n");
	request.append("\r\n");
	write(streamSocket, request.c_str(), request.length());

	linebuf = (char*)malloc(buflen);

	result = readLine(streamSocket, &linebuf, &buflen);
	if (result <= 0) goto error;

	result = sscanf(linebuf, "%99s %d %99s", proto, &statuscode, statusmsg);
	if (result != 3 || statuscode != 200) 
	{
		eDebug("eHttpStream::open: wrong http response code: %d", statuscode);
		goto error;
	}
	while (result > 0)
	{
		result = readLine(streamSocket, &linebuf, &buflen);
	}

	free(linebuf);
	return 0;
error:
	eDebug("eHttpStream::open failed");
	free(linebuf);
	close();
	return -1;
}

off_t eHttpStream::lseek(off_t offset, int whence)
{
	return (off_t)-1;
}

int eHttpStream::close()
{
	int retval = -1;
	if (streamSocket >= 0)
	{
		retval = ::close(streamSocket);
		streamSocket = -1;
	}
	return retval;
}

ssize_t eHttpStream::read(off_t offset, void *buf, size_t count)
{
	return timedRead(streamSocket, buf, count, 5000, 500);
}

int eHttpStream::valid()
{
	return streamSocket >= 0;
}

off_t eHttpStream::length()
{
	return (off_t)-1;
}
