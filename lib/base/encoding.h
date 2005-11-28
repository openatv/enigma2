#ifndef __lib_base_encoding_h__
#define __lib_base_encoding_h__

#include <string>
#include <set>
#include <map>

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

#endif // __lib_base_encoding_h__
