#ifndef __db_h
#define __db_h

#include <lib/dvb/idvb.h>
#include <set>

class ServiceDescriptionTable;

class eDVBDB: public iDVBChannelList
{
DECLARE_REF(eDVBDB);
	friend class eDVBDBQuery;
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

	RESULT startQuery(ePtr<iDVBChannelListQuery> &query, eDVBChannelQuery *query);
};

	// we have to add a possibility to invalidate here.
class eDVBDBQuery: public iDVBChannelListQuery
{
DECLARE_REF(eDVBDBQuery);
private:
	std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator m_cursor;
	ePtr<eDVBDB> m_db;
	ePtr<eDVBChannelQuery> m_query;
public:
	eDVBDBQuery(eDVBDB *db, eDVBChannelQuery *query);
	virtual RESULT getNextResult(eServiceReferenceDVB &ref);
};

#endif
