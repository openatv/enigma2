#include <lib/python/python.h>
#include <Python.h>

extern "C" void init_enigma();

ePython::ePython()
{
	Py_Initialize();
	
	init_enigma();
}

ePython::~ePython()
{
	Py_Finalize();
}

int ePython::execute(const std::string &pythonfile, const std::string &funcname)
{
	PyObject *pName, *pModule, *pDict, *pFunc, *pArgs, *pValue;
	
	pName = PyString_FromString(pythonfile.c_str());
	
	pModule = PyImport_Import(pName);
	Py_DECREF(pName);
	
	if (pModule != NULL)
	{
		pDict = PyModule_GetDict(pModule);
		
		pFunc = PyDict_GetItemString(pDict, funcname.c_str());
		
		if (pFunc && PyCallable_Check(pFunc))
		{
			pArgs = PyTuple_New(0);
				// implement arguments..
			pValue = PyObject_CallObject(pFunc, pArgs);
			Py_DECREF(pArgs);
			if (pValue != NULL)
			{
				printf("Result of call: %ld\n", PyInt_AsLong(pValue));
				Py_DECREF(pValue);
			} else
			{
				Py_DECREF(pModule);
				PyErr_Print();
				return 1;
			}
		}
	} else
	{
		if (PyErr_Occurred())
			PyErr_Print();
		return 1;
	}
	return 0;
}
