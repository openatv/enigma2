#ifndef __dvb_sec_h
#define __dvb_sec_h

#include <config.h>
#include <lib/dvb/idvb.h>
#include <list>

#ifndef SWIG
class eSecCommand
{
public:
	enum { modeStatic, modeDynamic };
	enum {
		NONE, SLEEP, SET_VOLTAGE, SET_TONE, GOTO,
		SEND_DISEQC, SEND_TONEBURST, SET_FRONTEND,
	 	MEASURE_IDLE_INPUTPOWER, MEASURE_RUNNING_INPUTPOWER,
		IF_TIMEOUT_GOTO, IF_INPUTPOWER_DELTA_GOTO,
		UPDATE_CURRENT_ROTORPARAMS, SET_TIMEOUT,
		IF_IDLE_INPUTPOWER_AVAIL_GOTO, SET_POWER_LIMITING_MODE,
		IF_VOLTAGE_GOTO
	};
	int cmd;
	struct rotor
	{
		int deltaA;   // difference in mA between running and stopped rotor
		int okcount;  // counter
		int steps;    // goto steps
		int direction;
	};
	struct pair
	{
		int voltage;
		int steps;
	};
	union
	{
		int val;
		int steps;
		int timeout;
		int voltage;
		int tone;
		int toneburst;
		int msec;
		int mode;
		rotor measure;
		eDVBDiseqcCommand diseqc;
		pair compare;
	};
	eSecCommand( int cmd )
		:cmd(cmd)
	{}
	eSecCommand( int cmd, int val )
		:cmd(cmd), val(val)
	{}
	eSecCommand( int cmd, eDVBDiseqcCommand diseqc )
		:cmd(cmd), diseqc(diseqc)
	{}
	eSecCommand( int cmd, rotor measure )
		:cmd(cmd), measure(measure)
	{}
	eSecCommand( int cmd, pair compare )
		:cmd(cmd), compare(compare)
	{}
	eSecCommand()
		:cmd(NONE)
	{}
};

class eSecCommandList
{
	std::list<eSecCommand> secSequence;
	std::list<eSecCommand>::iterator cur;
public:
	eSecCommandList()
		:cur(secSequence.end())
	{
	}
	void push_front(const eSecCommand &cmd)
	{
		secSequence.push_front(cmd);
	}
	void push_back(const eSecCommand &cmd)
	{
		secSequence.push_back(cmd);
	}
	void clear()
	{
		secSequence.clear();
		cur=secSequence.end();
	}
	inline std::list<eSecCommand>::iterator &current()
	{
		return cur;
	}
	inline std::list<eSecCommand>::iterator begin()
	{
		return secSequence.begin();
	}
	inline std::list<eSecCommand>::iterator end()
	{
		return secSequence.end();
	}
	int size() const
	{
		return secSequence.size();
	}
	operator bool() const
	{
		return secSequence.size();
	}
};

class eDVBSatelliteDiseqcParameters
{
public:
	enum { AA=0, AB=1, BA=2, BB=3, SENDNO=4 /* and 0xF0 .. 0xFF*/  };	// DiSEqC Parameter
	__u8 m_committed_cmd;

	enum t_diseqc_mode { NONE=0, V1_0=1, V1_1=2, V1_2=3, SMATV=4 };	// DiSEqC Mode
	t_diseqc_mode m_diseqc_mode;

	enum t_toneburst_param { NO=0, A=1, B=2 };
	t_toneburst_param m_toneburst_param;

	__u8 m_repeats;	// for cascaded switches
	bool m_use_fast;	// send no DiSEqC on H/V or Lo/Hi change
	bool m_seq_repeat;	// send the complete DiSEqC Sequence twice...
	__u8 m_command_order;
	/* 	diseqc 1.0)
			0) commited, toneburst
			1) toneburst, committed
		diseqc > 1.0)
			2) committed, uncommitted, toneburst
			3) toneburst, committed, uncommitted
			4) uncommitted, committed, toneburst
			5) toneburst, uncommitted, committed */
	__u8 m_uncommitted_cmd;	// state of the 4 uncommitted switches..
};

class eDVBSatelliteSwitchParameters
{
public:
	enum t_22khz_signal {	HILO=0, ON=1, OFF=2	}; // 22 Khz
	enum t_voltage_mode	{	HV=0, _14V=1, _18V=2, _0V=3 }; // 14/18 V
	t_voltage_mode m_voltage_mode;
	t_22khz_signal m_22khz_signal;
	__u8 m_rotorPosNum; // 0 is disable.. then use gotoxx
};

