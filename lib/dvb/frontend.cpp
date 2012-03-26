#include <lib/dvb/dvb.h>
#include <lib/dvb/frontendparms.h>
#include <lib/base/eerror.h>
#include <lib/base/nconfig.h> // access to python config
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#ifndef I2C_SLAVE_FORCE
#define I2C_SLAVE_FORCE	0x0706
#endif

#if HAVE_DVB_API_VERSION < 3
#include <ost/frontend.h>
#include <ost/sec.h>
#define QAM_AUTO				(Modulation)6
#define TRANSMISSION_MODE_AUTO	(TransmitMode)2
#define BANDWIDTH_AUTO			(BandWidth)3
#define GUARD_INTERVAL_AUTO		(GuardInterval)4
#define HIERARCHY_AUTO			(Hierarchy)4
#define parm_frequency parm.Frequency
#define parm_inversion parm.Inversion
#define parm_u_qpsk_symbol_rate parm.u.qpsk.SymbolRate
#define parm_u_qpsk_fec_inner parm.u.qpsk.FEC_inner
#define parm_u_qam_symbol_rate parm.u.qam.SymbolRate
#define parm_u_qam_fec_inner parm.u.qam.FEC_inner
#define parm_u_qam_modulation parm.u.qam.QAM
#define parm_u_ofdm_bandwidth parm.u.ofdm.bandWidth
#define parm_u_ofdm_code_rate_LP parm.u.ofdm.LP_CodeRate
#define parm_u_ofdm_code_rate_HP parm.u.ofdm.HP_CodeRate
#define parm_u_ofdm_constellation parm.u.ofdm.Constellation
#define parm_u_ofdm_transmission_mode parm.u.ofdm.TransmissionMode
#define parm_u_ofdm_guard_interval parm.u.ofdm.guardInterval
#define parm_u_ofdm_hierarchy_information parm.u.ofdm.HierarchyInformation
#else
#include <linux/dvb/frontend.h>
#define parm_frequency parm.frequency
#define parm_inversion parm.inversion
#define parm_u_qpsk_symbol_rate parm.u.qpsk.symbol_rate
#define parm_u_qpsk_fec_inner parm.u.qpsk.fec_inner
#define parm_u_qam_symbol_rate parm.u.qam.symbol_rate
#define parm_u_qam_fec_inner parm.u.qam.fec_inner
#define parm_u_qam_modulation parm.u.qam.modulation
#define parm_u_ofdm_bandwidth parm.u.ofdm.bandwidth
#define parm_u_ofdm_code_rate_LP parm.u.ofdm.code_rate_LP
#define parm_u_ofdm_code_rate_HP parm.u.ofdm.code_rate_HP
#define parm_u_ofdm_constellation parm.u.ofdm.constellation
#define parm_u_ofdm_transmission_mode parm.u.ofdm.transmission_mode
#define parm_u_ofdm_guard_interval parm.u.ofdm.guard_interval
#define parm_u_ofdm_hierarchy_information parm.u.ofdm.hierarchy_information
#if HAVE_DVB_API_VERSION < 5
	#define FEC_S2_QPSK_1_2 (fe_code_rate_t)(FEC_AUTO+1)
	#define FEC_S2_QPSK_2_3 (fe_code_rate_t)(FEC_S2_QPSK_1_2+1)
	#define FEC_S2_QPSK_3_4 (fe_code_rate_t)(FEC_S2_QPSK_2_3+1)
	#define FEC_S2_QPSK_5_6 (fe_code_rate_t)(FEC_S2_QPSK_3_4+1)
	#define FEC_S2_QPSK_7_8 (fe_code_rate_t)(FEC_S2_QPSK_5_6+1)
	#define FEC_S2_QPSK_8_9 (fe_code_rate_t)(FEC_S2_QPSK_7_8+1)
	#define FEC_S2_QPSK_3_5 (fe_code_rate_t)(FEC_S2_QPSK_8_9+1)
	#define FEC_S2_QPSK_4_5 (fe_code_rate_t)(FEC_S2_QPSK_3_5+1)
	#define FEC_S2_QPSK_9_10 (fe_code_rate_t)(FEC_S2_QPSK_4_5+1)
	#define FEC_S2_8PSK_1_2 (fe_code_rate_t)(FEC_S2_QPSK_9_10+1)
	#define FEC_S2_8PSK_2_3 (fe_code_rate_t)(FEC_S2_8PSK_1_2+1)
	#define FEC_S2_8PSK_3_4 (fe_code_rate_t)(FEC_S2_8PSK_2_3+1)
	#define FEC_S2_8PSK_5_6 (fe_code_rate_t)(FEC_S2_8PSK_3_4+1)
	#define FEC_S2_8PSK_7_8 (fe_code_rate_t)(FEC_S2_8PSK_5_6+1)
	#define FEC_S2_8PSK_8_9 (fe_code_rate_t)(FEC_S2_8PSK_7_8+1)
	#define FEC_S2_8PSK_3_5 (fe_code_rate_t)(FEC_S2_8PSK_8_9+1)
	#define FEC_S2_8PSK_4_5 (fe_code_rate_t)(FEC_S2_8PSK_3_5+1)
	#define FEC_S2_8PSK_9_10 (fe_code_rate_t)(FEC_S2_8PSK_4_5+1)
#else
	#define FEC_S2_QPSK_1_2 (fe_code_rate_t)(FEC_1_2)
	#define FEC_S2_QPSK_2_3 (fe_code_rate_t)(FEC_2_3)
	#define FEC_S2_QPSK_3_4 (fe_code_rate_t)(FEC_3_4)
	#define FEC_S2_QPSK_5_6 (fe_code_rate_t)(FEC_5_6)
	#define FEC_S2_QPSK_6_7 (fe_code_rate_t)(FEC_6_7)
	#define FEC_S2_QPSK_7_8 (fe_code_rate_t)(FEC_7_8)
	#define FEC_S2_QPSK_8_9 (fe_code_rate_t)(FEC_8_9)
	#define FEC_S2_QPSK_3_5 (fe_code_rate_t)(FEC_3_5)
	#define FEC_S2_QPSK_4_5 (fe_code_rate_t)(FEC_4_5)
	#define FEC_S2_QPSK_9_10 (fe_code_rate_t)(FEC_9_10)
#endif
#endif

#include <dvbsi++/satellite_delivery_system_descriptor.h>
#include <dvbsi++/cable_delivery_system_descriptor.h>
#include <dvbsi++/terrestrial_delivery_system_descriptor.h>

#define eDebugNoSimulate(x...) \
	do { \
		if (!m_simulate) \
			eDebug(x); \
	} while(0)
#if 0
		else \
		{ \
			eDebugNoNewLine("SIMULATE:"); \
			eDebug(x); \
		}
#endif

#define eDebugNoSimulateNoNewLine(x...) \
	do { \
		if (!m_simulate) \
			eDebugNoNewLine(x); \
	} while(0)
#if 0
		else \
		{ \
			eDebugNoNewLine("SIMULATE:"); \
			eDebugNoNewLine(x); \
		}
#endif

void eDVBDiseqcCommand::setCommandString(const char *str)
{
	if (!str)
		return;
	len=0;
	int slen = strlen(str);
	if (slen % 2)
	{
		eDebug("invalid diseqc command string length (not 2 byte aligned)");
		return;
	}
	if (slen > MAX_DISEQC_LENGTH*2)
	{
		eDebug("invalid diseqc command string length (string is to long)");
		return;
	}
	unsigned char val=0;
	for (int i=0; i < slen; ++i)
	{
		unsigned char c = str[i];
		switch(c)
		{
			case '0' ... '9': c-=48; break;
			case 'a' ... 'f': c-=87; break;
			case 'A' ... 'F': c-=55; break;
			default:
				eDebug("invalid character in hex string..ignore complete diseqc command !");
				return;
		}
		if ( i % 2 )
		{
			val |= c;
			data[i/2] = val;
		}
		else
			val = c << 4;
	}
	len = slen/2;
}

void eDVBFrontendParametersSatellite::set(const SatelliteDeliverySystemDescriptor &descriptor)
{
	frequency    = descriptor.getFrequency() * 10;
	symbol_rate  = descriptor.getSymbolRate() * 100;
	polarisation = descriptor.getPolarization();
	fec = descriptor.getFecInner();
	if ( fec != eDVBFrontendParametersSatellite::FEC_None && fec > eDVBFrontendParametersSatellite::FEC_9_10 )
		fec = eDVBFrontendParametersSatellite::FEC_Auto;
	inversion = eDVBFrontendParametersSatellite::Inversion_Unknown;
	pilot = eDVBFrontendParametersSatellite::Pilot_Unknown;
	orbital_position  = ((descriptor.getOrbitalPosition() >> 12) & 0xF) * 1000;
	orbital_position += ((descriptor.getOrbitalPosition() >> 8) & 0xF) * 100;
	orbital_position += ((descriptor.getOrbitalPosition() >> 4) & 0xF) * 10;
	orbital_position += ((descriptor.getOrbitalPosition()) & 0xF);
	if (orbital_position && (!descriptor.getWestEastFlag()))
		orbital_position = 3600 - orbital_position;
	system = descriptor.getModulationSystem();
	modulation = descriptor.getModulation();
	if (system == eDVBFrontendParametersSatellite::System_DVB_S && modulation == eDVBFrontendParametersSatellite::Modulation_8PSK)
	{
		eDebug("satellite_delivery_descriptor non valid modulation type.. force QPSK");
		modulation=eDVBFrontendParametersSatellite::Modulation_QPSK;
	}
	rolloff = descriptor.getRollOff();
	if (system == eDVBFrontendParametersSatellite::System_DVB_S2)
	{
		eDebug("SAT DVB-S2 freq %d, %s, pos %d, sr %d, fec %d, modulation %d, rolloff %d",
			frequency,
			polarisation ? "hor" : "vert",
			orbital_position,
			symbol_rate, fec,
			modulation,
			rolloff);
	}
	else
	{
		eDebug("SAT DVB-S freq %d, %s, pos %d, sr %d, fec %d",
			frequency,
			polarisation ? "hor" : "vert",
			orbital_position,
			symbol_rate, fec);
	}
}

void eDVBFrontendParametersCable::set(const CableDeliverySystemDescriptor &descriptor)
{
	frequency = descriptor.getFrequency() / 10;
	symbol_rate = descriptor.getSymbolRate() * 100;
	fec_inner = descriptor.getFecInner();
	if ( fec_inner != eDVBFrontendParametersCable::FEC_None && fec_inner > eDVBFrontendParametersCable::FEC_8_9 )
		fec_inner = eDVBFrontendParametersCable::FEC_Auto;
	modulation = descriptor.getModulation();
	if ( modulation > 0x5 )
		modulation = eDVBFrontendParametersCable::Modulation_Auto;
	inversion = eDVBFrontendParametersCable::Inversion_Unknown;
	eDebug("Cable freq %d, mod %d, sr %d, fec %d",
		frequency,
		modulation, symbol_rate, fec_inner);
}

void eDVBFrontendParametersTerrestrial::set(const TerrestrialDeliverySystemDescriptor &descriptor)
{
	frequency = descriptor.getCentreFrequency() * 10;
	bandwidth = descriptor.getBandwidth();
	if ( bandwidth > 2 ) // 5Mhz forced to auto
		bandwidth = eDVBFrontendParametersTerrestrial::Bandwidth_Auto;
	code_rate_HP = descriptor.getCodeRateHpStream();
	if (code_rate_HP > 4)
		code_rate_HP = eDVBFrontendParametersTerrestrial::FEC_Auto;
	code_rate_LP = descriptor.getCodeRateLpStream();
	if (code_rate_LP > 4)
		code_rate_LP = eDVBFrontendParametersTerrestrial::FEC_Auto;
	transmission_mode = descriptor.getTransmissionMode();
	if (transmission_mode > 1) // TM4k forced to auto
		transmission_mode = eDVBFrontendParametersTerrestrial::TransmissionMode_Auto;
	guard_interval = descriptor.getGuardInterval();
	if (guard_interval > 3)
		guard_interval = eDVBFrontendParametersTerrestrial::GuardInterval_Auto;
	hierarchy = descriptor.getHierarchyInformation()&3;
	modulation = descriptor.getConstellation();
	if (modulation > 2)
		modulation = eDVBFrontendParametersTerrestrial::Modulation_Auto;
	inversion = eDVBFrontendParametersTerrestrial::Inversion_Unknown;
	eDebug("Terr freq %d, bw %d, cr_hp %d, cr_lp %d, tm_mode %d, guard %d, hierarchy %d, const %d",
		frequency, bandwidth, code_rate_HP, code_rate_LP, transmission_mode,
		guard_interval, hierarchy, modulation);
}

eDVBFrontendParameters::eDVBFrontendParameters()
	:m_type(-1), m_flags(0)
{
}

DEFINE_REF(eDVBFrontendParameters);

RESULT eDVBFrontendParameters::getSystem(int &t) const
{
	if (m_type == -1)
		return -1;
	t = m_type;
	return 0;
}

RESULT eDVBFrontendParameters::getDVBS(eDVBFrontendParametersSatellite &p) const
{
	if (m_type != iDVBFrontend::feSatellite)
		return -1;
	p = sat;
	return 0;
}

RESULT eDVBFrontendParameters::getDVBC(eDVBFrontendParametersCable &p) const
{
	if (m_type != iDVBFrontend::feCable)
		return -1;
	p = cable;
	return 0;
}

RESULT eDVBFrontendParameters::getDVBT(eDVBFrontendParametersTerrestrial &p) const
{
	if (m_type != iDVBFrontend::feTerrestrial)
		return -1;
	p = terrestrial;
	return 0;
}

RESULT eDVBFrontendParameters::setDVBS(const eDVBFrontendParametersSatellite &p, bool no_rotor_command_on_tune)
{
	sat = p;
	sat.no_rotor_command_on_tune = no_rotor_command_on_tune;
	m_type = iDVBFrontend::feSatellite;
	return 0;
}

RESULT eDVBFrontendParameters::setDVBC(const eDVBFrontendParametersCable &p)
{
	cable = p;
	m_type = iDVBFrontend::feCable;
	return 0;
}

