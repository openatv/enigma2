%{
#include <lib/base/console.h>
#include "structmember.h"

extern "C" {

struct eConsolePy
{
	PyObject_HEAD
	eConsoleAppContainer *cont;
	PyObject *in_weakreflist; /* List of weak references */
};

static PyObject *
eConsolePy_dataAvail(eConsolePy *self, void *closure)
{
	return self->cont->dataAvail.get();
}

static PyObject *
eConsolePy_stdoutAvail(eConsolePy *self, void *closure)
{
	return self->cont->stdoutAvail.get();
}

static PyObject *
eConsolePy_stderrAvail(eConsolePy *self, void *closure)
{
	return self->cont->stderrAvail.get();
}

static PyObject *
eConsolePy_dataSent(eConsolePy *self, void *closure)
{
	return self->cont->dataSent.get();
}

static PyObject *
eConsolePy_appClosed(eConsolePy *self, void *closure)
{
	return self->cont->appClosed.get();
}

static PyGetSetDef eConsolePy_getseters[] = {
	{(char*)"dataAvail",
	 (getter)eConsolePy_dataAvail, (setter)0,
	 (char*)"dataAvail callback list",
	 NULL},
	{(char*)"stdoutAvail",
	 (getter)eConsolePy_stdoutAvail, (setter)0,
	 (char*)"stdoutAvail callback list",
	 NULL},
	{(char*)"stderrAvail",
	 (getter)eConsolePy_stderrAvail, (setter)0,
	 (char*)"stderrAvail callback list",
	 NULL},
	{(char*)"dataSent",
	 (getter)eConsolePy_dataSent, (setter)0,
	 (char*)"dataSent callback list",
	 NULL},
	{(char*)"appClosed",
	 (getter)eConsolePy_appClosed, (setter)0,
	 (char*)"appClosed callback list",
	 NULL},
	{NULL} /* Sentinel */
};

static int
eConsolePy_traverse(eConsolePy *self, visitproc visit, void *arg)
{
	PyObject *obj = self->cont->dataAvail.getSteal();
	if (obj) {
		Py_VISIT(obj);
	}
	obj = self->cont->stdoutAvail.getSteal();
	if (obj) {
		Py_VISIT(obj);
	}
	obj = self->cont->stderrAvail.getSteal();
	if (obj) {
		Py_VISIT(obj);
	}
	obj = self->cont->dataSent.getSteal();
	if (obj) {
		Py_VISIT(obj);
	}
	obj = self->cont->appClosed.getSteal();
	if (obj) {
		Py_VISIT(obj);
	}
	return 0;
}

static int
eConsolePy_clear(eConsolePy *self)
{
	PyObject *obj = self->cont->dataAvail.getSteal(true);
	if (obj) {
		Py_CLEAR(obj);
	}
	obj = self->cont->stdoutAvail.getSteal(true);
	if (obj) {
		Py_CLEAR(obj);
	}
	obj = self->cont->stderrAvail.getSteal(true);
	if (obj) {
		Py_CLEAR(obj);
	}
	obj = self->cont->dataSent.getSteal(true);
	if (obj) {
		Py_CLEAR(obj);
	}
	obj = self->cont->appClosed.getSteal(true);
	if (obj) {
		Py_CLEAR(obj);
	}
	return 0;
}

static void
eConsolePy_dealloc(eConsolePy* self)
{
	if (self->in_weakreflist != NULL)
		PyObject_ClearWeakRefs((PyObject *) self);
	eConsolePy_clear(self);
	self->cont->Release();
	self->ob_type->tp_free((PyObject*)self);
}

static PyObject *
eConsolePy_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
	eConsolePy *self = (eConsolePy *)type->tp_alloc(type, 0);
	self->cont = new eConsoleAppContainer();
	self->cont->AddRef();
	self->in_weakreflist = NULL;
	return (PyObject *)self;
}

static PyObject *
eConsolePy_running(eConsolePy* self)
{
	PyObject *ret = NULL;
	ret = self->cont->running() ? Py_True : Py_False;
	Org_Py_INCREF(ret);
	return ret;
}

static PyObject *
eConsolePy_execute(eConsolePy* self, PyObject *argt)
{
	Py_ssize_t argc = PyTuple_Size(argt);
	if (argc > 1)
	{
		const char *argv[argc + 1];
		int argpos=0;
		while(argpos < argc)
		{
			PyObject *arg = PyTuple_GET_ITEM(argt, argpos);
			if (!PyString_Check(arg))
			{
				char err[255];
				if (argpos)
					snprintf(err, 255, "arg %d is not a string", argpos);
				else
					snprintf(err, 255, "cmd is not a string!");
				PyErr_SetString(PyExc_TypeError, err);
				return NULL;
			}
			argv[argpos++] = PyString_AsString(arg);
		}
		argv[argpos] = 0;
		return PyInt_FromLong(self->cont->execute(argv[0], argv+1));
	}
	else
	{
		const char *str;
		if (PyArg_ParseTuple(argt, "s", &str))
			return PyInt_FromLong(self->cont->execute(str));
		PyErr_SetString(PyExc_TypeError,
			"cmd is not a string!");
	}
	return NULL;
}

static PyObject *
eConsolePy_write(eConsolePy* self, PyObject *args)
{
	char *data;
	int data_len;
	int len = -1;
	if (!PyArg_ParseTuple(args, "s#|i", &data, &data_len, &len))
	{
		PyErr_SetString(PyExc_TypeError,
			"1st arg must be a string, optionaly 2nd arg can be the string length");
		return NULL;
	}
	if (len < 0)
		len = data_len;	
	self->cont->write(data, len);
	Py_RETURN_NONE;
}

static PyObject *
eConsolePy_getPID(eConsolePy* self)
{
	return PyInt_FromLong(self->cont->getPID());
}

static PyObject *
eConsolePy_setCWD(eConsolePy* self, PyObject *args)
{
	const char *path=0;
	if (!PyArg_ParseTuple(args, "s", &path))
		return NULL;
	self->cont->setCWD(path);
	Py_RETURN_NONE;
}

static PyObject *
eConsolePy_setBufferSize(eConsolePy* self, PyObject *args)
{
	int size = 0;
	if (!PyArg_ParseTuple(args, "i", &size))
		return NULL;
	self->cont->setBufferSize(size);
	Py_RETURN_NONE;
}

static PyObject *
eConsolePy_kill(eConsolePy* self)
{
	self->cont->kill();
	Py_RETURN_NONE;
}

static PyObject *
eConsolePy_sendCtrlC(eConsolePy* self)
{
	self->cont->sendCtrlC();
	Py_RETURN_NONE;
}

static PyObject *
eConsolePy_sendEOF(eConsolePy* self)
{
	self->cont->sendEOF();
	Py_RETURN_NONE;
}

static PyObject *
eConsolePy_dumpToFile(eConsolePy* self, PyObject *args)
{
	char *filename;
	if (!PyArg_ParseTuple(args, "s", &filename))
	{
		PyErr_SetString(PyExc_TypeError,
			"arg must be a string (filename)");
		return NULL;
	}
	else
	{
		int fd = open(filename, O_WRONLY|O_CREAT|O_TRUNC, 0644);
		self->cont->setFileFD(1, fd);
		eDebug("eConsoleAppContainer::dumpToFile open(%s, O_WRONLY|O_CREAT|O_TRUNC, 0644)=%d", filename, fd);
	}
	Py_RETURN_NONE;
}

static PyObject *
eConsolePy_readFromFile(eConsolePy* self, PyObject *args)
{
	char *filename;
	if (!PyArg_ParseTuple(args, "s", &filename))
	{
		PyErr_SetString(PyExc_TypeError,
			"arg must be a string (filename)");
		return NULL;
	}
	else
	{
		int fd = open(filename, O_RDONLY);
		if (fd >= 0)
		{
			char readbuf[32*1024];
			int rsize = read(fd, readbuf, 32*1024);
			self->cont->setFileFD(0, fd);
			eDebug("eConsoleAppContainer::readFromFile open(%s, O_RDONLY)=%d, read: %d", filename, fd, rsize);
			self->cont->write(readbuf, rsize);
		}
		else
		{
			eDebug("eConsoleAppContainer::readFromFile %s not exist!", filename);
			self->cont->setFileFD(0, -1);
		}
	}
	Py_RETURN_NONE;
}

static PyMethodDef eConsolePy_methods[] = {
	{(char*)"setCWD", (PyCFunction)eConsolePy_setCWD, METH_VARARGS,
	 (char*)"set working dir"
	},
	{(char*)"setBufferSize", (PyCFunction)eConsolePy_setBufferSize, METH_VARARGS,
	 (char*)"set transfer buffer size"
	},
	{(char*)"execute", (PyCFunction)eConsolePy_execute, METH_VARARGS,
	 (char*)"execute command"
	},
	{(char*)"dumpToFile", (PyCFunction)eConsolePy_dumpToFile, METH_VARARGS,
	 (char*)"set output file"
	},
	{(char*)"readFromFile", (PyCFunction)eConsolePy_readFromFile, METH_VARARGS,
	 (char*)"set input file"
	},
	{(char*)"getPID", (PyCFunction)eConsolePy_getPID, METH_NOARGS,
	 (char*)"execute command"
	},
	{(char*)"kill", (PyCFunction)eConsolePy_kill, METH_NOARGS,
	 (char*)"kill application"
	},
	{(char*)"sendCtrlC", (PyCFunction)eConsolePy_sendCtrlC, METH_NOARGS,
	 (char*)"send Ctrl-C to application"
	},
	{(char*)"sendEOF", (PyCFunction)eConsolePy_sendEOF, METH_NOARGS,
	 (char*)"send EOF to application"
	},
	{(char*)"write", (PyCFunction)eConsolePy_write, METH_VARARGS,
	 (char*)"write data to application"
	},
	{(char*)"running", (PyCFunction)eConsolePy_running, METH_NOARGS,
	 (char*)"returns the running state"
	},
	{NULL}  /* Sentinel */
};

static PyTypeObject eConsolePyType = {
	PyObject_HEAD_INIT(NULL)
	0, /*ob_size*/
	"eConsoleImpl.eConsoleAppContainer", /*tp_name*/
	sizeof(eConsolePy), /*tp_basicsize*/
	0, /*tp_itemsize*/
	(destructor)eConsolePy_dealloc, /*tp_dealloc*/
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
	"eConsoleAppContainer objects", /* tp_doc */
	(traverseproc)eConsolePy_traverse, /* tp_traverse */
	(inquiry)eConsolePy_clear, /* tp_clear */
	0, /* tp_richcompare */
	offsetof(eConsolePy, in_weakreflist), /* tp_weaklistoffset */
	0, /* tp_iter */
	0, /* tp_iternext */
	eConsolePy_methods, /* tp_methods */
	0, /* tp_members */
	eConsolePy_getseters, /* tp_getset */
	0, /* tp_base */
	0, /* tp_dict */
	0, /* tp_descr_get */
	0, /* tp_descr_set */
	0, /* tp_dictoffset */
	0, /* tp_init */
	0, /* tp_alloc */
	eConsolePy_new, /* tp_new */
};

static PyMethodDef console_module_methods[] = {
	{NULL}  /* Sentinel */
};

void eConsoleInit(void)
{
	PyObject* m = Py_InitModule3("eConsoleImpl", console_module_methods,
		"Module that implements eConsoleAppContainer with working cyclic garbage collection.");

	if (m == NULL)
		return;

	if (!PyType_Ready(&eConsolePyType))
	{
		Org_Py_INCREF((PyObject*)&eConsolePyType);
		PyModule_AddObject(m, "eConsoleAppContainer", (PyObject*)&eConsolePyType);
	}
}
}
%}
