#include <lib/base/ebase.h>

#include <fcntl.h>
#include <unistd.h>
#include <errno.h>

#include <lib/base/eerror.h>

eSocketNotifier::eSocketNotifier(eMainloop *context, int fd, int requested, bool startnow): context(*context), fd(fd), state(0), requested(requested)
{
	if (startnow)	
		start();
}

eSocketNotifier::~eSocketNotifier()
{
	stop();
}

void eSocketNotifier::start()
{
	if (state)
		stop();

	context.addSocketNotifier(this);
	state=1;
}

void eSocketNotifier::stop()
{
	if (state)
		context.removeSocketNotifier(this);

	state=0;
}

					// timer
void eTimer::start(long msek, bool singleShot)
{
	if (bActive)
		stop();

	bActive = true;
	bSingleShot = singleShot;
	interval = msek;
 	gettimeofday(&nextActivation, 0);		
//	eDebug("this = %p\nnow sec = %d, usec = %d\nadd %d msec", this, nextActivation.tv_sec, nextActivation.tv_usec, msek);
	nextActivation += (msek<0 ? 0 : msek);
//	eDebug("next Activation sec = %d, usec = %d", nextActivation.tv_sec, nextActivation.tv_usec );
	context.addTimer(this);
}

void eTimer::stop()
{	
	eDebug("stop timer");
	if (bActive)
	{
		bActive=false;
		context.removeTimer(this);
	}
}

void eTimer::changeInterval(long msek)
{
	if (bActive)  // Timer is running?
	{
		context.removeTimer(this);	 // then stop
		nextActivation -= interval;  // sub old interval
	}
	else
		bActive=true;	// then activate Timer

	interval = msek;   			 			// set new Interval
	nextActivation += interval;		// calc nextActivation

	context.addTimer(this);				// add Timer to context TimerList
}

void eTimer::activate()   // Internal Function... called from eApplication
{
	timeval now;
	gettimeofday(&now, 0);
//	eDebug("this = %p\nnow sec = %d, usec = %d\nnextActivation sec = %d, usec = %d", this, now.tv_sec, now.tv_usec, nextActivation.tv_sec, nextActivation.tv_usec );
//	eDebug("Timer emitted");
	context.removeTimer(this);

	if (!bSingleShot)
	{
		nextActivation += interval;
		context.addTimer(this);
	}
	else
		bActive=false;

	/*emit*/ timeout();
}

// mainloop

void eMainloop::addSocketNotifier(eSocketNotifier *sn)
{
	notifiers.insert(std::pair<int,eSocketNotifier*> (sn->getFD(), sn));
}

void eMainloop::removeSocketNotifier(eSocketNotifier *sn)
{
	notifiers.erase(sn->getFD());
}

void eMainloop::processOneEvent()
{
		/* notes:
		  - we should use epoll(4)
		  - timer are checked twice. there was a strong reason for it, but i can't remember. (FIXME)
		  - for each time, we gettimeofday() and check wether the timer should fire.
		    we should do this all better - we know how long the poll last, so we know which
		    timers should fire. Problem is that a timer handler could have required so
		    much time that another timer fired.
		    
		    A probably structure could look
		    
		    while (1)
		    {
			    time = gettimeofday()
			    timeout = calculate_pending_timers(time);
		    
		      doPoll(timeout or infinite);
		    	
		    	if (poll_had_results)
		    		handle_poll_handler();
		    	else
				    fire_timers(time + timeout)
			  }
			  
			  the gettimeofday() call is required because fire_timers could last more
			  than nothing.
			  
			  when poll did no timeout, we don't handle timers, as this will be done
			  in the next iteration (without adding overhead - we had to get the new
			  time anyway
		*/

		// first, process pending timers...
	long usec=0;

	while (TimerList && (usec = timeout_usec( TimerList.begin()->getNextActivation() ) ) <= 0 )
		TimerList.begin()->activate();

		// build the poll aray
	int fdAnz = notifiers.size();
	pollfd* pfd = new pollfd[fdAnz];  // make new pollfd array

	std::map<int,eSocketNotifier*>::iterator it(notifiers.begin());
	for (int i=0; i < fdAnz; i++, it++)
	{
		pfd[i].fd = it->first;
		pfd[i].events = it->second->getRequested();
	}

		// to the poll. When there are no timers, we have an infinite timeout
	int ret=poll(pfd, fdAnz, TimerList ? usec / 1000 : -1);  // convert to us

	if (ret>0)
	{
		for (int i=0; i < fdAnz ; i++)
		{
			if( notifiers.find(pfd[i].fd) == notifiers.end())
				continue;

			int req = notifiers[pfd[i].fd]->getRequested();

			if ( pfd[i].revents & req )
			{
				notifiers[pfd[i].fd]->activate(pfd[i].revents);

				if (!--ret)
					break;
			} else if (pfd[i].revents & (POLLERR|POLLHUP|POLLNVAL))
				eFatal("poll: unhandled POLLERR/HUP/NVAL for fd %d(%d) -> FIX YOUR CODE", pfd[i].fd,pfd[i].revents);
		}
	} else if (ret<0)
	{
			/* when we got a signal, we get EINTR. we do not care, 
			   because we check current time in timers anyway. */
		if (errno != EINTR)
			eDebug("poll made error (%m)");
	} 

		// check timer...
	while ( TimerList && timeout_usec( TimerList.begin()->getNextActivation() ) <= 0 )
		TimerList.begin()->activate();

	delete [] pfd;
}


int eMainloop::exec()
{
	if (!loop_level)
	{
		app_quit_now = false;
		enter_loop();
	}
	return retval;
}

	/* use with care! better: don't use it anymore. it was used for gui stuff, but 
		 doesn't allow multiple paths (or active dialogs, if you want it that way.) */
void eMainloop::enter_loop()
{
	loop_level++;

	// Status der vorhandenen Loop merken
	bool old_exit_loop = app_exit_loop;
	
	app_exit_loop = false;

	while (!app_exit_loop && !app_quit_now)
	{
		processOneEvent();
	}

	// wiederherstellen der vorherigen app_exit_loop
	app_exit_loop = old_exit_loop;

	loop_level--;

	if (!loop_level)
	{
			// do something here on exit the last loop
	}
}

void eMainloop::exit_loop()  // call this to leave the current loop
{
	app_exit_loop = true;	
}

void eMainloop::quit( int ret )   // call this to leave all loops
{
	retval=ret;
	app_quit_now = true;
}

eApplication* eApp = 0;
