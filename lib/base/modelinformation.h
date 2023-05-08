#ifndef __lib_base_modelinformation_h
#define __lib_base_modelinformation_h

#include <map>
#include <string>

class eModelInformation
{
public:
	eModelInformation();
	static eModelInformation &getInstance()
	{
		static eModelInformation m_instance;
		return m_instance;
	}
	std::string getValue(const std::string &key);

private:
	std::map<std::string, std::string> m_modelinformation;
};

#endif
