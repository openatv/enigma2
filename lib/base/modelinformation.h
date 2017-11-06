#ifndef __lib_base_modelinformation_h
#define __lib_base_modelinformation_h

#include <map>
#include <string>

class eModelInformation
{
	public:
		eModelInformation();
		static eModelInformation& getInstance() { static eModelInformation m_instance; return m_instance; }
		std::string getValue(const std::string &key);
		std::string BoxType() { return getValue("box_type"); }
		std::string BuildType() { return getValue("build_type"); }
		std::string MachineBrand() { return getValue("machine_brand"); }
		std::string MachineName() { return getValue("machine_name"); }
		std::string Version() { return getValue("version"); }
		std::string Build() { return getValue("build"); }
		std::string Date() { return getValue("date"); }
		std::string Comment() { return getValue("comment"); }
		std::string Target() { return getValue("target"); }
		std::string Creator() { return getValue("creator"); }
		std::string Url() { return getValue("url"); }
		std::string Catalog() { return getValue("catalog"); }
	private:
		std::map<std::string,std::string> m_modelinformation;
};

#endif
