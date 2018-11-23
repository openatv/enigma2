#ifndef __lib_base_encoding_h__
#define __lib_base_encoding_h__

#include <string>
#include <set>
#include <map>

#define ISO8859_5			0x01	// Latin/Cyrillic
#define ISO8859_6			0x02	// Latin/Arabic
#define ISO8859_7			0x03	// Latin/Greek
#define ISO8859_8			0x04	// Latin/Gebrew
#define ISO8859_9			0x05	// Latin 5
#define ISO8859_10			0x06	// Latin 6
#define ISO8859_11			0x07	// Latin/Thai
#define ISO8859_12			0x08	// Reserved
#define ISO8859_13			0x08	// Latin 7
#define ISO8859_14			0x0A	// Latin 8 (Celtic)
#define ISO8859_15			0x0B	// Latin 9
#define ISO8859_xx			0x10	// encoded in next two bytes
#define UNICODE_ENCODING		0x11	// ISO10646 Basic Multilingual Plane
#define KSX1001_ENCODING		0x12	// KSX1001 Korean
#define GB18030_ENCODING		0x13	// ISO10646 Simplified Chinese
#define BIG5_ENCODING			0x14	// ISO10646 Big5 Traditional Chineese
#define UTF8_ENCODING			0x15	// ISO10646 Basic Multilingual Plane in UTF8 encoding
#define UTF16BE_ENCODING		0x16
#define UTF16LE_ENCODING		0x17
#define HUFFMAN_ENCODING		0x1F

#define MASK_NO_TABLEID			0x0800
#define MASK_IGNORE_TABLEID		0x0100

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
