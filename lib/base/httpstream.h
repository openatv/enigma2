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
	std::string streamUrl;
	std::string authorizationData;

	int openUrl(const std::string &url, std::string &newurl);
	void thread();

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
