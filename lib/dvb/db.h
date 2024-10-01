#ifndef __db_h
#define __db_h

#ifndef SWIG
#include <lib/dvb/idvb.h>
#include <lib/dvb/frontend.h>
#include <lib/base/eptrlist.h>
#include <set>
#include <vector>
#include <sstream>
class ServiceDescriptionSection;

struct LCNData
{
private:
	bool FOUND;
	int SIGNAL;
	int LCN_BROADCAST;
	int LCN_GUI;
	int LCN_SCANNED;
	int NS;
	std::string PROVIDER;
	std::string PROVIDER_GUI;
	std::string SERVICENAME;
	std::string SERVICENAME_GUI;

	std::vector<std::string> split_str(std::string s)
	{
		std::vector<std::string> tokens;
		std::string token;
		std::stringstream str(s);
		while (getline(str, token, ':')) {
			tokens.push_back(token);
		}
		return tokens;
	}

public:
	LCNData()
	{
		LCN_BROADCAST = 0;
		LCN_SCANNED = 0;
		LCN_GUI = 0;
		SIGNAL = -1;
		PROVIDER = "";
		PROVIDER_GUI = "";
		SERVICENAME = "";
		SERVICENAME_GUI = "";
		FOUND = true;
		NS = 0;
	}

	eServiceReferenceDVB parse(const char *line, int version)
	{
		int onid;
		int tsid;
		int sid;
		char buffer[2048];
		buffer[0] = '\0';

		// will be removed
		if (version == 1)
		{
			if (sscanf(line, "%x:%x:%x:%x:%d:%d", &NS, &onid, &tsid, &sid, &LCN_BROADCAST, &SIGNAL) == 6)
				return eServiceReferenceDVB(eDVBNamespace(NS), eTransportStreamID(tsid), eOriginalNetworkID(onid), eServiceID(sid), 0);
			else
				return eServiceReferenceDVB();
		}

		if (sscanf(line, "%x:%x:%x:%x:%d:%d:%d:%d:%[^\n]", &sid, &tsid, &onid, &NS, &SIGNAL, &LCN_BROADCAST, &LCN_SCANNED, &LCN_GUI, buffer) == 9)
		{
			// eDebug("[eDVBDB] LCNData parse %X:%X:%X:%X: LCN_BROADCAST %d LCN_SCANNED %d LCN_GUI %d", sid, tsid, onid, ns, LCN_BROADCAST, LCN_SCANNED, LCN_GUI);
			auto Data = split_str(buffer);
			if (Data.size() > 2)
			{
				PROVIDER = Data[0];
				PROVIDER_GUI = Data[1];
				if (Data.size() == 4)
				{
					SERVICENAME = Data[2];
					SERVICENAME_GUI = Data[3];
				}
			}
			return eServiceReferenceDVB(eDVBNamespace(NS), eTransportStreamID(tsid), eOriginalNetworkID(onid), eServiceID(sid), 0);
		}
		return eServiceReferenceDVB();
	}

	int getLCN()
	{
		return (LCN_GUI != 0) ? LCN_GUI : (LCN_SCANNED != 0) ? LCN_SCANNED : LCN_BROADCAST;
	}

	std::string getServiceNameGui()
	{
		return SERVICENAME_GUI;
	}

	std::string getProviderNameGui()
	{
		return PROVIDER_GUI;
	}

	void Update(uint16_t lcn, uint32_t signal)
	{
		LCN_BROADCAST = lcn;
		SIGNAL = signal;
		FOUND = true;
	}

	void write(FILE *lf, const eServiceReferenceDVB &key)
	{
		if (FOUND)
		{
			int sid = key.getServiceID().get();
			int tsid = key.getTransportStreamID().get();
			int onid = key.getOriginalNetworkID().get();
			int ns = key.getDVBNamespace().get();
			// eDebug("[eDVBDB] LCNData write %X:%X:%X:%X: LCN_BROADCAST %d LCN_SCANNED %d LCN_GUI %d", sid, tsid, onid, ns, LCN_BROADCAST, LCN_SCANNED, LCN_GUI);
			fprintf(lf, "%X:%X:%X:%X:%d:%d:%d:%d:%s:%s:%s:%s\n", sid, tsid, onid, ns, SIGNAL, LCN_BROADCAST, LCN_SCANNED, LCN_GUI, PROVIDER.c_str(), PROVIDER_GUI.c_str(), SERVICENAME.c_str(), SERVICENAME_GUI.c_str());
		}
	}

