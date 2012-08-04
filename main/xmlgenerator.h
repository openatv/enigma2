#ifndef _main_xmlgenerator_h__
#define _main_xmlgenerator_h__

#include <cstdarg>
#include <cstdio>
#include <stack>
#include <string>

class XmlGenerator
{
private:
	FILE *m_file;
	bool m_indent;
	unsigned int m_level;
	std::stack<std::string> m_tags;

	void vprint(const char *fmt, va_list ap, bool newline);
	void __attribute__ ((__format__(__printf__, 2, 3))) print(const char *fmt, ...);
	void __attribute__ ((__format__(__printf__, 2, 3))) printLn(const char *fmt, ...);

	void open(const std::string &tag, bool newline);
	void commentFromErrno(const std::string &tag);

	std::string cDataEscape(const std::string &str);

public:
	XmlGenerator(FILE *f);
	~XmlGenerator();

	void open(const std::string &tag);
	void close();

	void comment(const std::string &str);

	void cDataFromCmd(const std::string &tag, const std::string &cmd);
	void cDataFromFile(const std::string &tag, const std::string &filename, const char *filter = 0);
	void cDataFromString(const std::string &tag, const std::string &str);

	void string(const std::string &tag, const std::string &str);
	void stringFromFile(const std::string &tag, const std::string &filename);
};

#endif
