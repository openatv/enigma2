#ifndef __lib_base_thread_h
#define __lib_base_thread_h

#include <pthread.h>

class eThread
{
	pthread_t the_thread;
	static void *wrapper(void *ptr);
	int alive;
public:
	bool thread_running() { return alive; }
	eThread();
	virtual ~eThread();
	
	void run();

	virtual void thread()=0;
	
	void kill();
};

#endif
