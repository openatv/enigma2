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
	for (std::multimap<int,eSocketNotifier*>::iterator i = notifiers.find(sn->getFD());
			i != notifiers.end();
			++i)
		if (i->second == sn)
			return notifiers.erase(i);
	eFatal("removed socket notifier which is not present");
}

int eMainloop::processOneEvent(unsigned int user_timeout, PyObject **res, PyObject *additional)
{
	int return_reason = 0;
		/* get current time */
	timeval now;
	gettimeofday(&now, 0);
	m_now_is_invalid = 0;
		
	if (additional && !PyDict_Check(additional))
		eFatal("additional, but it's not dict");
		
	if (additional && !res)
		eFatal("additional, but no res");
		
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
	
	if ((user_timeout > 0) && (poll_timeout > 0) && ((unsigned int)poll_timeout > user_timeout))
	{
		poll_timeout = user_timeout;
		return_reason = 1;
	}
		
	int ret = 0;
		
	std::multimap<int,eSocketNotifier*>::iterator it;
	std::map<int,int> fd_merged;
	std::map<int,int>::const_iterator fd_merged_it;
		
	for (it = notifiers.begin(); it != notifiers.end(); ++it)
		fd_merged[it->first] |= it->second->getRequested();
		
	fd_merged_it = fd_merged.begin();
		
	int nativecount, fdcount;
		
	nativecount = fdcount = fd_merged.size();
		
	if (additional)
	{
		additional = PyDict_Items(additional);
		fdcount += PyList_Size(additional);
	}
		
		// build the poll aray
	pollfd pfd[fdcount];  // make new pollfd array
		
	for (int i=0; i < nativecount; i++, fd_merged_it++)
	{
		pfd[i].fd = fd_merged_it->first;
		pfd[i].events = fd_merged_it->second;
	}
		
	if (additional)
	{
		for (int i=0; i < PyList_Size(additional); ++i)
		{
			PyObject *it = PyList_GET_ITEM(additional, i);
			if (!PyTuple_Check(it))
				eFatal("poll item is not a tuple");
			if (PyTuple_Size(it) != 2)
				eFatal("poll tuple size is not 2");
			int fd = PyObject_AsFileDescriptor(PyTuple_GET_ITEM(it, 0));
			if (fd == -1)
				eFatal("poll tuple not a filedescriptor");
			pfd[nativecount + i].fd = fd;
			pfd[nativecount + i].events = PyInt_AsLong(PyTuple_GET_ITEM(it, 1));
		}
		Py_DECREF(additional);
	}
		
	ret = ::poll(pfd, fdcount, poll_timeout);
		
			/* ret > 0 means that there are some active poll entries. */
	if (ret > 0)
	{
		return_reason = 0;
		for (int i=0; i < nativecount ; i++)
		{
			it = notifiers.begin();
				
			int handled = 0;
				
			std::multimap<int,eSocketNotifier*>::iterator 
				l = notifiers.lower_bound(pfd[i].fd),
				u = notifiers.upper_bound(pfd[i].fd);
				
			ePtrList<eSocketNotifier> n;
				
			for (; l != u; ++l)
				n.push_back(l->second);
				
			for (ePtrList<eSocketNotifier>::iterator li(n.begin()); li != n.end(); ++li)
			{
				int req = li->getRequested();
					
				handled |= req;
				
				if (pfd[i].revents & req)
					(*li)->activate(pfd[i].revents);
			}
			if ((pfd[i].revents&~handled) & (POLLERR|POLLHUP|POLLNVAL))
				eDebug("poll: unhandled POLLERR/HUP/NVAL for fd %d(%d)", pfd[i].fd, pfd[i].revents);
		}
			
		for (int i = nativecount; i < fdcount; ++i)
		{
			if (pfd[i].revents)
			{
				if (!*res)
					*res = PyList_New(0);
				PyObject *it = PyTuple_New(2);
				PyTuple_SET_ITEM(it, 0, PyInt_FromLong(pfd[i].fd));
				PyTuple_SET_ITEM(it, 1, PyInt_FromLong(pfd[i].revents));
				PyList_Append(*res, it);
				Py_DECREF(it);
			}
		}
			
		ret = 1; /* poll did not timeout. */
	} else if (ret < 0)
	{
			/* when we got a signal, we get EINTR. */
		if (errno != EINTR)
			eDebug("poll made error (%m)");
		else
		{
			return_reason = 2;
			ret = -1; /* don't assume the timeout has passed when we got a signal */
		}
	}
	
		/* when we not processed anything, check timers. */
	if (!m_timer_list.empty())
	{
			/* we know that this time has passed. */
		singleLock s(recalcLock);

		if (ret || m_now_is_invalid)
			gettimeofday(&now, 0);
		else
			now += poll_timeout;

			/* process all timers which are ready. first remove them out of the list. */
		while ((!m_timer_list.empty()) && (m_timer_list.begin()->getNextActivation() <= now))
			m_timer_list.begin()->activate();
	}
	
	return return_reason;
}

void eMainloop::addTimer(eTimer* e)
{
	m_timer_list.insert_in_order(e);
}

void eMainloop::removeTimer(eTimer* e)
{
	m_timer_list.remove(e);
}

int eMainloop::iterate(unsigned int user_timeout, PyObject **res, PyObject *dict)
{
	int ret = 0;
	
	timeval user_timer;
	gettimeofday(&user_timer, 0);
	user_timer += user_timeout;

		/* TODO: this code just became ugly. fix that. */
	do
	{
		if (m_interrupt_requested)
		{
			m_interrupt_requested = 0;
			return 0;
		}
		if (app_quit_now) return -1;
		timeval now, timeout;
		gettimeofday(&now, 0);
		timeout = user_timer - now;
		
		if (user_timeout && (user_timer <= now))
			return 0;
		
		int to = 0;
		if (user_timeout)
			to = timeout.tv_sec * 1000 + timeout.tv_usec / 1000;
		
		ret = processOneEvent(to, res, dict);
		if (res && *res)
			return ret;
	} while (ret == 0);
	
	return ret;
}

int eMainloop::runLoop()
{
	while (!app_quit_now)
		iterate();
	return retval;
}

void eMainloop::reset()
{
	app_quit_now=false;
}

PyObject *eMainloop::poll(PyObject *timeout, PyObject *dict)
{
	PyObject *res = 0;
	
	if (app_quit_now)
	{
		Py_INCREF(Py_None);
		return Py_None;
	}
	
	int user_timeout = (timeout == Py_None) ? 0 : PyInt_AsLong(timeout);

	iterate(user_timeout, &res, dict);
	
	if (!res) /* return empty list on timeout */
		res = PyList_New(0);
	
	return res;
}

void eMainloop::interruptPoll()
{
	m_interrupt_requested = 1;
}

void eMainloop::quit(int ret)
{
	retval = ret;
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
