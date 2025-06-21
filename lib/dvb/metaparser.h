#ifndef __lib_dvb_metaparser_h
#define __lib_dvb_metaparser_h

#ifndef SWIG
#include <lib/dvb/idvb.h>
#include <lib/dvb/tstools.h>
#include <string>
#else
#include <lib/python/swig.h>
#endif

class iDVBMetaFile {
public:
	enum {
		idServiceRef = 0,
		idName = 1,
		idDescription = 2,
		idCreated = 3,
		idTags = 4,
		idLength = 5,
		idFileSize = 6,
		idServiceData = 7,
		idPacketSize = 8,
		idScrambled = 9,
	};
};
SWIG_ALLOW_OUTPUT_SIMPLE(iDVBMetaFile);

#ifndef SWIG
class eDVBMetaParser {
public:
	eDVBMetaParser();
	int parseFile(const std::string& basename);
	int parseMeta(const std::string& filename);
	int parseRecordings(const std::string& filename);
	int updateMeta(const std::string& basename);
	std::string parseTxtFile(const std::string& basename);
	eServiceReferenceDVB m_ref;
	int m_data_ok, m_time_create, m_packet_size, m_scrambled;
	pts_t m_length;
	std::string m_name, m_description, m_tags, m_service_data, m_prov;
	long long m_filesize;
};
#endif

#endif
