#include <lib/base/ebase.h>

#include <fcntl.h>
#include <unistd.h>
#include <errno.h>

#include <lib/base/eerror.h>
#include <lib/base/elock.h>
#include <lib/gdi/grc.h>

DEFINE_REF(eSocketNotifier);

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
	if (m_inActivate && m_inActivate->ref.count == 1)
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

	if (!m_timer_list.empty())
	{
		/* process all timers which are ready. first remove them out of the list. */
		while (!m_timer_list.empty() && (poll_timeout = timeout_usec( m_timer_list.begin()->getNextActivation() ) ) <= 0 )
		{
			eTimer *tmr = m_timer_list.begin();
			tmr->AddRef();
			tmr->activate();
			tmr->Release();
		}
		if (poll_timeout < 0)
			poll_timeout = 0;
		else /* convert us to ms */
			poll_timeout /= 1000;
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
	m_timer_list.remove(e);
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

#include "structmember.h"

extern "C" {

// eTimer replacement

struct eTimerPy
{
	PyObject_HEAD
	eTimer *tm;
	PyObject *in_weakreflist; /* List of weak references */
};

static int
eTimerPy_traverse(eTimerPy *self, visitproc visit, void *arg)
{
	PyObject *obj = self->tm->timeout.getSteal();
	if (obj) {
		Py_VISIT(obj);
	}
	return 0;
}

static int
eTimerPy_clear(eTimerPy *self)
{
	PyObject *obj = self->tm->timeout.getSteal(true);
	if (obj)
		Py_CLEAR(obj);
	return 0;
}

static void
eTimerPy_dealloc(eTimerPy* self)
{
	if (self->in_weakreflist != NULL)
		PyObject_ClearWeakRefs((PyObject *) self);
	eTimerPy_clear(self);
	self->tm->Release();
	self->ob_type->tp_free((PyObject*)self);
}

static PyObject *
eTimerPy_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
	eTimerPy *self = (eTimerPy *)type->tp_alloc(type, 0);
	self->tm = eTimer::create(eApp);
	self->tm->AddRef();
	self->in_weakreflist = NULL;
	return (PyObject *)self;
}

static PyObject *
eTimerPy_is_active(eTimerPy* self)
{
	PyObject *ret = NULL;
	ret = self->tm->isActive() ? Py_True : Py_False;
	Org_Py_INCREF(ret);
	return ret;
}

static PyObject *
eTimerPy_start(eTimerPy* self, PyObject *args)
{
	long v=0;
	long singleShot=0;
	if (PyTuple_Size(args) > 1)
	{
		if (!PyArg_ParseTuple(args, "ll", &v, &singleShot)) // when 2nd arg is a value
		{
			PyObject *obj=0;
			if (!PyArg_ParseTuple(args, "lO", &v, &obj)) // get 2nd arg as python object
				return NULL;
			else if (obj == Py_True)
				singleShot=1;
			else if (obj != Py_False)
				return NULL;
		}
	}
	else if (!PyArg_ParseTuple(args, "l", &v))
		return NULL;
	self->tm->start(v, singleShot);
	Py_RETURN_NONE;
}

static PyObject *
eTimerPy_start_long(eTimerPy* self, PyObject *args)
{
	int v=0;
	if (!PyArg_ParseTuple(args, "i", &v)) {
		return NULL;
	}
	self->tm->startLongTimer(v);
	Py_RETURN_NONE;
}

static PyObject *
eTimerPy_change_interval(eTimerPy* self, PyObject *args)
{
	long v=0;
	if (!PyArg_ParseTuple(args, "l", &v)) {
		return NULL;
	}
	self->tm->changeInterval(v);
	Py_RETURN_NONE;
}

static PyObject *
eTimerPy_stop(eTimerPy* self)
{
	self->tm->stop();
	Py_RETURN_NONE;
}

static PyObject *
eTimerPy_get_callback_list(eTimerPy *self)
{ //used for compatibilty with the old eTimer
	return self->tm->timeout.get();
}

static PyMethodDef eTimerPy_methods[] = {
	{"isActive", (PyCFunction)eTimerPy_is_active, METH_NOARGS,
	 "returns the timer state"
	},
	{"start", (PyCFunction)eTimerPy_start, METH_VARARGS,
	 "start timer with interval in msecs"
	},
	{"startLongTimer", (PyCFunction)eTimerPy_start_long, METH_VARARGS,
	 "start timer with interval in secs"
	},
	{"changeInterval", (PyCFunction)eTimerPy_change_interval, METH_VARARGS,
	 "change interval of a timer (in msecs)"
	},
	{"stop", (PyCFunction)eTimerPy_stop, METH_NOARGS,
	 "stops the timer"
	},
	//used for compatibilty with the old eTimer
	{"get", (PyCFunction)eTimerPy_get_callback_list, METH_NOARGS,
	 "get timeout callback list"
	},
	{NULL}  /* Sentinel */
};

static PyObject *
eTimerPy_get_cb_list(eTimerPy *self, void *closure)
{
	return self->tm->timeout.get();
}

static PyObject *
eTimerPy_timeout(eTimerPy *self, void *closure) 
{ //used for compatibilty with the old eTimer
	Org_Py_INCREF((PyObject*)self);
	return (PyObject*)self;
}

static PyGetSetDef eTimerPy_getseters[] = {
	{"callback",
	 (getter)eTimerPy_get_cb_list, (setter)0,
	 "returns the callback python list",
	 NULL},

	{"timeout", //used for compatibilty with the old eTimer
	 (getter)eTimerPy_timeout, (setter)0,
	 "synonym for our self",
	 NULL},

	{NULL} /* Sentinel */
};

static PyTypeObject eTimerPyType = {
	PyObject_HEAD_INIT(NULL)
	0, /*ob_size*/
	"eBaseImpl.eTimer", /*tp_name*/
	sizeof(eTimerPy), /*tp_basicsize*/
	0, /*tp_itemsize*/
	(destructor)eTimerPy_dealloc, /*tp_dealloc*/
	0, /*tp_print*/
	0, /*tp_getattr*/
	0, /*tp_setattr*/
	0, /*tp_compare*/
	0, /*tp_repr*/
	0, /*tp_as_number*/
	0, /*tp_as_sequence*/
	0, /*tp_as_mapping*/
	0, /*tp_hash */
	0, /*tp_call*/
	0, /*tp_str*/
	0, /*tp_getattro*/
	0, /*tp_setattro*/
	0, /*tp_as_buffer*/
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC, /*tp_flags*/
	"eTimer objects", /* tp_doc */
	(traverseproc)eTimerPy_traverse, /* tp_traverse */
	(inquiry)eTimerPy_clear, /* tp_clear */
	0, /* tp_richcompare */
	offsetof(eTimerPy, in_weakreflist), /* tp_weaklistoffset */
	0, /* tp_iter */
	0, /* tp_iternext */
	eTimerPy_methods, /* tp_methods */
	0, /* tp_members */
	eTimerPy_getseters, /* tp_getset */
	0, /* tp_base */
	0, /* tp_dict */
	0, /* tp_descr_get */
	0, /* tp_descr_set */
	0, /* tp_dictoffset */
	0, /* tp_init */
	0, /* tp_alloc */
	eTimerPy_new, /* tp_new */
};

// eSocketNotifier replacement

struct eSocketNotifierPy
{
	PyObject_HEAD
	eSocketNotifier *sn;
	PyObject *in_weakreflist; /* List of weak references */
};

static int
eSocketNotifierPy_traverse(eSocketNotifierPy *self, visitproc visit, void *arg)
{
	PyObject *obj = self->sn->activated.getSteal();
	if (obj)
		Py_VISIT(obj);
	return 0;
}

static int
eSocketNotifierPy_clear(eSocketNotifierPy *self)
{
	PyObject *obj = self->sn->activated.getSteal(true);
	if (obj)
		Py_CLEAR(obj);
	return 0;
}

static void
eSocketNotifierPy_dealloc(eSocketNotifierPy* self)
{
	if (self->in_weakreflist != NULL)
		PyObject_ClearWeakRefs((PyObject *) self);
	eSocketNotifierPy_clear(self);
	self->sn->Release();
	self->ob_type->tp_free((PyObject*)self);
}

static PyObject *
eSocketNotifierPy_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
	eSocketNotifierPy *self = (eSocketNotifierPy *)type->tp_alloc(type, 0);
	int fd, req, immediate_start = 1, size = PyTuple_Size(args);
	if (size > 2)
	{
		if (!PyArg_ParseTuple(args, "iii", &fd, &req, &immediate_start))
		{
			PyObject *obj = NULL;
			if (!PyArg_ParseTuple(args, "iiO", &fd, &req, &immediate_start))
				return NULL;
			if (obj == Py_False)
				immediate_start = 0;
			else if (obj != Py_True)
				return NULL;
		}
	}
	else if (size < 2 || !PyArg_ParseTuple(args, "ii", &fd, &req))
		return NULL;
	self->sn = eSocketNotifier::create(eApp, fd, req, immediate_start);
	self->sn->AddRef();
	self->in_weakreflist = NULL;
	return (PyObject *)self;
}

