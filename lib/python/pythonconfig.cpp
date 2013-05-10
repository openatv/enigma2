#include <lib/python/pythonconfig.h>
#include <lib/python/python.h>

ePyObject ePythonConfigQuery::m_queryFunc;

void ePythonConfigQuery::setQueryFunc(ePyObject queryFunc)
{
	if (m_queryFunc)
		Py_DECREF(m_queryFunc);
	m_queryFunc = queryFunc;
	if (m_queryFunc)
		Py_INCREF(m_queryFunc);
}

RESULT ePythonConfigQuery::getConfigValue(const char *key, std::string &value)
{
	if (key && PyCallable_Check(m_queryFunc))
	{
		ePyObject pArgs = PyTuple_New(1);
		PyTuple_SET_ITEM(pArgs, 0, PyString_FromString(key));
		ePyObject pRet = PyObject_CallObject(m_queryFunc, pArgs);
		Py_DECREF(pArgs);
		if (pRet)
		{
			if (PyString_Check(pRet))
			{
				value.assign(PyString_AS_STRING(pRet));
				Py_DECREF(pRet);
				return 0;
			}
			Py_DECREF(pRet);
		}
	}
	return -1;
}

std::string ePythonConfigQuery::getConfig(const char *key)
{
	std::string value;
	getConfigValue(key, value);
	return value;
}
