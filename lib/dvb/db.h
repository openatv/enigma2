#ifndef __db_h
#define __db_h

#ifndef SWIG
#include <lib/dvb/idvb.h>
#include <lib/dvb/frontend.h>
#include <lib/base/eptrlist.h>
#include <set>
#include <vector>
class ServiceDescriptionSection;
#endif

class eDVBDB: public iDVBChannelList
{
	DECLARE_REF(eDVBDB);
	static eDVBDB *instance;
	friend class eDVBDBQuery;
	friend class eDVBDBBouquetQuery;
	friend class eDVBDBSatellitesQuery;
	friend class eDVBDBProvidersQuery;

	struct channel
	{
		ePtr<iDVBFrontendParameters> m_frontendParameters;
	};

	std::map<eDVBChannelID, channel> m_channels;

	std::map<eServiceReferenceDVB, ePtr<eDVBService> > m_services;

	std::map<std::string, eBouquet> m_bouquets;

	bool m_numbering_mode;
#ifdef SWIG
	eDVBDB();
	~eDVBDB();
#endif
public:
// iDVBChannelList
	RESULT removeFlags(unsigned int flagmask, int dvb_namespace=-1, int tsid=-1, int onid=-1, unsigned int orb_pos=0xFFFFFFFF);
	RESULT removeServices(int dvb_namespace=-1, int tsid=-1, int onid=-1, unsigned int orb_pos=0xFFFFFFFF);
	RESULT removeService(const eServiceReference &service);
	RESULT addFlag(const eServiceReference &service, unsigned int flagmask);
	RESULT removeFlag(const eServiceReference &service, unsigned int flagmask);
	PyObject *readSatellites(SWIG_PYOBJECT(ePyObject) sat_list, SWIG_PYOBJECT(ePyObject) sat_dict, SWIG_PYOBJECT(ePyObject) tp_dict);
	PyObject *readTerrestrials(SWIG_PYOBJECT(ePyObject) ter_list, SWIG_PYOBJECT(ePyObject) tp_dict);
	PyObject *readCables(SWIG_PYOBJECT(ePyObject) cab_list, SWIG_PYOBJECT(ePyObject) tp_dict);
#ifndef SWIG
	RESULT removeFlags(unsigned int flagmask, eDVBChannelID chid, unsigned int orb_pos);
	RESULT removeServices(eDVBChannelID chid, unsigned int orb_pos);
	RESULT removeServices(iDVBFrontendParameters *feparm);

	RESULT addChannelToList(const eDVBChannelID &id, iDVBFrontendParameters *feparm);
	RESULT removeChannel(const eDVBChannelID &id);

	RESULT getChannelFrontendData(const eDVBChannelID &id, ePtr<iDVBFrontendParameters> &parm);

	RESULT addService(const eServiceReferenceDVB &referenc, eDVBService *service);
	RESULT getService(const eServiceReferenceDVB &reference, ePtr<eDVBService> &service);
	RESULT flush();

	RESULT startQuery(ePtr<iDVBChannelListQuery> &query, eDVBChannelQuery *q, const eServiceReference &source);

	RESULT getBouquet(const eServiceReference &ref, eBouquet* &bouquet);
//////
	void loadBouquet(const char *path);
	eServiceReference searchReference(int tsid, int onid, int sid);
	void searchAllReferences(std::vector<eServiceReference> &result, int tsid, int onid, int sid);
	eDVBDB();
	virtual ~eDVBDB();
	int renumberBouquet(eBouquet &bouquet, int startChannelNum = 1);
#endif
	void setNumberingMode(bool numberingMode);
	void renumberBouquet();
	void loadServicelist(const char *filename);
	static eDVBDB *getInstance() { return instance; }
	void reloadServicelist();
	void saveServicelist();
	void saveServicelist(const char *file);
	void reloadBouquets();
	void parseServiceData(ePtr<eDVBService> s, std::string str);
};

#ifndef SWIG
	// we have to add a possibility to invalidate here.
class eDVBDBQueryBase: public iDVBChannelListQuery
{
	DECLARE_REF(eDVBDBQueryBase);
protected:
	ePtr<eDVBDB> m_db;
	ePtr<eDVBChannelQuery> m_query;
	eServiceReference m_source;
public:
	eDVBDBQueryBase(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query);
	virtual int compareLessEqual(const eServiceReferenceDVB &a, const eServiceReferenceDVB &b);
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

class eDVBDBListQuery: public eDVBDBQueryBase
{
protected:
	std::list<eServiceReferenceDVB> m_list;
	std::list<eServiceReferenceDVB>::iterator m_cursor;
public:
	eDVBDBListQuery(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query);
	RESULT getNextResult(eServiceReferenceDVB &ref);
	int compareLessEqual(const eServiceReferenceDVB &a, const eServiceReferenceDVB &b);
};

class eDVBDBSatellitesQuery: public eDVBDBListQuery
{
public:
	eDVBDBSatellitesQuery(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query);
};

class eDVBDBProvidersQuery: public eDVBDBListQuery
{
public:
	eDVBDBProvidersQuery(eDVBDB *db, const eServiceReference &source, eDVBChannelQuery *query);
};
#endif // SWIG

#endif
