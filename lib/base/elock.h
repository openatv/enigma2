#ifndef __elock_h
#define __elock_h

#include <pthread.h>

class singleLock
{
	pthread_mutex_t &lock;
public:
	singleLock(pthread_mutex_t &m )
		:lock(m)
	{
		pthread_mutex_lock(&lock);
	}
	~singleLock()
	{
		pthread_mutex_unlock(&lock);
	}
};

class eRdWrLock
{
	friend class eRdLocker;
	friend class eWrLocker;
	pthread_rwlock_t m_lock;
	eRdWrLock(eRdWrLock &);
public:
	eRdWrLock()
	{
		pthread_rwlock_init(&m_lock, 0);
	}
	~eRdWrLock()
	{
		pthread_rwlock_destroy(&m_lock);
	}
	void RdLock()
	{
		pthread_rwlock_rdlock(&m_lock);
	}
	void WrLock()
	{
		pthread_rwlock_wrlock(&m_lock);
	}
	void Unlock()
	{
		pthread_rwlock_unlock(&m_lock);
	}
};

class eRdLocker
{
	eRdWrLock &m_lock;
public:
	eRdLocker(eRdWrLock &m)
		: m_lock(m)
	{
		pthread_rwlock_rdlock(&m_lock.m_lock);
	}
	~eRdLocker()
	{
		pthread_rwlock_unlock(&m_lock.m_lock);
	}
};

class eWrLocker
{
	eRdWrLock &m_lock;
public:
	eWrLocker(eRdWrLock &m)
		: m_lock(m)
	{
		pthread_rwlock_wrlock(&m_lock.m_lock);
	}
	~eWrLocker()
	{
		pthread_rwlock_unlock(&m_lock.m_lock);
	}
};

class eSingleLock
{
	friend class eSingleLocker;
	pthread_mutex_t m_lock;
	eSingleLock(eSingleLock &);
public:
	eSingleLock(bool recursive=false)
	{
		if (recursive)
		{
			pthread_mutexattr_t attr;
			pthread_mutexattr_init(&attr);
			pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_RECURSIVE);
			pthread_mutex_init(&m_lock, &attr);
			pthread_mutexattr_destroy(&attr);
		}
		else
			pthread_mutex_init(&m_lock, 0);
	}
	~eSingleLock()
	{
		pthread_mutex_destroy(&m_lock);
	}
};

class eSingleLocker
{
	eSingleLock &m_lock;
public:
	eSingleLocker(eSingleLock &m)
		: m_lock(m)
	{
		pthread_mutex_lock(&m_lock.m_lock);
	}
	~eSingleLocker()
	{
		pthread_mutex_unlock(&m_lock.m_lock);
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
