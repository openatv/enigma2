#ifndef __lib_python_python_class_h

#ifndef SKIP_PART2
	#define __lib_python_python_class_h
#endif

#include <string>
#include <lib/base/object.h>

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
#ifdef PYTHON_REFCOUNT_DEBUG
	inline ePyObject(PyObject *ob, const char *file, int line);
#endif
	inline ePyObject(PyVarObject *ob);
	inline ePyObject(PyDictObject *ob);
	inline ePyObject(PyTupleObject *ob);
	inline ePyObject(PyListObject *ob);
	inline ePyObject(PyStringObject *ob);
	operator bool() const { return !!m_ob; }
	operator bool() { return !!m_ob; }
	ePyObject &operator=(const ePyObject &);
	ePyObject &operator=(PyObject *);
	ePyObject &operator=(PyVarObject *ob) { return operator=((PyObject*)ob); }
	ePyObject &operator=(PyDictObject *ob) { return operator=((PyObject*)ob); }
	ePyObject &operator=(PyTupleObject *ob) { return operator=((PyObject*)ob); }
	ePyObject &operator=(PyListObject *ob) { return operator=((PyObject*)ob); }
	ePyObject &operator=(PyStringObject *ob) { return operator=((PyObject*)ob); }
	operator PyObject*();
	operator PyVarObject*() { return (PyVarObject*)operator PyVarObject*(); }
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

#ifdef PYTHON_REFCOUNT_DEBUG
inline ePyObject::ePyObject(PyObject *ob, const char* file, int line)
	:m_ob(ob)
	,m_file(file), m_line(line), m_from(ob->ob_refcnt), m_to(ob->ob_refcnt), m_erased(false)
{
}
#endif

inline ePyObject::ePyObject(PyVarObject *ob)
	:m_ob((PyObject*)ob)
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

class ePyObjectWrapper
{
	ePyObject m_obj;
public:
	ePyObjectWrapper(const ePyObjectWrapper &wrapper)
		:m_obj(wrapper.m_obj)
	{
		Py_INCREF(m_obj);
	}
	ePyObjectWrapper(const ePyObject &obj)
		:m_obj(obj)
	{
		Py_INCREF(m_obj);
	}
	~ePyObjectWrapper()
	{
		Py_DECREF(m_obj);
	}
	ePyObjectWrapper &operator=(const ePyObjectWrapper &wrapper)
	{
		Py_DECREF(m_obj);
		m_obj = wrapper.m_obj;
		Py_INCREF(m_obj);
		return *this;
	}
	operator PyObject*()
	{
		return m_obj;
	}
	operator ePyObject()
	{
		return m_obj;
	}
};

#endif // ! PYTHON_REFCOUNT_DEBUG

#endif  // !SWIG && !SKIP_PART1

#ifndef SKIP_PART2
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

inline ePyObject Impl_PyTuple_New(const char* file, int line, int elements=0)
{
	return ePyObject(PyTuple_New(elements), file, line);
}

inline ePyObject Impl_PyList_New(const char* file, int line, int elements=0)
{
	return ePyObject(PyList_New(elements), file, line);
}

inline ePyObject Impl_PyDict_New(const char* file, int line)
{
	return ePyObject(PyDict_New(), file, line);
}

inline ePyObject Impl_PyString_FromString(const char* file, int line, const char *str)
{
	return ePyObject(PyString_FromString(str), file, line);
}

inline ePyObject Impl_PyString_FromFormat(const char* file, int line, const char *fmt, ...)
{
	va_list ap;
	va_start(ap, fmt);
	PyObject *ob = PyString_FromFormatV(fmt, ap);
	va_end(ap);
	return ePyObject(ob, file, line);
}

inline ePyObject Impl_PyInt_FromLong(const char* file, int line, long val)
{
	return ePyObject(PyInt_FromLong(val), file, line);
}

inline ePyObject Impl_PyLong_FromLong(const char* file, int line, long val)
{
	return ePyObject(PyLong_FromLong(val), file, line);
}

inline ePyObject Impl_PyLong_FromUnsignedLong(const char* file, int line, unsigned long val)
{
	return ePyObject(PyLong_FromUnsignedLong(val), file, line);
}

inline ePyObject Impl_PyLong_FromLongLong(const char* file, int line, long long val)
{
	return ePyObject(PyLong_FromLongLong(val), file, line);
}

inline ePyObject Impl_PyList_GET_ITEM(const char *file, int line, ePyObject list, unsigned int pos)
{
	return ePyObject(PyList_GET_ITEM(list, pos), file, line);
}

