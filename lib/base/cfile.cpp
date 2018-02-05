#include <fstream>
#include <sstream>

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

	while(file >> word)
		if(word == word_to_match)
			return true;

	return false;
}