#include <fstream>
#include <lib/base/eerror.h>
#include "xmlgenerator.h"

XmlGenerator::XmlGenerator(FILE *f) : m_file(f), m_indent(true), m_level(0)
{
	::fprintf(m_file, "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n");
}

XmlGenerator::~XmlGenerator()
{
}

void XmlGenerator::vprint(const char *fmt, va_list ap, bool newline)
{
	unsigned int i;

	if (m_indent)
		for (i = 0; i < m_level; i++)
			::fprintf(m_file, "\t");

	::vfprintf(m_file, fmt, ap);

	if (newline)
		::fprintf(m_file, "\n");
}

void XmlGenerator::print(const char *fmt, ...)
{
	va_list ap;

	::va_start(ap, fmt);
	vprint(fmt, ap, false);
	::va_end(ap);
}

void XmlGenerator::printLn(const char *fmt, ...)
{
	va_list ap;

	::va_start(ap, fmt);
	vprint(fmt, ap, true);
	::va_end(ap);
}

void XmlGenerator::open(const std::string &tag, bool newline)
{
	if (newline) {
		printLn("<%s>", tag.c_str());
	} else {
		print("<%s>", tag.c_str());
		m_indent = false;
	}

	m_tags.push(tag);
	m_level++;
}

void XmlGenerator::open(const std::string &tag)
{
	open(tag, true);
}

void XmlGenerator::close()
{
	ASSERT(!m_tags.empty());
	ASSERT(m_level > 0);
	m_level--;

	printLn("</%s>", m_tags.top().c_str());
	m_indent = true;

	m_tags.pop();
}

void XmlGenerator::comment(const std::string &str)
{
	printLn("<!-- %s -->", str.c_str());
}

void XmlGenerator::commentFromErrno(const std::string &tag)
{
	open(tag);
	comment(strerror(errno));
	close();
}

std::string XmlGenerator::cDataEscape(const std::string &str)
{
	const std::string search = "]]>";
	const std::string replace = "]]]]><![CDATA[>";
	std::string ret;
	size_t pos = 0, opos;

	for (;;) {
		opos = pos;
		pos = str.find(search, opos);
		if (pos == std::string::npos)
			break;
		ret.append(str, opos, pos - opos);
		ret.append(replace);
		pos += search.size();
	}

	ret.append(str, opos, std::string::npos);
	return ret;
}

void XmlGenerator::cDataFromCmd(const std::string &tag, const std::string &cmd)
{
	FILE *pipe = ::popen(cmd.c_str(), "re");

	if (pipe == 0) {
		commentFromErrno(tag);
		return;
	}

	std::string result;
	char *lineptr = NULL;
	size_t n = 0;

	for (;;) {
		ssize_t ret = ::getline(&lineptr, &n, pipe);
		if (ret < 0)
			break;
		result.append(lineptr, ret);
	}

	if (lineptr)
		::free(lineptr);

	::pclose(pipe);
	cDataFromString(tag, result);
}

void XmlGenerator::cDataFromFile(const std::string &tag, const std::string &filename, const char *filter)
{
	std::ifstream in(filename.c_str());
	std::string line;
	std::string content;

	if (!in.good()) {
		commentFromErrno(tag);
		return;
	}

	while (std::getline(in, line))
		if (!filter || !line.find(filter))
			content += line + '\n';

	in.close();
	cDataFromString(tag, content);
}

void XmlGenerator::cDataFromString(const std::string &tag, const std::string &str)
{
	bool indent = false;

	open(tag);
	printLn("<![CDATA[");
	std::swap(m_indent, indent);
	print("%s", cDataEscape(str).c_str());
	printLn("]]>");
	std::swap(m_indent, indent);
	close();
}

void XmlGenerator::string(const std::string &tag, const std::string &str)
{
	open(tag, false);
	print("%s", str.c_str());
	close();
}

void XmlGenerator::stringFromFile(const std::string &tag, const std::string &filename)
{
	std::ifstream in(filename.c_str());
	std::string line;

	if (!in.good()) {
		commentFromErrno(tag);
		return;
	}

	std::getline(in, line);
	in.close();
	string(tag, line);
}
