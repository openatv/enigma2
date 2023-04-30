#include <fstream>
#include <algorithm>

#include <lib/base/eenv.h>
#include <lib/base/modelinformation.h>

eModelInformation::eModelInformation()
{
	std::string key, value;
	std::ifstream f(eEnv::resolve("${libdir}/enigma.info").c_str());

	while (f.good())
	{
		std::getline(f, key, '=');
		std::getline(f, value);
		if (!key.size())
			break;
		if (!value.size())
			value = "N/A";
		value.erase(std::remove(value.begin(), value.end(), '\"'), value.end());
		value.erase(std::remove(value.begin(), value.end(), '\''), value.end());
		m_modelinformation[key] = value;
	}
}

std::string eModelInformation::getValue(const std::string &key)
{
	std::map<std::string, std::string>::iterator it = m_modelinformation.find(key);
	if (it != m_modelinformation.end())
		return it->second;
	return "N/A";
}
