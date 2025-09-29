#ifndef __dvbci_dvbci_h
#define __dvbci_dvbci_h

#ifndef SWIG

#include <lib/base/ebase.h>
#include <lib/base/message.h>
#include <lib/base/thread.h>
#include <lib/service/iservice.h>
#include <lib/python/python.h>
#include <set>
#include <queue>

class eDVBCISession;
class eDVBCIApplicationManagerSession;
class eDVBCICAManagerSession;
class eDVBCICcSession;
class eDVBCIMMISession;
class eDVBServicePMTHandler;
class eDVBCISlot;
class eDVBCIInterfaces;

struct queueData
{
	uint8_t prio;
	unsigned char *data;
	unsigned int len;
	queueData(unsigned char *data, unsigned int len, uint8_t prio = 0)
		: prio(prio), data(data), len(len)
	{
	}
	bool operator<(const struct queueData &a) const
	{
		return prio < a.prio;
	}
};

typedef std::pair<std::string, uint32_t> providerPair;
typedef std::set<providerPair> providerSet;
typedef std::set<uint16_t> caidSet;
typedef std::set<eServiceReference> serviceSet;

class eDVBCISlot : public iObject, public sigc::trackable
{
	friend class eDVBCIInterfaces;
	DECLARE_REF(eDVBCISlot);
	int slotid;
	int fd;
	ePtr<eSocketNotifier> notifier;
	ePtr<eTimer> startup_timeout;
	int state;
	int m_ci_version;
	std::map<uint16_t, uint8_t> running_services;
	eDVBCIApplicationManagerSession *application_manager;
	eDVBCICAManagerSession *ca_manager;
	eDVBCICcSession *cc_manager;
	eDVBCIMMISession *mmi_session;
	std::priority_queue<queueData> sendqueue;
	caidSet possible_caids;
	serviceSet possible_services;
	providerSet possible_providers;
	int use_count;
	eDVBCISlot *linked_next; // needed for linked CI handling
	std::string current_source;
	int current_tuner;
	bool user_mapped;
	void data(int);
	bool plugged;
	bool m_isCamMgrRoutingActive;
	bool m_ciPlusRoutingDone;
	int16_t m_ca_demux_id;
	uint16_t m_program_number;
	int m_video_pid;
	int m_audio_pid;
	int m_audio_number;
	int m_audio_pids[16];
	int m_tunernum;
	eMainloop *m_context;
	int m_ciplus_routing_tunernum;
	bool m_operator_profiles_disabled;
	int m_alt_ca_handling;
	std::string m_ciplus_routing_input;
	std::string m_ciplus_routing_ci_input;

	eDVBCIApplicationManagerSession *getAppManager() { return application_manager; }
	eDVBCIMMISession *getMMIManager() { return mmi_session; }
	eDVBCICAManagerSession *getCAManager() { return ca_manager; }
	eDVBCICcSession *getCCManager() { return cc_manager; }

	int getState() { return state; };
	void setCamMgrRoutingActive(bool active) { m_isCamMgrRoutingActive = active; };
	bool isCamMgrRoutingActive() { return m_isCamMgrRoutingActive; };
	bool ciplusRoutingDone() { return m_ciPlusRoutingDone; };
	void setCIPlusRoutingDone() { m_ciPlusRoutingDone = true; };
	int getCIPlusRoutingTunerNum() { return m_ciplus_routing_tunernum; };
	std::string getCIPlusRoutingInput() { return m_ciplus_routing_input; };
	std::string getCIPlusRoutingCIInput() { return m_ciplus_routing_ci_input; };
	void setCIPlusRoutingParameter(int tunernum, std::string ciplus_routing_input, std::string ciplus_routing_ci_input);
	int reset();
	int startMMI();
	int stopMMI();
	int answerText(int answer);
	int answerEnq(char *value);
	int cancelEnq();
	int getMMIState();
	int sendCAPMT(eDVBServicePMTHandler *ptr, const std::vector<uint16_t> &caids = std::vector<uint16_t>());
	int setCaParameter(eDVBServicePMTHandler *pmthandler);
	void removeService(uint16_t program_number = 0xFFFF);
	int setSource(const std::string &source);
	int setClockRate(const std::string &rate);
	void determineCIVersion();
	int setEnabled(bool);

public:
	static std::string getTunerLetter(int tuner_no) { return std::string(1, char(65 + tuner_no)); }
	enum
	{
		stateRemoved,
		stateInserted,
		stateInvalid,
		stateResetted,
		stateDisabled
	};
	enum
	{
		versionUnknown = -1,
		versionCI = 0,
		versionCIPlus1 = 1,
		versionCIPlus2 = 2
	};
	eDVBCISlot(eMainloop *context, int nr);
	~eDVBCISlot();
	void closeDevice();
	void openDevice();

	int send(const unsigned char *data, size_t len);

	void setAppManager(eDVBCIApplicationManagerSession *session);
	void setMMIManager(eDVBCIMMISession *session);
	void setCAManager(eDVBCICAManagerSession *session);
	void setCCManager(eDVBCICcSession *session);

