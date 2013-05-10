#ifndef __lib_base_nconfig_h_
#define __lib_base_nconfig_h_

#include <string>
#include <stdbool.h>

class eConfigManager
{
protected:
	static eConfigManager *instance;
	static eConfigManager *getInstance();

	virtual std::string getConfig(const char *key) = 0;

public:
	eConfigManager();
	virtual ~eConfigManager();

	static std::string getConfigValue(const char *key);
	static int getConfigIntValue(const char *key, int defaultvalue = 0);
	static bool getConfigBoolValue(const char *key, bool defaultvalue = false);
};

#endif /* __lib_base_nconfig_h_ */
