#include <cstdio>
#include <openssl/evp.h>

#include <lib/base/httpstream.h>
#include <lib/base/eerror.h>
#include <lib/base/wrappers.h>

DEFINE_REF(eHttpStream);

eHttpStream::eHttpStream()
{
	streamSocket = -1;
	connectionStatus = FAILED;
	isChunked = false;
	currentChunkSize = 0;
	partialPktSz = 0;
	tmpBufSize = 32;
	tmpBuf = (char*)malloc(tmpBufSize);
}

eHttpStream::~eHttpStream()
{
	abort_badly();
	kill();
	free(tmpBuf);
	close();
}

int eHttpStream::openUrl(const std::string &url, std::string &newurl)
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
	bool playlist = false;
	bool contenttypeparsed = false;

	close();

	std::string user_agent = "Enigma2 HbbTV/1.1.1 (+PVR+RTSP+DL;openATV;;;)";
	std::string extra_headers = "";
	size_t pos = uri.find('#');
	if (pos != std::string::npos)
	{
		extra_headers = uri.substr(pos + 1);
		uri = uri.substr(0, pos);

		pos = extra_headers.find("User-Agent=");
		if (pos != std::string::npos)
		{
			size_t hpos_start = pos + 11;
			size_t hpos_end = extra_headers.find('&', hpos_start);
			if (hpos_end != std::string::npos)
				user_agent = extra_headers.substr(hpos_start, hpos_end - hpos_start);
			else
				user_agent = extra_headers.substr(hpos_start);
		}
	}

	int pathindex = uri.find("/", 7);
	if (pathindex > 0)
	{
		hostname = uri.substr(7, pathindex - 7);
		uri = uri.substr(pathindex, uri.length() - pathindex);
	}
	else
	{
		hostname = uri.substr(7, uri.length() - 7);
		uri = "/";
	}
	int authenticationindex = hostname.find("@");
	if (authenticationindex > 0)
	{
		BIO *mbio, *b64bio, *bio;
		char *p = (char*)NULL;
		int length = 0;
		authorizationData = hostname.substr(0, authenticationindex);
		hostname = hostname.substr(authenticationindex + 1);
		mbio = BIO_new(BIO_s_mem());
		b64bio = BIO_new(BIO_f_base64());
		bio = BIO_push(b64bio, mbio);
		BIO_write(bio, authorizationData.c_str(), authorizationData.length());
		BIO_flush(bio);
		length = BIO_ctrl(mbio, BIO_CTRL_INFO, 0, (char*)&p);
		authorizationData = "";
		if (p && length > 0)
		{
			/* base64 output contains a linefeed, which we ignore */
			authorizationData.append(p, length - 1);
		}
		BIO_free_all(bio);
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

	streamSocket = Connect(hostname.c_str(), port, 10);
	if (streamSocket < 0)
		goto error;

	request = "GET ";
	request.append(uri).append(" HTTP/1.1\r\n");
	request.append("Host: ").append(hostname).append("\r\n");
	request.append("User-Agent: ").append(user_agent).append("\r\n");
	if (authorizationData != "")
	{
		request.append("Authorization: Basic ").append(authorizationData).append("\r\n");
	}

	pos = 0;
	while (pos != std::string::npos && !extra_headers.empty())
	{
		std::string name, value;
		size_t start = pos;
		size_t len = std::string::npos;
		pos = extra_headers.find('=', pos);
		if (pos != std::string::npos)
		{
			len = pos - start;
			pos++;
			name = extra_headers.substr(start, len);
			start = pos;
			len = std::string::npos;
			pos = extra_headers.find('&', pos);
			if (pos != std::string::npos)
			{
				len = pos - start;
				pos++;
			}
			value = extra_headers.substr(start, len);
		}
		if (!name.empty() && !value.empty())
		{
			if (name.compare("User-Agent") == 0)
				continue;
			eDebug("[eHttpStream] setting extra-header '%s:%s'", name.c_str(), value.c_str());
			request.append(name).append(": ").append(value).append("\r\n");
		}
		else
		{
			eDebug("[eHttpStream] Invalid header format %s", extra_headers.c_str());
			break;
		}
	}

	request.append("Accept: */*\r\n");
	request.append("Connection: close\r\n");
	request.append("\r\n");

	writeAll(streamSocket, request.c_str(), request.length());

	linebuf = (char*)malloc(buflen);

	result = readLine(streamSocket, &linebuf, &buflen);
	if (result <= 0)
		goto error;

	result = sscanf(linebuf, "%99s %d %99s", proto, &statuscode, statusmsg);
	if (result != 3 || (statuscode != 200 && statuscode != 206 && statuscode != 302))
	{
		eDebug("[eHttpStream] %s: wrong http response code: %d", __func__, statuscode);
		goto error;
	}

	while (1)
	{
		result = readLine(streamSocket, &linebuf, &buflen);
		if (!contenttypeparsed)
		{
			char contenttype[33];
			if (sscanf(linebuf, "Content-Type: %32s", contenttype) == 1)
			{
				contenttypeparsed = true;
				if (!strcasecmp(contenttype, "application/text")
				|| !strcasecmp(contenttype, "audio/x-mpegurl")
				|| !strcasecmp(contenttype, "audio/mpegurl")
				|| !strcasecmp(contenttype, "application/m3u"))
				{
					/* assume we'll get a playlist, some text file containing a stream url */
					playlist = true;
				}
				continue;
			}
		}
		if (playlist && !strncasecmp(linebuf, "http://", 7))
		{
			newurl = linebuf;
			eDebug("[eHttpStream] %s: playlist entry: %s", __func__, newurl.c_str());
			break;
		}
		if (((statuscode == 301) || (statuscode == 302) || (statuscode == 303) || (statuscode == 307) || (statuscode == 308)) &&
				strncasecmp(linebuf, "location: ", 10) == 0)
		{
			newurl = &linebuf[10];
			if (!extra_headers.empty())
				newurl.append("#").append(extra_headers);
			eDebug("[eHttpStream] %s: redirecting to: %s", __func__, newurl.c_str());
			break;
		}

		if (((statuscode == 200) || (statuscode == 206)) && !strncasecmp(linebuf, "transfer-encoding: chunked", strlen("transfer-encoding: chunked")))
		{
			isChunked = true;
		}
		if (!playlist && result == 0)
			break;
		if (result < 0)
			break;
	}

	free(linebuf);
	return 0;
error:
	eDebug("[eHttpStream] %s failed", __func__);
	free(linebuf);
	close();
	return -1;
}

