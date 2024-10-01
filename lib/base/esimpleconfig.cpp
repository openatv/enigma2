#include <algorithm>
#include <cctype>
#include <climits>
#include <fstream>
#include <iostream>
#include <string>
#include <sstream>
#include <map>
#include <lib/base/eenv.h>
#include <lib/base/eerror.h>
#include <lib/base/esimpleconfig.h>
#include <lib/base/cfile.h>

namespace eSimpleConfig
{
	static std::map<std::string, std::string> configValues; // NOSONAR
	static int lastModified = 0; // NOSONAR

	static void load()
	{
		std::string file = eEnv::resolve("${sysconfdir}/enigma2/settings");

		struct stat settings_stat = {};
		if (stat(file.c_str(), &settings_stat) == -1 || settings_stat.st_mtime <= lastModified)
			return;

		std::ifstream in(file.c_str());
		if (!in.good())
			return;

		configValues.clear();
		do
		{
			std::string line;
			std::getline(in, line);

			if (line[0] == '#')
				continue;

			auto equals = line.find_first_of('=');
			if (equals != std::string::npos)
				configValues.insert(std::pair<std::string, std::string>(line.substr(0, equals), line.substr(equals + 1)));
		}
		while (in.good());
		in.close();

		lastModified = settings_stat.st_mtime;
	}

	std::string getString(const char *key, const char* defaultvalue)
	{
		load();
		auto it = configValues.find(key);
		return it == configValues.end() ? std::string(defaultvalue) : it->second;
	}

	int getInt(const char *key, int defaultvalue)
	{
		load();
		auto it = configValues.find(key);
		return it == configValues.end() ? defaultvalue : atoi(it->second.c_str());
	}

	bool getBool(const char *key, bool defaultvalue)
	{
		load();
		auto it = configValues.find(key);
		if (it == configValues.end())
			return defaultvalue;

		if (strcasecmp(it->second.c_str(), "true") == 0)
			return true;
		if (strcasecmp(it->second.c_str(), "false") == 0)
			return false;
		return defaultvalue;
	}
}