RESULT eDVBFrontendParameters::setDVBT(const eDVBFrontendParametersTerrestrial &p)
{
	terrestrial = p;
	m_type = iDVBFrontend::feTerrestrial;
	return 0;
}

RESULT eDVBFrontendParameters::calculateDifference(const iDVBFrontendParameters *parm, int &diff, bool exact) const
{
	if (!parm)
		return -1;
	int type;
	if (parm->getSystem(type))
		return -1;
	if (type != m_type)
	{
		diff = 1<<30; // big difference
		return 0;
	}

	switch (type)
	{
	case iDVBFrontend::feSatellite:
	{
		eDVBFrontendParametersSatellite osat;
		if (parm->getDVBS(osat))
			return -2;

		if (sat.orbital_position != osat.orbital_position)
			diff = 1<<29;
		else if (sat.polarisation != osat.polarisation)
			diff = 1<<28;
		else if (exact && sat.fec != osat.fec && sat.fec != eDVBFrontendParametersSatellite::FEC_Auto && osat.fec != eDVBFrontendParametersSatellite::FEC_Auto)
			diff = 1<<27;
		else if (exact && sat.modulation != osat.modulation && sat.modulation != eDVBFrontendParametersSatellite::Modulation_Auto && osat.modulation != eDVBFrontendParametersSatellite::Modulation_Auto)
			diff = 1<<27;
		else
		{
			diff = abs(sat.frequency - osat.frequency);
			diff += abs(sat.symbol_rate - osat.symbol_rate);
		}
		return 0;
	}
	case iDVBFrontend::feCable:
		eDVBFrontendParametersCable ocable;
		if (parm->getDVBC(ocable))
			return -2;

		if (exact && cable.modulation != ocable.modulation
			&& cable.modulation != eDVBFrontendParametersCable::Modulation_Auto
			&& ocable.modulation != eDVBFrontendParametersCable::Modulation_Auto)
			diff = 1 << 29;
		else if (exact && cable.fec_inner != ocable.fec_inner && cable.fec_inner != eDVBFrontendParametersCable::FEC_Auto && ocable.fec_inner != eDVBFrontendParametersCable::FEC_Auto)
			diff = 1 << 27;
		else
		{
			diff = abs(cable.frequency - ocable.frequency);
			diff += abs(cable.symbol_rate - ocable.symbol_rate);
		}
		return 0;
	case iDVBFrontend::feTerrestrial:
		eDVBFrontendParametersTerrestrial oterrestrial;
		if (parm->getDVBT(oterrestrial))
			return -2;

		if (exact && oterrestrial.bandwidth != terrestrial.bandwidth &&
			oterrestrial.bandwidth != eDVBFrontendParametersTerrestrial::Bandwidth_Auto &&
			terrestrial.bandwidth != eDVBFrontendParametersTerrestrial::Bandwidth_Auto)
			diff = 1 << 30;
		else if (exact && oterrestrial.modulation != terrestrial.modulation &&
			oterrestrial.modulation != eDVBFrontendParametersTerrestrial::Modulation_Auto &&
			terrestrial.modulation != eDVBFrontendParametersTerrestrial::Modulation_Auto)
			diff = 1 << 30;
		else if (exact && oterrestrial.transmission_mode != terrestrial.transmission_mode &&
			oterrestrial.transmission_mode != eDVBFrontendParametersTerrestrial::TransmissionMode_Auto &&
			terrestrial.transmission_mode != eDVBFrontendParametersTerrestrial::TransmissionMode_Auto)
			diff = 1 << 30;
		else if (exact && oterrestrial.guard_interval != terrestrial.guard_interval &&
			oterrestrial.guard_interval != eDVBFrontendParametersTerrestrial::GuardInterval_Auto &&
			terrestrial.guard_interval != eDVBFrontendParametersTerrestrial::GuardInterval_Auto)
			diff = 1 << 30;
		else if (exact && oterrestrial.hierarchy != terrestrial.hierarchy &&
			oterrestrial.hierarchy != eDVBFrontendParametersTerrestrial::Hierarchy_Auto &&
			terrestrial.hierarchy != eDVBFrontendParametersTerrestrial::Hierarchy_Auto)
			diff = 1 << 30;
		else if (exact && oterrestrial.code_rate_LP != terrestrial.code_rate_LP &&
			oterrestrial.code_rate_LP != eDVBFrontendParametersTerrestrial::FEC_Auto &&
			terrestrial.code_rate_LP != eDVBFrontendParametersTerrestrial::FEC_Auto)
			diff = 1 << 30;
		else if (exact && oterrestrial.code_rate_HP != terrestrial.code_rate_HP &&
			oterrestrial.code_rate_HP != eDVBFrontendParametersTerrestrial::FEC_Auto &&
			terrestrial.code_rate_HP != eDVBFrontendParametersTerrestrial::FEC_Auto)
			diff = 1 << 30;
		else
			diff = abs(terrestrial.frequency - oterrestrial.frequency) / 1000;
		return 0;
	default:
		return -1;
	}
	return 0;
}

RESULT eDVBFrontendParameters::getHash(unsigned long &hash) const
{
	switch (m_type)
	{
	case iDVBFrontend::feSatellite:
	{
		hash = (sat.orbital_position << 16);
		hash |= ((sat.frequency/1000)&0xFFFF)|((sat.polarisation&1) << 15);
		return 0;
	}
	case iDVBFrontend::feCable:
		hash = 0xFFFF0000;
		hash |= (cable.frequency/1000)&0xFFFF;
		return 0;
	case iDVBFrontend::feTerrestrial:
		hash = 0xEEEE0000;
		hash |= (terrestrial.frequency/1000000)&0xFFFF;
		return 0;
	default:
		return -1;
	}
}

RESULT eDVBFrontendParameters::calcLockTimeout(unsigned int &timeout) const
{
	switch (m_type)
	{
	case iDVBFrontend::feSatellite:
	{
			/* high symbol rate transponders tune faster, due to 
				requiring less zigzag and giving more symbols faster. 

				5s are definitely not enough on really low SR when
				zigzag has to find the exact frequency first.
			*/
		if (sat.symbol_rate > 20000000)
			timeout = 5000;
		else if (sat.symbol_rate > 10000000)
			timeout = 10000;
		else
			timeout = 20000;
		return 0;
	}
	case iDVBFrontend::feCable:
		timeout = 5000;
		return 0;
	case iDVBFrontend::feTerrestrial:
		timeout = 5000;
		return 0;
	default:
		return -1;
	}
}

DEFINE_REF(eDVBFrontend);

int eDVBFrontend::PriorityOrder=0;
int eDVBFrontend::PreferredFrontendIndex = -1;

eDVBFrontend::eDVBFrontend(int adap, int fe, int &ok, bool simulate, eDVBFrontend *simulate_fe)
	:m_simulate(simulate), m_enabled(false), m_type(-1), m_simulate_fe(simulate_fe), m_dvbid(fe), m_slotid(fe)
	,m_fd(-1), m_rotor_mode(false), m_need_rotor_workaround(false), m_can_handle_dvbs2(false)
	,m_state(stateClosed), m_timeout(0), m_tuneTimer(0)
#if HAVE_DVB_API_VERSION < 3
	,m_secfd(-1)
#endif
{
#if HAVE_DVB_API_VERSION < 3
	sprintf(m_filename, "/dev/dvb/card%d/frontend%d", adap, fe);
	sprintf(m_sec_filename, "/dev/dvb/card%d/sec%d", adap, fe);
#else
	sprintf(m_filename, "/dev/dvb/adapter%d/frontend%d", adap, fe);
#endif

	m_timeout = eTimer::create(eApp);
	CONNECT(m_timeout->timeout, eDVBFrontend::timeout);

	m_tuneTimer = eTimer::create(eApp);
	CONNECT(m_tuneTimer->timeout, eDVBFrontend::tuneLoop);

	for (int i=0; i<eDVBFrontend::NUM_DATA_ENTRIES; ++i)
		m_data[i] = -1;

	m_idleInputpower[0]=m_idleInputpower[1]=0;

	ok = !openFrontend();
	closeFrontend();
}

void eDVBFrontend::reopenFrontend()
{
	sleep(1);
	m_type = -1;
	openFrontend();
}

int eDVBFrontend::openFrontend()
{
	if (m_state != stateClosed)
		return -1;  // already opened

	m_state=stateIdle;
	m_tuning=0;

	if (!m_simulate)
	{
		eDebug("opening frontend %d", m_dvbid);
		if (m_fd < 0)
		{
			m_fd = ::open(m_filename, O_RDWR|O_NONBLOCK);
			if (m_fd < 0)
			{
				eWarning("failed! (%s) %m", m_filename);
				return -1;
			}
		}
		else
			eWarning("frontend %d already opened", m_dvbid);
		if (m_type == -1)
		{
			if (::ioctl(m_fd, FE_GET_INFO, &fe_info) < 0)
			{
				eWarning("ioctl FE_GET_INFO failed");
				::close(m_fd);
				m_fd = -1;
				return -1;
			}

			switch (fe_info.type)
			{
			case FE_QPSK:
				m_type = iDVBFrontend::feSatellite;
				break;
			case FE_QAM:
				m_type = iDVBFrontend::feCable;
				break;
			case FE_OFDM:
				m_type = iDVBFrontend::feTerrestrial;
				break;
			default:
				eWarning("unknown frontend type.");
				::close(m_fd);
				m_fd = -1;
				return -1;
			}
			if (m_simulate_fe)
				m_simulate_fe->m_type = m_type;
			eDebugNoSimulate("detected %s frontend", "satellite\0cable\0    terrestrial"+fe_info.type*10);
		}

#if HAVE_DVB_API_VERSION < 3
		if (m_type == iDVBFrontend::feSatellite)
		{
				if (m_secfd < 0)
				{
					if (!m_simulate)
					{
						m_secfd = ::open(m_sec_filename, O_RDWR);
						if (m_secfd < 0)
						{
							eWarning("failed! (%s) %m", m_sec_filename);
							::close(m_fd);
							m_fd=-1;
							return -1;
						}
					}
				}
				else
					eWarning("sec %d already opened", m_dvbid);
		}
#endif

		m_sn = eSocketNotifier::create(eApp, m_fd, eSocketNotifier::Read, false);
		CONNECT(m_sn->activated, eDVBFrontend::feEvent);
	}
	else
	{
		fe_info.frequency_min = 900000;
		fe_info.frequency_max = 2200000;
	}

	setTone(iDVBFrontend::toneOff);
	setVoltage(iDVBFrontend::voltageOff);

	return 0;
}

int eDVBFrontend::closeFrontend(bool force, bool no_delayed)
{
	if (!force && m_data[CUR_VOLTAGE] != -1 && m_data[CUR_VOLTAGE] != iDVBFrontend::voltageOff)
	{
		long tmp = m_data[LINKED_NEXT_PTR];
		while (tmp != -1)
		{
			eDVBRegisteredFrontend *linked_fe = (eDVBRegisteredFrontend*)tmp;
			if (linked_fe->m_inuse)
			{
				eDebugNoSimulate("dont close frontend %d until the linked frontend %d in slot %d is still in use",
					m_dvbid, linked_fe->m_frontend->getDVBID(), linked_fe->m_frontend->getSlotID());
				return -1;
			}
			linked_fe->m_frontend->getData(LINKED_NEXT_PTR, tmp);
		}
	}

	if (m_fd >= 0)
	{
		eDebugNoSimulate("close frontend %d", m_dvbid);
		if (m_data[SATCR] != -1)
		{
			if (!no_delayed)
			{
				m_sec->prepareTurnOffSatCR(*this, m_data[SATCR]);
				m_tuneTimer->start(0, true);
				if(!m_tuneTimer->isActive())
				{
					int timeout=0;
					eDebug("[turnOffSatCR] no mainloop");
					while(true)
					{
						timeout = tuneLoopInt();
						if (timeout == -1)
							break;
						usleep(timeout*1000); // blockierendes wait.. eTimer gibts ja nicht mehr
					}
				}
				else
					eDebug("[turnOffSatCR] running mainloop");
				return 0;
			}
			else
				m_data[ROTOR_CMD] = -1;
		}

		setTone(iDVBFrontend::toneOff);
		setVoltage(iDVBFrontend::voltageOff);
		m_tuneTimer->stop();

		if (m_sec && !m_simulate)
			m_sec->setRotorMoving(m_slotid, false);
		if (!::close(m_fd))
			m_fd=-1;
		else
			eWarning("couldnt close frontend %d", m_dvbid);
	}
	else if (m_simulate)
	{
		setTone(iDVBFrontend::toneOff);
		setVoltage(iDVBFrontend::voltageOff);
	}
#if HAVE_DVB_API_VERSION < 3
	if (m_secfd >= 0)
	{
		if (!::close(m_secfd))
			m_secfd=-1;
		else
			eWarning("couldnt close sec %d", m_dvbid);
	}
#endif
	m_sn=0;
	m_state = stateClosed;

	return 0;
}

eDVBFrontend::~eDVBFrontend()
{
	m_data[LINKED_PREV_PTR] = m_data[LINKED_NEXT_PTR] = -1;
	closeFrontend();
}

void eDVBFrontend::feEvent(int w)
{
	eDVBFrontend *sec_fe = this;
	long tmp = m_data[LINKED_PREV_PTR];
	while (tmp != -1)
	{
		eDVBRegisteredFrontend *linked_fe = (eDVBRegisteredFrontend*)tmp;
		sec_fe = linked_fe->m_frontend;
		sec_fe->getData(LINKED_NEXT_PTR, tmp);
	}
	while (1)
	{
#if HAVE_DVB_API_VERSION < 3
		FrontendEvent event;
#else
		dvb_frontend_event event;
#endif
		int res;
		int state;
		res = ::ioctl(m_fd, FE_GET_EVENT, &event);

		if (res && (errno == EAGAIN))
			break;

		if (w < 0)
			continue;

#if HAVE_DVB_API_VERSION < 3
		if (event.type == FE_COMPLETION_EV)
#else
		eDebug("(%d)fe event: status %x, inversion %s, m_tuning %d", m_dvbid, event.status, (event.parameters.inversion == INVERSION_ON) ? "on" : "off", m_tuning);
		if (event.status & FE_HAS_LOCK)
#endif
		{
			state = stateLock;
		} else
		{
			if (m_tuning) {
				state = stateTuning;
#if HAVE_DVB_API_VERSION >= 3
				if (event.status & FE_TIMEDOUT) {
					eDebug("FE_TIMEDOUT! ..abort");
					m_tuneTimer->stop();
					timeout();
					return;
				}
				++m_tuning;
#else
				m_tuneTimer->stop();
				timeout();
#endif
			}
			else
			{
				eDebug("stateLostLock");
				state = stateLostLock;
				if (!m_rotor_mode)
					sec_fe->m_data[CSW] = sec_fe->m_data[UCSW] = sec_fe->m_data[TONEBURST] = -1; // reset diseqc
			}
		}
		if (m_state != state)
		{
			m_state = state;
			m_stateChanged(this);
		}
	}
}

