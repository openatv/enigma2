#ifndef __db_h
#define __db_h

#include <lib/dvb/idvb.h>
#include <set>

class eDVBService: public iObject
{
	DECLARE_REF;
public:
	eDVBService();
	std::string m_service_name;
	std::string m_provider_name;
	
	int m_flags;
	std::set<int> m_ca;
	std::map<int,int> m_cache;
	virtual ~eDVBService();
	
	eDVBService &operator=(const eDVBService &);
};

class ServiceDescriptionTable;

class eDVBDB: public iDVBChannelList
{
DECLARE_REF;
private:
	struct channel
	{
		ePtr<iDVBFrontendParameters> m_frontendParameters;
	};
	
	std::map<eDVBChannelID, channel> m_channels;
	
	std::map<eServiceReferenceDVB, ePtr<eDVBService> > m_services;
public:
	eDVBDB();
	virtual ~eDVBDB();
	
	RESULT addChannelToList(const eDVBChannelID &id, iDVBFrontendParameters *feparm);
	RESULT removeChannel(const eDVBChannelID &id);

	RESULT getChannelFrontendData(const eDVBChannelID &id, ePtr<iDVBFrontendParameters> &parm);
	
	RESULT addService(const eServiceReferenceDVB &service, eDVBService *service);
	RESULT getService(const eServiceReferenceDVB &reference, ePtr<eDVBService> &service);
};

#endif
