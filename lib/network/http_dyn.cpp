#include <lib/network/http_dyn.h>

eHTTPDyn::eHTTPDyn(eHTTPConnection *c, eString result): eHTTPDataSource(c), result(result)
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

eHTTPDynPathResolver::eHTTPDynPathResolver()
{
	dyn.setAutoDelete(true);
}

void eHTTPDynPathResolver::addDyn(eString request, eString path, eString (*function)(eString, eString, eString, eHTTPConnection*))
{
	dyn.push_back(new eHTTPDynEntry(request, path, function));
}

eHTTPDataSource *eHTTPDynPathResolver::getDataSource(eString request, eString path, eHTTPConnection *conn)
{
	eString p, opt;
	if (path.find('?')!=eString::npos)
	{
		p=path.left(path.find('?'));
		opt=path.mid(path.find('?')+1);
	}	else
	{
		p=path;
		opt="";
	}
	for (ePtrList<eHTTPDynEntry>::iterator i(dyn); i != dyn.end(); ++i)
		if ((i->path==p) && (i->request==request))
		{
			conn->code=-1;
			eString s=i->function(request, path, opt, conn);

			if (s)
				return new eHTTPDyn(conn, s);

			return new eHTTPError(conn, 500);
		}
	return 0;
}