class eDVBSatelliteRotorParameters
{
public:
	enum { NORTH, SOUTH, EAST, WEST };

	eDVBSatelliteRotorParameters() { setDefaultOptions(); }

	struct eDVBSatelliteRotorInputpowerParameters
	{
		bool m_use;	// can we use rotor inputpower to detect rotor running state ?
		__u8 m_delta;	// delta between running and stopped rotor
	};
	eDVBSatelliteRotorInputpowerParameters m_inputpower_parameters;

	struct eDVBSatelliteRotorGotoxxParameters
	{
		__u8 m_lo_direction;	// EAST, WEST
		__u8 m_la_direction;	// NORT, SOUTH
		double m_longitude;	// longitude for gotoXX° function
		double m_latitude;	// latitude for gotoXX° function
	};
	eDVBSatelliteRotorGotoxxParameters m_gotoxx_parameters;

	void setDefaultOptions() // set default rotor options
	{
		m_inputpower_parameters.m_use = true;
		m_inputpower_parameters.m_delta = 60;
		m_gotoxx_parameters.m_lo_direction = EAST;
		m_gotoxx_parameters.m_la_direction = NORTH;
		m_gotoxx_parameters.m_longitude = 0.0;
		m_gotoxx_parameters.m_latitude = 0.0;
	}
};

class eDVBSatelliteLNBParameters
{
public:
	enum t_12V_relais_state { OFF=0, ON };
	t_12V_relais_state m_12V_relais_state;	// 12V relais output on/off

	__u8 tuner_mask; // useable by tuner ( 1 | 2 | 4...)

	unsigned int m_lof_hi,	// for 2 band universal lnb 10600 Mhz (high band offset frequency)
				m_lof_lo,	// for 2 band universal lnb  9750 Mhz (low band offset frequency)
				m_lof_threshold;	// for 2 band universal lnb 11750 Mhz (band switch frequency)

	bool m_increased_voltage; // use increased voltage ( 14/18V )

	std::map<int, eDVBSatelliteSwitchParameters> m_satellites;
	eDVBSatelliteDiseqcParameters m_diseqc_parameters;
	eDVBSatelliteRotorParameters m_rotor_parameters;
};
#endif

class eDVBSatelliteEquipmentControl: public iDVBSatelliteEquipmentControl
{
#ifndef SWIG
	static eDVBSatelliteEquipmentControl *instance;
	eDVBSatelliteLNBParameters m_lnbs[128]; // i think its enough
	int m_lnbidx; // current index for set parameters
	std::map<int, eDVBSatelliteSwitchParameters>::iterator m_curSat;
#endif
public:
#ifndef SWIG
	DECLARE_REF(eDVBSatelliteEquipmentControl);
	eDVBSatelliteEquipmentControl();
	RESULT prepare(iDVBFrontend &frontend, FRONTENDPARAMETERS &parm, eDVBFrontendParametersSatellite &sat);
	bool currentLNBValid() { return m_lnbidx > -1 && m_lnbidx < (int)(sizeof(m_lnbs) / sizeof(eDVBSatelliteLNBParameters)); }
#endif
	static eDVBSatelliteEquipmentControl *getInstance() { return instance; }
	RESULT clear();
/* LNB Specific Parameters */
	RESULT addLNB();
	RESULT setLNBTunerMask(int tunermask);
	RESULT setLNBLOFL(int lofl);
	RESULT setLNBLOFH(int lofh);
	RESULT setLNBThreshold(int threshold);
	RESULT setLNBIncreasedVoltage(bool onoff);
/* DiSEqC Specific Parameters */
	RESULT setDiSEqCMode(int diseqcmode);
	RESULT setToneburst(int toneburst);
	RESULT setRepeats(int repeats);
	RESULT setCommittedCommand(int command);
	RESULT setUncommittedCommand(int command);
	RESULT setCommandOrder(int order);
	RESULT setFastDiSEqC(bool onoff);
	RESULT setSeqRepeat(bool onoff); // send the complete switch sequence twice (without rotor command)
/* Rotor Specific Parameters */
	RESULT setLongitude(float longitude);
	RESULT setLatitude(float latitude);
	RESULT setLoDirection(int direction);
	RESULT setLaDirection(int direction);
	RESULT setUseInputpower(bool onoff);
	RESULT setInputpowerDelta(int delta);  // delta between running and stopped rotor
/* Satellite Specific Parameters */
	RESULT addSatellite(int orbital_position);
	RESULT setVoltageMode(int mode);
	RESULT setToneMode(int mode);
	RESULT setRotorPosNum(int rotor_pos_num);
};

#endif