void eDVBFrontend::timeout()
{
	m_tuning = 0;
	if (m_state == stateTuning)
	{
		m_state = stateFailed;
		m_data[CSW] = m_data[UCSW] = m_data[TONEBURST] = -1; // reset diseqc
		m_stateChanged(this);
	}
}

#define INRANGE(X,Y,Z) (((X<=Y) && (Y<=Z))||((Z<=Y) && (Y<=X)) ? 1 : 0)

/* unsigned 32 bit division */
static inline uint32_t fe_udiv(uint32_t a, uint32_t b)
{
	return (a + b / 2) / b;
}

int eDVBFrontend::readFrontendData(int type)
{
	switch(type)
	{
		case bitErrorRate:
		{
			uint32_t ber=0;
			if (!m_simulate)
			{
				if (ioctl(m_fd, FE_READ_BER, &ber) < 0 && errno != ERANGE)
					eDebug("FE_READ_BER failed (%m)");
			}
			return ber;
		}
		case signalQuality:
		case signalQualitydB: /* this will move into the driver */
		{
			int sat_max = 1600; // for stv0288 / bsbe2
			int ret = 0x12345678;
			uint16_t snr=0;
			if (m_simulate)
				return 0;
			if (ioctl(m_fd, FE_READ_SNR, &snr) < 0 && errno != ERANGE)
				eDebug("FE_READ_SNR failed (%m)");
			else if (!strcmp(m_description, "AVL2108")) // ET9000
			{
				ret = (int)(snr / 40.5);
				sat_max = 1618;
			}
			else if (!strcmp(m_description, "BCM4501 (internal)"))
			{
				float SDS_SNRE = snr << 16;
				float snr_in_db;

				if (oparm.sat.system == eDVBFrontendParametersSatellite::System_DVB_S) // DVB-S1 / QPSK
				{
					static float SNR_COEFF[6] = {
						100.0 / 4194304.0,
						-7136.0 / 4194304.0,
						197418.0 / 4194304.0,
						-2602183.0 / 4194304.0,
						20377212.0 / 4194304.0,
						-37791203.0 / 4194304.0,
					};
					float fval1 = 12.44714 - (2.0 * log10(SDS_SNRE / 256.0)),
	    				  fval2 = pow(10.0, fval1)-1;
					fval1 = 10.0 * log10(fval2);

					if (fval1 < 10.0)
					{
						fval2 = SNR_COEFF[0];
						for (int i=1; i<6; ++i)
						{
							fval2 *= fval1;
							fval2 += SNR_COEFF[i];
						}
						fval1 = fval2;
					}
					snr_in_db = fval1;
				}
#if HAVE_DVB_API_VERSION >= 3
				else
				{
					float fval1 = SDS_SNRE / 268435456.0,
						  fval2, fval3, fval4;

					if (oparm.sat.modulation == eDVBFrontendParametersSatellite::Modulation_QPSK)
					{
						fval2 = 6.76;
						fval3 = 4.35;
					}
					else // 8PSK
					{
						fval1 *= 0.5;
						fval2 = 8.06;
						fval3 = 6.18;
					}
					fval4 = -10.0 * log10(fval1);
					fval1 = fval4;
					for (int i=0; i < 5; ++i)
						fval1 = fval4 - fval2 * log10(1.0+pow(10.0, (fval3-fval1)/fval2));
					snr_in_db = fval1;
				}
#endif
				sat_max = 1750;
				ret = (int)(snr_in_db * 100);
			}
			else if (strstr(m_description, "Alps BSBE1 C01A") ||
				strstr(m_description, "Alps -S(STV0288)"))
			{
				if (snr == 0)
					ret = 0;
				else if (snr == 0xFFFF) // i think this should not happen
					ret = 100*100;
				else
				{
					enum { REALVAL, REGVAL };
					const long CN_lookup[31][2] = {
						{20,8900}, {25,8680}, {30,8420}, {35,8217}, {40,7897},
						{50,7333}, {60,6747}, {70,6162}, {80,5580}, {90,5029},
						{100,4529}, {110,4080}, {120,3685}, {130,3316}, {140,2982},
						{150,2688}, {160,2418}, {170,2188}, {180,1982}, {190,1802},
						{200,1663}, {210,1520}, {220,1400}, {230,1295}, {240,1201},
						{250,1123}, {260,1058}, {270,1004}, {280,957}, {290,920},
						{300,890}
					};
					int add=strchr(m_description, '.') ? 0xA250 : 0xA100;
					long regval = 0xFFFF - ((snr / 3) + add), // revert some dvb api calulations to get the real register value
						Imin=0,
						Imax=30,
						i;
					if(INRANGE(CN_lookup[Imin][REGVAL],regval,CN_lookup[Imax][REGVAL]))
					{
						while((Imax-Imin)>1)
						{
							i=(Imax+Imin)/2;
							if(INRANGE(CN_lookup[Imin][REGVAL],regval,CN_lookup[i][REGVAL]))
								Imax = i;
							else
								Imin = i;
						}
						ret = (((regval - CN_lookup[Imin][REGVAL])
								* (CN_lookup[Imax][REALVAL] - CN_lookup[Imin][REALVAL])
								/ (CN_lookup[Imax][REGVAL] - CN_lookup[Imin][REGVAL]))
								+ CN_lookup[Imin][REALVAL]) * 10;
					}
					else
						ret = 100;
				}
			}
			else if (!strcmp(m_description, "Alps BSBE1 702A") ||  // some frontends with STV0299
				!strcmp(m_description, "Alps -S") ||
				!strcmp(m_description, "Philips -S") ||
				!strcmp(m_description, "LG -S") )
			{
				sat_max = 1500;
				ret = (int)((snr-39075)/17.647);
			} else if (!strcmp(m_description, "Alps BSBE2"))
			{
				ret = (int)((snr >> 7) * 10);
			} else if (!strcmp(m_description, "Philips CU1216Mk3"))
			{
				int mse = (~snr) & 0xFF;
				switch (parm_u_qam_modulation) {
				case QAM_16: ret = fe_udiv(1950000, (32 * mse) + 138) + 1000; break;
				case QAM_32: ret = fe_udiv(2150000, (40 * mse) + 500) + 1350; break;
				case QAM_64: ret = fe_udiv(2100000, (40 * mse) + 500) + 1250; break;
				case QAM_128: ret = fe_udiv(1850000, (38 * mse) + 400) + 1380; break;
				case QAM_256: ret = fe_udiv(1800000, (100 * mse) + 40) + 2030; break;
				default: break;
				}
			} else if (!strcmp(m_description, "Philips TU1216"))
			{
				snr = 0xFF - (snr & 0xFF);
				if (snr != 0)
					ret = 10 * (int)(-100 * (log10(snr) - log10(255)));
			}
			else if (strstr(m_description, "BCM4506") || strstr(m_description, "BCM4505"))
			{
				ret = (snr * 100) >> 8;
			}
			else if (!strcmp(m_description, "Genpix"))
			{
				ret = (int)((snr << 1) / 5);
			}
			else if (!strcmp(m_description, "CXD1981"))
			{
				int mse = (~snr) & 0xFF;
				switch (parm_u_qam_modulation) {
					case QAM_16:
					case QAM_64:
					case QAM_256: ret = (int)(-950 * log(((double)mse) / 760)); break;
					case QAM_32:
					case QAM_128: ret = (int)(-875 * log(((double)mse) / 650)); break;

					default: break;
				}
			}

			if (type == signalQuality)
			{
				if (ret == 0x12345678) // no snr db calculation avail.. return untouched snr value..
					return snr;
				switch(m_type)
				{
					case feSatellite:
						return ret >= sat_max ? 65536 : ret * 65536 / sat_max;
					case feCable: // we assume a max of 42db here
						return ret >= 4200 ? 65536 : ret * 65536 / 4200;
					case feTerrestrial: // we assume a max of 24db here
						return ret >= 2400 ? 65536 : ret * 65536 / 2400;
				}
			}
/* else
				eDebug("no SNR dB calculation for frontendtype %s yet", m_description); */
			return ret;
		}
		case signalPower:
		{
			uint16_t strength=0;
			if (!m_simulate)
			{
				if (ioctl(m_fd, FE_READ_SIGNAL_STRENGTH, &strength) < 0 && errno != ERANGE)
					eDebug("FE_READ_SIGNAL_STRENGTH failed (%m)");
			}
			return strength;
		}
		case locked:
		{
#if HAVE_DVB_API_VERSION < 3
			FrontendStatus status=0;
#else
			fe_status_t status;
#endif
			if (!m_simulate)
			{
				if ( ioctl(m_fd, FE_READ_STATUS, &status) < 0 && errno != ERANGE )
					eDebug("FE_READ_STATUS failed (%m)");
				return !!(status&FE_HAS_LOCK);
			}
			return 1;
		}
		case synced:
		{
#if HAVE_DVB_API_VERSION < 3
			FrontendStatus status=0;
#else
			fe_status_t status;
#endif
			if (!m_simulate)
			{
				if ( ioctl(m_fd, FE_READ_STATUS, &status) < 0 && errno != ERANGE )
					eDebug("FE_READ_STATUS failed (%m)");
				return !!(status&FE_HAS_SYNC);
			}
			return 1;
		}
		case frontendNumber:
			return m_slotid;
	}
	return 0;
}

void PutToDict(ePyObject &dict, const char*key, long value)
{
	ePyObject item = PyInt_FromLong(value);
	if (item)
	{
		if (PyDict_SetItemString(dict, key, item))
			eDebug("put %s to dict failed", key);
		Py_DECREF(item);
	}
	else
		eDebug("could not create PyObject for %s", key);
}

void PutToDict(ePyObject &dict, const char*key, ePyObject item)
{
	if (item)
	{
		if (PyDict_SetItemString(dict, key, item))
			eDebug("put %s to dict failed", key);
		Py_DECREF(item);
	}
	else
		eDebug("invalid PyObject for %s", key);
}

void PutToDict(ePyObject &dict, const char*key, const char *value)
{
	ePyObject item = PyString_FromString(value);
	if (item)
	{
		if (PyDict_SetItemString(dict, key, item))
			eDebug("put %s to dict failed", key);
		Py_DECREF(item);
	}
	else
		eDebug("could not create PyObject for %s", key);
}

void PutSatelliteDataToDict(ePyObject &dict, eDVBFrontendParametersSatellite &feparm)
{
	PutToDict(dict, "tuner_type", "DVB-S");
	PutToDict(dict, "frequency", feparm.frequency);
	PutToDict(dict, "symbol_rate", feparm.symbol_rate);
	PutToDict(dict, "orbital_position", feparm.orbital_position);
	PutToDict(dict, "inversion", feparm.inversion);
	PutToDict(dict, "fec_inner", feparm.fec);
	PutToDict(dict, "modulation", feparm.modulation);
	PutToDict(dict, "polarization", feparm.polarisation);
	if (feparm.system == eDVBFrontendParametersSatellite::System_DVB_S2)
	{
		PutToDict(dict, "rolloff", feparm.rolloff);
		PutToDict(dict, "pilot", feparm.pilot);
	}
	PutToDict(dict, "system", feparm.system);
}

void PutTerrestrialDataToDict(ePyObject &dict, eDVBFrontendParametersTerrestrial &feparm)
{
	PutToDict(dict, "tuner_type", "DVB-T");
	PutToDict(dict, "frequency", feparm.frequency);
	PutToDict(dict, "bandwidth", feparm.bandwidth);
	PutToDict(dict, "code_rate_lp", feparm.code_rate_LP);
	PutToDict(dict, "code_rate_hp", feparm.code_rate_HP);
	PutToDict(dict, "constellation", feparm.modulation);
	PutToDict(dict, "transmission_mode", feparm.transmission_mode);
	PutToDict(dict, "guard_interval", feparm.guard_interval);
	PutToDict(dict, "hierarchy_information", feparm.hierarchy);
	PutToDict(dict, "inversion", feparm.inversion);
}

void PutCableDataToDict(ePyObject &dict, eDVBFrontendParametersCable &feparm)
{
	PutToDict(dict, "tuner_type", "DVB-C");
	PutToDict(dict, "frequency", feparm.frequency);
	PutToDict(dict, "symbol_rate", feparm.symbol_rate);
	PutToDict(dict, "modulation", feparm.modulation);
	PutToDict(dict, "inversion", feparm.inversion);
	PutToDict(dict, "fec_inner", feparm.fec_inner);
}

