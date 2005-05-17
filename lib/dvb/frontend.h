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

	RESULT setDVBS(eDVBFrontendParametersSatellite &p);
	RESULT setDVBC(eDVBFrontendParametersCable &p);
	RESULT setDVBT(eDVBFrontendParametersTerrestrial &p);
	
	RESULT calculateDifference(const iDVBFrontendParameters *parm, int &diff) const;
	
	RESULT getHash(unsigned long &hash) const;
};

class eDVBFrontend: public iDVBFrontend, public Object
{
	DECLARE_REF(eDVBFrontend);
	int m_type;
	int m_fd;
#if HAVE_DVB_API_VERSION < 3
	int m_secfd;
#endif
	FRONTENDPARAMETERS parm;
	int m_state;
	Signal1<void,iDVBFrontend*> m_stateChanged;
	ePtr<iDVBSatelliteEquipmentControl> m_sec;
	eSocketNotifier *m_sn;
	int m_tuning;
	eTimer *m_timeout;
	eTimer *m_tuneTimer;

	void feEvent(int);
	void timeout();
	eSecCommandList m_sec_sequence;
	void tuneLoop();  // called by m_tuneTimer
	void setFrontend();
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
};

#endif
