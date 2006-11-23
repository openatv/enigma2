#ifndef __lib_python_python_h
#define __lib_python_python_h

#include <string>
#include <lib/base/object.h>
#include <Python.h>

// useable for debugging python refcounting
#undef Py_DECREF
#undef Py_XDECREF
#undef Py_INCREF
#undef Py_XINCREF
#define Py_XDECREF(obj) Impl_Py_XDECREF(__FILE__, __LINE__, obj)
#define Py_DECREF(obj) Impl_Py_DECREF(__FILE__, __LINE__, obj)
#define Py_XINCREF(obj) Impl_Py_XINCREF(__FILE__, __LINE__, obj)
#define Py_INCREF(obj) Impl_Py_INCREF(__FILE__, __LINE__, obj)

void Impl_Py_DECREF(const char* file, int line, PyObject *obj);

inline void Impl_Py_XDECREF(const char* file, int line, PyObject *obj)
{
	if (obj)
		Impl_Py_DECREF(file, line, obj);
}

void Impl_Py_INCREF(const char* file, int line, PyObject *obj);

inline void Impl_Py_XINCREF(const char* file, int line, PyObject *obj)
{
	if (obj)
		Impl_Py_INCREF(file, line, obj);
}

extern PyObject *New_TestObj();

class TestObj
{
DECLARE_REF(TestObj);
public:
	TestObj();
	~TestObj();
};
TEMPLATE_TYPEDEF(ePtr<TestObj>, TestObjPtr);

#ifndef SWIG
/* class ePyObject
{
	void *m_object;
public:
	ePyObject(void *ptr);
	ePyObject(ePyObject &p);
	ePyObject();
	ePyObject &operator=(ePyObject &p);
	ePyObject &operator=(void *p);
	~ePyObject();
	void *get() { return m_object; }
}; */

class ePython
{
public:
	ePython();
	~ePython();
	int execute(const std::string &pythonfile, const std::string &funcname);
	static int call(PyObject *pFunc, PyObject *args);
	static PyObject *resolve(const std::string &pythonfile, const std::string &funcname);
private:
};
#endif // SWIG

#endif
