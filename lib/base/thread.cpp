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

static const int default_stack_size = 1024*1024;

int eThread::runAsync(int prio, int policy)
{
		/* the thread might already run. */
	if (sync())
		return -1;

	ASSERT(m_state.value() == 1); /* sync postconditions */
	ASSERT(!m_alive);
	m_state.down();
	ASSERT(m_state.value() == 0);

	m_alive = 1;
	m_started = 0;

		/* start thread. */
	pthread_attr_t attr;
	pthread_attr_init(&attr);
	if (pthread_attr_setstacksize(&attr, default_stack_size) != 0)
		eDebug("[eThread] pthread_attr_setstacksize failed");

	if (prio || policy)
	{
		struct sched_param p;
		p.__sched_priority=prio;
		pthread_attr_setschedpolicy(&attr, policy);
		pthread_attr_setschedparam(&attr, &p);
	}

	if (the_thread) {
		eDebug("[eThread] old thread joined %d", pthread_join(the_thread, 0));
		the_thread = 0;
	}

	if (pthread_create(&the_thread, &attr, wrapper, this))
	{
		pthread_attr_destroy(&attr);
		m_alive = 0;
		eDebug("[eThread] couldn't create new thread");
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
	if (the_thread)
	{
		/* Warn about this class' design being borked */
		eWarning("[eThread] Destroyed thread without joining it, this usually means your thread is now running with a halfway destroyed object");
		kill();
	}
}

int eThread::sync(void)
{
	int res;
	int debug_val_before = m_state.value();
	m_state.down(); /* this might block */
	res = m_alive;
	if (m_state.value() != 0)
		eFatal("[eThread] sync: m_state.value() == %d - was %d before", m_state.value(), debug_val_before);
	ASSERT(m_state.value() == 0);
	m_state.up();
	return res; /* 0: thread is guaranteed not to run. 1: state unknown. */
}

int eThread::sendSignal(int sig)
{
	if (m_alive)
		return pthread_kill(the_thread, sig);
	else
		eDebug("[eThread] send signal to non running thread");
	return -1;
}

void eThread::kill()
{
	/* FIXME: Allthough in Linux we seem to get away with it, there is no
	 * guarantee that "0" is an invalid value for pthread_t */
	if (!the_thread) /* already joined */
		return;

	int ret = pthread_join(the_thread, NULL);
	the_thread = 0;
	if (ret)
		eWarning("[eThread] pthread_join failed, code: %d", ret);
}

void eThread::hasStarted()
{
	ASSERT(!m_state.value());
	m_started = 1;
	m_state.up();
}
