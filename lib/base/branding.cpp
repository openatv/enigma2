#include <fstream>

#include <lib/base/branding.h>

eBranding::eBranding()
{
	std::string key, value;
	std::ifstream f("/etc/image-version");

	while (f.good())
	{
		std::getline(f, key, '=');
		std::getline(f, value);
		if (!key.size())
			break;
		if (!value.size())
			value = "N/A";
		m_branding[key] = value;
	}
}

std::string eBranding::getValue(const std::string &key)
{
	std::map<std::string,std::string>::iterator it = m_branding.find(key);
	if (it != m_branding.end())
		return it->second;
	return "N/A";
}
