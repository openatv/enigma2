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
//	eDebug("this = %p\nnow sec = %d, usec = %d\nadd %d msec", this, nextActivation.tv_sec, nextActivation.tv_usec, msek);
	nextActivation += (msek<0 ? 0 : msek);
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
//	eDebug("this = %p\nnow sec = %d, usec = %d\nadd %d sec", this, nextActivation.tv_sec, nextActivation.tv_usec, seconds);
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

void eTimer::addTimeOffset( int offset )
{
	nextActivation.tv_sec += offset;
}

// mainloop
ePtrList<eMainloop> eMainloop::existing_loops;

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
		/* get current time */
	timeval now;
	gettimeofday(&now, 0);
	m_now_is_invalid = 0;
	
	int poll_timeout = -1; /* infinite in case of empty timer list */
	
	if (m_timer_list)
	{
		singleLock s(recalcLock);
		poll_timeout = timeval_to_usec(m_timer_list.begin()->getNextActivation() - now);
			/* if current timer already passed, don't delay infinite. */
		if (poll_timeout < 0)
			poll_timeout = 0;
			
			/* convert us to ms */
		poll_timeout /= 1000;
	}
	
	int ret = 0;

	if (poll_timeout)
	{
			// build the poll aray
		int fdcount = notifiers.size();
		pollfd* pfd = new pollfd[fdcount];  // make new pollfd array

		std::map<int,eSocketNotifier*>::iterator it(notifiers.begin());
		for (int i=0; i < fdcount; i++, it++)
		{
			pfd[i].fd = it->first;
			pfd[i].events = it->second->getRequested();
		}

		ret = poll(pfd, fdcount, poll_timeout);

			/* ret > 0 means that there are some active poll entries. */
		if (ret > 0)
		{
			for (int i=0; i < fdcount ; i++)
			{
				if (notifiers.find(pfd[i].fd) == notifiers.end())
					continue;
				
				int req = notifiers[pfd[i].fd]->getRequested();
				
				if (pfd[i].revents & req)
				{
					notifiers[pfd[i].fd]->activate(pfd[i].revents);
				
					if (!--ret)
						break;
				} else if (pfd[i].revents & (POLLERR|POLLHUP|POLLNVAL))
					eFatal("poll: unhandled POLLERR/HUP/NVAL for fd %d(%d) -> FIX YOUR CODE", pfd[i].fd,pfd[i].revents);
			}
			
			ret = 1; /* poll did not timeout. */
		} else if (ret < 0)
		{
				/* when we got a signal, we get EINTR. */
			if (errno != EINTR)
				eDebug("poll made error (%m)");
			else
				ret = -1; /* don't assume the timeout has passed when we got a signal */
		}
		delete [] pfd;
	}
	
		/* when we not processed anything, check timers. */
	if (!ret)
	{
			/* we know that this time has passed. */
		now += poll_timeout;
		
		singleLock s(recalcLock);

			/* this will never change while we have the recalcLock */
			/* we can savely return here, the timer will be re-checked soon. */
		if (m_now_is_invalid)
			return;

			/* process all timers which are ready. first remove them out of the list. */
		while ((!m_timer_list.empty()) && (m_timer_list.begin()->getNextActivation() <= now))
			m_timer_list.begin()->activate();
	}
}

void eMainloop::addTimer(eTimer* e)
{
	m_timer_list.insert_in_order(e);
}

void eMainloop::removeTimer(eTimer* e)
{
	m_timer_list.remove(e);
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

void eMainloop::addTimeOffset(int offset)
{
	for (ePtrList<eMainloop>::iterator it(eMainloop::existing_loops)
		;it != eMainloop::existing_loops.end(); ++it)
	{
		singleLock s(it->recalcLock);
		it->m_now_is_invalid = 1;
		for (ePtrList<eTimer>::iterator tit = it->m_timer_list.begin(); tit != it->m_timer_list.end(); ++tit )
			tit->addTimeOffset(offset);
	}
}

eApplication* eApp = 0;
