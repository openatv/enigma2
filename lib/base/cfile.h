#ifndef __lib_base_cfile_h
#define __lib_base_cfile_h

#include <stdio.h>
#include <string>
#include <lib/base/eerror.h>

/* Wrapper around FILE to prevent leaks and to make your code a bit more OO */
struct CFile
{
	FILE *handle;
	CFile(const char *filename, const char *mode)
		: handle(fopen(filename, mode))
	{
/*#ifdef DEBUG
		if (!handle)
			eDebug("error %s [%m]",filename);
#endif*/
	}
	CFile(const std::string &filename, const char *mode)
		: handle(fopen(filename.c_str(), mode))
	{
/*#ifdef DEBUG
		if (!handle)
			eDebug("error %s [%m]",filename.c_str());
#endif*/
	}
	~CFile()
	{
		if (handle)
			fclose(handle);
	}
	void sync() { fsync(fileno(handle)); }
	operator bool() const { return handle != NULL; }
	operator FILE*() const { return handle; }

	/* Fetch integer from /proc files and such */
	static int parseIntHex(int *result, const char *filename);
	static int parseInt(int *result, const char *filename);
	static int writeIntHex(const char *filename, int value);
	static int writeInt(const char *filename, int value);
	static int writeStr(const char *filename, std::string value);
	static int write(const char *filename, const char *value);
	static std::string read(const std::string &filename);
	static bool contains_word(const std::string &filename, const std::string &word);
};

#endif
