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
protected:
	pthread_mutex_t m_lock;
private:
	eSingleLock(const eSingleLock &);
public:
	eSingleLock()
	{
		pthread_mutex_init(&m_lock, 0);
	}
	~eSingleLock()
	{
		pthread_mutex_destroy(&m_lock);
	}
	void lock()
	{
		pthread_mutex_lock(&m_lock);
	}
	void unlock()
	{
		pthread_mutex_unlock(&m_lock);
	}
	operator pthread_mutex_t&() { return m_lock; }
};

class eCondition
{
private:
	eCondition(const eCondition&);
protected:
	pthread_cond_t m_cond;
public:
	eCondition()
	{
		pthread_cond_init(&m_cond, 0);
	}
	~eCondition()
	{
		pthread_cond_destroy(&m_cond);
	}
	void signal()
	{
		pthread_cond_signal(&m_cond);
	}
	void wait(pthread_mutex_t& mutex)
	{
		pthread_cond_wait(&m_cond, &mutex);
	}
	operator pthread_cond_t&() { return m_cond; }
};

class eSingleLocker
{
protected:
	eSingleLock &m_lock;
public:
	eSingleLocker(eSingleLock &m)
		: m_lock(m)
	{
		m_lock.lock();
	}
	~eSingleLocker()
	{
		m_lock.unlock();
	}
};

class eLock
{
	pthread_mutex_t mutex;
	pthread_cond_t cond;

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
