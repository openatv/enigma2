#ifndef __lib_base_thread_h
#define __lib_base_thread_h

#include <pthread.h>
#include <signal.h>
#include <lib/base/elock.h>

/* the following states are possible:
 1 thread has not yet started
 2 thread has started, but not completed initialization (hadStarted not yet called)
 3 thread is running
 4 thread has finished, but not yet joined
 5 thread has joined (same as state 1)
 
 sync() will return:
 	0 (="not alive") for 1, 4, 5
 	1 for 3, 4
 	
 	it will wait when state is 2. It can't differentiate between
 	state 3 and 4, because a thread could always finish.
 	
 	all other state transitions (1 -> 2, 4 -> 5) must be activately
 	changed by either calling run() or kill().
 */

class eThread
{
public:
	eThread();
	virtual ~eThread();

		/* thread_finished is called from within the thread context as the last function
		   before the thread is going to die.
		   It should be used to do final cleanups (unlock locked mutexes ....) */
	virtual void thread_finished() {}

		/* runAsync starts the thread.
		   it assumes that the thread is not running,
		   i.e. sync() *must* return 0.
		   it will not wait for anything. */
	int runAsync(int prio=0, int policy=0);

		/* run will wait until the thread has either
		   passed it's initialization, or it has
		   died again. */
	int run(int prio=0, int policy=0);

	virtual void thread()=0;
	
		/* waits until thread is in "run" state */
		/* result: 0 - thread is not alive
		           1 - thread state unknown */
	int sync();
	int sendSignal(int sig);

		/* join the thread, i.e. busywait until thread has finnished. */
	void kill(bool sendcancel=false);
private:
	pthread_t the_thread;

	static void *wrapper(void *ptr);
	int m_alive, m_started;
	static void thread_completed(void *p);

	eSemaphore m_state;
protected:
	void hasStarted();
};

#endif