#if HAVE_DVB_API_VERSION >= 5
static void fillDictWithSatelliteData(ePyObject dict, struct dtv_property *p, unsigned int propertycount, long freq_offset, int orb_pos, int polarization)
{
	long tmp = 0;
	long system = eDVBFrontendParametersSatellite::System_DVB_S;

	PutToDict(dict, "orbital_position", orb_pos);
	PutToDict(dict, "polarization", polarization);

	for (unsigned int i = 0; i < propertycount; i++)
	{
		switch (p[i].cmd)
		{
		case DTV_FREQUENCY:
			PutToDict(dict, "frequency", p[i].u.data + freq_offset);
			break;
		case DTV_SYMBOL_RATE:
			PutToDict(dict, "symbol_rate", p[i].u.data);
			break;
		case DTV_INNER_FEC:
			switch (p[i].u.data)
			{
			case FEC_1_2: tmp = eDVBFrontendParametersSatellite::FEC_1_2; break;
			case FEC_2_3: tmp = eDVBFrontendParametersSatellite::FEC_2_3; break;
			case FEC_3_4: tmp = eDVBFrontendParametersSatellite::FEC_3_4; break;
			case FEC_3_5: tmp = eDVBFrontendParametersSatellite::FEC_3_5; break;
			case FEC_4_5: tmp = eDVBFrontendParametersSatellite::FEC_4_5; break;
			case FEC_5_6: tmp = eDVBFrontendParametersSatellite::FEC_5_6; break;
			case FEC_6_7: tmp = eDVBFrontendParametersSatellite::FEC_6_7; break;
			case FEC_7_8: tmp = eDVBFrontendParametersSatellite::FEC_7_8; break;
			case FEC_8_9: tmp = eDVBFrontendParametersSatellite::FEC_8_9; break;
			case FEC_9_10: tmp = eDVBFrontendParametersSatellite::FEC_9_10; break;
			case FEC_NONE: tmp = eDVBFrontendParametersSatellite::FEC_None; break;
			default: eDebug("got unsupported FEC from frontend! report as FEC_AUTO!\n");
			case FEC_AUTO: tmp = eDVBFrontendParametersSatellite::FEC_Auto; break;
			}
			PutToDict(dict, "fec_inner", tmp);
			break;
		case DTV_INVERSION:
			switch (p[i].u.data)
			{
			case INVERSION_OFF: tmp = eDVBFrontendParametersSatellite::Inversion_Off; break;
			case INVERSION_ON: tmp = eDVBFrontendParametersSatellite::Inversion_On; break;
			default: eDebug("got unsupported inversion from frontend! report as INVERSION_AUTO!\n");
			case INVERSION_AUTO: tmp = eDVBFrontendParametersSatellite::Inversion_Unknown; break;
			}
			PutToDict(dict, "inversion", tmp);
			break;
		case DTV_DELIVERY_SYSTEM:
			switch (p[i].u.data)
			{
			default: eDebug("got unsupported system from frontend! report as DVBS!");
			case SYS_DVBS: system = eDVBFrontendParametersSatellite::System_DVB_S; break;
			case SYS_DVBS2: system = eDVBFrontendParametersSatellite::System_DVB_S2; break;
			}
			PutToDict(dict, "system", system);
			break;
		case DTV_MODULATION:
			switch (p[i].u.data)
			{
			default: eDebug("got unsupported modulation from frontend! report as QPSK!");
			case QPSK: tmp = eDVBFrontendParametersSatellite::Modulation_QPSK; break;
			case PSK_8: tmp = eDVBFrontendParametersSatellite::Modulation_8PSK; break;
			}
			PutToDict(dict, "modulation", tmp);
			break;
		case DTV_ROLLOFF:
			if (system == eDVBFrontendParametersSatellite::System_DVB_S2)
			{
				switch (p[i].u.data)
				{
				case ROLLOFF_20: tmp = eDVBFrontendParametersSatellite::RollOff_alpha_0_20; break;
				case ROLLOFF_25: tmp = eDVBFrontendParametersSatellite::RollOff_alpha_0_25; break;
				case ROLLOFF_35: tmp = eDVBFrontendParametersSatellite::RollOff_alpha_0_35; break;
				default:
				case ROLLOFF_AUTO: tmp = eDVBFrontendParametersSatellite::RollOff_auto; break;
				}
				PutToDict(dict, "rolloff", tmp);
			}
			break;
		case DTV_PILOT:
			if (system == eDVBFrontendParametersSatellite::System_DVB_S2)
			{
				switch (p[i].u.data)
				{
				case PILOT_OFF: tmp = eDVBFrontendParametersSatellite::Pilot_Off; break;
				case PILOT_ON: tmp = eDVBFrontendParametersSatellite::Pilot_On; break;
				default:
				case PILOT_AUTO: tmp = eDVBFrontendParametersSatellite::Pilot_Unknown; break;
				}
				PutToDict(dict, "pilot", tmp);
			}
			break;
		}
	}
}

#else
static void fillDictWithSatelliteData(ePyObject dict, const FRONTENDPARAMETERS &parm, long freq_offset, int orb_pos, int polarization)
{
	long tmp=0;
	int frequency = parm_frequency + freq_offset;
	PutToDict(dict, "frequency", frequency);
	PutToDict(dict, "symbol_rate", parm_u_qpsk_symbol_rate);
	PutToDict(dict, "orbital_position", orb_pos);
	PutToDict(dict, "polarization", polarization);

	switch((int)parm_u_qpsk_fec_inner)
	{
	case FEC_1_2: tmp = eDVBFrontendParametersSatellite::FEC_1_2; break;
	case FEC_2_3: tmp = eDVBFrontendParametersSatellite::FEC_2_3; break;
	case FEC_3_4: tmp = eDVBFrontendParametersSatellite::FEC_3_4; break;
	case FEC_5_6: tmp = eDVBFrontendParametersSatellite::FEC_5_6; break;
	case FEC_6_7: tmp = eDVBFrontendParametersSatellite::FEC_6_7; break;
	case FEC_7_8: tmp = eDVBFrontendParametersSatellite::FEC_7_8; break;
	case FEC_NONE: tmp = eDVBFrontendParametersSatellite::FEC_None; break;
	default:
	case FEC_AUTO: tmp = eDVBFrontendParametersSatellite::FEC_Auto; break;
#if HAVE_DVB_API_VERSION >=3
	case FEC_S2_8PSK_1_2:
	case FEC_S2_QPSK_1_2: tmp = eDVBFrontendParametersSatellite::FEC_1_2; break;
	case FEC_S2_8PSK_2_3:
	case FEC_S2_QPSK_2_3: tmp = eDVBFrontendParametersSatellite::FEC_2_3; break;
	case FEC_S2_8PSK_3_4:
	case FEC_S2_QPSK_3_4: tmp = eDVBFrontendParametersSatellite::FEC_3_4; break;
	case FEC_S2_8PSK_5_6:
	case FEC_S2_QPSK_5_6: tmp = eDVBFrontendParametersSatellite::FEC_5_6; break;
	case FEC_S2_8PSK_7_8:
	case FEC_S2_QPSK_7_8: tmp = eDVBFrontendParametersSatellite::FEC_7_8; break;
	case FEC_S2_8PSK_8_9:
	case FEC_S2_QPSK_8_9: tmp = eDVBFrontendParametersSatellite::FEC_8_9; break;
	case FEC_S2_8PSK_3_5:
	case FEC_S2_QPSK_3_5: tmp = eDVBFrontendParametersSatellite::FEC_3_5; break;
	case FEC_S2_8PSK_4_5:
	case FEC_S2_QPSK_4_5: tmp = eDVBFrontendParametersSatellite::FEC_4_5; break;
	case FEC_S2_8PSK_9_10:
	case FEC_S2_QPSK_9_10: tmp = eDVBFrontendParametersSatellite::FEC_9_10; break;
#endif
	}
	PutToDict(dict, "fec_inner", tmp);
#if HAVE_DVB_API_VERSION >=3
	PutToDict(dict, "modulation",
		parm_u_qpsk_fec_inner > FEC_S2_QPSK_9_10 ?
			eDVBFrontendParametersSatellite::Modulation_8PSK :
			eDVBFrontendParametersSatellite::Modulation_QPSK );
	if (parm_u_qpsk_fec_inner > FEC_AUTO)
	{
		switch(parm_inversion & 0xc)
		{
		default: tmp = eDVBFrontendParametersSatellite::RollOff_auto; break;
		case 0: tmp = eDVBFrontendParametersSatellite::RollOff_alpha_0_35; break;
		case 4: tmp = eDVBFrontendParametersSatellite::RollOff_alpha_0_25; break;
		case 8: tmp = eDVBFrontendParametersSatellite::RollOff_alpha_0_20; break;
		}
		PutToDict(dict, "rolloff", tmp);
		switch(parm_inversion & 0x30)
		{
		case 0: tmp = eDVBFrontendParametersSatellite::Pilot_Off; break;
		case 0x10: tmp = eDVBFrontendParametersSatellite::Pilot_On; break;
		case 0x20: tmp = eDVBFrontendParametersSatellite::Pilot_Unknown; break;
		}
		PutToDict(dict, "pilot", tmp);
		tmp = eDVBFrontendParametersSatellite::System_DVB_S2;
	}
	else
		tmp = eDVBFrontendParametersSatellite::System_DVB_S;
#else
	PutToDict(dict, "modulation", eDVBFrontendParametersSatellite::Modulation_QPSK );
	tmp = eDVBFrontendParametersSatellite::System_DVB_S;
#endif
	PutToDict(dict, "system", tmp);
}
#endif

static void fillDictWithCableData(ePyObject dict, const FRONTENDPARAMETERS &parm)
{
	long tmp=0;
#if HAVE_DVB_API_VERSION < 3
	PutToDict(dict, "frequency", parm_frequency);
#else
	PutToDict(dict, "frequency", parm_frequency/1000);
#endif
	PutToDict(dict, "symbol_rate", parm_u_qam_symbol_rate);
	switch(parm_u_qam_fec_inner)
	{
	case FEC_NONE: tmp = eDVBFrontendParametersCable::FEC_None; break;
	case FEC_1_2: tmp = eDVBFrontendParametersCable::FEC_1_2; break;
	case FEC_2_3: tmp = eDVBFrontendParametersCable::FEC_2_3; break;
	case FEC_3_4: tmp = eDVBFrontendParametersCable::FEC_3_4; break;
	case FEC_5_6: tmp = eDVBFrontendParametersCable::FEC_5_6; break;
	case FEC_6_7: tmp = eDVBFrontendParametersCable::FEC_6_7; break;
	case FEC_7_8: tmp = eDVBFrontendParametersCable::FEC_7_8; break;
#if HAVE_DVB_API_VERSION >= 3
	case FEC_8_9: tmp = eDVBFrontendParametersCable::FEC_7_8; break;
#endif
	default:
	case FEC_AUTO: tmp = eDVBFrontendParametersCable::FEC_Auto; break;
	}
	PutToDict(dict, "fec_inner", tmp);
	switch(parm_u_qam_modulation)
	{
	case QAM_16: tmp = eDVBFrontendParametersCable::Modulation_QAM16; break;
	case QAM_32: tmp = eDVBFrontendParametersCable::Modulation_QAM32; break;
	case QAM_64: tmp = eDVBFrontendParametersCable::Modulation_QAM64; break;
	case QAM_128: tmp = eDVBFrontendParametersCable::Modulation_QAM128; break;
	case QAM_256: tmp = eDVBFrontendParametersCable::Modulation_QAM256; break;
	default:
	case QAM_AUTO:   tmp = eDVBFrontendParametersCable::Modulation_Auto; break;
	}
	PutToDict(dict, "modulation", tmp);
}

static void fillDictWithTerrestrialData(ePyObject dict, const FRONTENDPARAMETERS &parm)
{
	long tmp=0;
	PutToDict(dict, "frequency", parm_frequency);
	switch (parm_u_ofdm_bandwidth)
	{
	case BANDWIDTH_8_MHZ: tmp = eDVBFrontendParametersTerrestrial::Bandwidth_8MHz; break;
	case BANDWIDTH_7_MHZ: tmp = eDVBFrontendParametersTerrestrial::Bandwidth_7MHz; break;
	case BANDWIDTH_6_MHZ: tmp = eDVBFrontendParametersTerrestrial::Bandwidth_6MHz; break;
	default:
	case BANDWIDTH_AUTO: tmp = eDVBFrontendParametersTerrestrial::Bandwidth_Auto; break;
	}
	PutToDict(dict, "bandwidth", tmp);
	switch (parm_u_ofdm_code_rate_LP)
	{
	case FEC_1_2: tmp = eDVBFrontendParametersTerrestrial::FEC_1_2; break;
	case FEC_2_3: tmp = eDVBFrontendParametersTerrestrial::FEC_2_3; break;
	case FEC_3_4: tmp = eDVBFrontendParametersTerrestrial::FEC_3_4; break;
	case FEC_5_6: tmp = eDVBFrontendParametersTerrestrial::FEC_5_6; break;
	case FEC_7_8: tmp = eDVBFrontendParametersTerrestrial::FEC_7_8; break;
	default:
	case FEC_AUTO: tmp = eDVBFrontendParametersTerrestrial::FEC_Auto; break;
	}
	PutToDict(dict, "code_rate_lp", tmp);
	switch (parm_u_ofdm_code_rate_HP)
	{
	case FEC_1_2: tmp = eDVBFrontendParametersTerrestrial::FEC_1_2; break;
	case FEC_2_3: tmp = eDVBFrontendParametersTerrestrial::FEC_2_3; break;
	case FEC_3_4: tmp = eDVBFrontendParametersTerrestrial::FEC_3_4; break;
	case FEC_5_6: tmp = eDVBFrontendParametersTerrestrial::FEC_5_6; break;
	case FEC_7_8: tmp = eDVBFrontendParametersTerrestrial::FEC_7_8; break;
	default:
	case FEC_AUTO: tmp = eDVBFrontendParametersTerrestrial::FEC_Auto; break;
	}
	PutToDict(dict, "code_rate_hp", tmp);
	switch (parm_u_ofdm_constellation)
	{
	case QPSK: tmp = eDVBFrontendParametersTerrestrial::Modulation_QPSK; break;
	case QAM_16: tmp = eDVBFrontendParametersTerrestrial::Modulation_QAM16; break;
	case QAM_64: tmp = eDVBFrontendParametersTerrestrial::Modulation_QAM64; break;
	default:
	case QAM_AUTO: tmp = eDVBFrontendParametersTerrestrial::Modulation_Auto; break;
	}
	PutToDict(dict, "constellation", tmp);
	switch (parm_u_ofdm_transmission_mode)
	{
	case TRANSMISSION_MODE_2K: tmp = eDVBFrontendParametersTerrestrial::TransmissionMode_2k; break;
	case TRANSMISSION_MODE_8K: tmp = eDVBFrontendParametersTerrestrial::TransmissionMode_8k; break;
	default:
	case TRANSMISSION_MODE_AUTO: tmp = eDVBFrontendParametersTerrestrial::TransmissionMode_Auto; break;
	}
	PutToDict(dict, "transmission_mode", tmp);
	switch (parm_u_ofdm_guard_interval)
	{
		case GUARD_INTERVAL_1_32: tmp = eDVBFrontendParametersTerrestrial::GuardInterval_1_32; break;
		case GUARD_INTERVAL_1_16: tmp = eDVBFrontendParametersTerrestrial::GuardInterval_1_16; break;
		case GUARD_INTERVAL_1_8: tmp = eDVBFrontendParametersTerrestrial::GuardInterval_1_8; break;
		case GUARD_INTERVAL_1_4: tmp = eDVBFrontendParametersTerrestrial::GuardInterval_1_4; break;
		default:
		case GUARD_INTERVAL_AUTO: tmp = eDVBFrontendParametersTerrestrial::GuardInterval_Auto; break;
	}
	PutToDict(dict, "guard_interval", tmp);
	switch (parm_u_ofdm_hierarchy_information)
	{
		case HIERARCHY_NONE: tmp = eDVBFrontendParametersTerrestrial::Hierarchy_None; break;
		case HIERARCHY_1: tmp = eDVBFrontendParametersTerrestrial::Hierarchy_1; break;
		case HIERARCHY_2: tmp = eDVBFrontendParametersTerrestrial::Hierarchy_2; break;
		case HIERARCHY_4: tmp = eDVBFrontendParametersTerrestrial::Hierarchy_4; break;
		default:
		case HIERARCHY_AUTO: tmp = eDVBFrontendParametersTerrestrial::Hierarchy_Auto; break;
	}
	PutToDict(dict, "hierarchy_information", tmp);
}

