#ifndef __http_dyn_h_
#define __http_dyn_h_
#include <string>
#include <lib/network/httpd.h>

class eHTTPDyn: public eHTTPDataSource
{
	eString result;
	int wptr, size;
public:
	eHTTPDyn(eHTTPConnection *c, eString result);
	~eHTTPDyn();
	int doWrite(int);
};

class eHTTPDynPathResolver: public eHTTPPathResolver
{
	struct eHTTPDynEntry
	{
		eString request, path;
		eString (*function)(eString request, eString path, eString opt, eHTTPConnection *content);
		
		eHTTPDynEntry(eString request, eString path, eString (*function)(eString, eString, eString, eHTTPConnection *)): request(request), path(path), function(function)
		{
		}
	};
	ePtrList<eHTTPDynEntry> dyn;
public:
	void addDyn(eString request, eString path, eString (*function)(eString, eString, eString, eHTTPConnection *conn));
	eHTTPDynPathResolver();
	eHTTPDataSource *getDataSource(eString request, eString path, eHTTPConnection *conn);
};

#endif
