%{
#include <lib/base/ebase.h>
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
	Py_TYPE(self)->tp_free((PyObject*)self);
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
	{(char*)"callback",
	 (getter)eTimerPy_get_cb_list, (setter)0,
	 (char*)"returns the callback python list",
	 NULL},

	{(char*)"timeout", //used for compatibilty with the old eTimer
	 (getter)eTimerPy_timeout, (setter)0,
	 (char*)"synonym for our self",
	 NULL},

	{NULL} /* Sentinel */
};

static PyTypeObject eTimerPyType = {
	PyVarObject_HEAD_INIT(NULL, 0)
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
	Py_TYPE(self)->tp_free((PyObject*)self);
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
	{(char*)"callback",
	 (getter)eSocketNotifierPy_get_cb_list, (setter)0,
	 (char*)"returns the callback python list",
	 NULL},
	{NULL} /* Sentinel */
};

static PyTypeObject eSocketNotifierPyType = {
	PyVarObject_HEAD_INIT(NULL, 0)
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

static PyMethodDef base_module_methods[] = {
	{NULL}  /* Sentinel */
};

void eBaseInit(void)
{
	PyObject* m = Py_InitModule3("eBaseImpl", base_module_methods,
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

%}
