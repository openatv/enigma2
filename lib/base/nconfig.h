#ifndef __lib_base_nconfig_h_
#define __lib_base_nconfig_h_

#include <lib/python/python.h>

class ePythonConfigQuery
{
	static ePyObject m_queryFunc;
	ePythonConfigQuery() {}
	~ePythonConfigQuery() {}
public:
	static void setQueryFunc(SWIG_PYOBJECT(ePyObject) func);
#ifndef SWIG
	static RESULT getConfigValue(const char *key, std::string &value);
#endif
};

#endif // __lib_base_nconfig_h_
