#include <string.h>

#include <iostream>
#include <fstream>
#include <sstream>

#include <lib/network/uri.h>

URI::URI()
{
	m_valid = false;
}

URI::URI(const std::string &url)
{
	m_valid = Parse(url);
}

bool URI::Parse(const std::string &u)
{
	const char *tmpstr;
	const char *curstr;
	int len;
	int i;
	int userpass_flag;
	int bracket_flag;

	m_url = u;
	m_scheme = m_host = m_port = m_path = m_query = m_fragment = m_username = m_password = std::string();

	curstr = m_url.c_str();

	/*
	 * <scheme>:<scheme-specific-part>
	 * <scheme> := [a-z\+\-\.]+
	 *			 upper case = lower case for resiliency
	 */
	/* Read scheme */
	tmpstr = strchr(curstr, ':');

	if (NULL == tmpstr)
	{
		/* Not found the character */
		return false;
	}

	/* Get the scheme length */
	len = tmpstr - curstr;
	/* Check restrictions */
	for(i = 0; i < len; i++)
	{
		if (!is_scheme_char(curstr[i]))
		{
			/* Invalid format */
			return false;
		}
	}

	/* Copy the scheme to the storage */
	m_scheme = std::string(curstr, len);

	/* Make the character to lower if it is upper case. */
	for(i = 0; i < len; i++)
	{
		m_scheme[i] = tolower(m_scheme[i]);
	}

	/* Skip ':' */
	tmpstr++;
	curstr = tmpstr;

	/*
	 * //<user>:<password>@<host>:<port>/<url-path>
	 * Any ":", "@" and "/" must be encoded.
	 */
	/* Eat "//" */
	for(i = 0; i < 2; i++)
	{
		if ('/' != *curstr)
		{
			return false;
		}
		curstr++;
	}

	/* Check if the user (and password) are specified. */
	userpass_flag = 0;
	tmpstr = curstr;
	while ('\0' != *tmpstr)
	{
		if ('@' == *tmpstr)
		{
			/* Username and password are specified */
			userpass_flag = 1;
			break;
		}
		else if ('/' == *tmpstr)
		{
			/* End of <host>:<port> specification */
			userpass_flag = 0;
			break;
		}
		tmpstr++;
	}

	/* User and password specification */
	tmpstr = curstr;
	if (userpass_flag)
	{
		/* Read username */
		while ('\0' != *tmpstr && ':' != *tmpstr && '@' != *tmpstr)
		{
			tmpstr++;
		}
		len = tmpstr - curstr;

		m_username = std::string(curstr, len);

		/* Proceed current pointer */
		curstr = tmpstr;
		if (':' == *curstr)
		{
			/* Skip ':' */
			curstr++;
			/* Read password */
			tmpstr = curstr;
			while ('\0' != *tmpstr && '@' != *tmpstr) {
				tmpstr++;
			}
			len = tmpstr - curstr;
			m_password = std::string(curstr, len);
			curstr = tmpstr;
		}

		/* Skip '@' */
		if ('@' != *curstr) {
			return false;
		}
		curstr++;
	}

	if ('[' == *curstr)
	{
		bracket_flag = 1;
	}
	else
	{
		bracket_flag = 0;
	}
	/* Proceed on by delimiters with reading host */
	tmpstr = curstr;
	while ('\0' != *tmpstr)
	{
		if (bracket_flag && ']' == *tmpstr)
		{
			/* End of IPv6 address. */
			tmpstr++;
			break;
		}
		else if (!bracket_flag && (':' == *tmpstr || '/' == *tmpstr))
		{
			/* Port number is specified. */
			break;
		}
		tmpstr++;
	}
	len = tmpstr - curstr;

	m_host = std::string(curstr, len);

	curstr = tmpstr;

	/* Is port number specified? */
	if (':' == *curstr)
	{
		curstr++;
		/* Read port number */
		tmpstr = curstr;
		while ('\0' != *tmpstr && '/' != *tmpstr)
		{
			tmpstr++;
		}
		len = tmpstr - curstr;
		m_port = std::string(curstr, len);
		curstr = tmpstr;
	}

	/* End of the string */
	if ('\0' == *curstr)
	{
		return true;
	}

	/* Skip '/' */
	if ('/' != *curstr)
	{
		return false;
	}
	curstr++;

	/* Parse path */
	tmpstr = curstr;
	while ('\0' != *tmpstr && '#' != *tmpstr  && '?' != *tmpstr)
	{
		tmpstr++;
	}
	len = tmpstr - curstr;

	/* assign path */
	m_path = std::string(curstr, len);

	curstr = tmpstr;

	/* Is query specified? */
	if ('?' == *curstr)
	{
		/* Skip '?' */
		curstr++;
		/* Read query */
		tmpstr = curstr;
		while ('\0' != *tmpstr && '#' != *tmpstr)
		{
			tmpstr++;
		}
		len = tmpstr - curstr;

		/* assign query */
		m_query = std::string(curstr, len);

		curstr = tmpstr;
	}

	/* Is fragment specified? */
	if ('#' == *curstr)
	{
		/* Skip '#' */
		curstr++;
		/* Read fragment */
		tmpstr = curstr;
		while ('\0' != *tmpstr)
		{
			tmpstr++;
		}
		len = tmpstr - curstr;

		/* assign fragment */
		m_fragment = std::string(curstr, len);

		curstr = tmpstr;
	}

	/* parse key value parameters from query 
	 * multiple parameters with the same key
	 * not supported at the moment
	 */
	std::istringstream ss(m_query);
	std::string key, value;
	while (!ss.eof())
	{
		std::getline(ss, key, '=');
		if (!key.size())
			break;
		std::getline(ss, value, '&');
		m_parameters[key] = value;
	}

	return true;
}

std::string URI::Query(const std::string &key)
{
	std::map<std::string,std::string>::iterator it = m_parameters.find(key);
	if (it != m_parameters.end())
		return it->second;
	return std::string();
}

