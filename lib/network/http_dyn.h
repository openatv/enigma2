#ifndef __http_dyn_h_
#define __http_dyn_h_
#include <string>
#include <lib/network/httpd.h>

class eHTTPDyn: public eHTTPDataSource
{
	DECLARE_REF(eHTTPDyn);
	std::string result;
	int wptr, size;
public:
	eHTTPDyn(eHTTPConnection *c, std::string result);
	~eHTTPDyn();
	int doWrite(int);
};

class eHTTPDynPathResolver: public iHTTPPathResolver
{
	DECLARE_REF(eHTTPDynPathResolver);
	struct eHTTPDynEntry: public iObject
	{
		DECLARE_REF(eHTTPDynEntry);
	public:
		std::string request, path;
		std::string (*function)(std::string request, std::string path, std::string opt, eHTTPConnection *content);
		
		eHTTPDynEntry(std::string request, std::string path, std::string (*function)(std::string, std::string, std::string, eHTTPConnection *)): request(request), path(path), function(function)
		{
		}
	};
	eSmartPtrList<eHTTPDynEntry> dyn;
public:
	void addDyn(std::string request, std::string path, std::string (*function)(std::string, std::string, std::string, eHTTPConnection *conn));
	eHTTPDynPathResolver();
	RESULT getDataSource(eHTTPDataSourcePtr &ptr, std::string request, std::string path, eHTTPConnection *conn);
};

#endif