void eDVBFrontend::getFrontendStatus(ePyObject dest)
{
	if (dest && PyDict_Check(dest))
	{
		const char *tmp = "UNKNOWN";
		switch(m_state)
		{
			case stateIdle:
				tmp="IDLE";
				break;
			case stateTuning:
				tmp="TUNING";
				break;
			case stateFailed:
				tmp="FAILED";
				break;
			case stateLock:
				tmp="LOCKED";
				break;
			case stateLostLock:
				tmp="LOSTLOCK";
				break;
			default:
				break;
		}
		PutToDict(dest, "tuner_state", tmp);
		PutToDict(dest, "tuner_locked", readFrontendData(locked));
		PutToDict(dest, "tuner_synced", readFrontendData(synced));
		PutToDict(dest, "tuner_bit_error_rate", readFrontendData(bitErrorRate));
		PutToDict(dest, "tuner_signal_quality", readFrontendData(signalQuality));
		int sigQualitydB = readFrontendData(signalQualitydB);
		if (sigQualitydB == 0x12345678) // not support yet
		{
			ePyObject obj=Py_None;
			Py_INCREF(obj);
			PutToDict(dest, "tuner_signal_quality_db", obj);
		}
		else
			PutToDict(dest, "tuner_signal_quality_db", sigQualitydB);
		PutToDict(dest, "tuner_signal_power", readFrontendData(signalPower));
	}
}

void eDVBFrontend::getTransponderData(ePyObject dest, bool original)
{
	if (dest && PyDict_Check(dest))
	{
		FRONTENDPARAMETERS front;
#if HAVE_DVB_API_VERSION >= 5
		struct dtv_property p[16];
		struct dtv_properties cmdseq;
		cmdseq.props = p;
		cmdseq.num = 0;
#endif
		if (m_simulate || m_fd == -1 || original)
			original = true;
#if HAVE_DVB_API_VERSION >= 5
		else if (m_type == feSatellite)
		{
			p[cmdseq.num++].cmd = DTV_FREQUENCY;
			p[cmdseq.num++].cmd = DTV_SYMBOL_RATE;
			p[cmdseq.num++].cmd = DTV_INNER_FEC;
			p[cmdseq.num++].cmd = DTV_INVERSION;
			p[cmdseq.num++].cmd = DTV_DELIVERY_SYSTEM;
			p[cmdseq.num++].cmd = DTV_MODULATION;
			p[cmdseq.num++].cmd = DTV_ROLLOFF;
			p[cmdseq.num++].cmd = DTV_PILOT;
			if (ioctl(m_fd, FE_GET_PROPERTY, &cmdseq) < 0)
			{
				eDebug("FE_GET_PROPERTY failed (%m)");
				original = true;
			}
		}
#endif
		else if (ioctl(m_fd, FE_GET_FRONTEND, &front)<0)
		{
			eDebug("FE_GET_FRONTEND failed (%m)");
			original = true;
		}
		if (original)
		{
			switch(m_type)
			{
				case feSatellite:
					PutSatelliteDataToDict(dest, oparm.sat);
					break;
				case feCable:
					PutCableDataToDict(dest, oparm.cab);
					break;
				case feTerrestrial:
					PutTerrestrialDataToDict(dest, oparm.ter);
					break;
			}
		}
		else
		{
			FRONTENDPARAMETERS &parm = front;
			long tmp = eDVBFrontendParametersSatellite::Inversion_Unknown;
			switch(parm_inversion & 3)
			{
				case INVERSION_ON:
					tmp = eDVBFrontendParametersSatellite::Inversion_On;
					break;
				case INVERSION_OFF:
					tmp = eDVBFrontendParametersSatellite::Inversion_Off;
				default:
					break;
			}
			PutToDict(dest, "inversion", tmp);
			switch(m_type)
			{
				case feSatellite:
#if HAVE_DVB_API_VERSION >= 5
					fillDictWithSatelliteData(dest, cmdseq.props, cmdseq.num, m_data[FREQ_OFFSET], oparm.sat.orbital_position, oparm.sat.polarisation);
#else
					fillDictWithSatelliteData(dest, parm, m_data[FREQ_OFFSET], oparm.sat.orbital_position, oparm.sat.polarisation);
#endif
					break;
				case feCable:
					fillDictWithCableData(dest, parm);
					break;
				case feTerrestrial:
					fillDictWithTerrestrialData(dest, parm);
					break;
			}
		}
	}
}

void eDVBFrontend::getFrontendData(ePyObject dest)
{
	if (dest && PyDict_Check(dest))
	{
		const char *tmp=0;
		PutToDict(dest, "tuner_number", m_slotid);
		switch(m_type)
		{
			case feSatellite:
				tmp = "DVB-S";
				break;
			case feCable:
				tmp = "DVB-C";
				break;
			case feTerrestrial:
				tmp = "DVB-T";
				break;
			default:
				tmp = "UNKNOWN";
				break;
		}
		PutToDict(dest, "tuner_type", tmp);
	}
}

#ifndef FP_IOCTL_GET_ID
#define FP_IOCTL_GET_ID 0
#endif
int eDVBFrontend::readInputpower()
{
	if (m_simulate)
		return 0;
	int power=m_slotid;  // this is needed for read inputpower from the correct tuner !
	char proc_name[64];
	char proc_name2[64];
	sprintf(proc_name, "/proc/stb/frontend/%d/lnb_sense", m_slotid);
	sprintf(proc_name2, "/proc/stb/fp/lnb_sense%d", m_slotid);
	FILE *f;
	if ((f=fopen(proc_name, "r")) || (f=fopen(proc_name2, "r")))
	{
		if (fscanf(f, "%d", &power) != 1)
			eDebug("read %s failed!! (%m)", proc_name);
		else
			eDebug("%s is %d\n", proc_name, power);
		fclose(f);
	}
	else
	{
		// open front prozessor
		int fp=::open("/dev/dbox/fp0", O_RDWR);
		if (fp < 0)
		{
			eDebug("couldn't open fp");
			return -1;
		}
		static bool old_fp = (::ioctl(fp, FP_IOCTL_GET_ID) < 0);
		if ( ioctl( fp, old_fp ? 9 : 0x100, &power ) < 0 )
		{
			eDebug("FP_IOCTL_GET_LNB_CURRENT failed (%m)");
			return -1;
		}
		::close(fp);
	}

	return power;
}

bool eDVBFrontend::setSecSequencePos(int steps)
{
	eDebugNoSimulate("set sequence pos %d", steps);
	if (!steps)
		return false;
	while( steps > 0 )
	{
		if (m_sec_sequence.current() != m_sec_sequence.end())
			++m_sec_sequence.current();
		--steps;
	}
	while( steps < 0 )
	{
		if (m_sec_sequence.current() != m_sec_sequence.begin() && m_sec_sequence.current() != m_sec_sequence.end())
			--m_sec_sequence.current();
		++steps;
	}
	return true;
}

void eDVBFrontend::tuneLoop()
{
	tuneLoopInt();
}