static PyObject *
eSocketNotifierPy_is_running(eSocketNotifierPy* self)
{
	PyObject *ret = self->sn->isRunning() ? Py_True : Py_False;
	Org_Py_INCREF(ret);
	return ret;
}

static PyObject *
eSocketNotifierPy_start(eSocketNotifierPy* self)
{
	self->sn->start();
	Py_RETURN_NONE;
}

static PyObject *
eSocketNotifierPy_stop(eSocketNotifierPy* self)
{
	self->sn->stop();
	Py_RETURN_NONE;
}

static PyObject *
eSocketNotifierPy_get_fd(eSocketNotifierPy* self)
{
	return PyInt_FromLong(self->sn->getFD());
}

static PyObject *
eSocketNotifierPy_get_requested(eSocketNotifierPy* self)
{
	return PyInt_FromLong(self->sn->getRequested());
}

static PyObject *
eSocketNotifierPy_set_requested(eSocketNotifierPy* self, PyObject *args)
{
	int req;
	if (PyTuple_Size(args) != 1 || !PyArg_ParseTuple(args, "i", &req))
		return NULL;
	self->sn->setRequested(req);
	Py_RETURN_NONE;
}

static PyMethodDef eSocketNotifierPy_methods[] = {
	{"isRunning", (PyCFunction)eSocketNotifierPy_is_running, METH_NOARGS,
	 "returns the running state"
	},
	{"start", (PyCFunction)eSocketNotifierPy_start, METH_NOARGS,
	 "start the sn"
	},
	{"stop", (PyCFunction)eSocketNotifierPy_stop, METH_NOARGS,
	 "stops the sn"
	},
	{"getFD", (PyCFunction)eSocketNotifierPy_get_fd, METH_NOARGS,
	 "get file descriptor"
	},
	{"getRequested", (PyCFunction)eSocketNotifierPy_get_requested, METH_NOARGS,
	 "get requested"
	},
	{"setRequested", (PyCFunction)eSocketNotifierPy_set_requested, METH_VARARGS,
	 "set requested"
	},
	{NULL}  /* Sentinel */
};

