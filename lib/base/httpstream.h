#ifndef __lib_base_httpstream_h
#define __lib_base_httpstream_h

#include <string>
#include <lib/base/ebase.h>
#include <lib/base/itssource.h>
#include <lib/base/thread.h>

class eHttpStream: public iTsSource, public Object, public eThread
{
	DECLARE_REF(eHttpStream);

	int streamSocket;
	enum { BUSY, CONNECTED, FAILED } connectionStatus;
	bool isChunked;
	size_t currentChunkSize;
	std::string streamUrl;
	std::string authorizationData;
	char partialPkt[192];
	size_t partialPktSz;
	char* tmpBuf;
	size_t tmpBufSize;

	int openUrl(const std::string &url, std::string &newurl);
	void thread();
	ssize_t httpChunkedRead(void *buf, size_t count);
	ssize_t syncNextRead(void *buf, ssize_t count);

	/* iTsSource */
	ssize_t read(off_t offset, void *buf, size_t count);
	off_t length();
	off_t offset();
	int valid();
	bool isStream() { return true; };

public:
	eHttpStream();
	~eHttpStream();
	int open(const char *url);
	int close();
};

#endif
