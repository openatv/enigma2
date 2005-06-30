#include <lib/base/ebase.h>

#include <fcntl.h>
#include <unistd.h>
#include <errno.h>

#include <lib/base/eerror.h>
#include <lib/base/elock.h>

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
	nextActivation.tv_sec -= context.getTimerOffset();
	nextActivation += (msek<0 ? 0 : msek);
//	eDebug("this = %p\nnow sec = %d, usec = %d\nadd %d msec", this, nextActivation.tv_sec, nextActivation.tv_usec, msek);
//	eDebug("next Activation sec = %d, usec = %d", nextActivation.tv_sec, nextActivation.tv_usec );
	context.addTimer(this);
}

void eTimer::startLongTimer( int seconds )
{
	if (bActive)
		stop();

	bActive = bSingleShot = true;
	interval = 0;
	gettimeofday(&nextActivation, 0);
	nextActivation.tv_sec -= context.getTimerOffset();
//	eDebug("this = %p\nnow sec = %d, usec = %d\nadd %d msec", this, nextActivation.tv_sec, nextActivation.tv_usec, msek);
	if ( seconds > 0 )
		nextActivation.tv_sec += seconds;
//	eDebug("next Activation sec = %d, usec = %d", nextActivation.tv_sec, nextActivation.tv_usec );
	context.addTimer(this);
}

void eTimer::stop()
{
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
		bActive=true; // then activate Timer

	interval = msek;   			 			// set new Interval
	nextActivation += interval;		// calc nextActivation

	context.addTimer(this);				// add Timer to context TimerList
}

void eTimer::activate()   // Internal Funktion... called from eApplication
{
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

inline void eTimer::recalc( int offset )
{
	nextActivation.tv_sec += offset;
}

// mainloop
ePtrList<eMainloop> eMainloop::existing_loops;

void eMainloop::setTimerOffset( int difference )
{
	singleLock s(recalcLock);
	if (!TimerList)
		timer_offset=0;
	else
	{
		if ( timer_offset )
			eDebug("time_offset %d avail.. add new offset %d than new is %d",
			timer_offset, difference, timer_offset+difference);
		timer_offset+=difference;
	}
}

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

	if ( TimerList )
		doRecalcTimers();
	while (TimerList && (usec = timeout_usec( TimerList.begin()->getNextActivation() ) ) <= 0 )
	{
		TimerList.begin()->activate();
		doRecalcTimers();
	}

	int fdAnz = notifiers.size();
	pollfd pfd[fdAnz];

// fill pfd array
	std::map<int,eSocketNotifier*>::iterator it(notifiers.begin());
	for (int i=0; i < fdAnz; i++, it++)
	{
		pfd[i].fd = it->first;
		pfd[i].events = it->second->getRequested();
	}

		// to the poll. When there are no timers, we have an infinite timeout
	int ret=poll(pfd, fdAnz, TimerList ? usec / 1000 : -1);  // convert to ms

	if (ret>0)
	{
	//		eDebug("bin aussem poll raus und da war was");
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
			}
			else if (pfd[i].revents & (POLLERR|POLLHUP|POLLNVAL))
				eDebug("poll: unhandled POLLERR/HUP/NVAL for fd %d(%d)", pfd[i].fd,pfd[i].revents);
		}
	}
	else if (ret<0)
	{
			/* when we got a signal, we get EINTR. we do not care,
			   because we check current time in timers anyway. */
		if (errno != EINTR)
			eDebug("poll made error");
	}
}

int eMainloop::exec()
{
	if (!loop_level)
	{
		app_quit_now = false;
		app_exit_loop = false;
		enter_loop();
	}
	return retval;
}

void eMainloop::enter_loop()
{
	loop_level++;
	// Status der vorhandenen Loop merken
	bool old_exit_loop = app_exit_loop;

	app_exit_loop = false;

	while (!app_exit_loop && !app_quit_now)
		processOneEvent();

	// wiederherstellen der vorherigen app_exit_loop
	app_exit_loop = old_exit_loop;

	--loop_level;

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

inline void eMainloop::doRecalcTimers()
{
	singleLock s(recalcLock);
	if ( timer_offset )
	{
		for (ePtrList<eTimer>::iterator it(TimerList); it != TimerList.end(); ++it )
			it->recalc( timer_offset );
		timer_offset=0;
	}
}

eApplication* eApp = 0;
