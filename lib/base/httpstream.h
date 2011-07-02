#ifndef __lib_base_httpstream_h
#define __lib_base_httpstream_h

#include <string>
#include <lib/base/ebase.h>
#include <lib/base/itssource.h>

class eHttpStream: public iTsSource, public Object
{
	DECLARE_REF(eHttpStream);

	int streamSocket;

	ssize_t singleRead(int fd, void *buf, size_t count);
	ssize_t timedRead(int fd, void *buf, size_t count, int initialtimeout, int interbytetimeout);
	ssize_t readLine(int fd, char** buffer, size_t* bufsize);
	ssize_t write(int fd, const void *buf, size_t count);
	int select(int maxfd, fd_set *readfds, fd_set *writefds, fd_set *exceptfds, struct timeval *timeout);
	int connect(const char *hostname, int port, int timeoutsec);

	/* iTsSource */
	off_t lseek(off_t offset, int whence);
	ssize_t read(off_t offset, void *buf, size_t count);
	off_t length();
	int valid();

public:
	eHttpStream();
	~eHttpStream();
	int open(const char *url);
	int close();
};

#endif
