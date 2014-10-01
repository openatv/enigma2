#include "cfile.h"

int CFile::parseIntHex(int *result, const char *filename)
{
	CFile f(filename, "r");
	if (!f)
		return -1;
	if (fscanf(f, "%x", result) != 1)
		return -2;
	return 0;
}

int CFile::parseInt(int *result, const char *filename)
{
	CFile f(filename, "r");
	if (!f)
		return -1;
	if (fscanf(f, "%d", result) != 1)
		return -2;
	return 0;
}

int CFile::writeIntHex(const char *filename, int value)
{
	CFile f(filename, "w");
	if (!f)
		return -1;
	return fprintf(f, "%x", value);
}

int CFile::writeInt(const char *filename, int value)
{
	CFile f(filename, "w");
	if (!f)
		return -1;
	return fprintf(f, "%d", value);
}
