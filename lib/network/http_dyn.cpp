#include <lib/network/http_dyn.h>

DEFINE_REF(eHTTPDyn);
eHTTPDyn::eHTTPDyn(eHTTPConnection *c, std::string result): eHTTPDataSource(c), result(result)
{
	wptr=0;
	char buffer[10];
	snprintf(buffer, 10, "%d", size=result.length());
	c->local_header["Content-Length"]=std::string(buffer);
	if (c->code == -1)
	{
		c->code=200;
		c->code_descr="OK";
	}
}

eHTTPDyn::~eHTTPDyn()
{
}

int eHTTPDyn::doWrite(int hm)
{
	int tw=size-wptr;
	if (tw>hm)
		tw=hm;
	if (tw<=0)
		return -1;
	connection->writeBlock(result.c_str()+wptr, tw);
	wptr+=tw;
	return (size > wptr) ? 1 : -1;
}

DEFINE_REF(eHTTPDynPathResolver);
DEFINE_REF(eHTTPDynPathResolver::eHTTPDynEntry);

eHTTPDynPathResolver::eHTTPDynPathResolver()
{
}

void eHTTPDynPathResolver::addDyn(std::string request, std::string path, std::string (*function)(std::string, std::string, std::string, eHTTPConnection*))
{
	dyn.push_back(new eHTTPDynEntry(request, path, function));
}

RESULT eHTTPDynPathResolver::getDataSource(eHTTPDataSourcePtr &ptr, std::string request, std::string path, eHTTPConnection *conn)
{
	std::string p, opt;
	if (path.find('?')!=std::string::npos)
	{
		p=path.substr(0, path.find('?'));
		opt=path.substr(path.find('?')+1);
	}	else
	{
		p=path;
		opt="";
	}
	for (eSmartPtrList<eHTTPDynEntry>::iterator i(dyn); i != dyn.end(); ++i)
		if ((i->path==p) && (i->request==request))
		{
			conn->code=-1;
			std::string s=i->function(request, path, opt, conn);

			if (!s.empty())
			{
				ptr = new eHTTPDyn(conn, s);
				return 0;
			}

			ptr = new eHTTPError(conn, 500);
			return 0;
		}
	ptr = 0;
	return -1;
}
