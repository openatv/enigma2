#ifndef __lib_base_httpstream_h
#define __lib_base_httpstream_h

#include <string>
#include <lib/base/ebase.h>
#include <lib/base/itssource.h>
#include <lib/base/socketbase.h>

class eHttpStream: public iTsSource, public eSocketBase, public Object
{
	DECLARE_REF(eHttpStream);

	int streamSocket;

	/* iTsSource */
	off_t lseek(off_t offset, int whence);
	ssize_t read(off_t offset, void *buf, size_t count);
	off_t length();
	off_t offset();
	int valid();

public:
	eHttpStream();
	~eHttpStream();
	int open(const char *url);
	int close();
};

#endif
