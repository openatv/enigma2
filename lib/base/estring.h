#ifndef __E_STRING__
#define __E_STRING__

#include <string>
#include <stdarg.h>
#include <stdio.h>
#include "eerror.h"

int strnicmp(const char*, const char*, int);

class eString : public std::string
{
public:
// constructors
	inline eString()	{}	
	inline eString(const char* p);
	inline eString(const char* p, int cnt);
	inline eString(const std::string &s);
// methods
	inline eString left(unsigned int len) const;
	inline eString mid(unsigned int index, unsigned int len=(unsigned)-1) const;
	inline eString right(unsigned int len) const;
	bool isNull() const;
// operators
	inline operator bool() const;
	inline bool operator!() const;
// methods with implementation in estring.cpp
	eString& sprintf(char *fmt, ...);
	eString& setNum(int val, int sys=10);
	eString& removeChars(const char fchar);
	eString& strReplace(const char* fstr, const eString& rstr);
	eString& upper();
	int icompare(const eString& s);
};

eString convertDVBUTF8(unsigned char *data, int len, int table=5);
eString convertUTF8DVB(const eString &string);  // with default ISO8859-5
eString convertLatin1UTF8(const eString &string);
int isUTF8(const eString &string);

/////////////////////////////////////////////// Copy Constructors ////////////////////////////////////////////////
inline eString::eString(const std::string &s)
	:std::string(s)
{
}

inline eString::eString(const char* p)
	:std::string(p?p:"")	 // when the char* p is null, than use ""... otherwise crash...
{
}

inline eString::eString(const char* p, int cnt)
	:std::string(p, cnt)
{
}

///////////////////////////////////////// eString operator bool /////////////////////////////////////////////////
inline eString::operator bool() const
{
// Returns a bool that contains true if the string longer than 0 Character otherwise false;
	return !empty();
}

///////////////////////////////////////// eString operator! ////////////////////////////////////////////////////
inline bool eString::operator!() const
{
// Returns a bool that contains true if the string ist empty otherwise false;
	return empty();
}

///////////////////////////////////////// eString left //////////////////////////////////////////////////////////
inline eString eString::left(unsigned int len) const
{
//	Returns a substring that contains the len leftmost characters of the string.
//	The whole string is returned if len exceeds the length of the string.
 	return len >= length() ? *this : substr(0, len);
}

//////////////////////////////////////// eString mid ////////////////////////////////////////////////////////////
inline eString eString::mid(unsigned int index, unsigned int len) const
{
//	Returns a substring that contains the len characters of this string, starting at position index.
//	Returns a null string if the string is empty or index is out of range. Returns the whole string from index if index+len exceeds the length of the string.
	register unsigned int strlen = length();

	if (index >= strlen)
		return eString();

	if (len == (unsigned)-1)
		return substr(index);

	if (strlen < index + len)
		len = strlen-index;

	return substr(index, len);
}

//////////////////////////////////////// eString right ////////////////////////////////////////////////////////////
inline eString eString::right(unsigned int len) const
{
//	Returns a substring that contains the len rightmost characters of the string.
//	The whole string is returned if len exceeds the length of the string.
	register unsigned int strlen = length();
	return len >= strlen ? *this : substr(strlen-len, len);
}

inline bool eString::isNull() const
{
//	Returns a bool, that contains true, when the internal char* is null (only when a string ist empty constructed)
	return !c_str();
}

#endif // __E_STRING__
