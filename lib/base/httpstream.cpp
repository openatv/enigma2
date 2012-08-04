#include <cstdio>

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
	writeAll(streamSocket, request.c_str(), request.length());

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

off_t eHttpStream::offset()
{
	return 0;
}
