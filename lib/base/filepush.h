#ifndef __lib_base_filepush_h
#define __lib_base_filepush_h

#include <lib/base/thread.h>

class eFilePushThread: public eThread
{
public:
	eFilePushThread();
	void thread();
	void stop();
	void start(int sourcefd, int destfd);
private:
	int m_stop;
	unsigned char m_buffer[65536];
	int m_buf_start, m_buf_end;
	int m_fd_source, m_fd_dest;
};

#endif
