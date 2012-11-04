#ifndef __lib_base_cfile_h
#define __lib_base_cfile_h

#include <stdio.h>

/* Wrapper around FILE to prevent leaks and to make your code a bit more OO */
struct CFile
{
	FILE *handle;
	CFile(const char *filename, const char *mode)
		: handle(fopen(filename, mode))
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
	static int parseIntHex(int *result, const char *filename)
	{
		CFile f(filename, "r");
		if (!f)
			return -1;
		if (fscanf(f, "%x", result) != 1)
			return -2;
		return 0;
	}
	static int writeIntHex(const char *filename, int value)
	{
		CFile f(filename, "w");
		if (!f)
			return -1;
		return fprintf(f, "%x", value);
	}
};

#endif