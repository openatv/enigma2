#ifndef __db_h
#define __db_h

#include <lib/base/eptrlist.h>
#include <lib/dvb/idvb.h>
#include <set>

class ServiceDescriptionSection;

class eDVBDB: public iDVBChannelList
{
DECLARE_REF(eDVBDB);
	friend class eDVBDBQuery;
	friend class eDVBDBBouquetQuery;
private:
	struct channel
	{
		ePtr<iDVBFrontendParameters> m_frontendParameters;
	};
	
	std::map<eDVBChannelID, channel> m_channels;
	
	std::map<eServiceReferenceDVB, ePtr<eDVBService> > m_services;
	
	std::map<std::string, eBouquet> m_bouquets;
public:
	void load();
	void save();

	void loadBouquet(const char *path);
	void saveBouquet(const char *path);
	void loadBouquets();
	void saveBouquets();

	eDVBDB();
	virtual ~eDVBDB();
	
	RESULT addChannelToList(const eDVBChannelID &id, iDVBFrontendParameters *feparm);
	RESULT removeChannel(const eDVBChannelID &id);

	RESULT getChannelFrontendData(const eDVBChannelID &id, ePtr<iDVBFrontendParameters> &parm);
	
	RESULT addService(const eServiceReferenceDVB &service, eDVBService *service);
	RESULT getService(const eServiceReferenceDVB &reference, ePtr<eDVBService> &service);

	RESULT startQuery(ePtr<iDVBChannelListQuery> &query, eDVBChannelQuery *query, const eServiceReference &source);

	RESULT getBouquet(const eServiceReference &ref, const eBouquet* &bouquet);
};

	// we have to add a possibility to invalidate here.
class eDVBDBQueryBase: public iDVBChannelListQuery
{
DECLARE_REF(eDVBDBQueryBase);
protected:
	std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator m_cursor;
	ePtr<eDVBDB> m_db;
	ePtr<eDVBChannelQuery> m_query;
	eServiceReference m_source;
public:
	eDVBDBQueryBase(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query);
	int compareLessEqual(const eServiceReferenceDVB &a, const eServiceReferenceDVB &b);
};

class eDVBDBQuery: public eDVBDBQueryBase
{
	std::map<eServiceReferenceDVB, ePtr<eDVBService> >::iterator m_cursor;
public:
	eDVBDBQuery(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query);
	RESULT getNextResult(eServiceReferenceDVB &ref);
};

class eDVBDBBouquetQuery: public eDVBDBQueryBase
{
	std::list<eServiceReference>::iterator m_cursor;
public:
	eDVBDBBouquetQuery(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query);
	RESULT getNextResult(eServiceReferenceDVB &ref);
};

#endif
