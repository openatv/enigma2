#include <lib/base/nconfig.h>

eConfigManager *eConfigManager::instance = NULL;

eConfigManager::eConfigManager()
{
	instance = this;
}

eConfigManager::~eConfigManager()
{
	instance = NULL;
}

eConfigManager *eConfigManager::getInstance()
{
	return instance;
}

std::string eConfigManager::getConfigValue(const char *key)
{
	return instance ? instance->getConfig(key) : "";
}

int eConfigManager::getConfigIntValue(const char *key, int defaultvalue)
{
	std::string value = getConfigValue(key);
	return (value != "") ? atoi(value.c_str()) : defaultvalue;
}

bool eConfigManager::getConfigBoolValue(const char *key, bool defaultvalue)
{
	std::string value = getConfigValue(key);
	if (value == "True" || value == "true") return true;
	if (value == "False" || value == "false") return false;
	return defaultvalue;
}
