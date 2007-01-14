#ifndef __lib_python_swig_h
#define __lib_python_swig_h

#ifdef SWIG
#define SWIG_IGNORE(x) %ignore x
#define SWIG_EXTEND(x, code) %extend x { code }
#define SWIG_TEMPLATE_TYPEDEF(x, y) %template(y) x; %typemap_output_ptr(x)
#define SWIG_ALLOW_OUTPUT_SIMPLE(x) %typemap_output_simple(x)
#define SWIG_INPUT INPUT
#define SWIG_OUTPUT OUTPUT
#define SWIG_NAMED_OUTPUT(x) OUTPUT
#define SWIG_VOID(x) void
#define SWIG_PYOBJECT(x) PyObject*
#else
#define SWIG_IGNORE(x)
#define SWIG_EXTEND(x, code)
#define SWIG_TEMPLATE_TYPEDEF(x, y)
#define SWIG_ALLOW_OUTPUT_SIMPLE(x)
#define SWIG_INPUT
#define SWIG_OUTPUT
#define SWIG_NAMED_OUTPUT(x) x
#define SWIG_VOID(x) x
#define SWIG_PYOBJECT(x) x
#endif  // SWIG

#endif  // __lib_python_swig_h
