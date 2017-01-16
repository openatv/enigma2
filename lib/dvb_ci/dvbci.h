#ifndef __dvbci_dvbci_h
#define __dvbci_dvbci_h

#ifndef SWIG

#include <lib/base/ebase.h>
#include <lib/service/iservice.h>
#ifdef __sh__
#include <lib/base/thread.h>
#endif
#include <lib/python/python.h>
#include <set>
#include <queue>

class eDVBCISession;
class eDVBCIApplicationManagerSession;
class eDVBCICAManagerSession;
class eDVBCIMMISession;
class eDVBServicePMTHandler;
class eDVBCISlot;
class eDVBCIInterfaces;

struct queueData
{
	uint8_t prio;
	unsigned char *data;
	unsigned int len;
	queueData( unsigned char *data, unsigned int len, uint8_t prio = 0 )
		:prio(prio), data(data), len(len)
	{

	}
	bool operator < ( const struct queueData &a ) const
	{
		return prio < a.prio;
	}
};

enum data_source
{
#ifdef TUNER_FBC
	TUNER_A=0, TUNER_B, TUNER_C, TUNER_D, TUNER_E, TUNER_F, TUNER_G, TUNER_H, TUNER_I, TUNER_J, TUNER_K, TUNER_L, TUNER_M, TUNER_N, TUNER_O, TUNER_P, TUNER_Q, TUNER_R, CI_A, CI_B, CI_C, CI_D
#else
	TUNER_A, TUNER_B, TUNER_C, TUNER_D, TUNER_E, TUNER_F, CI_A, CI_B, CI_C, CI_D
#endif
};

typedef std::pair<std::string, uint32_t> providerPair;
typedef std::set<providerPair> providerSet;
typedef std::set<uint16_t> caidSet;
typedef std::set<eServiceReference> serviceSet;

#ifdef __sh__
/* ********************************** */
/* constants taken from dvb-apps 
 */
#define T_SB                0x80	// sb                           primitive   h<--m
#define T_RCV               0x81	// receive                      primitive   h-->m
#define T_CREATE_T_C        0x82	// create transport connection  primitive   h-->m
#define T_C_T_C_REPLY       0x83	// ctc reply                    primitive   h<--m
#define T_DELETE_T_C        0x84	// delete tc                    primitive   h<->m
#define T_D_T_C_REPLY       0x85	// dtc reply                    primitive   h<->m
#define T_REQUEST_T_C       0x86	// request transport connection primitive   h<--m
#define T_NEW_T_C           0x87	// new tc / reply to t_request  primitive   h-->m
#define T_T_C_ERROR         0x77	// error creating tc            primitive   h-->m
#define T_DATA_LAST         0xA0	// convey data from higher      constructed h<->m
				 // layers
#define T_DATA_MORE         0xA1	// convey data from higher      constructed h<->m
				 // layers

typedef enum {eDataTimeout, eDataError, eDataReady, eDataWrite, eDataStatusChanged} eData;

static inline int time_after(struct timespec oldtime, uint32_t delta_ms)
{
	// calculate the oldtime + add on the delta
	uint64_t oldtime_ms = (oldtime.tv_sec * 1000) + (oldtime.tv_nsec / 1000000);
	oldtime_ms += delta_ms;

	// calculate the nowtime
	struct timespec nowtime;
	clock_gettime(CLOCK_MONOTONIC, &nowtime);
	uint64_t nowtime_ms = (nowtime.tv_sec * 1000) + (nowtime.tv_nsec / 1000000);

	// check
	return nowtime_ms > oldtime_ms;
}
#endif

class eDVBCISlot: public iObject, public Object
{
	friend class eDVBCIInterfaces;
	DECLARE_REF(eDVBCISlot);
	int slotid;
	int fd;
	ePtr<eSocketNotifier> notifier;
	int state;
	std::map<uint16_t, uint8_t> running_services;
	eDVBCIApplicationManagerSession *application_manager;
	eDVBCICAManagerSession *ca_manager;
	eDVBCIMMISession *mmi_session;
	std::priority_queue<queueData> sendqueue;
	caidSet possible_caids;
	serviceSet possible_services;
	providerSet possible_providers;
	int use_count;
	eDVBCISlot *linked_next; // needed for linked CI handling
	data_source current_source;
	int current_tuner;
	bool user_mapped;
	void data(int);
	bool plugged;
#ifdef __sh__
	//dagobert
	char connection_id;
	bool mmi_active;
	int receivedLen;
	unsigned char* receivedData;
#endif
public:
	enum {stateRemoved, stateInserted, stateInvalid, stateResetted};
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
	int setSource(data_source source);
	int setClockRate(int);
#ifdef __sh__
	bool checkQueueSize();
	void thread();
	void mmiOpened() { mmi_active = true; };
	void mmiClosed() { mmi_active = false; };
	void process_tpdu(unsigned char tpdu_tag, __u8* data, int asn_data_length, int con_id);
	bool sendCreateTC();
	eData sendData(unsigned char* data, int len);
	struct timeval tx_time;
	struct timespec last_poll_time;
#endif
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

#endif // SWIG

class eDVBCIInterfaces
{
	DECLARE_REF(eDVBCIInterfaces);
	static eDVBCIInterfaces *instance;
	eSmartPtrList<eDVBCISlot> m_slots;
	eDVBCISlot *getSlot(int slotid);
	PMTHandlerList m_pmt_handlers;
#ifndef SWIG
public:
#endif
	eDVBCIInterfaces();
	~eDVBCIInterfaces();

	void addPMTHandler(eDVBServicePMTHandler *pmthandler);
	void removePMTHandler(eDVBServicePMTHandler *pmthandler);
	void recheckPMTHandlers();
	void gotPMT(eDVBServicePMTHandler *pmthandler);
	void ciRemoved(eDVBCISlot *slot);
	int getSlotState(int slot);

	int reset(int slot);
	int initialize(int slot);
	int startMMI(int slot);
	int stopMMI(int slot);
	int answerText(int slot, int answer);
	int answerEnq(int slot, char *value);
	int cancelEnq(int slot);
	int getMMIState(int slot);
	int sendCAPMT(int slot);
	int setInputSource(int tunerno, data_source source);
	int setCIClockRate(int slot, int rate);
#ifdef SWIG
public:
#endif
	static eDVBCIInterfaces *getInstance();
	int getNumOfSlots() { return m_slots.size(); }
	PyObject *getDescrambleRules(int slotid);
	RESULT setDescrambleRules(int slotid, SWIG_PYOBJECT(ePyObject) );
	PyObject *readCICaIds(int slotid);
};

#endif
