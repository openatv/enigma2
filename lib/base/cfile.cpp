#include <fstream>
#include <sstream>
#include <sys/vfs.h>
#include <linux/magic.h>
#include <lib/base/eerror.h>

#include "cfile.h"

#define eDebugErrorOpenFile(MODULE, FILENAME) eDebug("[%s] Error %d: Unable to open file '%s'!  (%m)", MODULE, errno, FILENAME)
#define eDebugErrorReadFile(MODULE, FILENAME) eDebug("[%s] Error %d: Unable to read from file '%s'!  (%m)", MODULE, errno, FILENAME)
#define eDebugErrorWriteFile(MODULE, FILENAME) eDebug("[%s] Error %d: Unable to write to file '%s'!  (%m)", MODULE, errno, FILENAME)

off_t CFile::getRecordingSplitSize(int fd, unsigned int packetSize)
{
	struct statfs fs = {};
	if (!packetSize || fstatfs(fd, &fs) < 0)
		return -1;
	// CIFS and SMB2 values are also needed with older receiver kernel headers.
	const unsigned int type = static_cast<unsigned int>(fs.f_type);
	if (type == MSDOS_SUPER_MAGIC || type == NFS_SUPER_MAGIC || type == FUSE_SUPER_MAGIC
		|| type == 0xff534d42U || type == 0xfe534d42U || type == SMB_SUPER_MAGIC)
		return ((1LL << 31) - 1) / packetSize * packetSize;
	return 0;
}

int CFile::parseIntHex(int *result, const char *fileName)
{
	CFile f(fileName, "r");
	if (!f)
		return -1;
	if (fscanf(f, "%x", result) != 1)
		return -2;
	return 0;
}

int CFile::parseUint32Hex(uint32_t *result, const char *filename)
{
	CFile f(filename, "r");
	if (!f)
		return -1;
	if (fscanf(f, "0x%x", result) != 1)
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

int CFile::writeUint32Hex(const char *filename, uint32_t value)
{
	CFile f(filename, "w");
	if (!f)
		return -1;
	return fprintf(f, "0x%x", value);
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
