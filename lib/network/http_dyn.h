#ifndef __http_dyn_h_
#define __http_dyn_h_
#include <string>
#include <lib/network/httpd.h>

class eHTTPDyn: public eHTTPDataSource
{
	std::string result;
	int wptr, size;
public:
	eHTTPDyn(eHTTPConnection *c, std::string result);
	~eHTTPDyn();
	int doWrite(int);
};

class eHTTPDynPathResolver: public eHTTPPathResolver
{
	struct eHTTPDynEntry
	{
		std::string request, path;
		std::string (*function)(std::string request, std::string path, std::string opt, eHTTPConnection *content);
		
		eHTTPDynEntry(std::string request, std::string path, std::string (*function)(std::string, std::string, std::string, eHTTPConnection *)): request(request), path(path), function(function)
		{
		}
	};
	ePtrList<eHTTPDynEntry> dyn;
public:
	void addDyn(std::string request, std::string path, std::string (*function)(std::string, std::string, std::string, eHTTPConnection *conn));
	eHTTPDynPathResolver();
	eHTTPDataSource *getDataSource(std::string request, std::string path, eHTTPConnection *conn);
};

#endif
