#include <lib/base/ebase.h>

#include <fcntl.h>
#include <unistd.h>
#include <errno.h>

#include <lib/base/eerror.h>
#include <lib/base/elock.h>
#include <lib/gdi/grc.h>

DEFINE_REF(eSocketNotifier);

eSocketNotifier::eSocketNotifier(eMainloop *context, int fd, int requested, bool startnow):
	context(*context), fd(fd), state(0), requested(requested)
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

	if (eMainloop::isValid(&context))
	{
		context.addSocketNotifier(this);
		state=2;  // running but not in poll yet
	}
}

void eSocketNotifier::stop()
{
	if (state)
	{
		state=0;
		context.removeSocketNotifier(this);
	}
}

DEFINE_REF(eTimer);

void eTimer::start(long msek, bool singleShot)
{
	if (bActive)
		stop();

	if (eMainloop::isValid(&context))
	{
		bActive = true;
		bSingleShot = singleShot;
		interval = msek;
		clock_gettime(CLOCK_MONOTONIC, &nextActivation);
//		eDebug("this = %p\nnow sec = %d, nsec = %d\nadd %d msec", this, nextActivation.tv_sec, nextActivation.tv_nsec, msek);
		nextActivation += (msek<0 ? 0 : msek);
//		eDebug("next Activation sec = %d, nsec = %d", nextActivation.tv_sec, nextActivation.tv_nsec );
		context.addTimer(this);
	}
}

