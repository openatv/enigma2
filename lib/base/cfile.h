#ifndef __lib_base_cfile_h
#define __lib_base_cfile_h

#include <stdio.h>
#include <string>

/* Wrapper around FILE to prevent leaks and to make your code a bit more OO */
struct CFile
{
	FILE *handle;
	CFile(const char *filename, const char *mode)
		: handle(fopen(filename, mode))
	{}
	CFile(const std::string &filename, const char *mode)
		: handle(fopen(filename.c_str(), mode))
	{}
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
	static int write(const char *filename, const char *value);
};

#endif
