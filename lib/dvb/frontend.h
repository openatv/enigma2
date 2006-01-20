#ifndef __dvb_frontend_h
#define __dvb_frontend_h

#include <config.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/sec.h>

class eSecCommandList;

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
	RESULT getDVBS(eDVBFrontendParametersSatellite &p) const;
	RESULT getDVBC(eDVBFrontendParametersCable &p) const;
	RESULT getDVBT(eDVBFrontendParametersTerrestrial &p) const;

	RESULT setDVBS(const eDVBFrontendParametersSatellite &p);
	RESULT setDVBC(const eDVBFrontendParametersCable &p);
	RESULT setDVBT(const eDVBFrontendParametersTerrestrial &p);
	
	RESULT calculateDifference(const iDVBFrontendParameters *parm, int &diff) const;
	
	RESULT getHash(unsigned long &hash) const;
};

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

	int m_data[9]; /* when satellite frontend then
		data[0] = lastcsw -> state of the committed switch
		data[1] = lastucsw -> state of the uncommitted switch
		data[2] = lastToneburst -> current state of toneburst switch
		data[3] = newRotorCmd -> last sent rotor cmd
		data[4] = newRotorPos -> current Rotor Position
		data[5] = curRotorCmd
		data[6] = curRotorPos
		data[7] = linkedToTunerNo
		data[8] = dependsToTunerNo (just satpos.. for rotor with twin lnb) */

	int m_idleInputpower[2];  // 13V .. 18V
	int m_runningInputpower;
	int m_timeoutCount; // needed for timeout
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

	int readFrontendData(int type); // bitErrorRate, signalPower, signalQuality
	int isCompatibleWith(ePtr<iDVBFrontendParameters> &feparm);
	int getID() { return m_fe; }

	int openFrontend();
	int closeFrontend();
};

#endif
