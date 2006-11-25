#include <lib/python/connections.h>

PSignal::PSignal()
{
	m_list = PyList_New(0);
	Py_INCREF(m_list);
}

PSignal::~PSignal()
{
	Py_DECREF(m_list);
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
	Py_INCREF(m_list);
	return m_list;
}
