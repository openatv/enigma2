#include <lib/base/console.h>
#include <lib/base/eerror.h>
#include <sys/vfs.h> // for statfs
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <poll.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <fcntl.h>

int bidirpipe(int pfd[], const char *cmd , const char * const argv[], const char *cwd )
{
	int pfdin[2];  /* from child to parent */
	int pfdout[2]; /* from parent to child */
	int pfderr[2]; /* stderr from child to parent */
	int pid;       /* child's pid */

	if ( pipe(pfdin) == -1 || pipe(pfdout) == -1 || pipe(pfderr) == -1)
		return(-1);

	if ( ( pid = vfork() ) == -1 )
		return(-1);
	else if (pid == 0) /* child process */
	{
		setsid();
		if ( close(0) == -1 || close(1) == -1 || close(2) == -1 )
			_exit(0);

		if (dup(pfdout[0]) != 0 || dup(pfdin[1]) != 1 || dup(pfderr[1]) != 2 )
			_exit(0);

		if (close(pfdout[0]) == -1 || close(pfdout[1]) == -1 ||
				close(pfdin[0]) == -1 || close(pfdin[1]) == -1 ||
				close(pfderr[0]) == -1 || close(pfderr[1]) == -1 )
			_exit(0);

		for (unsigned int i=3; i < 90; ++i )
			close(i);

		if (cwd)
			chdir(cwd);

		execvp(cmd, (char * const *)argv); 
				/* the vfork will actually suspend the parent thread until execvp is called. thus it's ok to use the shared arg/cmdline pointers here. */
		_exit(0);
	}
	if (close(pfdout[0]) == -1 || close(pfdin[1]) == -1 || close(pfderr[1]) == -1)
			return(-1);

	pfd[0] = pfdin[0];
	pfd[1] = pfdout[1];
	pfd[2] = pfderr[0];

	return(pid);
}

DEFINE_REF(eConsoleAppContainer);

eConsoleAppContainer::eConsoleAppContainer()
:pid(-1), killstate(0)
{
	for (int i=0; i < 3; ++i)
	{
		fd[i]=-1;
		filefd[i]=-1;
	}
}

int eConsoleAppContainer::setCWD( const char *path )
{
	struct stat dir_stat;

	if (stat(path, &dir_stat) == -1)
		return -1;

	if (!S_ISDIR(dir_stat.st_mode))
		return -2;

	m_cwd = path;
	return 0;
}

int eConsoleAppContainer::execute( const char *cmd )
{
	int argc = 3;
	const char *argv[argc + 1];
	argv[0] = "/bin/sh";
	argv[1] = "-c";
	argv[2] = cmd;
	argv[argc] = NULL;

	return execute(argv[0], argv);
}

int eConsoleAppContainer::execute(const char *cmdline, const char * const argv[])
{
	if (running())
		return -1;

	pid=-1;
	killstate=0;

	// get one read ,one write and the err pipe to the prog..
	pid = bidirpipe(fd, cmdline, argv, m_cwd.length() ? m_cwd.c_str() : 0);

	if ( pid == -1 )
		return -3;

//	eDebug("pipe in = %d, out = %d, err = %d", fd[0], fd[1], fd[2]);

	::fcntl(fd[0], F_SETFL, O_NONBLOCK);
	::fcntl(fd[1], F_SETFL, O_NONBLOCK);
	::fcntl(fd[2], F_SETFL, O_NONBLOCK);
	in = eSocketNotifier::create(eApp, fd[0], eSocketNotifier::Read|eSocketNotifier::Priority|eSocketNotifier::Hungup );
	out = eSocketNotifier::create(eApp, fd[1], eSocketNotifier::Write, false);  
	err = eSocketNotifier::create(eApp, fd[2], eSocketNotifier::Read|eSocketNotifier::Priority );
	CONNECT(in->activated, eConsoleAppContainer::readyRead);
	CONNECT(out->activated, eConsoleAppContainer::readyWrite);
	CONNECT(err->activated, eConsoleAppContainer::readyErrRead);
	in->m_clients.push_back(this);
	out->m_clients.push_back(this);
	err->m_clients.push_back(this);

	return 0;
}

