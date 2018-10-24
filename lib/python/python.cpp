#include <lib/base/eerror.h>
                /* avoid warnigs :) */
#undef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200112L
extern "C" void init_enigma();
extern "C" void eBaseInit(void);
extern "C" void eConsoleInit(void);
extern void quitMainloop(int exitCode);
extern void bsodFatal(const char *component);
extern bool bsodRestart();

#define SKIP_PART2
#include <lib/python/python.h>
#undef SKIP_PART2

#ifdef PYTHON_REFCOUNT_DEBUG
ePyObject &ePyObject::operator=(PyObject *ob)
{
	m_ob=ob;
	m_file=0;
	m_line=0;
	m_from=m_to=0;
	m_erased=false;
	return *this;
}

ePyObject &ePyObject::operator=(const ePyObject &ob)
{
	m_ob=ob.m_ob;
	m_file=ob.m_file;
	m_line=ob.m_line;
	m_from=ob.m_from;
	m_to=ob.m_to;
	m_erased=ob.m_erased;
	return *this;
}

ePyObject::operator PyObject*()
{
	if (m_ob)
	{
		if (!m_erased && m_ob->ob_refcnt > 0)
			return m_ob;
		eDebug("[ePyObject] invalid access PyObject %s with refcount <= 0 %d",
			m_erased ? "deleted" : "undeleted", m_ob->ob_refcnt);
		if (m_file)
			eDebug("[ePyObject] last modified in file %s line %d from %d to %d",
				m_file, m_line, m_from, m_to);
		bsodFatal("enigma2, refcnt");
	}
	return 0;
}

void ePyObject::incref(const char *file, int line)
{
	if (!m_ob)
	{
		eDebug("[ePyObject] invalid incref python object with null pointer %s %d!!!", file, line);
		if (m_file)
			eDebug("[ePyObject] last modified in file %s line %d from %d to %d",
				m_file, m_line, m_from, m_to);
		bsodFatal("enigma2, refcnt");
	}
	if (m_erased || m_ob->ob_refcnt <= 0)
	{
		eDebug("[ePyObject] invalid incref %s python object with refcounting value %d in file %s line %d!!!",
			m_erased ? "deleted" : "undeleted", m_ob->ob_refcnt, file, line);
		if (m_file)
			eDebug("[ePyObject] last modified in file %s line %d from %d to %d",
				m_file, m_line, m_from, m_to);
		bsodFatal("enigma2, refcnt");
	}
	if (m_ob->ob_refcnt == 0x7FFFFFFF)
	{
		eDebug("[ePyObject] invalid incref %s python object with refcounting value %d (MAX_INT!!!) in file %s line %d!!!",
			m_erased ? "deleted" : "undeleted", m_ob->ob_refcnt, file, line);
		if (m_file)
			eDebug("[ePyObject] last modified in file %s line %d from %d to %d",
				m_file, m_line, m_from, m_to);
		bsodFatal("enigma2, refcnt");
	}
	m_file = file;
	m_line = line;
	m_from = m_ob->ob_refcnt;
	m_to = m_from+1;
	Py_INCREF(m_ob);
}

void ePyObject::decref(const char *file, int line)
{
	if (!m_ob)
	{
		eDebug("[ePyObject] invalid decref python object with null pointer %s %d!!!", file, line);
		if (m_file)
			eDebug("[ePyObject] last modified in file %s line %d from %d to %d",
				m_file, m_line, m_from, m_to);
		bsodFatal("enigma2, refcnt");
	}
	if (m_erased || m_ob->ob_refcnt <= 0)
	{
		eDebug("[ePyObject] invalid decref %s python object with refcounting value %d in file %s line %d!!!",
			m_erased ? "deleted" : "undeleted", m_ob->ob_refcnt, file, line);
		if (m_file)
			eDebug("[ePyObject] last modified in file %s line %d from %d to %d",
				m_file, m_line, m_from, m_to);
		bsodFatal("enigma2, refcnt");
	}
	m_file = file;
	m_line = line;
	m_from = m_ob->ob_refcnt;
	m_to = m_from-1;
	m_erased = !m_to;
	Py_DECREF(m_ob);
}
#endif  // PYTHON_REFCOUNT_DEBUG

#define SKIP_PART1
#include <lib/python/python.h>
#undef SKIP_PART1

ePython::ePython()
{
//	Py_VerboseFlag = 1;

//	Py_OptimizeFlag = 1;

	Py_Initialize();
	PyEval_InitThreads();

	init_enigma();
	eBaseInit();
	eConsoleInit();
}

ePython::~ePython()
{
// This appears to hang, sorry.
//	Py_Finalize();
}

int ePython::execFile(const char *file)
{
	FILE *fp = fopen(file, "r");
	if (!fp)
		return -ENOENT;
	int ret = PyRun_SimpleFile(fp, file);
	fclose(fp);
	return ret;
}

int ePython::execute(const std::string &pythonfile, const std::string &funcname)
{
	ePyObject pName, pModule, pDict, pFunc, pArgs, pValue;
	pName = PyString_FromString(pythonfile.c_str());

	pModule = PyImport_Import(pName);
	Py_DECREF(pName);

	if (pModule)
	{
		pDict = PyModule_GetDict(pModule);

		pFunc = PyDict_GetItemString(pDict, funcname.c_str());

		if (pFunc && PyCallable_Check(pFunc))
		{
			pArgs = PyTuple_New(0);
				// implement arguments..
			pValue = PyObject_CallObject(pFunc, pArgs);
			Py_DECREF(pArgs);
			if (pValue)
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

int ePython::call(ePyObject pFunc, ePyObject pArgs)
{
	int res = -1;
	ePyObject pValue;
	if (pFunc && PyCallable_Check(pFunc))
	{
		pValue = PyObject_CallObject(pFunc, pArgs);
 		if (pValue)
		{
			if (PyInt_Check(pValue))
				res = PyInt_AsLong(pValue);
			else
				res = 0;
			Py_DECREF(pValue);
		} else
		{
		 	PyErr_Print();
			ePyObject FuncStr = PyObject_Str(pFunc);
			ePyObject ArgStr = PyObject_Str(pArgs);
		 	eDebug("[ePyObject] (PyObject_CallObject(%s,%s) failed)", PyString_AS_STRING(FuncStr), PyString_AS_STRING(ArgStr));
			Py_DECREF(FuncStr);
			Py_DECREF(ArgStr);
			/* immediately show BSOD, so we have the actual error at the bottom */
		 	bsodFatal(0);
			/* and make sure we quit (which would also eventually cause a bsod, but with useless termination messages) */
			if (bsodRestart())
				quitMainloop(5);
		}
	}
	return res;
}

ePyObject ePython::resolve(const std::string &pythonfile, const std::string &funcname)
{
	ePyObject pName, pModule, pDict, pFunc;

	pName = PyString_FromString(pythonfile.c_str());

	pModule = PyImport_Import(pName);
	Py_DECREF(pName);

	if (pModule)
	{
		pDict = PyModule_GetDict(pModule);
		pFunc = PyDict_GetItemString(pDict, funcname.c_str());
		Py_XINCREF(pFunc);
		Py_DECREF(pModule);
	} else if (PyErr_Occurred())
		PyErr_Print();
	return pFunc;
}
