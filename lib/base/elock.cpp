#include <lib/base/elock.h>
#include <unistd.h>

void eLock::lock(int res)
{
	if (res>max)
		res=max;
	pthread_mutex_lock(&mutex);
	while ((counter+res)>max)
		pthread_cond_wait(&cond, &mutex);
	counter+=res;
	pthread_mutex_unlock(&mutex);
}

void eLock::unlock(int res)
{
	if (res>max)
		res=max;
	pthread_mutex_lock(&mutex);
	counter-=res;
	pthread_mutex_unlock(&mutex);
	pthread_cond_signal(&cond);
}

eLock::eLock(int max): max(max)
{
	pthread_mutex_init(&mutex, 0);
	pthread_cond_init(&cond, 0);
	counter=0;
	pid=-1;
}

eLock::~eLock()
{
	pthread_mutex_destroy(&mutex);
	pthread_cond_destroy(&cond);
}

eLocker::eLocker(eLock &lock, int res): lock(lock), res(res)
{
	lock.lock(res);
}

eLocker::~eLocker()
{
	lock.unlock(res);
}

eSemaphore::eSemaphore()
{
	v=1;
	pthread_mutex_init(&mutex, 0);
	pthread_cond_init(&cond, 0);
}

eSemaphore::~eSemaphore()
{
	pthread_mutex_destroy(&mutex);
	pthread_cond_destroy(&cond);
}

int eSemaphore::down()
{
	int value_after_op;
	pthread_mutex_lock(&mutex);
	while (v<=0)
		pthread_cond_wait(&cond, &mutex);
	v--;
	value_after_op=v;
	pthread_mutex_unlock(&mutex);
	return value_after_op;
}

int eSemaphore::decrement()
{
	int value_after_op;
	pthread_mutex_lock(&mutex);
	v--;
	value_after_op=v;
	pthread_mutex_unlock(&mutex);
	pthread_cond_signal(&cond);
	return value_after_op;
}

int eSemaphore::up()
{
	int value_after_op;
	pthread_mutex_lock(&mutex);
	v++;
	value_after_op=v;
	pthread_mutex_unlock(&mutex);
	pthread_cond_signal(&cond);
	return value_after_op;
}

int eSemaphore::value()
{
	int value_after_op;
	pthread_mutex_lock(&mutex);
	value_after_op=v;
	pthread_mutex_unlock(&mutex);
	return value_after_op;
}