eConsoleAppContainer::~eConsoleAppContainer()
{
	kill();
}

void eConsoleAppContainer::kill()
{
	if ( killstate != -1 && pid != -1 )
	{
		eDebug("user kill(SIGKILL) console App");
		killstate=-1;
		/*
		 * Use a negative pid value, to signal the whole process group
		 * ('pid' might not even be running anymore at this point)
		 */
		::kill(-pid, SIGKILL);
		closePipes();
	}
	while( outbuf.size() ) // cleanup out buffer
	{
		queue_data d = outbuf.front();
		outbuf.pop();
		delete [] d.data;
	}
	in = 0;
	out = 0;
	err = 0;

	for (int i=0; i < 3; ++i)
	{
		if ( filefd[i] > 0 )
			close(filefd[i]);
	}
}

void eConsoleAppContainer::sendCtrlC()
{
	if ( killstate != -1 && pid != -1 )
	{
		eDebug("user send SIGINT(Ctrl-C) to console App");
		/*
		 * Use a negative pid value, to signal the whole process group
		 * ('pid' might not even be running anymore at this point)
		 */
		::kill(-pid, SIGINT);
	}
}

void eConsoleAppContainer::sendEOF()
{
	if (out)
		out->stop();
	if (fd[1] != -1)
	{
		::close(fd[1]);
		fd[1]=-1;
	}
}

void eConsoleAppContainer::closePipes()
{
	if (in)
		in->stop();
	if (out)
		out->stop();
	if (err)
		err->stop();
	if (fd[0] != -1)
	{
		::close(fd[0]);
		fd[0]=-1;
	}
	if (fd[1] != -1)
	{
		::close(fd[1]);
		fd[1]=-1;
	}
	if (fd[2] != -1)
	{
		::close(fd[2]);
		fd[2]=-1;
	}
	eDebug("pipes closed");
	while( outbuf.size() ) // cleanup out buffer
	{
		queue_data d = outbuf.front();
		outbuf.pop();
		delete [] d.data;
	}
	in = 0; out = 0; err = 0;
	pid = -1;
}

void eConsoleAppContainer::readyRead(int what)
{
	bool hungup = what & eSocketNotifier::Hungup;
	if (what & (eSocketNotifier::Priority|eSocketNotifier::Read))
	{
//		eDebug("what = %d");
		char buf[2049];
		int rd;
		while((rd = read(fd[0], buf, 2048)) > 0)
		{
			buf[rd]=0;
			/*emit*/ dataAvail(buf);
			stdoutAvail(buf);
			if ( filefd[1] > 0 )
				::write(filefd[1], buf, rd);
			if (!hungup)
				break;
		}
	}
	readyErrRead(eSocketNotifier::Priority|eSocketNotifier::Read); /* be sure to flush all data which might be already written */
	if (hungup)
	{
		eDebug("child has terminated");
		closePipes();
		int childstatus;
		int retval = killstate;
		/*
		 * We have to call 'wait' on the child process, in order to avoid zombies.
		 * Also, this gives us the chance to provide better exit status info to appClosed.
		 */
		if (::waitpid(pid, &childstatus, 0) > 0)
		{
			if (WIFEXITED(childstatus))
			{
				retval = WEXITSTATUS(childstatus);
			}
		}
		/*emit*/ appClosed(retval);
	}
}

void eConsoleAppContainer::readyErrRead(int what)
{
	if (what & (eSocketNotifier::Priority|eSocketNotifier::Read))
	{
//		eDebug("what = %d");
		char buf[2049];
		int rd;
		while((rd = read(fd[2], buf, 2048)) > 0)
		{
/*			for ( int i = 0; i < rd; i++ )
				eDebug("%d = %c (%02x)", i, buf[i], buf[i] );*/
			buf[rd]=0;
			/*emit*/ dataAvail(buf);
			stderrAvail(buf);
		}
	}
}

void eConsoleAppContainer::write( const char *data, int len )
{
	char *tmp = new char[len];
	memcpy(tmp, data, len);
	outbuf.push(queue_data(tmp,len));
	if (out)
		out->start();
}

