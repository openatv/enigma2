#ifndef __lib_python_python_h
#define __lib_python_python_h

#include <string>
#include <lib/base/object.h>

typedef struct _object PyObject;

// useable for debugging python refcounting

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
