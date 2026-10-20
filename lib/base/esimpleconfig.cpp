#include <algorithm>
#include <cctype>
#include <climits>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>
#include <sstream>
#include <map>
#include <strings.h>
#include <sys/stat.h>
#include <lib/base/eenv.h>
#include <lib/base/eerror.h>
#include <lib/base/esimpleconfig.h>
#include <lib/base/cfile.h>

namespace eSimpleConfig
{
	static std::map<std::string, std::string>* configValues = nullptr; // NOSONAR
	static time_t lastModified = 0; // NOSONAR

	static std::map<std::string, std::string>& getConfigValues()
	{
		if (!configValues)
			configValues = new std::map<std::string, std::string>();
		return *configValues;
	}

	bool getValues(std::map<std::string, std::string> &values)
	{
		values.clear();
		std::ifstream in(eEnv::resolve("${sysconfdir}/enigma2/settings"));
		if (!in.good())
			return false;

		std::string line;
		while (std::getline(in, line))
		{
			if (line.empty() || line[0] == '#')
				continue;

			auto equals = line.find_first_of('=');
			if (equals != std::string::npos)
				values.insert(std::pair<std::string, std::string>(line.substr(0, equals), line.substr(equals + 1)));
		}
		if (!in.eof())
		{
			values.clear();
			return false;
		}
		return true;
	}

	static void load()
	{
		std::string file = eEnv::resolve("${sysconfdir}/enigma2/settings");
		struct stat settings_stat = {};
		if (stat(file.c_str(), &settings_stat) == -1 || settings_stat.st_mtime <= lastModified)
			return;
		std::map<std::string, std::string> values;
		if (!getValues(values))
			return;
		getConfigValues().swap(values);
		lastModified = settings_stat.st_mtime;
	}

	std::string getString(const char *key, const char* defaultvalue)
	{
		load();
		auto it = getConfigValues().find(key);
		return it == getConfigValues().end() ? std::string(defaultvalue) : it->second;
	}

	int getInt(const char *key, int defaultvalue)
	{
		load();
		auto it = getConfigValues().find(key);
		return it == getConfigValues().end() ? defaultvalue : atoi(it->second.c_str());
	}

	bool getBool(const char *key, bool defaultvalue)
	{
		load();
		auto it = getConfigValues().find(key);
		if (it == getConfigValues().end())
			return defaultvalue;

		if (strcasecmp(it->second.c_str(), "true") == 0)
			return true;
		if (strcasecmp(it->second.c_str(), "false") == 0)
			return false;
		return defaultvalue;
	}
}
