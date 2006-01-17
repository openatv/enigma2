#ifndef __lib_base_filepush_h
#define __lib_base_filepush_h

#include <lib/base/thread.h>
#include <libsig_comp.h>
#include <lib/base/message.h>
#include <sys/types.h>

class eFilePushThread: public eThread, public Object
{
public:
	eFilePushThread();
	void thread();
	void stop();
	void start(int sourcefd, int destfd);
	
	void pause();
	void seek(int whence, off_t where);
	void resume();
	
		/* flushes the internal readbuffer */ 
	void flush();
	
	enum { evtEOF, evtReadError, evtWriteError };
	Signal1<void,int> m_event;
	
private:
	int m_stop;
	unsigned char m_buffer[65536];
	int m_buf_start, m_buf_end;
	int m_fd_source, m_fd_dest;
	
	eFixedMessagePump<int> m_messagepump;
	
	void sendEvent(int evt);
	void recvEvent(const int &evt);
};

#endif
