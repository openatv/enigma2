#ifndef __lib_esimpleconfig_h_
#define __lib_esimpleconfig_h_

#include <map>
#include <string>

// Simple configuration reader that doesn't rely on Python to provide values, so is
// safe to use in non UI threads
namespace eSimpleConfig
{
	// Read a fresh snapshot without changing the cache used by the single-value getters.
	// Return false and clear values if the settings file cannot be read completely.
	bool getValues(std::map<std::string, std::string> &values);
	std::string getString(const char *key, const char* defaultvalue = "");
	int getInt(const char *key, int defaultvalue = 0);
	bool getBool(const char *key, bool defaultvalue = true);
}

#endif // __lib_esimpleconfig_h_
