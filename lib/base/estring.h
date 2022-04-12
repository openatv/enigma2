#ifndef __E_STRING__
#define __E_STRING__

#include <vector>
#include <string>
#include <stdarg.h>
#include <stdio.h>
#include "eerror.h"

std::string buildShortName( const std::string &str );

void undoAbbreviation(std::string &str1, std::string &str2);

int strnicmp(const char*, const char*, int);

std::string getNum(int num, int base=10);

std::string GB18030ToUTF8(const char *szIn, int len,int *pconvertedLen=0);
std::string Big5ToUTF8(const char *szIn, int len,int *pconvertedLen=0);
std::string GEOSTD8ToUTF8(const char *szIn, int len, int *pconvertedLen=0);

std::string convertDVBUTF8(const unsigned char *data, int len, int table=-1, int tsidonid=1,int *pconvertedLen=0);
std::string convertLatin1UTF8(const std::string &string);
int isUTF8(const std::string &string);
unsigned int truncateUTF8(std::string &s, unsigned int newsize);

std::string removeDVBChars(const std::string &s);
void makeUpper(std::string &s);
std::string replace_all(const std::string &in, const std::string &entity, const std::string &symbol,int table=-1);

inline std::string convertDVBUTF8(const std::string &string, int table=-1, int tsidonid=1,int *pconvertedLen=0)
{
	return convertDVBUTF8((const unsigned char*)string.c_str(), string.length(), table, tsidonid,pconvertedLen);
}

std::string urlDecode(const std::string &s);
std::string string_to_hex(const std::string& input);
std::string strip_non_graph(std::string s);
std::vector<std::string> split(std::string s, const std::string& separator);
int strcasecmp(const std::string& s1, const std::string& s2);

std::string formatNumber(size_t size, const std::string& suffix={}, bool binary = false);
inline std::string formatBits(size_t size) { return formatNumber(size, "bit"); }
inline std::string formatBytes(size_t size) { return formatNumber(size, "B", true); }
inline std::string formatHz(size_t size) { return formatNumber(size, "Hz"); }

#endif // __E_STRING__
