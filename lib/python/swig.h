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
#define SWIG_VOID(x) void
#else
#define SWIG_INPUT
#define SWIG_OUTPUT
#define SWIG_VOID(x) x
#endif

#endif