int eHttpStream::open(const char *url)
{
	streamUrl = url;
	/*
	 * We're in gui thread context here, and establishing
	 * a connection might block for up to 10 seconds.
	 * Spawn a new thread to establish the connection.
	 */
	connectionStatus = BUSY;
	eDebug("[eHttpStream] Start thread");
	run();
	return 0;
}

void eHttpStream::thread()
{
	hasStarted();
	usleep(500000); // wait half a second in general as not only fallback receiver needs this.
	std::string currenturl, newurl;
	currenturl = streamUrl;
	for (unsigned int i = 0; i < 5; i++)
	{
		if (openUrl(currenturl, newurl) < 0)
		{
			/* connection failed */
			eDebug("[eHttpStream] Thread end NO connection");
			connectionStatus = FAILED;
			return;
		}
		if (newurl == "")
		{
			/* we have a valid stream connection */
			eDebug("[eHttpStream] Thread end connection");
			connectionStatus = CONNECTED;
			return;
		}
		/* switch to new url */
		close();
		currenturl = newurl;
		newurl = "";
	}
	/* too many redirect / playlist levels */
	eDebug("[eHttpStream] hread end NO connection");
	connectionStatus = FAILED;
	return;
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

ssize_t eHttpStream::syncNextRead(void *buf, ssize_t length)
{
	unsigned char *b = (unsigned char*)buf;
	unsigned char *e = b + length;
	partialPktSz = 0;

	if (*(char*)buf != 0x47)
	{
		// the current read is not aligned
		// get the head position of the last packet
		// so we'll try to align the next read
		while (e != b && *e != 0x47) e--;
	}
	else
	{
		// the current read is aligned
		// get the last incomplete packet position
		e -= length % packetSize;
	}

	if (e != b && e != (b + length))
	{
		partialPktSz = (b + length) - e;
		// if the last packet is read partially save it to align the next read
		if (partialPktSz > 0 && partialPktSz < packetSize)
		{
			memcpy(partialPkt, e, partialPktSz);
		}
	}
	return (length - partialPktSz);
}

ssize_t eHttpStream::httpChunkedRead(void *buf, size_t count)
{
	ssize_t ret = -1;
	size_t total_read = partialPktSz;

	// write partial packet from the previous read
	if (partialPktSz > 0)
	{
		memcpy(buf, partialPkt, partialPktSz);
		partialPktSz = 0;
	}

	if (!isChunked)
	{
		ret = timedRead(streamSocket,((char*)buf) + total_read , count - total_read, 5000, 100);
		if (ret > 0)
		{
			ret += total_read;
			ret = syncNextRead(buf, ret);
		}
	}
	else
	{
		while (total_read < count)
		{
			if (0 == currentChunkSize)
			{
				do
				{
					ret = readLine(streamSocket, &tmpBuf, &tmpBufSize);
					if (ret < 0) return -1;
				} while (!*tmpBuf && ret > 0); /* skip CR LF from last chunk */
				if (ret == 0)
					break;
				currentChunkSize = strtol(tmpBuf, NULL, 16);
				if (currentChunkSize == 0) return -1;
			}

			size_t to_read = count - total_read;
			if (currentChunkSize < to_read)
				to_read = currentChunkSize;

			// do not wait too long if we have something in the buffer already
			ret = timedRead(streamSocket, ((char*)buf) + total_read, to_read, ((total_read)? 100 : 5000), 100);
			if (ret <= 0)
				break;
			currentChunkSize -= ret;
			total_read += ret;
		}
		if (total_read > 0)
		{
			ret = syncNextRead(buf, total_read);
		}
	}
	return ret;
}

ssize_t eHttpStream::read(off_t offset, void *buf, size_t count)
{
	if (connectionStatus == BUSY)
		return 0;
	else if (connectionStatus == FAILED)
		return -1;
	return httpChunkedRead(buf, count);
}

int eHttpStream::valid()
{
	if (connectionStatus == BUSY)
		return 0;
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
