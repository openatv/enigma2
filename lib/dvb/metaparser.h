#ifndef __lib_dvb_metaparser_h
#define __lib_dvb_metaparser_h

#include <string>
#include <lib/dvb/idvb.h>

class eDVBMetaParser
{
public:
	eDVBMetaParser();
	int parseFile(const std::string &basename);
	
	int parseMeta(const std::string &filename);
	int parseRecordings(const std::string &filename);

	eServiceReferenceDVB m_ref;
	std::string m_name, m_description;
	int m_time_create;
	
	std::string m_tags;
};

#endif
