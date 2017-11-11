#ifndef __network_uri_h
#define __network_uri_h

#include <ctype.h>

#include <string>
#include <map>

/*
 * URI parser based on http://draft.scyphus.co.jp/lang/c/url_parser.html
 */

class URI
{
private:
	bool m_valid;
	std::string m_url;
	std::string m_scheme;
	std::string m_host;
	std::string m_port;
	std::string m_path;
	std::string m_query;
	std::string m_fragment;
	std::string m_username;
	std::string m_password;
	std::map<std::string,std::string> m_parameters;
	/*
	 * Check whether the character is permitted in scheme string
	 */
	static inline int is_scheme_char(int c)
	{
		return (!isalpha(c) && '+' != c && '-' != c && '.' != c) ? 0 : 1;
	};
public:
	URI();
	URI(const std::string &);
	bool Parse(const std::string &);
	bool Valid() { return m_valid; };
	std::string Scheme() { return m_scheme; };
	std::string Host() { return m_host; };
	std::string Port() { return m_port; };
	std::string Path() { return m_path; };
	std::string Query() { return m_query; };
	std::string Fragment() { return m_fragment; };
	std::string Username() { return m_username; };
	std::string Password() { return m_password; };
	std::string Query(const std::string &);
};

#endif /* __network_uri_h */
