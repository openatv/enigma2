#ifndef __lib_python_python_h
#define __lib_python_python_h

#include <string>

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

typedef struct _object PyObject;

class ePython
{
public:
	ePython();
	~ePython();
	int execute(const std::string &pythonfile, const std::string &funcname);
	static void call(PyObject *pFunc, PyObject *args);
	static PyObject *resolve(const std::string &pythonfile, const std::string &funcname);
private:
};

#endif
