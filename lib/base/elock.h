#ifndef __elock_h
#define __elock_h

#include <pthread.h>

class singleLock
{
	pthread_mutex_t &lock;
public:
	singleLock( pthread_mutex_t &m )
		:lock(m)
	{
		pthread_mutex_lock(&lock);
	}
	~singleLock()
	{
		pthread_mutex_unlock(&lock);
	}
};

class eLock
{
	pthread_mutex_t mutex;
	pthread_cond_t cond;

	int pid;
	int counter, max;
public:
	void lock(int res=100);
	void unlock(int res=100);

	eLock(int max=100);
	~eLock();
};

class eLocker
{
	eLock &lock;
	int res;
public:
	eLocker(eLock &lock, int res=100);
	~eLocker();
};

class eSemaphore
{
	int v;
	pthread_mutex_t mutex;
	pthread_cond_t cond;
public:
	eSemaphore();
	~eSemaphore();
	
	int down();
	int decrement();
	int up();
	int value();
};

#endif
