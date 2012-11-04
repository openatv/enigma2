#ifndef __lib_base_cfile_h
#define __lib_base_cfile_h

#include <stdio.h>

/* Wrapper around FILE to prevent leaks and to make your code a bit more OO */
struct CFile
{
	FILE* handle;
	CFile(const char *filename, const char* mode):
		handle(fopen(filename, mode))
	{}
	~CFile()
	{
		if (valid())
			fclose(handle);
	}
	bool valid() const { return handle != NULL; }
	void sync() { fsync(fileno(handle)); }

	/* Fetch integer from /proc files and such */
	static int parseIntHex(int *result, const char* filename)
	{
		CFile f(filename, "r");
		if (!f.valid())
			return -1;
		if (fscanf(f.handle, "%x", result) != 1)
			return -2;
		return 0;
	}
	static int writeIntHex(const char* filename, int value)
	{
		CFile f(filename, "w");
		if (!f.valid())
			return -1;
		return fprintf(f.handle, "%x", value);
	}
};

#endif