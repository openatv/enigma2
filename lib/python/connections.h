#ifndef __lib_python_connections_h
#define __lib_python_connections_h

#include <libsig_comp.h>

#include <lib/python/python.h>
#include <utility>

class PSignal
{
protected:
	ePyObject m_list;
public:
	PSignal();
	~PSignal();
	void callPython(SWIG_PYOBJECT(ePyObject) tuple);
#ifndef SWIG
	PyObject *getSteal(bool clear=false);
#endif
	PyObject *get();
};

inline PyObject *PyFrom(int v)
{
	return PyInt_FromLong(v);
}

inline PyObject *PyFrom(const char *c)
{
	return PyString_FromString(c);
}

inline PyObject *PyFrom(std::pair<const char*, int>& p)
{
	return PyString_FromStringAndSize(p.first, p.second);
}

template <class R>
class PSignal0: public PSignal, public sigc::signal0<R>
{
public:
	R operator()()
	{
		if (m_list)
		{
			PyObject *pArgs = PyTuple_New(0);
			callPython(pArgs);
			Org_Py_DECREF(pArgs);
		}
		return sigc::signal0<R>::operator()();
	}
};

template <class R, class V0>
class PSignal1: public PSignal, public sigc::signal1<R,V0>
{
public:
	R operator()(V0 a0)
	{
		if (m_list)
		{
			PyObject *pArgs = PyTuple_New(1);
			PyTuple_SET_ITEM(pArgs, 0, PyFrom(a0));
			callPython(pArgs);
			Org_Py_DECREF(pArgs);
		}
		return sigc::signal1<R,V0>::operator()(a0);
	}
};

template <class R, class V0, class V1>
class PSignal2: public PSignal, public sigc::signal2<R,V0,V1>
{
public:
	R operator()(V0 a0, V1 a1)
	{
		if (m_list)
		{
			PyObject *pArgs = PyTuple_New(2);
			PyTuple_SET_ITEM(pArgs, 0, PyFrom(a0));
			PyTuple_SET_ITEM(pArgs, 1, PyFrom(a1));
			callPython(pArgs);
			Org_Py_DECREF(pArgs);
		}
		return sigc::signal2<R,V0,V1>::operator()(a0, a1);
	}
};

template <class R, class V0, class V1, class V2>
class PSignal3: public PSignal, public sigc::signal3<R,V0,V1,V2>
{
public:
	R operator()(V0 a0, V1 a1, V2 a2)
	{
		if (m_list)
		{
			PyObject *pArgs = PyTuple_New(3);
			PyTuple_SET_ITEM(pArgs, 0, PyFrom(a0));
			PyTuple_SET_ITEM(pArgs, 1, PyFrom(a1));
			PyTuple_SET_ITEM(pArgs, 2, PyFrom(a2));
			callPython(pArgs);
			Org_Py_DECREF(pArgs);
		}
		return sigc::signal3<R,V0,V1,V2>::operator()(a0, a1, a2);
	}
};

#endif