void eTimer::startLongTimer(int seconds)
{
	if (bActive)
		stop();

	if (eMainloop::isValid(&context))
	{
		bActive = bSingleShot = true;
		interval = 0;
		clock_gettime(CLOCK_MONOTONIC, &nextActivation);
//		eDebug("this = %p\nnow sec = %d, nsec = %d\nadd %d sec", this, nextActivation.tv_sec, nextActivation.tv_nsec, seconds);
		if ( seconds > 0 )
			nextActivation.tv_sec += seconds;
//		eDebug("next Activation sec = %d, nsec = %d", nextActivation.tv_sec, nextActivation.tv_nsec );
		context.addTimer(this);
	}
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
	/* timer has already been removed from the context, when activate is called */

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
ePtrList<eMainloop> eMainloop::existing_loops;

bool eMainloop::isValid(eMainloop *ml)
{
	return std::find(existing_loops.begin(), existing_loops.end(), ml) != existing_loops.end();
}

eMainloop::~eMainloop()
{
	existing_loops.remove(this);
	for (std::map<int, eSocketNotifier*>::iterator it(notifiers.begin());it != notifiers.end();++it)
		it->second->stop();
	while(m_timer_list.begin() != m_timer_list.end())
		m_timer_list.begin()->stop();
}

void eMainloop::addSocketNotifier(eSocketNotifier *sn)
{
	int fd = sn->getFD();
	if (m_inActivate && m_inActivate->ref == 1)
	{
		/*  when the current active SocketNotifier's refcount is one,
			then no more external references are existing.
			So it gets destroyed when the activate callback is finished (->AddRef() / ->Release() calls in processOneEvent).
			But then the sn->stop() is called to late for the next Asserion.
			Thus we call sn->stop() here (this implicitly calls eMainloop::removeSocketNotifier) and we don't get trouble
			with the next Assertion.
		*/
		m_inActivate->stop();
	}
	ASSERT(notifiers.find(fd) == notifiers.end());
	notifiers[fd]=sn;
}

void eMainloop::removeSocketNotifier(eSocketNotifier *sn)
{
	int fd = sn->getFD();
	std::map<int,eSocketNotifier*>::iterator i(notifiers.find(fd));
	if (i != notifiers.end())
	{
		notifiers.erase(i);
		return;
	}
	for (i = notifiers.begin(); i != notifiers.end(); ++i)
		eDebug("fd=%d, sn=%p", i->second->getFD(), (void*)i->second);
	eFatal("removed socket notifier which is not present, fd=%d", fd);
}

int eMainloop::processOneEvent(unsigned int twisted_timeout, PyObject **res, ePyObject additional)
{
	int return_reason = 0;
		/* get current time */

	if (additional && !PyDict_Check(additional))
		eFatal("additional, but it's not dict");

	if (additional && !res)
		eFatal("additional, but no res");

	long poll_timeout = -1; /* infinite in case of empty timer list */

	{
		ePtrList<eTimer>::iterator it = m_timer_list.begin();
		if (it != m_timer_list.end())
		{
			eTimer *tmr = *it;
			timespec now;
			clock_gettime(CLOCK_MONOTONIC, &now);
			/* process all timers which are ready. first remove them out of the list. */
			while (tmr->needsActivation(now))
			{
				m_timer_list.erase(it);
				tmr->AddRef();
				tmr->activate();
				tmr->Release();
				it = m_timer_list.begin();
				if (it == m_timer_list.end()) break;
				tmr = *it;
			}
			it = m_timer_list.begin();
			if (it != m_timer_list.end()) poll_timeout = timeout_usec((*it)->getNextActivation());
			if (poll_timeout < 0)
				poll_timeout = 0;
			else /* convert us to ms */
				poll_timeout /= 1000;
		}
	}

	if ((twisted_timeout > 0) && (poll_timeout > 0) && ((unsigned int)poll_timeout > twisted_timeout))
	{
		poll_timeout = twisted_timeout;
		return_reason = 1;
	}

	int nativecount=notifiers.size(),
		fdcount=nativecount,
		ret=0;

	if (additional)
		fdcount += PyDict_Size(additional);

		// build the poll aray
	pollfd pfd[fdcount];  // make new pollfd array
	std::map<int,eSocketNotifier*>::iterator it = notifiers.begin();

	int i=0;
	for (; i < nativecount; ++i, ++it)
	{
		it->second->state = 1; // running and in poll
		pfd[i].fd = it->first;
		pfd[i].events = it->second->getRequested();
	}

	if (additional)
	{
#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
		typedef int Py_ssize_t;
# define PY_SSIZE_T_MAX INT_MAX
# define PY_SSIZE_T_MIN INT_MIN
#endif
		PyObject *key, *val;
		Py_ssize_t pos=0;
		while (PyDict_Next(additional, &pos, &key, &val)) {
			pfd[i].fd = PyObject_AsFileDescriptor(key);
			pfd[i++].events = PyInt_AsLong(val);
		}
	}

	m_is_idle = 1;
	++m_idle_count;

	if (this == eApp)
	{
		Py_BEGIN_ALLOW_THREADS
		ret = ::poll(pfd, fdcount, poll_timeout);
		Py_END_ALLOW_THREADS
	} else
		ret = ::poll(pfd, fdcount, poll_timeout);

	m_is_idle = 0;

			/* ret > 0 means that there are some active poll entries. */
	if (ret > 0)
	{
		int i=0;
		return_reason = 0;
		for (; i < nativecount; ++i)
		{
			if (pfd[i].revents)
			{
				it = notifiers.find(pfd[i].fd);
				if (it != notifiers.end()
					&& it->second->state == 1) // added and in poll
				{
					m_inActivate = it->second;
					int req = m_inActivate->getRequested();
					if (pfd[i].revents & req) {
						m_inActivate->AddRef();
						m_inActivate->activate(pfd[i].revents & req);
						m_inActivate->Release();
					}
					pfd[i].revents &= ~req;
					m_inActivate = 0;
				}
				if (pfd[i].revents & (POLLERR|POLLHUP|POLLNVAL))
					eDebug("poll: unhandled POLLERR/HUP/NVAL for fd %d(%d)", pfd[i].fd, pfd[i].revents);
			}
		}
		for (; i < fdcount; ++i)
		{
			if (pfd[i].revents)
			{
				if (!*res)
					*res = PyList_New(0);
				ePyObject it = PyTuple_New(2);
				PyTuple_SET_ITEM(it, 0, PyInt_FromLong(pfd[i].fd));
				PyTuple_SET_ITEM(it, 1, PyInt_FromLong(pfd[i].revents));
				PyList_Append(*res, it);
				Py_DECREF(it);
			}
		}
	}
	else if (ret < 0)
	{
			/* when we got a signal, we get EINTR. */
		if (errno != EINTR)
			eDebug("poll made error (%m)");
		else
			return_reason = 2; /* don't assume the timeout has passed when we got a signal */
	}

	return return_reason;
}

void eMainloop::addTimer(eTimer* e)
{
	m_timer_list.insert_in_order(e);
}

void eMainloop::removeTimer(eTimer* e)
{
	/* use singleremove, timers never occur in our list multiple times, and remove() is a lot more expensive */
	m_timer_list.singleremove(e);
}

int eMainloop::iterate(unsigned int twisted_timeout, PyObject **res, ePyObject dict)
{
	int ret = 0;

	if (twisted_timeout)
	{
		clock_gettime(CLOCK_MONOTONIC, &m_twisted_timer);
		m_twisted_timer += twisted_timeout;
	}

		/* TODO: this code just became ugly. fix that. */
	do
	{
		if (m_interrupt_requested)
		{
			m_interrupt_requested = 0;
			return 0;
		}

		if (app_quit_now)
			return -1;

		int to = 0;
		if (twisted_timeout)
		{
			timespec now, timeout;
			clock_gettime(CLOCK_MONOTONIC, &now);
			if (m_twisted_timer<=now) // timeout
				return 0;
			timeout = m_twisted_timer - now;
			to = timeout.tv_sec * 1000 + timeout.tv_nsec / 1000000;
		}
		ret = processOneEvent(to, res, dict);
	} while ( !ret && !(res && *res) );

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

PyObject *eMainloop::poll(ePyObject timeout, ePyObject dict)
{
	PyObject *res=0;

	if (app_quit_now)
		Py_RETURN_NONE;

	int twisted_timeout = (timeout == Py_None) ? 0 : PyInt_AsLong(timeout);

	iterate(twisted_timeout, &res, dict);
	if (res)
		return res;

	return PyList_New(0); /* return empty list on timeout */
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

eApplication* eApp = 0;