inline ePyObject Impl_PyTuple_GET_ITEM(const char *file, int line, ePyObject list, unsigned int pos)
{
	return ePyObject(PyTuple_GET_ITEM(list, pos), file, line);
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

inline ePyObject Impl_PyTuple_New(int elements=0)
{
	return PyTuple_New(elements);
}

inline ePyObject Impl_PyList_New(int elements=0)
{
	return PyList_New(elements);
}

inline ePyObject Impl_PyDict_New()
{
	return PyDict_New();
}

inline ePyObject Impl_PyString_FromString(const char *str)
{
	return PyString_FromString(str);
}

inline ePyObject Impl_PyString_FromFormat(const char *fmt, ...)
{
	va_list ap;
	va_start(ap, fmt);
	PyObject *ob = PyString_FromFormatV(fmt, ap);
	va_end(ap);
	return ePyObject(ob);
}

inline ePyObject Impl_PyInt_FromLong(long val)
{
	return PyInt_FromLong(val);
}

inline ePyObject Impl_PyLong_FromLong(long val)
{
	return PyLong_FromLong(val);
}

inline ePyObject Impl_PyLong_FromUnsignedLong(unsigned long val)
{
	return PyLong_FromUnsignedLong(val);
}

inline ePyObject Impl_PyLong_FromLongLong(long long val)
{
	return PyLong_FromLongLong(val);
}

inline ePyObject Impl_PyList_GET_ITEM(ePyObject list, unsigned int pos)
{
	return PyList_GET_ITEM(list, pos);
}

inline ePyObject Impl_PyTuple_GET_ITEM(ePyObject list, unsigned int pos)
{
	return PyTuple_GET_ITEM(list, pos);
}
#endif

inline void Impl_INCREF(PyObject *ob)
{
	Py_INCREF(ob);
}

inline void Impl_DECREF(PyObject *ob)
{
	Py_DECREF(ob);
}
#define Org_Py_INCREF(obj) Impl_INCREF(obj)
#define Org_Py_DECREF(obj) Impl_DECREF(obj)
#undef Py_DECREF
#undef Py_XDECREF
#undef Py_INCREF
#undef Py_XINCREF
#undef PyList_GET_ITEM
#undef PyTuple_GET_ITEM
#ifdef PYTHON_REFCOUNT_DEBUG
#define Py_DECREF(obj) Impl_Py_DECREF(__FILE__, __LINE__, obj)
#define Py_XDECREF(obj) Impl_Py_XDECREF(__FILE__, __LINE__, obj)
#define Py_INCREF(obj) Impl_Py_INCREF(__FILE__, __LINE__, obj)
#define Py_XINCREF(obj) Impl_Py_XINCREF(__FILE__, __LINE__, obj)
#define PyList_New(args...) Impl_PyList_New(__FILE__, __LINE__, args)
#define PyTuple_New(args...) Impl_PyTuple_New(__FILE__, __LINE__, args)
#define PyDict_New(...) Impl_PyDict_New(__FILE__, __LINE__)
#define PyString_FromString(str) Impl_PyString_FromString(__FILE__, __LINE__, str)
#define PyString_FromFormat(str, args...) Impl_PyString_FromFormat(__FILE__, __LINE__, str, args)
#define PyInt_FromLong(val) Impl_PyInt_FromLong(__FILE__, __LINE__, val)
#define PyLong_FromLong(val) Impl_PyLong_FromLong(__FILE__, __LINE__, val)
#define PyLong_FromUnsignedLong(val) Impl_PyLong_FromUnsignedLong(__FILE__, __LINE__, val)
#define PyLong_FromLongLong(val) Impl_PyLong_FromLongLong(__FILE__, __LINE__, val)
#define PyList_GET_ITEM(list, pos) Impl_PyList_GET_ITEM(__FILE__, __LINE__, list, pos)
#define PyTuple_GET_ITEM(list, pos) Impl_PyTuple_GET_ITEM(__FILE__, __LINE__, list, pos)
#else
#define Py_DECREF(obj) Impl_Py_DECREF(obj)
#define Py_XDECREF(obj) Impl_Py_XDECREF(obj)
#define Py_INCREF(obj) Impl_Py_INCREF(obj)
#define Py_XINCREF(obj) Impl_Py_XINCREF(obj)
#define PyList_New(args...) Impl_PyList_New(args)
#define PyTuple_New(args...) Impl_PyTuple_New(args)
#define PyDict_New(...) Impl_PyDict_New()
#define PyString_FromString(str) Impl_PyString_FromString(str)
#define PyString_FromFormat(str, args...) Impl_PyString_FromFormat(str, args)
#define PyInt_FromLong(val) Impl_PyInt_FromLong(val)
#define PyLong_FromLong(val) Impl_PyLong_FromLong(val)
#define PyLong_FromUnsignedLong(val) Impl_PyLong_FromUnsignedLong(val)
#define PyLong_FromLongLong(val) Impl_PyLong_FromLongLong(val)
#define PyList_GET_ITEM(list, pos) Impl_PyList_GET_ITEM(list, pos)
#define PyTuple_GET_ITEM(list, pos) Impl_PyTuple_GET_ITEM(list, pos)
#endif

class ePython
{
public:
	ePython();
	~ePython();
	int execFile(const char *file);
	int execute(const std::string &pythonfile, const std::string &funcname);
	static int call(ePyObject pFunc, ePyObject args);
	static ePyObject resolve(const std::string &pythonfile, const std::string &funcname);
private:
};

#endif // SWIG
#endif // SKIP_PART2
#endif // __lib_python_python_class_h
