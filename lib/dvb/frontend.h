#ifndef __dvb_frontend_h
#define __dvb_frontend_h

#include <map>
#include <lib/dvb/idvb.h>
#include <lib/dvb/frontendparms.h>

class eDVBFrontendParameters: public iDVBFrontendParameters
{
	DECLARE_REF(eDVBFrontendParameters);
	union
	{
		eDVBFrontendParametersSatellite sat;
		eDVBFrontendParametersCable cable;
		eDVBFrontendParametersTerrestrial terrestrial;
		eDVBFrontendParametersATSC atsc;
	};
	int m_type;
	int m_flags;
public:
	eDVBFrontendParameters();
	~eDVBFrontendParameters()
	{
	}

	SWIG_VOID(RESULT) getSystem(int &SWIG_OUTPUT) const;
	SWIG_VOID(RESULT) getDVBS(eDVBFrontendParametersSatellite &SWIG_OUTPUT) const;
	SWIG_VOID(RESULT) getDVBC(eDVBFrontendParametersCable &SWIG_OUTPUT) const;
	SWIG_VOID(RESULT) getDVBT(eDVBFrontendParametersTerrestrial &SWIG_OUTPUT) const;
	SWIG_VOID(RESULT) getATSC(eDVBFrontendParametersATSC &SWIG_OUTPUT) const;

	RESULT setDVBS(const eDVBFrontendParametersSatellite &p, bool no_rotor_command_on_tune=false);
	RESULT setDVBC(const eDVBFrontendParametersCable &p);
	RESULT setDVBT(const eDVBFrontendParametersTerrestrial &p);
	RESULT setATSC(const eDVBFrontendParametersATSC &p);
	SWIG_VOID(RESULT) getFlags(unsigned int &SWIG_NAMED_OUTPUT(flags)) const { flags = m_flags; return 0; }
	RESULT setFlags(unsigned int flags) { m_flags = flags; return 0; }
#ifndef SWIG
	RESULT calculateDifference(const iDVBFrontendParameters *parm, int &, bool exact) const;

	RESULT getHash(unsigned long &) const;
	RESULT calcLockTimeout(unsigned int &) const;
#endif
};

#ifndef SWIG

#include <lib/dvb/sec.h>
class eSecCommandList;

class eDVBFrontend: public iDVBFrontend, public Object
{
public:
	enum {
		NEW_CSW,
		NEW_UCSW,
		NEW_TONEBURST,
		CSW,                  // state of the committed switch
		UCSW,                 // state of the uncommitted switch
		TONEBURST,            // current state of toneburst switch
		NEW_ROTOR_CMD,        // prev sent rotor cmd
		NEW_ROTOR_POS,        // new rotor position (not validated)
		ROTOR_CMD,            // completed rotor cmd (finalized)
		ROTOR_POS,            // current rotor position
		LINKED_PREV_PTR,      // prev double linked list (for linked FEs)
		LINKED_NEXT_PTR,      // next double linked list (for linked FEs)
		SATPOS_DEPENDS_PTR,   // pointer to FE with configured rotor (with twin/quattro lnb)
		FREQ_OFFSET,          // current frequency offset
		CUR_VOLTAGE,          // current voltage
		CUR_TONE,             // current continuous tone
		SATCR,                // current SatCR
		NUM_DATA_ENTRIES
	};
	Signal1<void,iDVBFrontend*> m_stateChanged;
private:
	DECLARE_REF(eDVBFrontend);
	bool m_simulate;
	bool m_enabled;
	eDVBFrontend *m_simulate_fe; // only used to set frontend type in dvb.cpp
	int m_dvbid;
	int m_slotid;
	int m_fd;
#define DVB_VERSION(major, minor) ((major << 8) | minor)
	int m_dvbversion;
	bool m_rotor_mode;
	bool m_need_rotor_workaround;
	std::map<fe_delivery_system_t, bool> m_delsys, m_delsys_whitelist;
	std::string m_filename;
	char m_description[128];
	dvb_frontend_info fe_info;
	int satfrequency;
	eDVBFrontendParameters oparm;

	int m_state;
	ePtr<iDVBSatelliteEquipmentControl> m_sec;
	ePtr<eSocketNotifier> m_sn;
	int m_tuning;
	ePtr<eTimer> m_timeout, m_tuneTimer;

	eSecCommandList m_sec_sequence;

	long m_data[NUM_DATA_ENTRIES];

	int m_idleInputpower[2];  // 13V .. 18V
	int m_runningInputpower;

	int m_timeoutCount; // needed for timeout
	int m_retryCount; // diseqc retry for rotor

	void feEvent(int);
	void timeout();
	void tuneLoop();  // called by m_tuneTimer
	int tuneLoopInt();
	void setFrontend(bool recvEvents=true);
	bool setSecSequencePos(int steps);
	void calculateSignalQuality(int snr, int &signalquality, int &signalqualitydb);

	static int PriorityOrder;
	static int PreferredFrontendIndex;
public:
	eDVBFrontend(const char *devidenodename, int fe, int &ok, bool simulate=false, eDVBFrontend *simulate_fe=NULL);
	virtual ~eDVBFrontend();

	int readInputpower();
	RESULT getFrontendType(int &type);
	RESULT tune(const iDVBFrontendParameters &where);
	RESULT prepare_sat(const eDVBFrontendParametersSatellite &, unsigned int timeout);
	RESULT prepare_cable(const eDVBFrontendParametersCable &);
	RESULT prepare_terrestrial(const eDVBFrontendParametersTerrestrial &);
	RESULT prepare_atsc(const eDVBFrontendParametersATSC &);
	RESULT connectStateChange(const Slot1<void,iDVBFrontend*> &stateChange, ePtr<eConnection> &connection);
	RESULT getState(int &state);
	RESULT setTone(int tone);
	RESULT setVoltage(int voltage);
	RESULT sendDiseqc(const eDVBDiseqcCommand &diseqc);
	RESULT sendToneburst(int burst);
	RESULT setSEC(iDVBSatelliteEquipmentControl *sec);
	RESULT setSecSequence(eSecCommandList &list);
	RESULT getData(int num, long &data);
	RESULT setData(int num, long val);

	int readFrontendData(int type); // iFrontendInformation_ENUMS
	void getFrontendStatus(ePtr<iDVBFrontendStatus> &dest);
	void getTransponderData(ePtr<iDVBTransponderData> &dest, bool original);
	void getFrontendData(ePtr<iDVBFrontendData> &dest);

	int isCompatibleWith(ePtr<iDVBFrontendParameters> &feparm);
	int getDVBID() { return m_dvbid; }
	int getSlotID() { return m_slotid; }
	bool setSlotInfo(int id, const char *descr, bool enabled, bool isDVBS2, int frontendid);
	static void setTypePriorityOrder(int val) { PriorityOrder = val; }
	static int getTypePriorityOrder() { return PriorityOrder; }
	static void setPreferredFrontend(int index) { PreferredFrontendIndex = index; }
	static int getPreferredFrontend() { return PreferredFrontendIndex; }
	bool supportsDeliverySystem(const fe_delivery_system_t &sys, bool obeywhitelist);
	void setDeliverySystemWhitelist(const std::vector<fe_delivery_system_t> &whitelist);

	void reopenFrontend();
	int openFrontend();
	int closeFrontend(bool force=false, bool no_delayed=false);
	const char *getDescription() const { return m_description; }
	bool is_simulate() const { return m_simulate; }
};

#endif // SWIG

#endif
