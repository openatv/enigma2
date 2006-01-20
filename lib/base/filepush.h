#ifndef __lib_base_filepush_h
#define __lib_base_filepush_h

#include <lib/base/thread.h>
#include <libsig_comp.h>
#include <lib/base/message.h>
#include <sys/types.h>

class iFilePushScatterGather
{
public:
	virtual void getNextSourceSpan(size_t bytes_read, off_t &start, size_t &size)=0;
};

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
	void enablePVRCommit(int);
	
	void setSG(iFilePushScatterGather *);
	
	enum { evtEOF, evtReadError, evtWriteError };
	Signal1<void,int> m_event;
	
private:
	iFilePushScatterGather *m_sg;
	int m_stop;
	unsigned char m_buffer[65536];
	int m_buf_start, m_buf_end;
	int m_fd_source, m_fd_dest;
	int m_send_pvr_commit;
	
	eFixedMessagePump<int> m_messagepump;
	
	void sendEvent(int evt);
	void recvEvent(const int &evt);
};

#endif
