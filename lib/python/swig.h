#ifndef __lib_python_swig_h
#define __lib_python_swig_h

#ifdef SWIG
#define TEMPLATE_TYPEDEF(x, y) \
%template(y) x; \
typedef x y; \
%typemap_output_ptr(x);
#define SWIG_ALLOW_OUTPUT_SIMPLE(x) %typemap_output_simple(x);
#else
#define TEMPLATE_TYPEDEF(x, y) typedef x y
#define SWIG_ALLOW_OUTPUT_SIMPLE(x) 
#endif


#ifdef SWIG
#define SWIG_INPUT INPUT
#define SWIG_OUTPUT OUTPUT
#define SWIG_NAMED_OUTPUT(x) OUTPUT
#define SWIG_VOID(x) void
#define SWIG_PYOBJECT(x) PyObject*
#else
#define SWIG_INPUT
#define SWIG_OUTPUT
#define SWIG_NAMED_OUTPUT(x) x
#define SWIG_VOID(x) x
#define SWIG_PYOBJECT(x) x
#endif

#endif
