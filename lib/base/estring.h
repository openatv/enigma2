#ifndef __E_STRING__
#define __E_STRING__

#include <string>
#include <stdarg.h>
#include <stdio.h>
#include "eerror.h"

std::string buildShortName( const std::string &str );

int strnicmp(const char*, const char*, int);

std::string getNum(int num, int base=10);

std::string convertDVBUTF8(const unsigned char *data, int len, int table=1, int tsidonid=1); // with default ISO8859-1 / Latin1
std::string convertLatin1UTF8(const std::string &string);
int isUTF8(const std::string &string);

std::string removeDVBChars(const std::string &s);
void makeUpper(std::string &s);
std::string replace_all(const std::string &in, const std::string &entity, const std::string &symbol);

inline std::string convertDVBUTF8(const std::string &string, int table=1, int tsidonid=1) // with default ISO8859-1 / Latin1
{
	return convertDVBUTF8((const unsigned char*)string.c_str(), string.length(), table, tsidonid);
}

#endif // __E_STRING__
