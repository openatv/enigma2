#ifndef __lib_python_connections_h
#define __lib_python_connections_h

#include <libsig_comp.h>

		/* avoid warnigs :) */
#include <features.h>
#undef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200112L
#include <lib/python/python.h>

class PSignal
{
public:
	PyObject *m_list;
public:
	PSignal()
	{
		m_list = PyList_New(0);
		Py_INCREF(m_list);
	}
	~PSignal()
	{
		Py_DECREF(m_list);
	}
	
	void callPython(PyObject *tuple)
	{
		int size = PyList_Size(m_list);
		int i;
		for (i=0; i<size; ++i)
		{
			PyObject *b = PyList_GET_ITEM(m_list, i);
			ePython::call(b, tuple);
		}
	}
	
	
	PyObject *get() { Py_INCREF(m_list); return m_list; }
};

inline PyObject *PyFrom(int v)
{
	return PyInt_FromLong(v);
}

inline PyObject *PyFrom(const char *c)
{
	return PyString_FromString(c);
}

template <class R>
class PSignal0: public PSignal, public Signal0<R>
{
public:
	R operator()()
	{
		PyObject *pArgs = PyTuple_New(0);
		callPython(pArgs);
		Py_DECREF(pArgs);
		return Signal0<R>::operator()();
	}
};

template <class R, class V0>
class PSignal1: public PSignal, public Signal1<R,V0>
{
public:
	R operator()(V0 a0)
	{
		PyObject *pArgs = PyTuple_New(1);
		PyTuple_SET_ITEM(pArgs, 0, PyFrom(a0));
		callPython(pArgs);
		Py_DECREF(pArgs);
		return Signal1<R,V0>::operator()(a0);
	}
};

template <class R, class V0, class V1>
class PSignal2: public PSignal, public Signal2<R,V0,V1>
{
public:
	R operator()(V0 a0, V1 a1)
	{
		PyObject *pArgs = PyTuple_New(2);
		PyTuple_SET_ITEM(pArgs, 0, PyFrom(a0));
		PyTuple_SET_ITEM(pArgs, 1, PyFrom(a1));
		callPython(pArgs);
		Py_DECREF(pArgs);
		return Signal2<R,V0,V1>::operator()(a0, a1);
	}
};

#endif