static PyObject *
eSocketNotifierPy_get_cb_list(eSocketNotifierPy *self, void *closure)
{
	return self->sn->activated.get();
}

static PyGetSetDef eSocketNotifierPy_getseters[] = {
	{"callback",
	 (getter)eSocketNotifierPy_get_cb_list, (setter)0,
	 "returns the callback python list",
	 NULL},
	{NULL} /* Sentinel */
};

static PyTypeObject eSocketNotifierPyType = {
	PyObject_HEAD_INIT(NULL)
	0, /*ob_size*/
	"eBaseImpl.eSocketNotifier", /*tp_name*/
	sizeof(eSocketNotifierPy), /*tp_basicsize*/
	0, /*tp_itemsize*/
	(destructor)eSocketNotifierPy_dealloc, /*tp_dealloc*/
	0, /*tp_print*/
	0, /*tp_getattr*/
	0, /*tp_setattr*/
	0, /*tp_compare*/
	0, /*tp_repr*/
	0, /*tp_as_number*/
	0, /*tp_as_sequence*/
	0, /*tp_as_mapping*/
	0, /*tp_hash */
	0, /*tp_call*/
	0, /*tp_str*/
	0, /*tp_getattro*/
	0, /*tp_setattro*/
	0, /*tp_as_buffer*/
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_HAVE_GC, /*tp_flags*/
	"eTimer objects", /* tp_doc */
	(traverseproc)eSocketNotifierPy_traverse, /* tp_traverse */
	(inquiry)eSocketNotifierPy_clear, /* tp_clear */
	0, /* tp_richcompare */
	offsetof(eSocketNotifierPy, in_weakreflist), /* tp_weaklistoffset */
	0, /* tp_iter */
	0, /* tp_iternext */
	eSocketNotifierPy_methods, /* tp_methods */
	0, /* tp_members */
	eSocketNotifierPy_getseters, /* tp_getset */
	0, /* tp_base */
	0, /* tp_dict */
	0, /* tp_descr_get */
	0, /* tp_descr_set */
	0, /* tp_dictoffset */
	0, /* tp_init */
	0, /* tp_alloc */
	eSocketNotifierPy_new, /* tp_new */
};

static PyMethodDef module_methods[] = {
	{NULL}  /* Sentinel */
};

void eBaseInit(void)
{
	PyObject* m = Py_InitModule3("eBaseImpl", module_methods,
		"Module that implements some enigma classes with working cyclic garbage collection.");

	if (m == NULL)
		return;

	if (!PyType_Ready(&eTimerPyType))
	{
		Org_Py_INCREF((PyObject*)&eTimerPyType);
		PyModule_AddObject(m, "eTimer", (PyObject*)&eTimerPyType);
	}
	if (!PyType_Ready(&eSocketNotifierPyType))
	{
		Org_Py_INCREF((PyObject*)&eSocketNotifierPyType);
		PyModule_AddObject(m, "eSocketNotifier", (PyObject*)&eSocketNotifierPyType);
	}
}
}