int eDVBFrontend::tuneLoopInt()  // called by m_tuneTimer
{
	int delay=-1;
	eDVBFrontend *sec_fe = this;
	eDVBRegisteredFrontend *regFE = 0;
	long tmp = m_data[LINKED_PREV_PTR];
	while ( tmp != -1 )
	{
		eDVBRegisteredFrontend *prev = (eDVBRegisteredFrontend *)tmp;
		sec_fe = prev->m_frontend;
		tmp = prev->m_frontend->m_data[LINKED_PREV_PTR];
		if (tmp == -1 && sec_fe != this && !prev->m_inuse) {
			int state = sec_fe->m_state;
			// workaround to put the kernel frontend thread into idle state!
			if (state != eDVBFrontend::stateIdle && state != stateClosed)
			{
				sec_fe->closeFrontend(true);
				state = sec_fe->m_state;
			}
			// sec_fe is closed... we must reopen it here..
			if (state == stateClosed)
			{
				regFE = prev;
				prev->inc_use();
			}
		}
	}

	if ( m_sec_sequence && m_sec_sequence.current() != m_sec_sequence.end() )
	{
		long *sec_fe_data = sec_fe->m_data;
//		eDebugNoSimulate("tuneLoop %d\n", m_sec_sequence.current()->cmd);
		delay = 0;
		switch (m_sec_sequence.current()->cmd)
		{
			case eSecCommand::SLEEP:
				delay = m_sec_sequence.current()++->msec;
				eDebugNoSimulate("[SEC] sleep %dms", delay);
				break;
			case eSecCommand::GOTO:
				if ( !setSecSequencePos(m_sec_sequence.current()->steps) )
					++m_sec_sequence.current();
				break;
			case eSecCommand::SET_VOLTAGE:
			{
				int voltage = m_sec_sequence.current()++->voltage;
				eDebugNoSimulate("[SEC] setVoltage %d", voltage);
				sec_fe->setVoltage(voltage);
				break;
			}
			case eSecCommand::IF_VOLTAGE_GOTO:
			{
				eSecCommand::pair &compare = m_sec_sequence.current()->compare;
				if ( compare.voltage == sec_fe_data[CUR_VOLTAGE] && setSecSequencePos(compare.steps) )
					break;
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::IF_NOT_VOLTAGE_GOTO:
			{
				eSecCommand::pair &compare = m_sec_sequence.current()->compare;
				if ( compare.voltage != sec_fe_data[CUR_VOLTAGE] && setSecSequencePos(compare.steps) )
					break;
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::IF_TONE_GOTO:
			{
				eSecCommand::pair &compare = m_sec_sequence.current()->compare;
				if ( compare.tone == sec_fe_data[CUR_TONE] && setSecSequencePos(compare.steps) )
					break;
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::IF_NOT_TONE_GOTO:
			{
				eSecCommand::pair &compare = m_sec_sequence.current()->compare;
				if ( compare.tone != sec_fe_data[CUR_TONE] && setSecSequencePos(compare.steps) )
					break;
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::SET_TONE:
				eDebugNoSimulate("[SEC] setTone %d", m_sec_sequence.current()->tone);
				sec_fe->setTone(m_sec_sequence.current()++->tone);
				break;
			case eSecCommand::SEND_DISEQC:
				sec_fe->sendDiseqc(m_sec_sequence.current()->diseqc);
				eDebugNoSimulateNoNewLine("[SEC] sendDiseqc: ");
				for (int i=0; i < m_sec_sequence.current()->diseqc.len; ++i)
				    eDebugNoSimulateNoNewLine("%02x", m_sec_sequence.current()->diseqc.data[i]);
			 	if (!memcmp(m_sec_sequence.current()->diseqc.data, "\xE0\x00\x00", 3))
					eDebugNoSimulate("(DiSEqC reset)");
				else if (!memcmp(m_sec_sequence.current()->diseqc.data, "\xE0\x00\x03", 3))
					eDebugNoSimulate("(DiSEqC peripherial power on)");
				else
					eDebugNoSimulate("");
				++m_sec_sequence.current();
				break;
			case eSecCommand::SEND_TONEBURST:
				eDebugNoSimulate("[SEC] sendToneburst: %d", m_sec_sequence.current()->toneburst);
				sec_fe->sendToneburst(m_sec_sequence.current()++->toneburst);
				break;
			case eSecCommand::SET_FRONTEND:
			{
				int enableEvents = (m_sec_sequence.current()++)->val;
				eDebugNoSimulate("[SEC] setFrontend %d", enableEvents);
				setFrontend(enableEvents);
				break;
			}
			case eSecCommand::START_TUNE_TIMEOUT:
			{
				int tuneTimeout = m_sec_sequence.current()->timeout;
				eDebugNoSimulate("[SEC] startTuneTimeout %d", tuneTimeout);
				if (!m_simulate)
					m_timeout->start(tuneTimeout, 1);
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::SET_TIMEOUT:
				m_timeoutCount = m_sec_sequence.current()++->val;
				eDebugNoSimulate("[SEC] set timeout %d", m_timeoutCount);
				break;
			case eSecCommand::IF_TIMEOUT_GOTO:
				if (!m_timeoutCount)
				{
					eDebugNoSimulate("[SEC] rotor timout");
					setSecSequencePos(m_sec_sequence.current()->steps);
				}
				else
					++m_sec_sequence.current();
				break;
			case eSecCommand::MEASURE_IDLE_INPUTPOWER:
			{
				int idx = m_sec_sequence.current()++->val;
				if ( idx == 0 || idx == 1 )
				{
					m_idleInputpower[idx] = sec_fe->readInputpower();
					eDebugNoSimulate("[SEC] idleInputpower[%d] is %d", idx, m_idleInputpower[idx]);
				}
				else
					eDebugNoSimulate("[SEC] idleInputpower measure index(%d) out of bound !!!", idx);
				break;
			}
			case eSecCommand::IF_MEASURE_IDLE_WAS_NOT_OK_GOTO:
			{
				eSecCommand::pair &compare = m_sec_sequence.current()->compare;
				int idx = compare.val;
				if ( !m_simulate && (idx == 0 || idx == 1) )
				{
					int idle = sec_fe->readInputpower();
					int diff = abs(idle-m_idleInputpower[idx]);
					if ( diff > 0)
					{
						eDebugNoSimulate("measure idle(%d) was not okay.. (%d - %d = %d) retry", idx, m_idleInputpower[idx], idle, diff);
						setSecSequencePos(compare.steps);
						break;
					}
				}
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::IF_TUNER_LOCKED_GOTO:
			{
				eSecCommand::rotor &cmd = m_sec_sequence.current()->measure;
				if (m_simulate)
				{
					setSecSequencePos(cmd.steps);
					break;
				}
				int signal = 0;
				int isLocked = readFrontendData(locked);
				m_idleInputpower[0] = m_idleInputpower[1] = 0;
				--m_timeoutCount;
				if (!m_timeoutCount && m_retryCount > 0)
					--m_retryCount;
				if (isLocked && ((abs((signal = readFrontendData(signalQualitydB)) - cmd.lastSignal) < 40) || !cmd.lastSignal))
				{
					if (cmd.lastSignal)
						eDebugNoSimulate("[SEC] locked step %d ok (%d %d)", cmd.okcount, signal, cmd.lastSignal);
					else
					{
						eDebugNoSimulate("[SEC] locked step %d ok", cmd.okcount);
						if (!cmd.okcount)
							cmd.lastSignal = signal;
					}
					++cmd.okcount;
					if (cmd.okcount > 4)
					{
						eDebugNoSimulate("ok > 4 .. goto %d\n", cmd.steps);
						setSecSequencePos(cmd.steps);
						m_state = stateLock;
						m_stateChanged(this);
						feEvent(-1); // flush events
						m_sn->start();
						break;
					}
				}
				else
				{
					if (isLocked)
						eDebugNoSimulate("[SEC] rotor locked step %d failed (oldSignal %d, curSignal %d)", cmd.okcount, signal, cmd.lastSignal);
					else
						eDebugNoSimulate("[SEC] rotor locked step %d failed (not locked)", cmd.okcount);
					cmd.okcount=0;
					cmd.lastSignal=0;
				}
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::MEASURE_RUNNING_INPUTPOWER:
				m_runningInputpower = sec_fe->readInputpower();
				eDebugNoSimulate("[SEC] runningInputpower is %d", m_runningInputpower);
				++m_sec_sequence.current();
				break;
			case eSecCommand::SET_ROTOR_MOVING:
				if (!m_simulate)
					m_sec->setRotorMoving(m_slotid, true);
				++m_sec_sequence.current();
				break;
			case eSecCommand::SET_ROTOR_STOPPED:
				if (!m_simulate)
					m_sec->setRotorMoving(m_slotid, false);
				++m_sec_sequence.current();
				break;
			case eSecCommand::IF_INPUTPOWER_DELTA_GOTO:
			{
				eSecCommand::rotor &cmd = m_sec_sequence.current()->measure;
				if (m_simulate)
				{
					setSecSequencePos(cmd.steps);
					break;
				}
				int idleInputpower = m_idleInputpower[ (sec_fe_data[CUR_VOLTAGE]&1) ? 0 : 1];
				const char *txt = cmd.direction ? "running" : "stopped";
				--m_timeoutCount;
				if (!m_timeoutCount && m_retryCount > 0)
					--m_retryCount;
				eDebugNoSimulate("[SEC] waiting for rotor %s %d, idle %d, delta %d",
					txt,
					m_runningInputpower,
					idleInputpower,
					cmd.deltaA);
				if ( (cmd.direction && abs(m_runningInputpower - idleInputpower) >= cmd.deltaA)
					|| (!cmd.direction && abs(m_runningInputpower - idleInputpower) <= cmd.deltaA) )
				{
					++cmd.okcount;
					eDebugNoSimulate("[SEC] rotor %s step %d ok", txt, cmd.okcount);
					if ( cmd.okcount > 6 )
					{
						eDebugNoSimulate("[SEC] rotor is %s", txt);
						if (setSecSequencePos(cmd.steps))
							break;
					}
				}
				else
				{
					eDebugNoSimulate("[SEC] rotor not %s... reset counter.. increase timeout", txt);
					cmd.okcount=0;
				}
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::IF_ROTORPOS_VALID_GOTO:
				if (sec_fe_data[ROTOR_CMD] != -1 && sec_fe_data[ROTOR_POS] != -1)
					setSecSequencePos(m_sec_sequence.current()->steps);
				else
					++m_sec_sequence.current();
				break;
			case eSecCommand::INVALIDATE_CURRENT_SWITCHPARMS:
				eDebugNoSimulate("[SEC] invalidate current switch params");
				sec_fe_data[CSW] = -1;
				sec_fe_data[UCSW] = -1;
				sec_fe_data[TONEBURST] = -1;
				++m_sec_sequence.current();
				break;
			case eSecCommand::UPDATE_CURRENT_SWITCHPARMS:
				sec_fe_data[CSW] = sec_fe_data[NEW_CSW];
				sec_fe_data[UCSW] = sec_fe_data[NEW_UCSW];
				sec_fe_data[TONEBURST] = sec_fe_data[NEW_TONEBURST];
				eDebugNoSimulate("[SEC] update current switch params");
				++m_sec_sequence.current();
				break;
			case eSecCommand::INVALIDATE_CURRENT_ROTORPARMS:
				eDebugNoSimulate("[SEC] invalidate current rotorparams");
				sec_fe_data[ROTOR_CMD] = -1;
				sec_fe_data[ROTOR_POS] = -1;
				++m_sec_sequence.current();
				break;
			case eSecCommand::UPDATE_CURRENT_ROTORPARAMS:
				sec_fe_data[ROTOR_CMD] = sec_fe_data[NEW_ROTOR_CMD];
				sec_fe_data[ROTOR_POS] = sec_fe_data[NEW_ROTOR_POS];
				eDebugNoSimulate("[SEC] update current rotorparams %d %04lx %ld", m_timeoutCount, sec_fe_data[ROTOR_CMD], sec_fe_data[ROTOR_POS]);
				++m_sec_sequence.current();
				break;
			case eSecCommand::SET_ROTOR_DISEQC_RETRYS:
				m_retryCount = m_sec_sequence.current()++->val;
				eDebugNoSimulate("[SEC] set rotor retries %d", m_retryCount);
				break;
			case eSecCommand::IF_NO_MORE_ROTOR_DISEQC_RETRYS_GOTO:
				if (!m_retryCount)
				{
					eDebugNoSimulate("[SEC] no more rotor retrys");
					setSecSequencePos(m_sec_sequence.current()->steps);
				}
				else
					++m_sec_sequence.current();
				break;
			case eSecCommand::SET_POWER_LIMITING_MODE:
			{
				if (!m_simulate)
				{
					char proc_name[64];
					sprintf(proc_name, "/proc/stb/frontend/%d/static_current_limiting", sec_fe->m_dvbid);
					FILE *f=fopen(proc_name, "w");
					if (f) // new interface exist?
					{
						bool slimiting = m_sec_sequence.current()->mode == eSecCommand::modeStatic;
						if (fprintf(f, "%s", slimiting ? "on" : "off") <= 0)
							eDebugNoSimulate("write %s failed!! (%m)", proc_name);
						else
							eDebugNoSimulate("[SEC] set %s current limiting", slimiting ? "static" : "dynamic");
						fclose(f);
					}
					else if (sec_fe->m_need_rotor_workaround)
					{
						char dev[16];
						int slotid = sec_fe->m_slotid;
						// FIXMEEEEEE hardcoded i2c devices for dm7025 and dm8000
						if (slotid < 2)
							sprintf(dev, "/dev/i2c-%d", slotid);
						else if (slotid == 2)
							sprintf(dev, "/dev/i2c-2"); // first nim socket on DM8000 use /dev/i2c-2
						else if (slotid == 3)
							sprintf(dev, "/dev/i2c-4"); // second nim socket on DM8000 use /dev/i2c-4
						int fd = ::open(dev, O_RDWR);
						if (fd >= 0)
						{
							unsigned char data[2];
							::ioctl(fd, I2C_SLAVE_FORCE, 0x10 >> 1);
							if(::read(fd, data, 1) != 1)
								eDebugNoSimulate("[SEC] error read lnbp (%m)");
							if ( m_sec_sequence.current()->mode == eSecCommand::modeStatic )
							{
								data[0] |= 0x80;  // enable static current limiting
								eDebugNoSimulate("[SEC] set static current limiting");
							}
							else
							{
								data[0] &= ~0x80;  // enable dynamic current limiting
								eDebugNoSimulate("[SEC] set dynamic current limiting");
							}
							if(::write(fd, data, 1) != 1)
								eDebugNoSimulate("[SEC] error write lnbp (%m)");
							::close(fd);
						}
					}
				}
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::DELAYED_CLOSE_FRONTEND:
			{
				eDebugNoSimulate("[SEC] delayed close frontend");
				closeFrontend(false, true);
				++m_sec_sequence.current();
				break;
			}
			default:
				eDebugNoSimulate("[SEC] unhandled sec command %d",
					++m_sec_sequence.current()->cmd);
				++m_sec_sequence.current();
		}
		if (!m_simulate)
			m_tuneTimer->start(delay,true);
	}
	if (regFE)
		regFE->dec_use();
	if (m_simulate && m_sec_sequence.current() != m_sec_sequence.end())
		tuneLoop();
	return delay;
}

void eDVBFrontend::setFrontend(bool recvEvents)
{
	if (!m_simulate)
	{
		eDebug("setting frontend %d", m_dvbid);
		if (recvEvents)
			m_sn->start();
		feEvent(-1); // flush events
#if HAVE_DVB_API_VERSION >= 5
		if (m_type == iDVBFrontend::feSatellite)
		{
			fe_rolloff_t rolloff = ROLLOFF_35;
			fe_pilot_t pilot = PILOT_OFF;
			fe_modulation_t modulation = QPSK;
			fe_delivery_system_t system = SYS_DVBS;
			switch(oparm.sat.system)
			{
			case eDVBFrontendParametersSatellite::System_DVB_S: system = SYS_DVBS; break;
			case eDVBFrontendParametersSatellite::System_DVB_S2: system = SYS_DVBS2; break;
			};
			switch(oparm.sat.modulation)
			{
			case eDVBFrontendParametersSatellite::Modulation_QPSK: modulation = QPSK; break;
			case eDVBFrontendParametersSatellite::Modulation_8PSK: modulation = PSK_8; break;
			case eDVBFrontendParametersSatellite::Modulation_QAM16: modulation = QAM_16; break;
			};
			switch(oparm.sat.pilot)
			{
			case eDVBFrontendParametersSatellite::Pilot_Off: pilot = PILOT_OFF; break;
			case eDVBFrontendParametersSatellite::Pilot_On: pilot = PILOT_ON; break;
			case eDVBFrontendParametersSatellite::Pilot_Unknown: pilot = PILOT_AUTO; break;
			};
			switch(oparm.sat.rolloff)
			{
			case eDVBFrontendParametersSatellite::RollOff_alpha_0_20: rolloff = ROLLOFF_20; break;
			case eDVBFrontendParametersSatellite::RollOff_alpha_0_25: rolloff = ROLLOFF_25; break;
			case eDVBFrontendParametersSatellite::RollOff_alpha_0_35: rolloff = ROLLOFF_35; break;
			case eDVBFrontendParametersSatellite::RollOff_auto: rolloff = ROLLOFF_AUTO; break;
			};
			struct dtv_property p[10];
			struct dtv_properties cmdseq;
			cmdseq.props = p;
			p[0].cmd = DTV_CLEAR;
			p[1].cmd = DTV_DELIVERY_SYSTEM,	p[1].u.data = system;
			p[2].cmd = DTV_FREQUENCY,	p[2].u.data = parm_frequency;
			p[3].cmd = DTV_MODULATION,	p[3].u.data = modulation;
			p[4].cmd = DTV_SYMBOL_RATE,	p[4].u.data = parm_u_qpsk_symbol_rate;
			p[5].cmd = DTV_INNER_FEC,	p[5].u.data = parm_u_qpsk_fec_inner;
			p[6].cmd = DTV_INVERSION,	p[6].u.data = parm_inversion;
			if (system == SYS_DVBS2)
			{
				p[7].cmd = DTV_ROLLOFF,		p[7].u.data = rolloff;
				p[8].cmd = DTV_PILOT,		p[8].u.data = pilot;
				p[9].cmd = DTV_TUNE;
				cmdseq.num = 10;
			}
			else
			{
				p[7].cmd = DTV_TUNE;
				cmdseq.num = 8;
			}
			if (ioctl(m_fd, FE_SET_PROPERTY, &cmdseq) == -1)
			{
				perror("FE_SET_PROPERTY failed");
				return;
			}
		}
		else
#endif
		{
			if (ioctl(m_fd, FE_SET_FRONTEND, &parm) == -1)
			{
				perror("FE_SET_FRONTEND failed");
				return;
			}
		}
	}
}

RESULT eDVBFrontend::getFrontendType(int &t)
{
	if (m_type == -1)
		return -ENODEV;
	t = m_type;
	return 0;
}

RESULT eDVBFrontend::prepare_sat(const eDVBFrontendParametersSatellite &feparm, unsigned int tunetimeout)
{
	int res;
	if (!m_sec)
	{
		eWarning("no SEC module active!");
		return -ENOENT;
	}
	res = m_sec->prepare(*this, parm, feparm, 1 << m_slotid, tunetimeout);
	if (!res)
	{
#if HAVE_DVB_API_VERSION >= 3
		eDebugNoSimulate("prepare_sat System %d Freq %d Pol %d SR %d INV %d FEC %d orbpos %d system %d modulation %d pilot %d, rolloff %d",
			feparm.system,
			feparm.frequency,
			feparm.polarisation,
			feparm.symbol_rate,
			feparm.inversion,
			feparm.fec,
			feparm.orbital_position,
			feparm.system,
			feparm.modulation,
			feparm.pilot,
			feparm.rolloff);
#else
		eDebugNoSimulate("prepare_sat System %d Freq %d Pol %d SR %d INV %d FEC %d orbpos %d",
			feparm.system,
			feparm.frequency,
			feparm.polarisation,
			feparm.symbol_rate,
			feparm.inversion,
			feparm.fec,
			feparm.orbital_position);
#endif
		parm_u_qpsk_symbol_rate = feparm.symbol_rate;
		switch (feparm.inversion)
		{
			case eDVBFrontendParametersSatellite::Inversion_On:
				parm_inversion = INVERSION_ON;
				break;
			case eDVBFrontendParametersSatellite::Inversion_Off:
				parm_inversion = INVERSION_OFF;
				break;
			default:
			case eDVBFrontendParametersSatellite::Inversion_Unknown:
				parm_inversion = INVERSION_AUTO;
				break;
		}
		if (feparm.system == eDVBFrontendParametersSatellite::System_DVB_S)
		{
			switch (feparm.fec)
			{
				case eDVBFrontendParametersSatellite::FEC_None:
					parm_u_qpsk_fec_inner = FEC_NONE;
					break;
				case eDVBFrontendParametersSatellite::FEC_1_2:
					parm_u_qpsk_fec_inner = FEC_1_2;
					break;
				case eDVBFrontendParametersSatellite::FEC_2_3:
					parm_u_qpsk_fec_inner = FEC_2_3;
					break;
				case eDVBFrontendParametersSatellite::FEC_3_4:
					parm_u_qpsk_fec_inner = FEC_3_4;
					break;
				case eDVBFrontendParametersSatellite::FEC_5_6:
					parm_u_qpsk_fec_inner = FEC_5_6;
					break;
				case eDVBFrontendParametersSatellite::FEC_6_7:
					parm_u_qpsk_fec_inner = FEC_6_7;
					break;
				case eDVBFrontendParametersSatellite::FEC_7_8:
					parm_u_qpsk_fec_inner = FEC_7_8;
					break;
				default:
					eDebugNoSimulate("no valid fec for DVB-S set.. assume auto");
				case eDVBFrontendParametersSatellite::FEC_Auto:
					parm_u_qpsk_fec_inner = FEC_AUTO;
					break;
			}
		}
#if HAVE_DVB_API_VERSION >= 3
		else // DVB_S2
		{
			switch (feparm.fec)
			{
				case eDVBFrontendParametersSatellite::FEC_1_2:
					parm_u_qpsk_fec_inner = FEC_S2_QPSK_1_2;
					break;
				case eDVBFrontendParametersSatellite::FEC_2_3:
					parm_u_qpsk_fec_inner = FEC_S2_QPSK_2_3;
					break;
				case eDVBFrontendParametersSatellite::FEC_3_4:
					parm_u_qpsk_fec_inner = FEC_S2_QPSK_3_4;
					break;
				case eDVBFrontendParametersSatellite::FEC_3_5:
					parm_u_qpsk_fec_inner = FEC_S2_QPSK_3_5;
					break;
				case eDVBFrontendParametersSatellite::FEC_4_5:
					parm_u_qpsk_fec_inner = FEC_S2_QPSK_4_5;
					break;
				case eDVBFrontendParametersSatellite::FEC_5_6:
					parm_u_qpsk_fec_inner = FEC_S2_QPSK_5_6;
					break;
#if HAVE_DVB_API_VERSION >= 5
				case eDVBFrontendParametersSatellite::FEC_6_7:
					parm_u_qpsk_fec_inner = FEC_S2_QPSK_6_7;
					break;
#endif
				case eDVBFrontendParametersSatellite::FEC_7_8:
					parm_u_qpsk_fec_inner = FEC_S2_QPSK_7_8;
					break;
				case eDVBFrontendParametersSatellite::FEC_8_9:
					parm_u_qpsk_fec_inner = FEC_S2_QPSK_8_9;
					break;
				case eDVBFrontendParametersSatellite::FEC_9_10:
					parm_u_qpsk_fec_inner = FEC_S2_QPSK_9_10;
					break;
				default:
					eDebugNoSimulate("no valid fec for DVB-S2 set.. abort !!");
					return -EINVAL;
			}
#if HAVE_DVB_API_VERSION < 5
			parm_inversion = (fe_spectral_inversion_t)((feparm.rolloff << 2) | parm_inversion); // Hack.. we use bit 2..3 of inversion param for rolloff
			parm_inversion = (fe_spectral_inversion_t)((feparm.pilot << 4) | parm_inversion); // Hack.. we use bit 4..5 of inversion param for pilot
			if (feparm.modulation == eDVBFrontendParametersSatellite::Modulation_8PSK) 
			{
				parm_u_qpsk_fec_inner = (fe_code_rate_t)((int)parm_u_qpsk_fec_inner+9);
				// 8PSK fec driver values are decimal 9 bigger
			}
#endif
		}
#endif
		if (parm_frequency < fe_info.frequency_min || parm_frequency > fe_info.frequency_max)
		{
			eDebugNoSimulate("%d mhz out of tuner range.. dont tune", parm_frequency/1000);
			return -EINVAL;
		}
		eDebugNoSimulate("tuning to %d mhz", parm_frequency/1000);
	}
	oparm.sat = feparm;
	return res;
}

RESULT eDVBFrontend::prepare_cable(const eDVBFrontendParametersCable &feparm)
{
#if HAVE_DVB_API_VERSION < 3
	parm_frequency = feparm.frequency;
#else
	parm_frequency = feparm.frequency * 1000;
#endif
	parm_u_qam_symbol_rate = feparm.symbol_rate;
	switch (feparm.modulation)
	{
	case eDVBFrontendParametersCable::Modulation_QAM16:
		parm_u_qam_modulation = QAM_16;
		break;
	case eDVBFrontendParametersCable::Modulation_QAM32:
		parm_u_qam_modulation = QAM_32;
		break;
	case eDVBFrontendParametersCable::Modulation_QAM64:
		parm_u_qam_modulation = QAM_64;
		break;
	case eDVBFrontendParametersCable::Modulation_QAM128:
		parm_u_qam_modulation = QAM_128;
		break;
	case eDVBFrontendParametersCable::Modulation_QAM256:
		parm_u_qam_modulation = QAM_256;
		break;
	default:
	case eDVBFrontendParametersCable::Modulation_Auto:
		parm_u_qam_modulation = QAM_AUTO;
		break;
	}
	switch (feparm.inversion)
	{
	case eDVBFrontendParametersCable::Inversion_On:
		parm_inversion = INVERSION_ON;
		break;
	case eDVBFrontendParametersCable::Inversion_Off:
		parm_inversion = INVERSION_OFF;
		break;
	default:
	case eDVBFrontendParametersCable::Inversion_Unknown:
		parm_inversion = INVERSION_AUTO;
		break;
	}
	switch (feparm.fec_inner)
	{
	case eDVBFrontendParametersCable::FEC_None:
		parm_u_qam_fec_inner = FEC_NONE;
		break;
	case eDVBFrontendParametersCable::FEC_1_2:
		parm_u_qam_fec_inner = FEC_1_2;
		break;
	case eDVBFrontendParametersCable::FEC_2_3:
		parm_u_qam_fec_inner = FEC_2_3;
		break;
	case eDVBFrontendParametersCable::FEC_3_4:
		parm_u_qam_fec_inner = FEC_3_4;
		break;
	case eDVBFrontendParametersCable::FEC_5_6:
		parm_u_qam_fec_inner = FEC_5_6;
		break;
	case eDVBFrontendParametersCable::FEC_6_7:
		parm_u_qam_fec_inner = FEC_6_7;
		break;
	case eDVBFrontendParametersCable::FEC_7_8:
		parm_u_qam_fec_inner = FEC_7_8;
		break;
#if HAVE_DVB_API_VERSION >= 3
	case eDVBFrontendParametersCable::FEC_8_9:
		parm_u_qam_fec_inner = FEC_8_9;
		break;
#endif
	default:
	case eDVBFrontendParametersCable::FEC_Auto:
		parm_u_qam_fec_inner = FEC_AUTO;
		break;
	}
	eDebugNoSimulate("tuning to %d khz, sr %d, fec %d, modulation %d, inversion %d",
		parm_frequency/1000,
		parm_u_qam_symbol_rate,
		parm_u_qam_fec_inner,
		parm_u_qam_modulation,
		parm_inversion);
	oparm.cab = feparm;
	return 0;
}

RESULT eDVBFrontend::prepare_terrestrial(const eDVBFrontendParametersTerrestrial &feparm)
{
	parm_frequency = feparm.frequency;

	switch (feparm.bandwidth)
	{
	case eDVBFrontendParametersTerrestrial::Bandwidth_8MHz:
		parm_u_ofdm_bandwidth = BANDWIDTH_8_MHZ;
		break;
	case eDVBFrontendParametersTerrestrial::Bandwidth_7MHz:
		parm_u_ofdm_bandwidth = BANDWIDTH_7_MHZ;
		break;
	case eDVBFrontendParametersTerrestrial::Bandwidth_6MHz:
		parm_u_ofdm_bandwidth = BANDWIDTH_6_MHZ;
		break;
	default:
	case eDVBFrontendParametersTerrestrial::Bandwidth_Auto:
		parm_u_ofdm_bandwidth = BANDWIDTH_AUTO;
		break;
	}
	switch (feparm.code_rate_LP)
	{
	case eDVBFrontendParametersTerrestrial::FEC_1_2:
		parm_u_ofdm_code_rate_LP = FEC_1_2;
		break;
	case eDVBFrontendParametersTerrestrial::FEC_2_3:
		parm_u_ofdm_code_rate_LP = FEC_2_3;
		break;
	case eDVBFrontendParametersTerrestrial::FEC_3_4:
		parm_u_ofdm_code_rate_LP = FEC_3_4;
		break;
	case eDVBFrontendParametersTerrestrial::FEC_5_6:
		parm_u_ofdm_code_rate_LP = FEC_5_6;
		break;
	case eDVBFrontendParametersTerrestrial::FEC_6_7:
		parm_u_ofdm_code_rate_LP = FEC_6_7;
		break;
	case eDVBFrontendParametersTerrestrial::FEC_7_8:
		parm_u_ofdm_code_rate_LP = FEC_7_8;
		break;
	case eDVBFrontendParametersTerrestrial::FEC_8_9:
		parm_u_ofdm_code_rate_LP = FEC_8_9;
		break;
	default:
	case eDVBFrontendParametersTerrestrial::FEC_Auto:
		parm_u_ofdm_code_rate_LP = FEC_AUTO;
		break;
	}
	switch (feparm.code_rate_HP)
	{
	case eDVBFrontendParametersTerrestrial::FEC_1_2:
		parm_u_ofdm_code_rate_HP = FEC_1_2;
		break;
	case eDVBFrontendParametersTerrestrial::FEC_2_3:
		parm_u_ofdm_code_rate_HP = FEC_2_3;
		break;
	case eDVBFrontendParametersTerrestrial::FEC_3_4:
		parm_u_ofdm_code_rate_HP = FEC_3_4;
		break;
	case eDVBFrontendParametersTerrestrial::FEC_5_6:
		parm_u_ofdm_code_rate_HP = FEC_5_6;
		break;
	case eDVBFrontendParametersTerrestrial::FEC_6_7:
		parm_u_ofdm_code_rate_HP = FEC_6_7;
		break;
	case eDVBFrontendParametersTerrestrial::FEC_7_8:
		parm_u_ofdm_code_rate_HP = FEC_7_8;
		break;
	case eDVBFrontendParametersTerrestrial::FEC_8_9:
		parm_u_ofdm_code_rate_HP = FEC_8_9;
		break;
	default:
	case eDVBFrontendParametersTerrestrial::FEC_Auto:
		parm_u_ofdm_code_rate_HP = FEC_AUTO;
		break;
	}
	switch (feparm.modulation)
	{
	case eDVBFrontendParametersTerrestrial::Modulation_QPSK:
		parm_u_ofdm_constellation = QPSK;
		break;
	case eDVBFrontendParametersTerrestrial::Modulation_QAM16:
		parm_u_ofdm_constellation = QAM_16;
		break;
	case eDVBFrontendParametersTerrestrial::Modulation_QAM64:
		parm_u_ofdm_constellation = QAM_64;
		break;
	default:
	case eDVBFrontendParametersTerrestrial::Modulation_Auto:
		parm_u_ofdm_constellation = QAM_AUTO;
		break;
	}
	switch (feparm.transmission_mode)
	{
	case eDVBFrontendParametersTerrestrial::TransmissionMode_2k:
		parm_u_ofdm_transmission_mode = TRANSMISSION_MODE_2K;
		break;
	case eDVBFrontendParametersTerrestrial::TransmissionMode_8k:
		parm_u_ofdm_transmission_mode = TRANSMISSION_MODE_8K;
		break;
	default:
	case eDVBFrontendParametersTerrestrial::TransmissionMode_Auto:
		parm_u_ofdm_transmission_mode = TRANSMISSION_MODE_AUTO;
		break;
	}
	switch (feparm.guard_interval)
	{
		case eDVBFrontendParametersTerrestrial::GuardInterval_1_32:
			parm_u_ofdm_guard_interval = GUARD_INTERVAL_1_32;
			break;
		case eDVBFrontendParametersTerrestrial::GuardInterval_1_16:
			parm_u_ofdm_guard_interval = GUARD_INTERVAL_1_16;
			break;
		case eDVBFrontendParametersTerrestrial::GuardInterval_1_8:
			parm_u_ofdm_guard_interval = GUARD_INTERVAL_1_8;
			break;
		case eDVBFrontendParametersTerrestrial::GuardInterval_1_4:
			parm_u_ofdm_guard_interval = GUARD_INTERVAL_1_4;
			break;
		default:
		case eDVBFrontendParametersTerrestrial::GuardInterval_Auto:
			parm_u_ofdm_guard_interval = GUARD_INTERVAL_AUTO;
			break;
	}
	switch (feparm.hierarchy)
	{
		case eDVBFrontendParametersTerrestrial::Hierarchy_None:
			parm_u_ofdm_hierarchy_information = HIERARCHY_NONE;
			break;
		case eDVBFrontendParametersTerrestrial::Hierarchy_1:
			parm_u_ofdm_hierarchy_information = HIERARCHY_1;
			break;
		case eDVBFrontendParametersTerrestrial::Hierarchy_2:
			parm_u_ofdm_hierarchy_information = HIERARCHY_2;
			break;
		case eDVBFrontendParametersTerrestrial::Hierarchy_4:
			parm_u_ofdm_hierarchy_information = HIERARCHY_4;
			break;
		default:
		case eDVBFrontendParametersTerrestrial::Hierarchy_Auto:
			parm_u_ofdm_hierarchy_information = HIERARCHY_AUTO;
			break;
	}
	switch (feparm.inversion)
	{
	case eDVBFrontendParametersTerrestrial::Inversion_On:
		parm_inversion = INVERSION_ON;
		break;
	case eDVBFrontendParametersTerrestrial::Inversion_Off:
		parm_inversion = INVERSION_OFF;
		break;
	default:
	case eDVBFrontendParametersTerrestrial::Inversion_Unknown:
		parm_inversion = INVERSION_AUTO;
		break;
	}
	oparm.ter = feparm;
	return 0;
}

RESULT eDVBFrontend::tune(const iDVBFrontendParameters &where)
{
	unsigned int timeout = 5000;
	eDebugNoSimulate("(%d)tune", m_dvbid);

	m_timeout->stop();

	int res=0;

	if (!m_sn && !m_simulate)
	{
		eDebug("no frontend device opened... do not try to tune !!!");
		res = -ENODEV;
		goto tune_error;
	}

	if (m_type == -1)
	{
		res = -ENODEV;
		goto tune_error;
	}

	if (!m_simulate)
		m_sn->stop();

	m_sec_sequence.clear();

	where.calcLockTimeout(timeout);

	switch (m_type)
	{
	case feSatellite:
	{
		eDVBFrontendParametersSatellite feparm;
		if (where.getDVBS(feparm))
		{
			eDebug("no dvbs data!");
			res = -EINVAL;
			goto tune_error;
		}
		if (m_rotor_mode != feparm.no_rotor_command_on_tune && !feparm.no_rotor_command_on_tune)
		{
			eDVBFrontend *sec_fe = this;
			long tmp = m_data[LINKED_PREV_PTR];
			while (tmp != -1)
			{
				eDVBRegisteredFrontend *linked_fe = (eDVBRegisteredFrontend*)tmp;
				sec_fe = linked_fe->m_frontend;
				sec_fe->getData(LINKED_NEXT_PTR, tmp);
			}
			eDebug("(fe%d) reset diseqc after leave rotor mode!", m_dvbid);
			sec_fe->m_data[CSW] = sec_fe->m_data[UCSW] = sec_fe->m_data[TONEBURST] = sec_fe->m_data[ROTOR_CMD] = sec_fe->m_data[ROTOR_POS] = -1; // reset diseqc
		}
		m_rotor_mode = feparm.no_rotor_command_on_tune;
		if (!m_simulate)
			m_sec->setRotorMoving(m_slotid, false);
		res=prepare_sat(feparm, timeout);
		if (res)
			goto tune_error;

		break;
	}
	case feCable:
	{
		eDVBFrontendParametersCable feparm;
		if (where.getDVBC(feparm))
		{
			res = -EINVAL;
			goto tune_error;
		}
		res=prepare_cable(feparm);
		if (res)
			goto tune_error;

		m_sec_sequence.push_back( eSecCommand(eSecCommand::START_TUNE_TIMEOUT, timeout) );
		m_sec_sequence.push_back( eSecCommand(eSecCommand::SET_FRONTEND, 1) );
		break;
	}
	case feTerrestrial:
	{
		eDVBFrontendParametersTerrestrial feparm;
		if (where.getDVBT(feparm))
		{
			eDebug("no -T data");
			res = -EINVAL;
			goto tune_error;
		}
		res=prepare_terrestrial(feparm);
		if (res)
			goto tune_error;

		std::string enable_5V;
		char configStr[255];
		snprintf(configStr, 255, "config.Nims.%d.terrestrial_5V", m_slotid);
		m_sec_sequence.push_back( eSecCommand(eSecCommand::START_TUNE_TIMEOUT, timeout) );
		ePythonConfigQuery::getConfigValue(configStr, enable_5V);
		if (enable_5V == "True")
			m_sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, iDVBFrontend::voltage13) );
		else
			m_sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, iDVBFrontend::voltageOff) );
		m_sec_sequence.push_back( eSecCommand(eSecCommand::SET_FRONTEND, 1) );

		break;
	}
	}

	m_sec_sequence.current() = m_sec_sequence.begin();

	if (!m_simulate)
	{
		m_tuneTimer->start(0,true);
		m_tuning = 1;
		if (m_state != stateTuning)
		{
			m_state = stateTuning;
			m_stateChanged(this);
		}
	}
	else
		tuneLoop();

	return res;

tune_error:
	m_tuneTimer->stop();
	return res;
}

RESULT eDVBFrontend::connectStateChange(const Slot1<void,iDVBFrontend*> &stateChange, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_stateChanged.connect(stateChange));
	return 0;
}

RESULT eDVBFrontend::setVoltage(int voltage)
{
	if (m_type == feCable)
		return -1;
#if HAVE_DVB_API_VERSION < 3
	secVoltage vlt;
#else
	bool increased=false;
	fe_sec_voltage_t vlt;
#endif
	m_data[CUR_VOLTAGE]=voltage;
	switch (voltage)
	{
	case voltageOff:
		m_data[CSW]=m_data[UCSW]=m_data[TONEBURST]=-1; // reset diseqc
		vlt = SEC_VOLTAGE_OFF;
		break;
	case voltage13_5:
#if HAVE_DVB_API_VERSION < 3
		vlt = SEC_VOLTAGE_13_5;
		break;
#else
		increased = true;
#endif
	case voltage13:
		vlt = SEC_VOLTAGE_13;
		break;
	case voltage18_5:
#if HAVE_DVB_API_VERSION < 3
		vlt = SEC_VOLTAGE_18_5;
		break;
#else
		increased = true;
#endif
	case voltage18:
		vlt = SEC_VOLTAGE_18;
		break;
	default:
		return -ENODEV;
	}
	if (m_simulate)
		return 0;
#if HAVE_DVB_API_VERSION < 3
	return ::ioctl(m_secfd, SEC_SET_VOLTAGE, vlt);
#else
	if (m_type == feSatellite && ::ioctl(m_fd, FE_ENABLE_HIGH_LNB_VOLTAGE, increased) < 0)
		perror("FE_ENABLE_HIGH_LNB_VOLTAGE");
	return ::ioctl(m_fd, FE_SET_VOLTAGE, vlt);
#endif
}

RESULT eDVBFrontend::getState(int &state)
{
	state = m_state;
	return 0;
}

RESULT eDVBFrontend::setTone(int t)
{
	if (m_type != feSatellite)
		return -1;
#if HAVE_DVB_API_VERSION < 3
	secToneMode_t tone;
#else
	fe_sec_tone_mode_t tone;
#endif
	m_data[CUR_TONE]=t;
	switch (t)
	{
	case toneOn:
		tone = SEC_TONE_ON;
		break;
	case toneOff:
		tone = SEC_TONE_OFF;
		break;
	default:
		return -ENODEV;
	}
	if (m_simulate)
		return 0;
#if HAVE_DVB_API_VERSION < 3	
	return ::ioctl(m_secfd, SEC_SET_TONE, tone);
#else	
	return ::ioctl(m_fd, FE_SET_TONE, tone);
#endif
}

#if HAVE_DVB_API_VERSION < 3 && !defined(SEC_DISEQC_SEND_MASTER_CMD)
	#define SEC_DISEQC_SEND_MASTER_CMD _IOW('o', 97, struct secCommand *)
#endif

RESULT eDVBFrontend::sendDiseqc(const eDVBDiseqcCommand &diseqc)
{
	if (m_simulate)
		return 0;
#if HAVE_DVB_API_VERSION < 3
	struct secCommand cmd;
	cmd.type = SEC_CMDTYPE_DISEQC_RAW;
	cmd.u.diseqc.cmdtype = diseqc.data[0];
	cmd.u.diseqc.addr = diseqc.data[1];
	cmd.u.diseqc.cmd = diseqc.data[2];
	cmd.u.diseqc.numParams = diseqc.len-3;
	memcpy(cmd.u.diseqc.params, diseqc.data+3, diseqc.len-3);
	if (::ioctl(m_secfd, SEC_DISEQC_SEND_MASTER_CMD, &cmd))
#else
	struct dvb_diseqc_master_cmd cmd;
	memcpy(cmd.msg, diseqc.data, diseqc.len);
	cmd.msg_len = diseqc.len;
	if (::ioctl(m_fd, FE_DISEQC_SEND_MASTER_CMD, &cmd))
#endif
		return -EINVAL;
	return 0;
}

#if HAVE_DVB_API_VERSION < 3 && !defined(SEC_DISEQC_SEND_BURST)
	#define SEC_DISEQC_SEND_BURST _IO('o', 96)
#endif
RESULT eDVBFrontend::sendToneburst(int burst)
{
	if (m_simulate)
		return 0;
#if HAVE_DVB_API_VERSION < 3
	secMiniCmd cmd = SEC_MINI_NONE;
#else
	fe_sec_mini_cmd_t cmd = SEC_MINI_A;
#endif
	if ( burst == eDVBSatelliteDiseqcParameters::A )
		cmd = SEC_MINI_A;
	else if ( burst == eDVBSatelliteDiseqcParameters::B )
		cmd = SEC_MINI_B;
#if HAVE_DVB_API_VERSION < 3
	if (::ioctl(m_secfd, SEC_DISEQC_SEND_BURST, cmd))
		return -EINVAL;
#else
	if (::ioctl(m_fd, FE_DISEQC_SEND_BURST, cmd))
		return -EINVAL;
#endif
	return 0;
}

RESULT eDVBFrontend::setSEC(iDVBSatelliteEquipmentControl *sec)
{
	m_sec = sec;
	return 0;
}

RESULT eDVBFrontend::setSecSequence(eSecCommandList &list)
{
	if (m_data[SATCR] != -1 && m_sec_sequence.current() != m_sec_sequence.end())
		m_sec_sequence.push_back(list);
	else
		m_sec_sequence = list;
	return 0;
}

RESULT eDVBFrontend::getData(int num, long &data)
{
	if ( num < NUM_DATA_ENTRIES )
	{
		data = m_data[num];
		return 0;
	}
	return -EINVAL;
}

RESULT eDVBFrontend::setData(int num, long val)
{
	if ( num < NUM_DATA_ENTRIES )
	{
		m_data[num] = val;
		return 0;
	}
	return -EINVAL;
}

int eDVBFrontend::isCompatibleWith(ePtr<iDVBFrontendParameters> &feparm)
{
	int type;
	if (feparm->getSystem(type) || type != m_type || !m_enabled)
		return 0;
	if (m_type == eDVBFrontend::feSatellite)
	{
		ASSERT(m_sec);
		eDVBFrontendParametersSatellite sat_parm;
		int ret = feparm->getDVBS(sat_parm);
		ASSERT(!ret);
		if (sat_parm.system == eDVBFrontendParametersSatellite::System_DVB_S2 && !m_can_handle_dvbs2)
			return 0;
		ret = m_sec->canTune(sat_parm, this, 1 << m_slotid);
		if (ret > 1 && sat_parm.system == eDVBFrontendParametersSatellite::System_DVB_S && m_can_handle_dvbs2)
			ret -= 1;
		return ret;
	}
	else if (m_type == eDVBFrontend::feCable)
		return 2;  // more prio for cable frontends
	else if (m_type == eDVBFrontend::feTerrestrial)
		return 1;
	return 0;
}

bool eDVBFrontend::setSlotInfo(ePyObject obj)
{
	ePyObject Id, Descr, Enabled, IsDVBS2, frontendId;
	if (!PyTuple_Check(obj) || PyTuple_Size(obj) != 5)
		goto arg_error;
	Id = PyTuple_GET_ITEM(obj, 0);
	Descr = PyTuple_GET_ITEM(obj, 1);
	Enabled = PyTuple_GET_ITEM(obj, 2);
	IsDVBS2 = PyTuple_GET_ITEM(obj, 3);
	frontendId = PyTuple_GET_ITEM(obj, 4);
	m_slotid = PyInt_AsLong(Id);
	if (!PyInt_Check(Id) || !PyString_Check(Descr) || !PyBool_Check(Enabled) || !PyBool_Check(IsDVBS2) || !PyInt_Check(frontendId))
		goto arg_error;
	strcpy(m_description, PyString_AS_STRING(Descr));
	if (PyInt_AsLong(frontendId) == -1 || PyInt_AsLong(frontendId) != m_dvbid) {
//		eDebugNoSimulate("skip slotinfo for slotid %d, descr %s",
//			m_slotid, m_description);
		return false;
	}
	m_enabled = Enabled == Py_True;
	// HACK.. the rotor workaround is neede for all NIMs with LNBP21 voltage regulator...
	m_need_rotor_workaround = !!strstr(m_description, "Alps BSBE1") ||
		!!strstr(m_description, "Alps BSBE2") ||
		!!strstr(m_description, "Alps -S") ||
		!!strstr(m_description, "BCM4501");
	m_can_handle_dvbs2 = IsDVBS2 == Py_True;
	eDebugNoSimulate("setSlotInfo for dvb frontend %d to slotid %d, descr %s, need rotorworkaround %s, enabled %s, DVB-S2 %s",
		m_dvbid, m_slotid, m_description, m_need_rotor_workaround ? "Yes" : "No", m_enabled ? "Yes" : "No", m_can_handle_dvbs2 ? "Yes" : "No" );
	return true;
arg_error:
	PyErr_SetString(PyExc_StandardError,
		"eDVBFrontend::setSlotInfo must get a tuple with first param slotid, second param slot description and third param enabled boolean");
	return false;
}