	int getFd() { return fd; };
	int getSlotID();
	int getNumOfServices();
	int getVersion();
	int getDescramblingOptions() { return m_alt_ca_handling; };
	bool getIsOperatorProfileDisabled() { return m_operator_profiles_disabled; };
	int16_t getCADemuxID() { return m_ca_demux_id; };
	int getTunerNum() { return m_tunernum; };
	int getUseCount() { return use_count; };
	int getProgramNumber() { return (int)m_program_number; };
	int getVideoPid() { return m_video_pid; };
	int getAudioPid() { return m_audio_pid; };
	int getAudioNumber() { return m_audio_number; };
	int *getAudioPids() { return m_audio_pids; };
};

struct CIPmtHandler
{
	eDVBServicePMTHandler *pmthandler;
	eDVBCISlot *cislot;
	CIPmtHandler()
		: pmthandler(NULL), cislot(NULL)
	{
	}
	CIPmtHandler(const CIPmtHandler &x)
		: pmthandler(x.pmthandler), cislot(x.cislot)
	{
	}
	CIPmtHandler(eDVBServicePMTHandler *ptr)
		: pmthandler(ptr), cislot(NULL)
	{
	}
	bool operator==(const CIPmtHandler &x) const { return x.pmthandler == pmthandler; }
};

typedef std::list<CIPmtHandler> PMTHandlerList;

#endif // SWIG

class eDVBCIInterfaces : public eMainloop, private eThread
{
private:
	typedef enum
	{
		interface_none,
		interface_use_dvr,
		interface_use_pvr,
	} stream_interface_t;

	typedef enum
	{
		finish_none,
		finish_use_tuner_a,
		finish_use_pvr_none,
		finish_use_none,
	} stream_finish_mode_t;

	DECLARE_REF(eDVBCIInterfaces);

	stream_interface_t m_stream_interface;
	stream_finish_mode_t m_stream_finish_mode;

	static eDVBCIInterfaces *instance;
	eSmartPtrList<eDVBCISlot> m_slots;
	eDVBCISlot *getSlot(int slotid);
	PMTHandlerList m_pmt_handlers;
	std::string m_language;
	eFixedMessagePump<int> m_messagepump_thread; // message handling in the thread
	eFixedMessagePump<int> m_messagepump_main;	 // message handling in the e2 mainloop
	ePtr<eTimer> m_runTimer;					 // workaround to interrupt thread mainloop as some ci drivers don't implement poll properly
	static pthread_mutex_t m_pmt_handler_lock;

	int sendCAPMT(int slot);

	void thread();
	void gotMessageThread(const int &message);
	void gotMessageMain(const int &message);

#ifndef SWIG
public:
#endif
	eDVBCIInterfaces();
	~eDVBCIInterfaces();

	static pthread_mutex_t m_slot_lock;

	void addPMTHandler(eDVBServicePMTHandler *pmthandler);
	void removePMTHandler(eDVBServicePMTHandler *pmthandler);
	void recheckPMTHandlers();
	void executeRecheckPMTHandlersInMainloop();
	void gotPMT(eDVBServicePMTHandler *pmthandler);
	bool isCiConnected(eDVBServicePMTHandler *pmthandler);
	void ciRemoved(eDVBCISlot *slot);
	int getSlotState(int slot);

	int setCIEnabled(int slot, bool enabled);
	int reset(int slot);
	int initialize(int slot);
	int startMMI(int slot);
	int stopMMI(int slot);
	int answerText(int slot, int answer);
	int answerEnq(int slot, char *value);
	int cancelEnq(int slot);
	int getMMIState(int slot);
	int setInputSource(int tunerno, const std::string &source);
	int setCIClockRate(int slot, const std::string &rate);
	void setCIPlusRouting(int slotid);
	void revertCIPlusRouting(int slotid);
	bool canDescrambleMultipleServices(eDVBCISlot *slot);
	std::string getLanguage() { return m_language; };
#ifdef SWIG
public:
#endif
	static eDVBCIInterfaces *getInstance();
	int getNumOfSlots() { return m_slots.size(); }
	PyObject *getDescrambleRules(int slotid);
	RESULT setDescrambleRules(int slotid, SWIG_PYOBJECT(ePyObject));
	PyObject *readCICaIds(int slotid);
	struct Message
	{
		enum
		{
			slotStateChanged,
			mmiSessionDestroyed,
			mmiDataReceived,
			appNameChanged,
			slotDecodingStateChanged
		};
		int m_type;
		int m_slotid;
		int m_state;
		unsigned char m_tag[3];
		unsigned char m_data[4096];
		int m_len;
		std::string m_appName;
		Message(int type, int slotid) : m_type(type), m_slotid(slotid) {};
		Message(int type, int slotid, int state) : m_type(type), m_slotid(slotid), m_state(state) {};
		Message(int type, int slotid, std::string appName) : m_type(type), m_slotid(slotid), m_appName(appName) {};
		Message(int type, int slotid, const unsigned char *tag, unsigned char *data, int len) : m_type(type), m_slotid(slotid), m_len(len)
		{
			memcpy(m_tag, tag, 3);
			memcpy(m_data, data, len);
		};
	};
};

#endif
