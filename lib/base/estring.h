#ifndef __E_STRING__
#define __E_STRING__

#include <string>
#include <stdarg.h>
#include <stdio.h>
#include "eerror.h"

int strnicmp(const char*, const char*, int);

std::string getNum(int num, int base=10);
std::string convertDVBUTF8(unsigned char *data, int len, int table=5);
std::string convertUTF8DVB(const std::string &string);  // with default ISO8859-5
std::string convertLatin1UTF8(const std::string &string);
int isUTF8(const std::string &string);

#endif // __E_STRING__
