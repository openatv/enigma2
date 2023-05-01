#include <fstream>
#include <sstream>
#include <lib/base/eerror.h>

#include "cfile.h"

#define eDebugErrorOpenFile(MODULE, FILENAME) eDebug("[%s] Error %d: Unable to open file '%s'!  (%m)", MODULE, errno, FILENAME)
#define eDebugErrorReadFile(MODULE, FILENAME) eDebug("[%s] Error %d: Unable to read from file '%s'!  (%m)", MODULE, errno, FILENAME)
#define eDebugErrorWriteFile(MODULE, FILENAME) eDebug("[%s] Error %d: Unable to write to file '%s'!  (%m)", MODULE, errno, FILENAME)

int CFile::parseIntHex(int *result, const char *fileName)
{
	CFile f(fileName, "r");
	if (!f)
		return -1;
	if (fscanf(f, "%x", result) != 1)
		return -2;
	return 0;
}

int CFile::parseInt(int *result, const char *fileName)
{
	CFile f(fileName, "r");
	if (!f)
		return -1;
	if (fscanf(f, "%d", result) != 1)
		return -2;
	return 0;
}

int CFile::parsePts_t(pts_t *result, const char *fileName)
{
	CFile f(fileName, "r");
	if (!f)
		return -1;
	if (fscanf(f, "%lld", result) != 1)
		return -2;
	return 0;
}

int CFile::writeIntHex(const char *fileName, int value)
{
	CFile f(fileName, "w");
	if (!f)
		return -1;
	return fprintf(f, "%x", value);
}

int CFile::writeInt(const char *fileName, int value)
{
	CFile f(fileName, "w");
	if (!f)
		return -1;
	return fprintf(f, "%d", value);
}

int CFile::writeStr(const char *fileName, const std::string &value)
{
	CFile f(fileName, "w");
	if (f)
		fprintf(f, "%s", value.c_str());
	return 0;
}

int CFile::write(const char *fileName, const char *value)
{
	CFile f(fileName, "w");
	if (!f)
		return -1;
	return fprintf(f, "%s", value);
}

std::string CFile::read(const char *fileName)
{
	std::ifstream file(fileName);
	if (!file.good())
		return std::string();
	std::stringstream ss;
	ss << file.rdbuf();
	return ss.str();
}

bool CFile::contains_word(const char *fileName, const std::string &word_to_match)
{
	std::string word;
	std::ifstream file(fileName);

	if (!file.good())
		return false;

	while (file >> word)
		if (word == word_to_match)
			return true;

	return false;
}

int CFile::parseIntHex(int *result, const char *fileName, const char *moduleName, int flags)
{
	CFile f(fileName, "r");
	if (!f)
	{
		if (!(flags & CFILE_FLAGS_SUPPRESS_NOT_EXISTS))
			eDebugErrorOpenFile(moduleName, fileName);
		return -1;
	}
	if (fscanf(f, "%x", result) != 1)
	{
		if (!(flags & CFILE_FLAGS_SUPPRESS_READWRITE_ERROR))
			eDebugErrorReadFile(moduleName, fileName);
		return -2;
	}
	return 0;
}

int CFile::parseInt(int *result, const char *fileName, const char *moduleName, int flags)
{
	CFile f(fileName, "r");
	if (!f)
	{
		if (!(flags & CFILE_FLAGS_SUPPRESS_NOT_EXISTS))
			eDebugErrorOpenFile(moduleName, fileName);
		return -1;
	}
	if (fscanf(f, "%d", result) != 1)
	{
		if (!(flags & CFILE_FLAGS_SUPPRESS_READWRITE_ERROR))
			eDebugErrorReadFile(moduleName, fileName);
		return -2;
	}
	return 0;
}

int CFile::writeIntHex(const char *fileName, int value, const char *moduleName, int flags)
{
	CFile f(fileName, "w");
	if (!f)
	{
		if (!(flags & CFILE_FLAGS_SUPPRESS_NOT_EXISTS))
			eDebugErrorOpenFile(moduleName, fileName);
		return -1;
	}
	int ret = fprintf(f, "%x", value);
	if (ret < 0 && !(flags & CFILE_FLAGS_SUPPRESS_READWRITE_ERROR))
		eDebugErrorWriteFile(moduleName, fileName);
	return ret;
}

int CFile::writeInt(const char *fileName, int value, const char *moduleName, int flags)
{
	CFile f(fileName, "w");
	if (!f)
	{
		if (!(flags & CFILE_FLAGS_SUPPRESS_NOT_EXISTS))
			eDebugErrorOpenFile(moduleName, fileName);
		return -1;
	}
	int ret = fprintf(f, "%d", value);
	if (ret < 0 && !(flags & CFILE_FLAGS_SUPPRESS_READWRITE_ERROR))
		eDebugErrorWriteFile(moduleName, fileName);
	return ret;
}

int CFile::writeStr(const char *fileName, const std::string &value, const char *moduleName, int flags)
{
	CFile f(fileName, "w");
	if (f)
	{
		int ret = fprintf(f, "%s", value.c_str());
		if (ret < 0 && !(flags & CFILE_FLAGS_SUPPRESS_READWRITE_ERROR))
			eDebugErrorWriteFile(moduleName, fileName);
	}
	else if (!(flags & CFILE_FLAGS_SUPPRESS_NOT_EXISTS))
		eDebugErrorOpenFile(moduleName, fileName);
	return 0;
}

int CFile::write(const char *fileName, const char *value, const char *moduleName, int flags)
{
	CFile f(fileName, "w");
	if (!f)
	{
		if (!(flags & CFILE_FLAGS_SUPPRESS_NOT_EXISTS))
			eDebugErrorOpenFile(moduleName, fileName);
		return -1;
	}
	int ret = fprintf(f, "%s", value);
	if (ret < 0 && !(flags & CFILE_FLAGS_SUPPRESS_READWRITE_ERROR))
		eDebugErrorWriteFile(moduleName, fileName);
	return ret;
}

std::string CFile::read(const char *fileName, const char *moduleName, int flags)
{
	std::ifstream file(fileName);
	if (!file.good())
	{
		if (!(flags & CFILE_FLAGS_SUPPRESS_NOT_EXISTS))
			eDebugErrorOpenFile(moduleName, fileName);
		return std::string();
	}
	std::stringstream ss;
	ss << file.rdbuf();
	return ss.str();
}
