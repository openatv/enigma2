#include <lib/python/connections.h>

PSignal::PSignal()
{
}

PSignal::~PSignal()
{
	Py_XDECREF(m_list);
}

void PSignal::callPython(ePyObject tuple)
{
	int size = PyList_Size(m_list);
	int i;
	for (i=0; i<size; ++i)
	{
		ePyObject b = PyList_GET_ITEM(m_list, i);
		ePython::call(b, tuple);
	}
}

PyObject *PSignal::get()
{
	if (!m_list)
	{
		m_list = PyList_New(0);
		Py_INCREF(m_list);
	}
	Py_INCREF(m_list);
	return m_list;
}
