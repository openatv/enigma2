#include <lib/base/thread.h>

#include <stdio.h>
#include <unistd.h>
#include <lib/base/eerror.h>

void eThread::thread_completed(void *ptr)
{
	eThread *p = (eThread*) ptr;
	p->m_alive = 0;

		/* recover state in case thread was cancelled before calling hasStarted */
	if (!p->m_started)
		p->hasStarted();

	p->thread_finished();
}

void *eThread::wrapper(void *ptr)
{
	eThread *p = (eThread*)ptr;
	pthread_cleanup_push(thread_completed, (void*)p);
	p->thread();
	pthread_exit(0);
	pthread_cleanup_pop(1);
	return 0;
}

eThread::eThread()
	: the_thread(0), m_alive(0)
{
}

int eThread::runAsync(int prio, int policy)
{
	eDebug("before: %d", m_state.value());
		/* the thread might already run. */
	if (sync())
		return -1;
	
	eDebug("after: %d", m_state.value());
	ASSERT(m_state.value() == 1); /* sync postconditions */
	ASSERT(!m_alive);
	m_state.down();
	ASSERT(m_state.value() == 0);
	
	m_alive = 1;
	m_started = 0;

		/* start thread. */
	pthread_attr_t attr;
	pthread_attr_init(&attr);
	
	if (prio || policy)
	{
		struct sched_param p;
		p.__sched_priority=prio;
		pthread_attr_setschedpolicy(&attr, policy);
		pthread_attr_setschedparam(&attr, &p);
	}

	if (the_thread) {
		eDebug("old thread joined %d", pthread_join(the_thread, 0));
		the_thread = 0;
	}

	if (pthread_create(&the_thread, &attr, wrapper, this))
	{
		pthread_attr_destroy(&attr);
		m_alive = 0;
		eDebug("couldn't create new thread");
		return -1;
	}
	
	pthread_attr_destroy(&attr);
	return 0;
}

int eThread::run(int prio, int policy)
{
	if (runAsync(prio, policy))
		return -1;
	sync();
	return 0;
}

eThread::~eThread()
{
	kill();
}

int eThread::sync(void)
{
	int res;
	int debug_val_before = m_state.value();
	m_state.down(); /* this might block */
	res = m_alive;
	if (m_state.value() != 0)
		eFatal("eThread::sync: m_state.value() == %d - was %d before", m_state.value(), debug_val_before);
	ASSERT(m_state.value() == 0);
	m_state.up();
	return res; /* 0: thread is guaranteed not to run. 1: state unknown. */
}

int eThread::sendSignal(int sig)
{
	if (m_alive)
		return pthread_kill(the_thread, sig);
	else
		eDebug("send signal to non running thread");
	return -1;
}

void eThread::kill(bool sendcancel)
{
	if (!the_thread) /* already joined */
		return;

	if (sync() && sendcancel)
	{
		eDebug("send cancel to thread");
		pthread_cancel(the_thread);
	}
	eDebug("thread joined %d", pthread_join(the_thread, 0));
	the_thread = 0;
}

void eThread::hasStarted()
{
	ASSERT(!m_state.value());
	m_started = 1;
	m_state.up();
}
