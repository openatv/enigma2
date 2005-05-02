#ifndef __dvb_sec_h
#define __dvb_sec_h

#include <config.h>
#include <lib/dvb/idvb.h>

class eDVBSatelliteDiseqcParameters
{
public:
	enum { AA=0, AB=1, BA=2, BB=3, SENDNO=4 /* and 0xF0 .. 0xFF*/  };	// DiSEqC Parameter
	int m_commited_cmd;

	enum t_diseqc_mode { NONE=0, V1_0=1, V1_1=2, V1_2=3, SMATV=4 };	// DiSEqC Mode
	t_diseqc_mode m_diseqc_mode;

	enum t_toneburst_param { NO=0, A=1, B=2 };
	t_toneburst_param m_toneburst_param;

	int m_repeats;	// for cascaded switches
	bool m_use_fast;	// send no DiSEqC on H/V or Lo/Hi change
	bool m_seq_repeat;	// send the complete DiSEqC Sequence twice...
	bool m_swap_cmds;	// swaps the committed & uncommitted cmd
	int m_uncommitted_cmd;	// state of the 4 uncommitted switches..
};

class eDVBSatelliteSwitchParameters
{
public:
	enum t_22khz_signal {	HILO=0, ON=1, OFF=2	}; // 22 Khz
	enum t_voltage_mode	{	HV=0, _14V=1, _18V=2, _0V=3 }; // 14/18 V
	t_voltage_mode m_voltage_mode;
	t_22khz_signal m_22khz_signal;
};

class eDVBSatelliteRotorParameters
{
public:
	enum { NORTH, SOUTH, EAST, WEST };

	struct eDVBSatelliteRotorInputpowerParameters
	{
		bool m_use;	// can we use rotor inputpower to detect rotor running state ?
		int m_threshold;	// threshold between running and stopped rotor
	};
	eDVBSatelliteRotorInputpowerParameters m_inputpower_parameters;

	struct eDVBSatelliteRotorGotoxxParameters
	{
		bool m_can_use;	// rotor support gotoXX cmd ?
		int m_lo_direction;	// EAST, WEST
		int m_la_direction;	// NORT, SOUTH
		double m_longitude;	// longitude for gotoXX° function
		double m_latitude;	// latitude for gotoXX° function
	};
	eDVBSatelliteRotorGotoxxParameters m_gotoxx_parameters;

	struct Orbital_Position_Compare
	{
		inline bool operator()(const int &i1, const int &i2) const
		{
			return abs(i1-i2) < 6 ? false: i1 < i2;
		}
	};
	std::map< int, int, Orbital_Position_Compare > m_rotor_position_table;
	/* mapping orbitalposition <-> number stored in rotor */

	void setDefaultOptions(); // set default rotor options
};

class eDVBSatelliteParameters
{
public:
	eDVBSatelliteDiseqcParameters m_diseqc_parameters;
	eDVBSatelliteRotorParameters m_rotor_parameters;
	eDVBSatelliteSwitchParameters m_switch_parameters;
};

class eDVBSatelliteLNBParameters
{
public:
	enum t_12V_relais_state { OFF=0, ON };
	t_12V_relais_state m_12V_relais_state;	// 12V relais output on/off

	unsigned int m_lof_hi,	// for 2 band universal lnb 10600 Mhz (high band offset frequency)
				m_lof_lo,	// for 2 band universal lnb  9750 Mhz (low band offset frequency)
				m_lof_threshold;	// for 2 band universal lnb 11750 Mhz (band switch frequency)

	bool m_increased_voltage; // use increased voltage ( 14/18V )

	std::map<int, eDVBSatelliteParameters> m_satellites;
};

class eDVBSatelliteEquipmentControl: public iDVBSatelliteEquipmentControl
{
	std::list<eDVBSatelliteLNBParameters> m_lnblist;
public:
	DECLARE_REF(eDVBSatelliteEquipmentControl);
	eDVBSatelliteEquipmentControl();
	RESULT prepare(iDVBFrontend &frontend, FRONTENDPARAMETERS &parm, eDVBFrontendParametersSatellite &sat);
};

#endif
