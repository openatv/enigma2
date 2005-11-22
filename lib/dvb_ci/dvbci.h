#ifndef __dvbci_dvbci_h
#define __dvbci_dvbci_h

#include <lib/base/ebase.h>

#include <set>

class eDVBCISession;
class eDVBCIApplicationManagerSession;
class eDVBCICAManagerSession;
class eDVBCIMMISession;
class eDVBServicePMTHandler;

class eDVBCISlot: public iObject, public Object
{
DECLARE_REF(eDVBCISlot);
private:
	int slotid;
	int fd;
	void data(int);
	eSocketNotifier *notifier;

	int state;
	enum {stateRemoved, stateInserted};
	uint8_t prev_sent_capmt_version;
public:
	eDVBCISlot(eMainloop *context, int nr);
	~eDVBCISlot();
	
	int send(const unsigned char *data, size_t len);
	
	eDVBCIApplicationManagerSession *application_manager;
	eDVBCICAManagerSession *ca_manager;
	eDVBCIMMISession *mmi_session;
	
	int getSlotID();
	int reset();
	int initialize();
	int startMMI();
	int stopMMI();
	int answerText(int answer);
	int answerEnq(int answer, char *value);
	int getMMIState();
	int sendCAPMT(eDVBServicePMTHandler *ptr, const std::vector<uint16_t> &caids=std::vector<uint16_t>());
	uint8_t getPrevSentCAPMTVersion() const { return prev_sent_capmt_version; }
	void resetPrevSentCAPMTVersion() { prev_sent_capmt_version = 0xFF; }
};

struct CIPmtHandler
{
	eDVBServicePMTHandler *pmthandler;
	eDVBCISlot *usedby;
	CIPmtHandler()
		:pmthandler(NULL), usedby(NULL)
	{}
	CIPmtHandler( const CIPmtHandler &x )
		:pmthandler(x.pmthandler), usedby(x.usedby)
	{}
	CIPmtHandler( eDVBServicePMTHandler *ptr )
		:pmthandler(ptr), usedby(NULL)
	{}
	bool operator<(const CIPmtHandler &x) const { return x.pmthandler < pmthandler; }
};

typedef std::set<CIPmtHandler> PMTHandlerSet;

class eDVBCIInterfaces
{
DECLARE_REF(eDVBCIInterfaces);
	static eDVBCIInterfaces *instance;
private:
	eSmartPtrList<eDVBCISlot>	m_slots;
	eDVBCISlot *getSlot(int slotid);

	PMTHandlerSet m_pmt_handlers; 
public:
	eDVBCIInterfaces();
	~eDVBCIInterfaces();

	void addPMTHandler(eDVBServicePMTHandler *pmthandler);
	void removePMTHandler(eDVBServicePMTHandler *pmthandler);
	void gotPMT(eDVBServicePMTHandler *pmthandler);

	static eDVBCIInterfaces *getInstance();
	
	int reset(int slot);
	int initialize(int slot);
	int startMMI(int slot);
	int stopMMI(int slot);
	int answerText(int slot, int answer);
	int answerEnq(int slot, int answer, char *value);
	int getMMIState(int slot);
};

#endif
