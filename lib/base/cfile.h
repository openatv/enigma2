#ifndef __lib_base_cfile_h
#define __lib_base_cfile_h

#include <stdio.h>
#include <string>

typedef long long pts_t;

/* Wrapper around FILE to prevent leaks and to make your code a bit more OO */
struct CFile
{
	FILE *handle;
	CFile(const char *fileName, const char *mode)
		: handle(fopen(fileName, mode))
	{
	}
	CFile(const std::string &fileName, const char *mode)
		: handle(fopen(fileName.c_str(), mode))
	{
	}
	~CFile()
	{
		if (handle)
			fclose(handle);
	}
	void sync() { fsync(fileno(handle)); }
	operator bool() const { return handle != NULL; }
	operator FILE *() const { return handle; }

	/* Fetch integer from /proc files and such */
	static int parseIntHex(int *result, const char *fileName);
	static int parseInt(int *result, const char *fileName);
	static int parsePts_t(pts_t *result, const char *fileName);
	static int writeIntHex(const char *fileName, int value);
	static int writeInt(const char *fileName, int value);
	static int writeStr(const char *fileName, const std::string &value);
	static int write(const char *fileName, const char *value);
	static std::string read(const char *fileName);
	static bool contains_word(const char *fileName, const std::string &word);

	/* debug versions */
	static int parseIntHex(int *result, const char *fileName, const char *moduleName, int flags = 0);
	static int parseInt(int *result, const char *fileName, const char *moduleName, int flags = 0);
	static int writeIntHex(const char *fileName, int value, const char *moduleName, int flags = 0);
	static int writeInt(const char *fileName, int value, const char *moduleName, int flags = 0);
	static int writeStr(const char *fileName, const std::string &value, const char *moduleName, int flags = 0);
	static int write(const char *fileName, const char *value, const char *moduleName, int flags = 0);
	static std::string read(const char *fileName, const char *moduleName, int flags = 0);

	enum
	{
		CFILE_FLAGS_SUPPRESS_NOT_EXISTS = 2,
		CFILE_FLAGS_SUPPRESS_READWRITE_ERROR = 4
	};
};

#endif
