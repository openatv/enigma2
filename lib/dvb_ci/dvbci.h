#ifndef __dvbci_dvbci_h
#define __dvbci_dvbci_h

#include <lib/base/ebase.h>

#include <set>
#include <queue>

class eDVBCISession;
class eDVBCIApplicationManagerSession;
class eDVBCICAManagerSession;
class eDVBCIMMISession;
class eDVBServicePMTHandler;
class eDVBCISlot;

struct queueData
{
	__u8 prio;
	unsigned char *data;
	unsigned int len;
	queueData( unsigned char *data, unsigned int len, __u8 prio = 0 )
		:prio(prio), data(data), len(len)
	{

	}
	bool operator < ( const struct queueData &a ) const
	{
		return prio < a.prio;
	}
};

class eDVBCISlot: public iObject, public Object
{
DECLARE_REF(eDVBCISlot);
private:
	int slotid;
	int fd;
	void data(int);
	eSocketNotifier *notifier;

	int state;
	std::map<uint16_t, uint8_t> running_services;
	eDVBCIApplicationManagerSession *application_manager;
	eDVBCICAManagerSession *ca_manager;
	eDVBCIMMISession *mmi_session;
	std::priority_queue<queueData> sendqueue;
public:
	enum {stateRemoved, stateInserted, stateInvalid, stateResetted};
	int use_count;

	eDVBCISlot(eMainloop *context, int nr);
	~eDVBCISlot();
	
	int send(const unsigned char *data, size_t len);

	void setAppManager( eDVBCIApplicationManagerSession *session );
	void setMMIManager( eDVBCIMMISession *session );
	void setCAManager( eDVBCICAManagerSession *session );

	eDVBCIApplicationManagerSession *getAppManager() { return application_manager; }
	eDVBCIMMISession *getMMIManager() { return mmi_session; }
	eDVBCICAManagerSession *getCAManager() { return ca_manager; }

	int getState() { return state; }
	int getSlotID();
	int reset();
	int startMMI();
	int stopMMI();
	int answerText(int answer);
	int answerEnq(char *value);
	int cancelEnq();
	int getMMIState();
	int sendCAPMT(eDVBServicePMTHandler *ptr, const std::vector<uint16_t> &caids=std::vector<uint16_t>());
	void removeService(uint16_t program_number=0xFFFF);
	int getNumOfServices() { return running_services.size(); }
	
	int enableTS(int enable, int tuner=0);

};

struct CIPmtHandler
{
	eDVBServicePMTHandler *pmthandler;
	eDVBCISlot *cislot;
	CIPmtHandler()
		:pmthandler(NULL), cislot(NULL)
	{}
	CIPmtHandler( const CIPmtHandler &x )
		:pmthandler(x.pmthandler), cislot(x.cislot)
	{}
	CIPmtHandler( eDVBServicePMTHandler *ptr )
		:pmthandler(ptr), cislot(NULL)
	{}
	bool operator==(const CIPmtHandler &x) const { return x.pmthandler == pmthandler; }
};

typedef std::list<CIPmtHandler> PMTHandlerList;

class eDVBCIInterfaces
{
DECLARE_REF(eDVBCIInterfaces);
	static eDVBCIInterfaces *instance;
private:
	eSmartPtrList<eDVBCISlot> m_slots;
	eDVBCISlot *getSlot(int slotid);

	PMTHandlerList m_pmt_handlers; 
public:
	eDVBCIInterfaces();
	~eDVBCIInterfaces();

	void addPMTHandler(eDVBServicePMTHandler *pmthandler);
	void removePMTHandler(eDVBServicePMTHandler *pmthandler);
	void recheckPMTHandlers();
	void gotPMT(eDVBServicePMTHandler *pmthandler);
	void ciRemoved(eDVBCISlot *slot);
	int getSlotState(int slot);

	static eDVBCIInterfaces *getInstance();
	
	int reset(int slot);
	int initialize(int slot);
	int startMMI(int slot);
	int stopMMI(int slot);
	int answerText(int slot, int answer);
	int answerEnq(int slot, char *value);
	int cancelEnq(int slot);
	int getMMIState(int slot);
	int enableTS(int slot, int enable);
	int sendCAPMT(int slot);
};

#endif
