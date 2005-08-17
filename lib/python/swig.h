#ifndef __lib_python_swig_h
#define __lib_python_swig_h

#ifdef SWIG
#define TEMPLATE_TYPEDEF(x, y) \
%template(y) x; \
typedef x y
#else
#define TEMPLATE_TYPEDEF(x, y) typedef x y
#endif

#ifdef SWIG
#define SWIG_INPUT INPUT
#define SWIG_OUTPUT OUTPUT
#else
#define SWIG_INPUT
#define SWIG_OUTPUT
#endif

#endif
