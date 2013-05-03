#ifndef __lib_python_pythonconfig_h_
#define __lib_python_pythonconfig_h_

#include <lib/base/nconfig.h>
#include <lib/python/python.h>

class ePythonConfigQuery : public eConfigManager
{
	static ePyObject m_queryFunc;
#ifndef SWIG
	RESULT getConfigValue(const char *key, std::string &value);
	std::string getConfig(const char *key);
#endif
public:
	ePythonConfigQuery() {}
	~ePythonConfigQuery() {}
	static void setQueryFunc(SWIG_PYOBJECT(ePyObject) func);
};

#endif // __lib_python_pythonconfig_h_
