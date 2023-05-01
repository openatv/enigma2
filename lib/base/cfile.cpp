#include <fstream>
#include <sstream>
#include <lib/base/eerror.h>

#include "cfile.h"

#define eDebugErrorOpenFile(MODULE, FILENAME) eDebug("[%s] Error %d: Unable to open file '%s'!  (%m)", MODULE, errno, FILENAME);
#define eDebugErrorReadFile(MODULE, FILENAME) eDebug("[%s] Error %d: Unable to read from file '%s'!  (%m)", MODULE, errno, FILENAME);
#define eDebugErrorWriteFile(MODULE, FILENAME) eDebug("[%s] Error %d: Unable to write to file '%s'!  (%m)", MODULE, errno, FILENAME);

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

int CFile::parsePts_t(pts_t *result, const char *filename)
{
	CFile f(filename, "r");
	if (!f)
		return -1;
	if (fscanf(f, "%lld", result) != 1)
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

int CFile::writeStr(const char *filename, std::string value)
{
	CFile f(filename, "w");
	if (f)
		fprintf(f, "%s", value.c_str());
	return 0;
}

int CFile::write(const char *filename, const char *value)
{
	CFile f(filename, "w");
	if (!f)
		return -1;
	return fprintf(f, "%s", value);
}

std::string CFile::read(const std::string &filename)
{
	std::ifstream file(filename.c_str());
	if (!file.good())
		return std::string();
	std::stringstream ss;
	ss << file.rdbuf();
	return ss.str();
}

bool CFile::contains_word(const std::string &filename, const std::string &word_to_match)
{
	std::string word;
	std::ifstream file(filename.c_str());

	if (!file.good())
		return false;

	while (file >> word)
		if (word == word_to_match)
			return true;

	return false;
}

int CFile::parseIntHex(int *result, const char *filename, const char *module, int flags)
{
	CFile f(filename, "r");
	if (!f)
	{
		if (!(flags & CFILE_FLAGS_SUPPRESS_NOT_EXISTS))
			eDebugErrorOpenFile(module, filename);
		return -1;
	}
	if (fscanf(f, "%x", result) != 1)
	{
		if (!(flags & CFILE_FLAGS_SUPPRESS_READWRITE_ERROR))
			eDebugErrorReadFile(module, filename);
		return -2;
	}
	return 0;
}

int CFile::parseInt(int *result, const char *filename, const char *module, int flags)
{
	CFile f(filename, "r");
	if (!f)
	{
		if (!(flags & CFILE_FLAGS_SUPPRESS_NOT_EXISTS))
			eDebugErrorOpenFile(module, filename);
		return -1;
	}
	if (fscanf(f, "%d", result) != 1)
	{
		if (!(flags & CFILE_FLAGS_SUPPRESS_READWRITE_ERROR))
			eDebugErrorReadFile(module, filename);
		return -2;
	}
	return 0;
}

int CFile::writeIntHex(const char *filename, int value, const char *module, int flags)
{
	CFile f(filename, "w");
	if (!f)
	{
		if (!(flags & CFILE_FLAGS_SUPPRESS_NOT_EXISTS))
			eDebugErrorOpenFile(module, filename);
		return -1;
	}
	int ret = fprintf(f, "%x", value);
	if (ret < 0 && !(flags & CFILE_FLAGS_SUPPRESS_READWRITE_ERROR))
		eDebugErrorWriteFile(module, filename);
	return ret;
}

int CFile::writeInt(const char *filename, int value, const char *module, int flags)
{
	CFile f(filename, "w");
	if (!f)
	{
		if (!(flags & CFILE_FLAGS_SUPPRESS_NOT_EXISTS))
			eDebugErrorOpenFile(module, filename);
		return -1;
	}
	int ret = fprintf(f, "%d", value);
	if (ret < 0 && !(flags & CFILE_FLAGS_SUPPRESS_READWRITE_ERROR))
		eDebugErrorWriteFile(module, filename);
	return ret;
}

int CFile::writeStr(const char *filename, std::string value, const char *module, int flags)
{
	CFile f(filename, "w");
	if (f)
	{
		int ret = fprintf(f, "%s", value.c_str());
		if (ret < 0 && !(flags & CFILE_FLAGS_SUPPRESS_READWRITE_ERROR))
			eDebugErrorWriteFile(module, filename);
	}
	else if (!(flags & CFILE_FLAGS_SUPPRESS_NOT_EXISTS))
		eDebugErrorOpenFile(module, filename);
	return 0;
}

int CFile::write(const char *filename, const char *value, const char *module, int flags)
{
	CFile f(filename, "w");
	if (!f)
	{
		if (module && !(flags & CFILE_FLAGS_SUPPRESS_NOT_EXISTS))
			eDebugErrorOpenFile(module, filename);
		return -1;
	}
	int ret = fprintf(f, "%s", value);
	if (ret < 0 && !(flags & CFILE_FLAGS_SUPPRESS_READWRITE_ERROR))
		eDebugErrorWriteFile(module, filename);
	return ret;
}

std::string CFile::read(const std::string &filename, const char *module, int flags)
{
	std::ifstream file(filename.c_str());
	if (!file.good())
	{
		if (!(flags & CFILE_FLAGS_SUPPRESS_NOT_EXISTS))
			eDebugErrorOpenFile(module, filename.c_str());
		return std::string();
	}
	std::stringstream ss;
	ss << file.rdbuf();
	return ss.str();
}
