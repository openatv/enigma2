#include <lib/base/thread.h>
#include <stdio.h>
#include <lib/base/eerror.h>

void *eThread::wrapper(void *ptr)
{
	((eThread*)ptr)->thread();
	pthread_exit(0);
}

eThread::eThread()
{
	alive=0;
}

void eThread::run()
{
	alive=1;
	pthread_create(&the_thread, 0, wrapper, this);
}

eThread::~eThread()
{
	if (alive)
		kill();
}

void eThread::kill()
{
	alive=0;
	eDebug("waiting for thread shutdown");
	pthread_join(the_thread, 0);
	eDebug("ok");
}
