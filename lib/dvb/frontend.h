#ifndef __dvb_frontend_h
#define __dvb_frontend_h

#include <lib/dvb/idvb.h>
class eDVBFrontendParameters: public iDVBFrontendParameters
{
	DECLARE_REF(eDVBFrontendParameters);
	union
	{
		eDVBFrontendParametersSatellite sat;
		eDVBFrontendParametersCable cable;
		eDVBFrontendParametersTerrestrial terrestrial;
	};
	int m_type;
public:
	eDVBFrontendParameters();
	
	RESULT getSystem(int &type) const;
	RESULT getDVBS(eDVBFrontendParametersSatellite &SWIG_OUTPUT) const;
	RESULT getDVBC(eDVBFrontendParametersCable &SWIG_OUTPUT) const;
	RESULT getDVBT(eDVBFrontendParametersTerrestrial &SWIG_OUTPUT) const;

	RESULT setDVBS(const eDVBFrontendParametersSatellite &p, bool no_rotor_command_on_tune=false);
	RESULT setDVBC(const eDVBFrontendParametersCable &p);
	RESULT setDVBT(const eDVBFrontendParametersTerrestrial &p);
	
	RESULT calculateDifference(const iDVBFrontendParameters *parm, int &SWIG_OUTPUT) const;
	
	RESULT getHash(unsigned long &SWIG_OUTPUT) const;
};

#ifndef SWIG

#include <lib/dvb/sec.h>
class eSecCommandList;

class eDVBFrontend: public iDVBFrontend, public Object
{
	DECLARE_REF(eDVBFrontend);
	int m_type;
	int m_fe;
	int m_fd;
	char m_filename[128];
#if HAVE_DVB_API_VERSION < 3
	int m_secfd;
	char m_sec_filename[128];
#endif

	FRONTENDPARAMETERS parm;
	int m_state;
	Signal1<void,iDVBFrontend*> m_stateChanged;
	ePtr<iDVBSatelliteEquipmentControl> m_sec;
	eSocketNotifier *m_sn;
	int m_tuning;
	eTimer *m_timeout;
	eTimer *m_tuneTimer;

	eSecCommandList m_sec_sequence;

	enum {
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
		NUM_DATA_ENTRIES
	};

	int m_data[NUM_DATA_ENTRIES];

	int m_idleInputpower[2];  // 13V .. 18V
	int m_runningInputpower;

	int m_timeoutCount; // needed for timeout
	int m_retryCount; // diseqc retry for rotor
	int m_curVoltage;

	void feEvent(int);
	void timeout();
	void tuneLoop();  // called by m_tuneTimer
	void setFrontend();
	int readInputpower();
	bool setSecSequencePos(int steps);
public:
	eDVBFrontend(int adap, int fe, int &ok);	
	virtual ~eDVBFrontend();

	RESULT getFrontendType(int &type);
	RESULT tune(const iDVBFrontendParameters &where);
	RESULT prepare_sat(const eDVBFrontendParametersSatellite &);
	RESULT prepare_cable(const eDVBFrontendParametersCable &);
	RESULT prepare_terrestrial(const eDVBFrontendParametersTerrestrial &);
	RESULT connectStateChange(const Slot1<void,iDVBFrontend*> &stateChange, ePtr<eConnection> &connection);
	RESULT getState(int &state);
	RESULT setTone(int tone);
	RESULT setVoltage(int voltage);
	RESULT sendDiseqc(const eDVBDiseqcCommand &diseqc);
	RESULT sendToneburst(int burst);
	RESULT setSEC(iDVBSatelliteEquipmentControl *sec);
	RESULT setSecSequence(const eSecCommandList &list);
	RESULT getData(int num, int &data);
	RESULT setData(int num, int val);

	int readFrontendData(int type); // bitErrorRate, signalPower, signalQuality, locked, synced
	PyObject *readTransponderData(bool original);

	int isCompatibleWith(ePtr<iDVBFrontendParameters> &feparm);
	int getID() { return m_fe; }

	int openFrontend();
	int closeFrontend();
};

#endif // SWIG
#endif