void eConsoleAppContainer::readyWrite(int what)
{
	if (what&eSocketNotifier::Write && outbuf.size() )
	{
		queue_data &d = outbuf.front();
		int wr = ::write( fd[1], d.data+d.dataSent, d.len-d.dataSent );
		if (wr < 0)
			eDebug("eConsoleAppContainer write failed (%m)");
		else
			d.dataSent += wr;
		if (d.dataSent == d.len)
		{
			outbuf.pop();
			delete [] d.data;
			if ( filefd[0] == -1 )
			/* emit */ dataSent(0);
		}
	}
	if ( !outbuf.size() )
	{
		if ( filefd[0] > 0 )
		{
			char readbuf[32*1024];
			int rsize = read(filefd[0], readbuf, 32*1024);
			if ( rsize > 0 )
				write(readbuf, rsize);
			else
			{
				close(filefd[0]);
				filefd[0] = -1;
				::close(fd[1]);
				eDebug("readFromFile done - closing eConsoleAppContainer stdin pipe");
				fd[1]=-1;
				dataSent(0);
				out->stop();
			}
		}
		else
			out->stop();
	}
}

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
	{"dataAvail",
	 (getter)eConsolePy_dataAvail, (setter)0,
	 "dataAvail callback list",
	 NULL},
	{"stdoutAvail",
	 (getter)eConsolePy_stdoutAvail, (setter)0,
	 "stdoutAvail callback list",
	 NULL},
	{"stderrAvail",
	 (getter)eConsolePy_stderrAvail, (setter)0,
	 "stderrAvail callback list",
	 NULL},
	{"dataSent",
	 (getter)eConsolePy_dataSent, (setter)0,
	 "dataSent callback list",
	 NULL},
	{"appClosed",
	 (getter)eConsolePy_appClosed, (setter)0,
	 "appClosed callback list",
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
	int len;
	char *data;
	int ret = -1;
	Py_ssize_t argc = PyTuple_Size(args);
	if (argc > 1)
		ret = !PyArg_ParseTuple(args, "si", &data, &len);
	else if (argc == 1)
	{
		PyObject *ob;
		ret = !PyArg_ParseTuple(args, "O", &ob) || !PyString_Check(ob);
		if (!ret)
		{
			Py_ssize_t length;
			if (!PyString_AsStringAndSize(ob, &data, &length))
				len = length;
			else
				len = 0;
		}
	}
	if (ret)
	{
		PyErr_SetString(PyExc_TypeError,
			"1st arg must be a string, optionaly 2nd arg can be the string length");
		return NULL;
	}
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
	{"setCWD", (PyCFunction)eConsolePy_setCWD, METH_VARARGS,
	 "set working dir"
	},
	{"execute", (PyCFunction)eConsolePy_execute, METH_VARARGS,
	 "execute command"
	},
	{"dumpToFile", (PyCFunction)eConsolePy_dumpToFile, METH_VARARGS,
	 "set output file"
	},
	{"readFromFile", (PyCFunction)eConsolePy_readFromFile, METH_VARARGS,
	 "set input file"
	},
	{"getPID", (PyCFunction)eConsolePy_getPID, METH_NOARGS,
	 "execute command"
	},
	{"kill", (PyCFunction)eConsolePy_kill, METH_NOARGS,
	 "kill application"
	},
	{"sendCtrlC", (PyCFunction)eConsolePy_sendCtrlC, METH_NOARGS,
	 "send Ctrl-C to application"
	},
	{"sendEOF", (PyCFunction)eConsolePy_sendEOF, METH_NOARGS,
	 "send EOF to application"
	},
	{"write", (PyCFunction)eConsolePy_write, METH_VARARGS,
	 "write data to application"
	},
	{"running", (PyCFunction)eConsolePy_running, METH_NOARGS,
	 "returns the running state"
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

static PyMethodDef module_methods[] = {
	{NULL}  /* Sentinel */
};

void eConsoleInit(void)
{
	PyObject* m = Py_InitModule3("eConsoleImpl", module_methods,
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
