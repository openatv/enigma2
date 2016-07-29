#ifndef __lib_base_encoding_h__
#define __lib_base_encoding_h__

#include <string>
#include <set>
#include <map>

#define UNICODE_ENCODING		0x11
#define GB18030_ENCODING		0x13
#define BIG5_ENCODING			0x14
#define UTF8_ENCODING			0x15
#define UTF16BE_ENCODING		0x16
#define UTF16LE_ENCODING		0x17

class eDVBTextEncodingHandler
{
	std::map<std::string, int> m_CountryCodeDefaultMapping;
	std::map<int, int> m_TransponderDefaultMapping;
	std::set<int> m_TransponderUseTwoCharMapping;
public:
	eDVBTextEncodingHandler();
	void getTransponderDefaultMapping(int tsidonid, int &table);
	bool getTransponderUseTwoCharMapping(int tsidonid);
	int getCountryCodeDefaultMapping( const std::string &country_code );
};

extern eDVBTextEncodingHandler encodingHandler;
extern int defaultEncodingTable;
#endif // __lib_base_encoding_h__