	void resetFound(int dvb_namespace)
	{
		if(dvb_namespace == 0 || NS == dvb_namespace)
			FOUND = false;
	}

};

#endif

class eDVBDB: public iDVBChannelList
{
	DECLARE_REF(eDVBDB);
	static eDVBDB *instance;
	friend class eDVBDBQuery;
	friend class eDVBDBBouquetQuery;
	friend class eDVBDBSatellitesQuery;
	friend class eDVBDBProvidersQuery;
	friend class eRTSPStreamClient;

	struct channel
	{
		ePtr<iDVBFrontendParameters> m_frontendParameters;
	};

	std::map<eDVBChannelID, channel> m_channels;

	std::map<eServiceReferenceDVB, ePtr<eDVBService> > m_services;

	std::map<std::string, eBouquet> m_bouquets;

	bool m_load_unlinked_userbouquets;
	int m_numbering_mode;
	int m_max_number;
#ifdef SWIG
	eDVBDB();
	~eDVBDB();
#endif
private:
	void loadServiceListV5(FILE * f);
	std::map<eServiceReferenceDVB, LCNData> m_lcnmap;
public:
// iDVBChannelList
	RESULT removeFlags(unsigned int flagmask, int dvb_namespace=-1, int tsid=-1, int onid=-1, unsigned int orb_pos=0xFFFFFFFF);
	RESULT removeServices(int dvb_namespace=-1, int tsid=-1, int onid=-1, unsigned int orb_pos=0xFFFFFFFF);
	RESULT removeService(const eServiceReference &service);
	PyObject *getFlag(const eServiceReference &service);
	PyObject *getCachedPid(const eServiceReference &service, int id);
	bool isCrypted(const eServiceReference &service);
	bool hasCAID(const eServiceReference &service, unsigned int caid);
	RESULT addCAID(const eServiceReference &service, unsigned int caid);
	RESULT addFlag(const eServiceReference &service, unsigned int flagmask);
	RESULT removeFlag(const eServiceReference &service, unsigned int flagmask);
	void removeServicesFlag(unsigned int flagmask);
	PyObject *readSatellites(SWIG_PYOBJECT(ePyObject) sat_list, SWIG_PYOBJECT(ePyObject) sat_dict, SWIG_PYOBJECT(ePyObject) tp_dict);
	PyObject *readTerrestrials(SWIG_PYOBJECT(ePyObject) ter_list, SWIG_PYOBJECT(ePyObject) tp_dict);
	PyObject *readCables(SWIG_PYOBJECT(ePyObject) cab_list, SWIG_PYOBJECT(ePyObject) tp_dict);
	PyObject *readATSC(SWIG_PYOBJECT(ePyObject) atsc_list, SWIG_PYOBJECT(ePyObject) tp_dict);
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
	void searchAllReferences(std::vector<eServiceReference> &result, int tsid, int onid, int sid);
	eDVBDB();
	virtual ~eDVBDB();
	int renumberBouquet(eBouquet &bouquet, int startChannelNum = 1);
	void addLcnToDB(int ns, int onid, int tsid, int sid, uint16_t lcn, uint32_t signal);
	void saveLcnDB();
#endif
	void resetLcnDB(int dvb_namespace=0);
	eServiceReference searchReference(int tsid, int onid, int sid);
	void setNumberingMode(int numberingMode);
	void setLoadUnlinkedUserbouquets(bool value) { m_load_unlinked_userbouquets=value; }
	void renumberBouquet();
	void loadServicelist(const char *filename);
	static eDVBDB *getInstance() { return instance; }
	void reloadServicelist();
	void saveServicelist();
	void saveServicelist(const char *file);
	void reloadBouquets();
	bool isValidService(int tsid, int onid, int sid);
	void parseServiceData(ePtr<eDVBService> s, std::string str);
	int getMaxNumber() const { return m_max_number; }
	PyObject *getAllServicesRaw(int type=0);
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
