#ifndef __lib_python_python_class_h

#ifndef SKIP_PART2
	#define __lib_python_python_class_h
#endif

#include <string>
#include <lib/base/object.h>
#include <Python.h>

#define PYTHON_REFCOUNT_DEBUG

#if !defined(SKIP_PART1) && !defined(SWIG)
class ePyObject
{
	PyObject *m_ob;
#ifdef PYTHON_REFCOUNT_DEBUG
	const char *m_file;
	int m_line, m_from, m_to;
	bool m_erased;
#endif
public:
	inline ePyObject();
	inline ePyObject(const ePyObject &ob);
	inline ePyObject(PyObject *ob);
	inline ePyObject(PyDictObject *ob);
	inline ePyObject(PyTupleObject *ob);
	inline ePyObject(PyListObject *ob);
	inline ePyObject(PyStringObject *ob);
	operator bool() { return !!m_ob; }
	ePyObject &operator=(const ePyObject &);
	ePyObject &operator=(PyObject *);
	ePyObject &operator=(PyDictObject *ob) { return operator=((PyObject*)ob); }
	ePyObject &operator=(PyTupleObject *ob) { return operator=((PyObject*)ob); }
	ePyObject &operator=(PyListObject *ob) { return operator=((PyObject*)ob); }
	ePyObject &operator=(PyStringObject *ob) { return operator=((PyObject*)ob); }
	operator PyObject*();
	operator PyTupleObject*() { return (PyTupleObject*)operator PyObject*(); }
	operator PyListObject*() { return (PyListObject*)operator PyObject*(); }
	operator PyStringObject*() { return (PyStringObject*)operator PyObject*(); }
	operator PyDictObject*() { return (PyDictObject*)operator PyObject*(); }
	PyObject *operator->() { return operator PyObject*(); }
#ifdef PYTHON_REFCOUNT_DEBUG
	void incref(const char *file, int line);
	void decref(const char *file, int line);
#else
	void incref();
	void decref();
#endif
};

inline ePyObject::ePyObject()
	:m_ob(0)
#ifdef PYTHON_REFCOUNT_DEBUG
	,m_file(0), m_line(0), m_from(0), m_to(0), m_erased(false)
#endif
{
}

inline ePyObject::ePyObject(const ePyObject &ob)
	:m_ob(ob.m_ob)
#ifdef PYTHON_REFCOUNT_DEBUG
	,m_file(ob.m_file), m_line(ob.m_line)
	,m_from(ob.m_from), m_to(ob.m_to), m_erased(ob.m_erased)
#endif
{
}

inline ePyObject::ePyObject(PyObject *ob)
	:m_ob(ob)
#ifdef PYTHON_REFCOUNT_DEBUG
	,m_file(0), m_line(0), m_from(0), m_to(0), m_erased(false)
#endif
{
}

inline ePyObject::ePyObject(PyDictObject *ob)
	:m_ob((PyObject*)ob)
#ifdef PYTHON_REFCOUNT_DEBUG
	,m_file(0), m_line(0), m_from(0), m_to(0), m_erased(false)
#endif
{
}

inline ePyObject::ePyObject(PyTupleObject *ob)
	:m_ob((PyObject*)ob)
#ifdef PYTHON_REFCOUNT_DEBUG
	,m_file(0), m_line(0), m_from(0), m_to(0), m_erased(false)
#endif
{
}

inline ePyObject::ePyObject(PyListObject *ob)
	:m_ob((PyObject*)ob)
#ifdef PYTHON_REFCOUNT_DEBUG
	,m_file(0), m_line(0), m_from(0), m_to(0), m_erased(false)
#endif
{
}

inline ePyObject::ePyObject(PyStringObject *ob)
	:m_ob((PyObject*)ob)
#ifdef PYTHON_REFCOUNT_DEBUG
	,m_file(0), m_line(0), m_from(0), m_to(0), m_erased(false)
#endif
{
}

#ifndef PYTHON_REFCOUNT_DEBUG
inline ePyObject &ePyObject::operator=(PyObject *ob)
{
	m_ob=ob;
	return *this;
}

inline ePyObject &ePyObject::operator=(const ePyObject &ob)
{
	m_ob=ob.m_ob;
	return *this;
}

inline ePyObject::operator PyObject*()
{
	return m_ob;
}

inline void ePyObject::incref()
{
	Py_INCREF(m_ob);
}

inline void ePyObject::decref()
{
	Py_DECREF(m_ob);
}

#endif // ! PYTHON_REFCOUNT_DEBUG

#endif  // !SWIG && !SKIP_PART1

#ifndef SKIP_PART2

class TestObj
{
DECLARE_REF(TestObj);
public:
	TestObj();
	~TestObj();
};
TEMPLATE_TYPEDEF(ePtr<TestObj>, TestObjPtr);

extern PyObject *New_TestObj();

#ifndef SWIG

#ifdef PYTHON_REFCOUNT_DEBUG
inline void Impl_Py_DECREF(const char* file, int line, const ePyObject &obj)
{
	((ePyObject*)(&obj))->decref(file, line);
}

inline void Impl_Py_INCREF(const char* file, int line, const ePyObject &obj)
{
	((ePyObject*)(&obj))->incref(file, line);
}

inline void Impl_Py_XDECREF(const char* file, int line, const ePyObject &obj)
{
	if (obj)
		((ePyObject*)(&obj))->decref(file, line);
}

inline void Impl_Py_XINCREF(const char* file, int line, const ePyObject &obj)
{
	if (obj)
		((ePyObject*)(&obj))->incref(file, line);
}
#else
inline void Impl_Py_DECREF(const ePyObject &obj)
{
	((ePyObject*)(&obj))->decref();
}

inline void Impl_Py_INCREF(const ePyObject &obj)
{
	((ePyObject*)(&obj))->incref();
}

inline void Impl_Py_XDECREF(const ePyObject &obj)
{
	if (obj)
		((ePyObject*)(&obj))->decref();
}

inline void Impl_Py_XINCREF(const ePyObject &obj)
{
	if (obj)
		((ePyObject*)(&obj))->incref();
}
#endif

inline void Impl_DECREF(PyObject *ob)
{
	Py_DECREF(ob);
}
#define Org_Py_DECREF(obj) Impl_DECREF(obj)
#undef Py_DECREF
#undef Py_XDECREF
#undef Py_INCREF
#undef Py_XINCREF
#ifdef PYTHON_REFCOUNT_DEBUG
#define Py_DECREF(obj) Impl_Py_DECREF(__FILE__, __LINE__, obj)
#define Py_XDECREF(obj) Impl_Py_XDECREF(__FILE__, __LINE__, obj)
#define Py_INCREF(obj) Impl_Py_INCREF(__FILE__, __LINE__, obj)
#define Py_XINCREF(obj) Impl_Py_XINCREF(__FILE__, __LINE__, obj)
#else
#define Py_DECREF(obj) Impl_Py_DECREF(obj)
#define Py_XDECREF(obj) Impl_Py_XDECREF(obj)
#define Py_INCREF(obj) Impl_Py_INCREF(obj)
#define Py_XINCREF(obj) Impl_Py_XINCREF(obj)
#endif

class ePython
{
public:
	ePython();
	~ePython();
	int execute(const std::string &pythonfile, const std::string &funcname);
	static int call(ePyObject pFunc, ePyObject args);
	static ePyObject resolve(const std::string &pythonfile, const std::string &funcname);
private:
};

#endif // SWIG
#endif // SKIP_PART2

#endif // __lib_python_python_class_h
