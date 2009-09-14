#include <lib/base/init_num.h>
#include <lib/base/init.h>
#include <lib/network/http.h>

eHTTPServer *eHTTPServer::m_instance;

RESULT eHTTPServer::getDynResolver(eHTTPDynPathResolverPtr &ptr)
{
	ptr = m_dyn;
	if (!m_dyn)
		return -1;
	return 0;
}

RESULT eHTTPServer::getFileResolver(eHTTPFilePathResolverPtr &ptr)
{
	ptr = m_file;
	if (!m_file)
		return -1;
	return 0;
}

eHTTPServer::eHTTPServer(): m_httpd(8080, eApp)
{
	m_instance = this;
	m_dyn = new eHTTPDynPathResolver();
	m_file = new eHTTPFilePathResolver();
	
	m_httpd.addResolver(m_dyn);
	m_httpd.addResolver(m_file);
}

eAutoInitP0<eHTTPServer> init_eHTTPServer(eAutoInitNumbers::network, "main http server");
