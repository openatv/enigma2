#include <linux/version.h>
#include <linux/dvb/version.h>

#include <lib/dvb/dvb.h>
#include <lib/dvb/frontendparms.h>
#include <lib/base/cfile.h>
#include <lib/base/eerror.h>
#include <lib/base/nconfig.h> // access to python config
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <stdio.h>
#include <sstream>

#ifndef I2C_SLAVE_FORCE
#define I2C_SLAVE_FORCE	0x0706
#endif

#define ioctlMeasureStart \
	struct timeval start, end; \
	int duration; \
	gettimeofday(&start, NULL);

#define ioctlMeasureEval(x) \
	do { \
		gettimeofday(&end, NULL); \
		duration = (((end.tv_usec - start.tv_usec)/1000) + 1000 ) % 1000; \
		if (duration>35) \
			eWarning("Slow ioctl '%s', potential driver issue, %dms",x,duration); \
	} while(0)

#define eDebugNoSimulateNoNewLineEnd(x...) \
	do { \
		if (!m_simulate) \
			eDebugNoNewLineEnd(x); \
	} while(0)

#define eDebugNoSimulate(x...) \
	do { \
		if (!m_simulate) \
			eDebug(x); \
	} while(0)

#define eDebugNoSimulateNoNewLineStart(x...) \
	do { \
		if (!m_simulate) \
			eDebugNoNewLineStart(x); \
	} while(0)

#define eDebugNoSimulateNoNewLine(x...) \
	do { \
		if (!m_simulate) \
			eDebugNoNewLine(x); \
	} while(0)

#define eDebugDeliverySystem(x...) \
	do { \
		if (m_DebugOptions & (1ULL << static_cast<int> (enumDebugOptions::DEBUG_DELIVERY_SYSTEM))) \
			eDebug(x); \
	} while(0)

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

void eDVBFrontendParametersSatellite::set(const S2SatelliteDeliverySystemDescriptor &descriptor)
{
	if(descriptor.getScramblingSequenceSelector())
	{
		is_id = descriptor.getInputStreamIdentifier();
		pls_mode = eDVBFrontendParametersSatellite::PLS_Root;
		pls_code = descriptor.getScramblingSequenceIndex();
	}
	else
	{
		is_id = NO_STREAM_ID_FILTER;
		pls_mode = eDVBFrontendParametersSatellite::PLS_Root;
		pls_code = 0;
	}
}

void eDVBFrontendParametersSatellite::set(const SatelliteDeliverySystemDescriptor &descriptor)
{
	frequency    = descriptor.getFrequency() * 10;
	symbol_rate  = descriptor.getSymbolRate() * 100;
	polarisation = descriptor.getPolarization();
	fec = descriptor.getFecInner();
	if (fec != FEC_None && fec > FEC_9_10 )
		fec = FEC_Auto;
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
	if (system == System_DVB_S && modulation != Modulation_QPSK)
	{
		eDebug("satellite_delivery_descriptor invalid modulation type.. force QPSK");
		modulation = Modulation_QPSK;
	}
	rolloff = descriptor.getRollOff();
	is_id = NO_STREAM_ID_FILTER;
	pls_mode = eDVBFrontendParametersSatellite::PLS_Root;
	pls_code = 0;
	if (system == System_DVB_S2)
	{
		eDebug("SAT DVB-S2 freq %d, %s, pos %d, sr %d, fec %d, modulation %d, rolloff %d, is_id %d, pls_mode %d, pls_code %d",
			frequency,
			polarisation ? "hor" : "vert",
			orbital_position,
			symbol_rate, fec,
			modulation,
			rolloff,
			is_id,
			pls_mode,
			pls_code);
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
	switch (descriptor.getFecInner())
	{
		default:
		case 0: fec_inner = FEC_Auto; break;
		case 1: fec_inner = FEC_1_2; break;
		case 2: fec_inner = FEC_2_3; break;
		case 3: fec_inner = FEC_3_4; break;
		case 4: fec_inner = FEC_5_6; break;
		case 5: fec_inner = FEC_7_8; break;
		case 6: fec_inner = FEC_8_9; break;
		case 7: fec_inner = FEC_3_5; break;
		case 8: fec_inner = FEC_4_5; break;
		case 9: fec_inner = FEC_9_10; break;
		case 10: fec_inner = FEC_6_7; break;
	}
	modulation = descriptor.getModulation();
	if (modulation > Modulation_QAM256)
		modulation = Modulation_Auto;
	inversion = Inversion_Unknown;
	system = System_DVB_C_ANNEX_A;
	eDebug("Cable freq %d, mod %d, sr %d, fec %d",
		frequency,
		modulation, symbol_rate, fec_inner);
}

void eDVBFrontendParametersTerrestrial::set(const TerrestrialDeliverySystemDescriptor &descriptor)
{
	frequency = descriptor.getCentreFrequency() * 10;
	switch (descriptor.getBandwidth())
	{
		case 0: bandwidth = 8000000; break;
		case 1: bandwidth = 7000000; break;
		case 2: bandwidth = 6000000; break;
		case 3: bandwidth = 5000000; break;
		default: bandwidth = 0; break;
	}
	code_rate_HP = descriptor.getCodeRateHpStream();
	if (code_rate_HP > FEC_Auto)
		code_rate_HP = FEC_Auto;
	code_rate_LP = descriptor.getCodeRateLpStream();
	if (code_rate_LP > FEC_Auto)
		code_rate_LP = FEC_Auto;
	switch (descriptor.getTransmissionMode())
	{
		case 0: transmission_mode = TransmissionMode_2k; break;
		case 1: transmission_mode = TransmissionMode_8k; break;
		case 2: transmission_mode = TransmissionMode_4k; break;
		default: transmission_mode = TransmissionMode_Auto; break;
	}
	guard_interval = descriptor.getGuardInterval();
	if (guard_interval > GuardInterval_1_4)
		guard_interval = GuardInterval_Auto;
	hierarchy = descriptor.getHierarchyInformation();
	if (hierarchy > Hierarchy_Auto)
		hierarchy = Hierarchy_Auto;
	modulation = descriptor.getConstellation();
	if (modulation > Modulation_Auto)
		modulation = Modulation_Auto;
	inversion = Inversion_Unknown;
	system = System_DVB_T;
	plp_id = 0;
	eDebug("[eDVBFrontendParametersTerrestrial] Terr freq %d, bw %d, cr_hp %d, cr_lp %d, tm_mode %d, guard %d, hierarchy %d, const %d",
		frequency, bandwidth, code_rate_HP, code_rate_LP, transmission_mode,
		guard_interval, hierarchy, modulation);
}

void eDVBFrontendParametersTerrestrial::set(const T2DeliverySystemDescriptor &descriptor)
{
	switch (descriptor.getBandwidth())
	{
		case 0: bandwidth = 8000000; break;
		case 1: bandwidth = 7000000; break;
		case 2: bandwidth = 6000000; break;
		case 3: bandwidth = 5000000; break;
		case 4: bandwidth = 1712000; break;
		case 5: bandwidth = 10000000; break;
		default: bandwidth = 0; break;
	}
	switch (descriptor.getTransmissionMode())
	{
		case 0: transmission_mode = TransmissionMode_2k; break;
		case 1: transmission_mode = TransmissionMode_8k; break;
		case 2: transmission_mode = TransmissionMode_4k; break;
		case 3: transmission_mode = TransmissionMode_1k; break;
		case 4: transmission_mode = TransmissionMode_16k; break;
		case 5: transmission_mode = TransmissionMode_32k; break;
		default: transmission_mode = TransmissionMode_Auto; break;
	}
	switch (descriptor.getGuardInterval())
	{
		case 0: guard_interval = GuardInterval_1_32; break;
		case 1: guard_interval = GuardInterval_1_16; break;
		case 2: guard_interval = GuardInterval_1_8; break;
		case 3: guard_interval = GuardInterval_1_4; break;
		case 4: guard_interval = GuardInterval_1_128; break;
		case 5: guard_interval = GuardInterval_19_128; break;
		case 6: guard_interval = GuardInterval_19_256; break;
		case 7: guard_interval = GuardInterval_Auto; break;
	}
	plp_id = descriptor.getPlpId();
	code_rate_HP = code_rate_LP = FEC_Auto;
	hierarchy = Hierarchy_Auto;
	modulation = Modulation_Auto;
	inversion = Inversion_Unknown;
	system = System_DVB_T2;
	eDebug("[eDVBFrontendParametersTerrestrial] T2 bw %d, tm_mode %d, guard %d, plp_id %d",
		bandwidth, transmission_mode, guard_interval, plp_id);
}

eDVBFrontendParameters::eDVBFrontendParameters()
	:m_type(-1), m_types(0), m_flags(0)
{
}

DEFINE_REF(eDVBFrontendParameters);

RESULT eDVBFrontendParameters::getSystem(int &t) const
{
	t = m_type;
	return (m_type == -1) ? -1 : 0;
}

RESULT eDVBFrontendParameters::getSystems(int &t) const
{
	t = m_types;
	return (m_types == 0) ? -1 : 0;
}

RESULT eDVBFrontendParameters::getDVBS(eDVBFrontendParametersSatellite &p) const
{
	if ((m_type == iDVBFrontend::feSatellite) || (m_types & (1 << iDVBFrontend::feSatellite)))
	{
		p = sat;
		return 0;
	}
	return -1;
}

RESULT eDVBFrontendParameters::getDVBC(eDVBFrontendParametersCable &p) const
{
	if ((m_type == iDVBFrontend::feCable) || (m_types & (1 << iDVBFrontend::feCable)))
	{
		p = cable;
		return 0;
	}
	return -1;
}

RESULT eDVBFrontendParameters::getDVBT(eDVBFrontendParametersTerrestrial &p) const
{
	if ((m_type == iDVBFrontend::feTerrestrial) || (m_types & (1 << iDVBFrontend::feTerrestrial)))
	{
		p = terrestrial;
		return 0;
	}
	return -1;
}

RESULT eDVBFrontendParameters::getATSC(eDVBFrontendParametersATSC &p) const
{
	if ((m_type == iDVBFrontend::feATSC) || (m_types & (1 << iDVBFrontend::feATSC)))
	{
		p = atsc;
		return 0;
	}
	return -1;
}

RESULT eDVBFrontendParameters::setDVBS(const eDVBFrontendParametersSatellite &p, bool no_rotor_command_on_tune)
{
	sat = p;
	sat.no_rotor_command_on_tune = no_rotor_command_on_tune;
	m_type = iDVBFrontend::feSatellite;
	m_types |= 1 << iDVBFrontend::feSatellite;
	return 0;
}

RESULT eDVBFrontendParameters::setDVBC(const eDVBFrontendParametersCable &p)
{
	cable = p;
	m_type = iDVBFrontend::feCable;
	m_types |= 1 << iDVBFrontend::feCable;
	return 0;
}

RESULT eDVBFrontendParameters::setDVBT(const eDVBFrontendParametersTerrestrial &p)
{
	terrestrial = p;
	m_type = iDVBFrontend::feTerrestrial;
	m_types |= 1 << iDVBFrontend::feTerrestrial;
	return 0;
}

RESULT eDVBFrontendParameters::setATSC(const eDVBFrontendParametersATSC &p)
{
	atsc = p;
	m_type = iDVBFrontend::feATSC;
	m_types |= 1 << iDVBFrontend::feATSC;
	return 0;
}

RESULT eDVBFrontendParameters::calculateDifference(const iDVBFrontendParameters *parm, int &diff, bool exact) const
{
	if (!parm)
		return -1;
	int type;
	parm->getSystem(type);
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
			else if (sat.is_id != osat.is_id)
				diff = 1<<27;
			else if (sat.pls_mode != osat.pls_mode)
				diff = 1<<27;
			else if (sat.pls_code != osat.pls_code)
				diff = 1<<27;
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
		{
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
		}
		case iDVBFrontend::feTerrestrial:
		{
			eDVBFrontendParametersTerrestrial oterrestrial;
			if (parm->getDVBT(oterrestrial))
				return -2;

			if (exact && oterrestrial.bandwidth != terrestrial.bandwidth &&
				oterrestrial.bandwidth && terrestrial.bandwidth)
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
			else if (oterrestrial.plp_id != terrestrial.plp_id)
				diff = 1 << 27;
			else if (oterrestrial.system != terrestrial.system)
				diff = 1 << 30;
			else
				diff = abs(terrestrial.frequency - oterrestrial.frequency) / 1000;
			return 0;
		}
		case iDVBFrontend::feATSC:
		{
			eDVBFrontendParametersATSC oatsc;
			if (parm->getATSC(oatsc))
				return -2;

			if (exact && atsc.modulation != oatsc.modulation
				&& atsc.modulation != eDVBFrontendParametersATSC::Modulation_Auto
				&& oatsc.modulation != eDVBFrontendParametersATSC::Modulation_Auto)
				diff = 1 << 29;
			else
			{
				diff = abs(atsc.frequency - oatsc.frequency);
			}
			return 0;
		}
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
		{
			hash = 0xFFFF0000;
			hash |= (cable.frequency/1000)&0xFFFF;
			return 0;
		}
		case iDVBFrontend::feTerrestrial:
		{
			hash = 0xEEEE0000;
			hash |= (terrestrial.frequency/1000000)&0xFFFF;
			return 0;
		}
		case iDVBFrontend::feATSC:
		{
			hash = atsc.system == eDVBFrontendParametersATSC::System_ATSC ? 0xEEEE0000 : 0xFFFF0000;
			hash |= (atsc.frequency/1000000)&0xFFFF;
			return 0;
		}
		default:
		{
			return -1;
		}
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
		{
			timeout = 5000;
			return 0;
		}
		case iDVBFrontend::feTerrestrial:
		{
			timeout = 5000;
			return 0;
		}
		case iDVBFrontend::feATSC:
		{
			timeout = 5000;
			return 0;
		}
		default:
		{
			return -1;
		}
	}
}

DEFINE_REF(eDVBFrontend);

int eDVBFrontend::PriorityOrder=0;
int eDVBFrontend::PreferredFrontendIndex = -1;

eDVBFrontend::eDVBFrontend(const char *devicenodename, int fe, int &ok, bool simulate, eDVBFrontend *simulate_fe)
	:m_simulate(simulate), m_enabled(false), m_fbc(false), m_simulate_fe(simulate_fe), m_type(-1), m_dvbid(fe), m_slotid(fe)
	,m_fd(-1), m_teakover(0), m_waitteakover(0), m_break_teakover(0), m_break_waitteakover(0), m_dvbversion(0), m_rotor_mode(false)
	,m_need_rotor_workaround(false), m_need_delivery_system_workaround(false), m_multitype(false), m_state(stateClosed), m_timeout(0), m_tuneTimer(0)
{
	m_DebugOptions = (1ULL << static_cast<int>(enumDebugOptions::DEBUG_DELIVERY_SYSTEM));
	m_filename = devicenodename;

	m_timeout = eTimer::create(eApp);
	CONNECT(m_timeout->timeout, eDVBFrontend::timeout);

	m_tuneTimer = eTimer::create(eApp);
	CONNECT(m_tuneTimer->timeout, eDVBFrontend::tuneLoop);

	for (int i=0; i<eDVBFrontend::NUM_DATA_ENTRIES; ++i)
		m_data[i] = -1;

	m_delsys.clear();
	m_delsys_whitelist.clear();

	m_idleInputpower[0]=m_idleInputpower[1]=0;

	ok = !openFrontend();
	closeFrontend();
}

void eDVBFrontend::reopenFrontend()
{
	sleep(1);
	m_delsys.clear();
	openFrontend();
}

int eDVBFrontend::initModeList()
{
	int fd;
	char buffer[4*1024];
	int rd;
	char id1[256];
	char* buf_pos;
	char* buf_pos2;
	char system[10];
	int mode;

	fd = open("/proc/bus/nim_sockets", O_RDONLY);
	if (fd < 0)
	{
		eDebug("Cannot open /proc/bus/nim_sockets");
		return -1;
	}
	rd = read(fd, buffer, sizeof(buffer));
	close(fd);
	if (rd < 0)
	{
		eDebug("Cannot read /proc/bus/nim_sockets");
		return -1;
	}
	buf_pos = buffer;

	snprintf(id1, sizeof(id1), "NIM Socket %d", m_slotid);

	buf_pos = strstr(buf_pos, id1);
	buf_pos2 = strstr(buf_pos+sizeof(id1), "NIM Socket");

	while ((buf_pos = strstr(buf_pos, "Mode ")) != NULL)
	{
		int num_fe_tmp;
		if (sscanf(buf_pos, "Mode %d:%s", &mode, system) == 2)
		{
			if(buf_pos2 && buf_pos >= buf_pos2)
				break;
			eDebug("[adenin]content of line:  mode:%d system:<%s>", mode, system);
			for (char *p=system ; *p; p++) *p = toupper(*p);
			if (!strcmp(system, "DVB-C") || !strcmp(system, "DVB-C2"))
			{
				eDebug("[adenin] add mode %d to DVB-C",mode);
#ifdef SYS_DVBC_ANNEX_A
				m_modelist[SYS_DVBC_ANNEX_A] = mode;
				m_modelist[SYS_DVBC_ANNEX_C] = mode;
#else
				m_modelist[SYS_DVBC_ANNEX_AC] = mode;
#endif
				m_modelist[SYS_DVBC_ANNEX_B] = mode;
			}
			else if (!strcmp(system, "DVB-S") || !strcmp(system, "DVB-S2"))
			{
				eDebug("[adenin] add mode %d to DVB-S",mode);
				m_modelist[SYS_DVBS] = mode;
				m_modelist[SYS_DVBS2] = mode;
			}
			else if (!strcmp(system, "DVB-T") || !strcmp(system, "DVB-T2"))
			{
				eDebug("[adenin] add mode %d to DVB-T",mode);
				m_modelist[SYS_DVBT] = mode;
				m_modelist[SYS_DVBT2] = mode;
			}
			else if (!strcmp(system, "ATSC"))
			{
				eDebug("[adenin] add mode %d to ATSC",mode);
				m_modelist[SYS_ATSC] = mode;
			}
			else
				eDebug("error: frontend %d unsupported delivery system %s", m_slotid, system);
		}
		buf_pos += 1;
	}
	return 0;
}

int eDVBFrontend::openFrontend()
{
	if (m_state != stateClosed)
		return -1;  // already opened

	m_state=stateIdle;
	m_tuning=0;

	if(initModeList())
		eDebug("Error: initModelist");

	if (!m_simulate)
	{
		m_need_delivery_system_workaround = eConfigManager::getConfigBoolValue("config.usage.enable_delivery_system_workaround", false);
		FILE *boxtype_file;
		char boxtype_name[20];
		if((boxtype_file = fopen("/proc/stb/info/boxtype", "r")) != NULL)
		{
			fgets(boxtype_name, sizeof(boxtype_name), boxtype_file);
			fclose(boxtype_file);

			if(!strcmp(boxtype_name, "osminiplus\n") || !strcmp(boxtype_name, "osmega") || !strcmp(boxtype_name, "spycat4kmini"))
			{
				m_need_delivery_system_workaround = false;
			}
		}
		eDebug("m_need_delivery_system_workaround = %d", m_need_delivery_system_workaround);

		eDebug("opening frontend %d", m_dvbid);
		if (m_fd < 0)
		{
			m_fd = ::open(m_filename.c_str(), O_RDWR | O_NONBLOCK | O_CLOEXEC);
			if (m_fd < 0)
			{
				eWarning("failed! (%s) %m", m_filename.c_str());
				return -1;
			}
		}
		else
			eWarning("frontend %d already opened", m_dvbid);
		if (m_dvbversion == 0)
		{
			m_dvbversion = DVB_VERSION(3, 0);
#if defined DTV_API_VERSION
			struct dtv_property p;
			memset(&p, 0, sizeof(p));
			struct dtv_properties cmdseq;
			cmdseq.props = &p;
			cmdseq.num = 1;
			p.cmd = DTV_API_VERSION;
			ioctlMeasureStart;
			if (ioctl(m_fd, FE_GET_PROPERTY, &cmdseq) >= 0)
			{
				m_dvbversion = p.u.data;
			}
			else
				eWarning("ioctl FE_GET_PROPERTY/DTV_API_VERSION failed: %m");
			ioctlMeasureEval("FE_GET_PROPERTY(DTV_API_VERSION)");
#endif
		}
		if (m_delsys.empty())
		{
			if (::ioctl(m_fd, FE_GET_INFO, &fe_info) < 0)
			{
				eWarning("ioctl FE_GET_INFO failed: %m");
				::close(m_fd);
				m_fd = -1;
				return -1;
			}
			strncpy(m_description, fe_info.name, sizeof(m_description));
#if defined DTV_ENUM_DELSYS
			struct dtv_property p[1];
			memset(p, 0, sizeof(p));
			p[0].cmd = DTV_ENUM_DELSYS;
			struct dtv_properties cmdseq;
			cmdseq.num = 1;
			cmdseq.props = p;
			ioctlMeasureStart;
			if (::ioctl(m_fd, FE_GET_PROPERTY, &cmdseq) >= 0)
			{
				ioctlMeasureEval("FE_GET_PROPERTY(DTV_ENUM_DELSYS)");
				m_delsys.clear();
				for (; p[0].u.buffer.len > 0; p[0].u.buffer.len--)
				{
					fe_delivery_system_t delsys = (fe_delivery_system_t)p[0].u.buffer.data[p[0].u.buffer.len - 1];
					m_delsys[delsys] = true;
					setDeliverySystem(delsys);
					if (::ioctl(m_fd, FE_GET_INFO, &m_fe_info[delsys]) < 0)
						eWarning("ioctl FE_GET_INFO failed: %m");
				}
			}
			else
				eWarning("ioctl FE_GET_PROPERTY/DTV_ENUM_DELSYS failed: %m");
			ioctlMeasureEval("DTV_ENUM_DELSYS");
#else
			/* no DTV_ENUM_DELSYS support */
			if (1)
#endif
			{
				/* old DVB API, fill delsys map with some defaults */
				switch (fe_info.type)
				{
					case FE_QPSK:
					{
						m_delsys[SYS_DVBS] = true;
						if (::ioctl(m_fd, FE_GET_INFO, &m_fe_info[SYS_DVBS]) < 0)
							eWarning("ioctl FE_GET_INFO failed: %m");
#if DVB_API_VERSION >= 5
						if (m_dvbversion >= DVB_VERSION(5, 0))
						{
							if (fe_info.caps & FE_CAN_2G_MODULATION)
							{
								m_delsys[SYS_DVBS2] = true;
								if (::ioctl(m_fd, FE_GET_INFO, &m_fe_info[SYS_DVBS2]) < 0)
									eWarning("ioctl FE_GET_INFO failed: %m");
							}
						}
#endif
						break;
					}
					case FE_QAM:
					{
						if (::ioctl(m_fd, FE_GET_INFO, &m_fe_info[SYS_DVBC_ANNEX_B]) < 0)
							eWarning("ioctl FE_GET_INFO failed: %m");
						
#if DVB_API_VERSION > 5 || DVB_API_VERSION == 5 && DVB_API_VERSION_MINOR >= 6
						/* no need for a m_dvbversion check, SYS_DVBC_ANNEX_A replaced SYS_DVBC_ANNEX_AC (same value) */
						m_delsys[SYS_DVBC_ANNEX_A] = true;
						if (::ioctl(m_fd, FE_GET_INFO, &m_fe_info[SYS_DVBC_ANNEX_A]) < 0)
							eWarning("ioctl FE_GET_INFO failed: %m");
						if (::ioctl(m_fd, FE_GET_INFO, &m_fe_info[SYS_DVBC_ANNEX_C]) < 0)
							eWarning("ioctl FE_GET_INFO failed: %m");
#else
						m_delsys[SYS_DVBC_ANNEX_AC] = true;
						if (::ioctl(m_fd, FE_GET_INFO, &m_fe_info[SYS_DVBC_ANNEX_AC]) < 0)
							eWarning("ioctl FE_GET_INFO failed: %m");
#endif
						break;
					}
					case FE_OFDM:
					{
						m_delsys[SYS_DVBT] = true;
						if (::ioctl(m_fd, FE_GET_INFO, &m_fe_info[SYS_DVBT]) < 0)
							eWarning("ioctl FE_GET_INFO failed: %m");
#if DVB_API_VERSION > 5 || DVB_API_VERSION == 5 && DVB_API_VERSION_MINOR >= 3
						if (m_dvbversion >= DVB_VERSION(5, 3))
						{
							if (fe_info.caps & FE_CAN_2G_MODULATION)
							{
								m_delsys[SYS_DVBT2] = true;
								if (::ioctl(m_fd, FE_GET_INFO, &m_fe_info[SYS_DVBT2]) < 0)
									eWarning("ioctl FE_GET_INFO failed: %m");
							}
						}
#endif
						break;
					}
					case FE_ATSC:
					{
						m_delsys[SYS_ATSC] = true;
						break;
					}
				}
			}
		}

		if (m_simulate_fe)
		{
			m_simulate_fe->m_delsys = m_delsys;
		}
		m_sn = eSocketNotifier::create(eApp, m_fd, eSocketNotifier::Read, false);
		CONNECT(m_sn->activated, eDVBFrontend::feEvent);
	}
	else
	{
		m_fe_info[SYS_DVBS].frequency_min = m_fe_info[SYS_DVBS2].frequency_min = 900000;
		m_fe_info[SYS_DVBS].frequency_max = m_fe_info[SYS_DVBS2].frequency_max = 2200000;
	}
	m_multitype = (
		m_delsys[SYS_DVBS] && m_delsys[SYS_DVBT])
#if DVB_API_VERSION > 5 || DVB_API_VERSION == 5 && DVB_API_VERSION_MINOR >= 6
		|| (m_delsys[SYS_DVBC_ANNEX_A] && m_delsys[SYS_DVBS])
		|| (m_delsys[SYS_DVBC_ANNEX_A] && m_delsys[SYS_DVBT]);
#else
		|| (m_delsys[SYS_DVBC_ANNEX_AC] && m_delsys[SYS_DVBS])
		|| (m_delsys[SYS_DVBC_ANNEX_AC] && m_delsys[SYS_DVBT]);
#endif
	if(!m_multitype)
	{
		if(m_delsys[SYS_DVBS])
			m_type = feSatellite;
		else if(m_delsys[SYS_DVBT])
			m_type = feTerrestrial;
#if DVB_API_VERSION > 5 || DVB_API_VERSION == 5 && DVB_API_VERSION_MINOR >= 6
		else if(m_delsys[SYS_DVBC_ANNEX_A])
#else
		else if(m_delsys[SYS_DVBC_ANNEX_AC])
#endif
			m_type = feCable;
		else if(m_delsys[SYS_ATSC])
			m_type = feATSC;
	}
	if(m_type == feSatellite)
		setTone(iDVBFrontend::toneOff);
	setVoltage(iDVBFrontend::voltageOff);

	return 0;
}

int eDVBFrontend::closeFrontend(bool force, bool no_delayed)
{
	bool isLinked = false;
	bool isUnicable = (m_type == feSatellite) && (m_data[SATCR] != -1);
	eDebugNoSimulate("try to close frontend %d", m_dvbid);

	eDVBFrontend *sec_fe = this;

	long linked_prev_ptr = -1;
	getData(eDVBFrontend::LINKED_PREV_PTR, linked_prev_ptr);
	while (linked_prev_ptr != -1)
	{
		eDVBRegisteredFrontend *linked_fe = (eDVBRegisteredFrontend*) linked_prev_ptr;
		if (linked_fe->m_inuse)
			isLinked = true;
		sec_fe = linked_fe->m_frontend;
		isUnicable = (m_type == feSatellite) && (sec_fe->m_data[SATCR] != -1);
		linked_fe->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, (long&)linked_prev_ptr);
	}

	if (isUnicable && m_fd >= 0)
	{
		if (!no_delayed)
		{
			m_sec->prepareTurnOffSatCR(*this);
			sec_fe->m_tuneTimer->start(0, true);
			if (sec_fe != this)
				this->m_tuneTimer->start(0, true);
			if(!sec_fe->m_tuneTimer->isActive())
			{
				int timeout = 0;
				int timeout_this = 0;
				eDebug("[turnOffSatCR] no mainloop");
				while(true)
				{
					timeout = sec_fe->tuneLoopInt();
					if (sec_fe != this)
						timeout_this = this->tuneLoopInt();
					else
						timeout_this = -1;
					if ((timeout == -1) && (timeout_this == -1))
						break;
					usleep(timeout*1000); // blockierendes wait.. eTimer gibts ja nicht mehr
				}
			}
			else
			{
				eDebug("[turnOffSatCR] running mainloop top_tuner %d", sec_fe->getDVBID());
				if (sec_fe != this)
					eDebug("[turnOffSatCR] running mainloop this_tuner %d", sec_fe->getDVBID());
			}
			return 0;
		}
		else
			m_data[ROTOR_CMD] = -1;
	}

	long tmp = m_data[LINKED_NEXT_PTR];
	while (tmp != -1)
	{
		eDVBRegisteredFrontend *linked_fe = (eDVBRegisteredFrontend*)tmp;
		if (linked_fe->m_inuse)
		{
			eDebugNoSimulate("dont close frontend %d until the linked frontend %d in slot %d is still in use",
				m_dvbid, linked_fe->m_frontend->getDVBID(), linked_fe->m_frontend->getSlotID());
			m_sn->stop();
			m_state = stateIdle;
			return -1;
		}
		linked_fe->m_frontend->getData(LINKED_NEXT_PTR, tmp);
	}

	if (m_fd >= 0)
	{
		if(m_type == feSatellite)
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
		if(m_type == feSatellite)
			setTone(iDVBFrontend::toneOff);
		setVoltage(iDVBFrontend::voltageOff);
	}

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
#if HAVE_AMLOGIC
			if (w < 0)
				return;
#endif
	while (tmp != -1)
	{
		eDVBRegisteredFrontend *linked_fe = (eDVBRegisteredFrontend*)tmp;
		sec_fe = linked_fe->m_frontend;
		sec_fe->getData(LINKED_NEXT_PTR, tmp);
	}
	while (1)
	{
		dvb_frontend_event event;
		int res;
		int state;
#if HAVE_AMLOGIC
		if((res = ::ioctl(m_fd, FE_READ_STATUS, &event.status)) != 0)
		{
			break;
		}

		else
		{
			if(event.status == 0)
			{
				break;
			}
		}
		usleep(10000);
		if (event.status & FE_HAS_LOCK)
		{
			state = stateLock;
			/* FIXME: gg this because FE_READ_STATUS always returns */
			if(m_state == state)
				break; /* I do not see any other way out */
		}
#else
		res = ::ioctl(m_fd, FE_GET_EVENT, &event);

		if (res && (errno == EAGAIN))
			break;

		if (w < 0)
			continue;

		eDebug("(%d)fe event: status %x, inversion %s, m_tuning %d", m_dvbid, event.status, (event.parameters.inversion == INVERSION_ON) ? "on" : "off", m_tuning);
		if (event.status & FE_HAS_LOCK)
		{
			state = stateLock;
		}
#endif
		else
		{
			if (m_tuning) {
				state = stateTuning;
				if (event.status & FE_TIMEDOUT) {
					eDebug("FE_TIMEDOUT! ..abort");
					m_tuneTimer->stop();
					timeout();
					return;
				}
				++m_tuning;
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

void eDVBFrontend::calculateSignalQuality(int snr, int &signalquality, int &signalqualitydb)
{
	int ret = 0x12345678;
	int sat_max = 1600; // we assume a max of 16db here
	int ter_max = 2900; // we assume a max of 29db here
	int cab_max = 4200; // we assume a max of 42db here
	int atsc_max = 4200; // we assume a max of 42db here

	if (!strcmp(m_description, "AVL2108")) // ET9000
	{
		ret = (int)(snr / 40.5);
		sat_max = 1618;
	}
	else if (!strcmp(m_description, "AVL6211")) // ET10000
	{
		ret = (int)(snr / 37.5);
		sat_max = 1700;
	}
	else if (strstr("Nova-T StickNovaT 500StickDTB03", m_description)) // dib0700
	{
		if ( snr > 300 )
			ret = 0; //error condition
		else
			ret = (int)(snr * 10);
	}
	else if (!strcmp(m_description, "BCM4501 (internal)"))
	{
		eDVBFrontendParametersSatellite parm;
		float SDS_SNRE = snr << 16;
		float snr_in_db;
		oparm.getDVBS(parm);

		if (parm.system == eDVBFrontendParametersSatellite::System_DVB_S) // DVB-S1 / QPSK
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
		else
		{
			float fval1 = SDS_SNRE / 268435456.0,
					fval2, fval3, fval4;

			if (parm.modulation == eDVBFrontendParametersSatellite::Modulation_QPSK)
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
	}
	else if (!strcmp(m_description, "Alps BSBE2"))
	{
		ret = (int)((snr >> 7) * 10);
	}
	else if (!strcmp(m_description, "Philips CU1216Mk3"))
	{
		eDVBFrontendParametersCable parm;
		int mse = (~snr) & 0xFF;
		oparm.getDVBC(parm);
		switch (parm.modulation)
		{
		case eDVBFrontendParametersCable::Modulation_QAM16: ret = fe_udiv(1950000, (32 * mse) + 138) + 1000; break;
		case eDVBFrontendParametersCable::Modulation_QAM32: ret = fe_udiv(2150000, (40 * mse) + 500) + 1350; break;
		case eDVBFrontendParametersCable::Modulation_QAM64: ret = fe_udiv(2100000, (40 * mse) + 500) + 1250; break;
		case eDVBFrontendParametersCable::Modulation_QAM128: ret = fe_udiv(1850000, (38 * mse) + 400) + 1380; break;
		case eDVBFrontendParametersCable::Modulation_QAM256: ret = fe_udiv(1800000, (100 * mse) + 40) + 2030; break;
		default: break;
		}
	}
	else if (!strcmp(m_description, "Philips TU1216"))
	{
		snr = 0xFF - (snr & 0xFF);
		if (snr != 0)
			ret = 10 * (int)(-100 * (log10(snr) - log10(255)));
		else
			ret = 2700;
	}
	else if (strstr(m_description, "BCM4506")
		|| strstr(m_description, "BCM4506 (internal)")
		|| strstr(m_description, "BCM4505")
		)
	{
		ret = (snr * 100) >> 8;
	}
	else if (strstr(m_description, "Si2166B"))
	{
		ret = (snr * 240) >> 8;
	}
	else if (!strcmp(m_description, "Vuplus DVB-S NIM(AVL2108)")) // VU+Ultimo/VU+Uno DVB-S2 NIM
	{
		ret = (int)((((double(snr) / (65535.0 / 100.0)) * 0.1600) + 0.2100) * 100);
	}
	else if (!strcmp(m_description, "Vuplus DVB-S NIM(AVL6222)")
		|| !strcmp(m_description, "Vuplus DVB-S NIM(AVL6211)")
		|| !strcmp(m_description, "BCM7335 DVB-S2 NIM (internal)")
		) // VU+
	{
		ret = (int)((((double(snr) / (65535.0 / 100.0)) * 0.1244) + 2.5079) * 100);
		if (!strcmp(m_description, "Vuplus DVB-S NIM(AVL6222)"))
			sat_max = 1490;
	}
	else if (!strcmp(m_description, "BCM7356 DVB-S2 NIM (internal)")) // VU+ Solo2
	{
		ret = (int)((((double(snr) / (65535.0 / 100.0)) * 0.1800) - 1.0000) * 100);
	}
	else if (!strcmp(m_description, "Vuplus DVB-S NIM(7376 FBC)")) // VU+ Solo4k
	{
		ret = (int)((((double(snr) / (65535.0 / 100.0)) * 0.1850) - 0.3500) * 100);
	}
	else if (!strcmp(m_description, "BCM7346 (internal)")) // MaxDigital XP1000
	{
		ret = (int)((((double(snr) / (65535.0 / 100.0)) * 0.1880) + 0.1959) * 100);
	}
	else if (!strcmp(m_description, "BCM7356 DVB-S2 NIM (internal)")
		|| !strcmp(m_description, "BCM7346 DVB-S2 NIM (internal)")
		|| !strcmp(m_description, "BCM7358 DVB-S2 NIM (internal)")
		|| !strcmp(m_description, "BCM7362 DVB-S2 NIM (internal)")
		|| !strcmp(m_description, "GIGA DVB-S2 NIM (Internal)")
		|| !strcmp(m_description, "GIGA DVB-S2 NIM (SP2246T)")
		) // Gigablue
	{
		ret = (int)((((double(snr) / (65535.0 / 100.0)) * 0.1800) - 1.0000) * 100);
	}
	else if (strstr(m_description, "GIGA DVB-C/T NIM (SP8221L)")
		|| strstr(m_description, "GIGA DVB-C/T NIM (SI4765)")
		|| strstr(m_description, "GIGA DVB-C/T NIM (SI41652)")
		|| strstr(m_description, "GIGA DVB-C/T2 NIM (SI4768)")
		)
	{
		int type = -1;
		oparm.getSystem(type);
		switch (type)
		{
			case feCable:
				ret = (int)(snr / 15);
				cab_max = 4200;
				break;
			case feTerrestrial:
				ret = (int)(snr / 75);
				ter_max = 1700;
				break;
		}
	}
	else if (!strcmp(m_description, "Genpix"))
	{
		ret = (int)((snr << 1) / 5);
	}
	else if (!strcmp(m_description, "CXD1981"))
	{
		int mse = (~snr) & 0xFF;
		int type = -1;
		oparm.getSystem(type);
		switch (type)
		{
		case feCable: 
			eDVBFrontendParametersCable parm;
			oparm.getDVBC(parm);
			switch (parm.modulation)
			{
			case eDVBFrontendParametersCable::Modulation_Auto:
			case eDVBFrontendParametersCable::Modulation_QAM16:
			case eDVBFrontendParametersCable::Modulation_QAM64:
			case eDVBFrontendParametersCable::Modulation_QAM256: ret = (int)(-950 * log(((double)mse) / 760)); break;
			case eDVBFrontendParametersCable::Modulation_QAM32:
			case eDVBFrontendParametersCable::Modulation_QAM128: ret = (int)(-875 * log(((double)mse) / 650)); break;
			}
			break;
		case feTerrestrial: 
			ret = (mse * 25) / 2;
			break;
		default:
			break;
		}
	}
	else if (!strcmp(m_description, "BCM73625 (G3)")) // DM520
	{
		ret = snr * 100 / 256;
	}
	else if (!strcmp(m_description, "Broadcom BCM73XX")
		|| !strcmp(m_description, "FTS-260 (Montage RS6000)")
		|| !strcmp(m_description, "Panasonic MN88472")
		|| !strcmp(m_description, "Panasonic MN88473")
		) // xcore
	{
		ret = snr * 100 / 256;

		if (!strcmp(m_description, "FTS-260 (Montage RS6000)"))
			sat_max = 1490;
	}
	else if (!strcmp(m_description, "Si216x"))
	{
		eDVBFrontendParametersTerrestrial parm;
		oparm.getDVBT(parm);
		switch (parm.system)
		{
			case eDVBFrontendParametersTerrestrial::System_DVB_T:
			case eDVBFrontendParametersTerrestrial::System_DVB_T2: 
			case eDVBFrontendParametersTerrestrial::System_DVB_T_T2: ret = (int)((snr * 10) / 15); break;
			default: break;
		}
	}
	else if (strstr(m_description, "Sundtek DVB-T (III)")) // Sundtek MediaTV Digital Home III...dvb-t/t2 mode
	{
		ret = (int)(snr / 75);
		ter_max = 1700;
	}
	else if (strstr(m_description, "Sundtek DVB-S/S2 (IV)"))
	{
		ret = (int)(snr / 52);
		sat_max = 1690;
	}
	else if(!strcmp(m_description, "TBS-5925") || !strcmp(m_description, "DVBS2BOX"))
	{
		ret = (snr * 2000) / 0xFFFF;
		sat_max = 2000;
	}
	else if (!strcmp(m_description, "Si21662")) // SF4008 S2
	{
		ret = (int)(snr / 46.8);
		sat_max = 1620;
	}
	else if (!strcmp(m_description, "Si21682")) // SF4008 T/T2/C
	{
	    int type = -1;
		oparm.getSystem(type);
		switch (type)
		{
			case feCable:
				ret = (int)(snr / 17);
				cab_max = 3800;
				break;
			case feTerrestrial:
				ret = (int)(snr / 22.3);
				ter_max = 2900;
				break;
		}
	}

	signalqualitydb = ret;
	if (ret == 0x12345678) // no snr db calculation avail.. return untouched snr value..
	{
		signalquality = snr;
	}
	else
	{
		int type = -1;
		oparm.getSystem(type);
		switch (type)
		{
		case feSatellite:
			signalquality = (ret >= sat_max ? 65535 : ret * 65535 / sat_max);
			break;
		case feCable:
			signalquality = (ret >= cab_max ? 65535 : ret * 65535 / cab_max);
			break;
		case feTerrestrial:
			signalquality = (ret >= ter_max ? 65535 : ret * 65535 / ter_max);
			break;
		case feATSC:
			signalquality = (ret >= atsc_max ? 65535 : ret * 65535 / atsc_max);
			break;
		}
	}
}

int eDVBFrontend::readFrontendData(int type)
{
	switch(type)
	{
		case iFrontendInformation_ENUMS::bitErrorRate:
			if (m_state == stateLock)
			{
				uint32_t ber=0;
				if (!m_simulate)
				{
					if (ioctl(m_fd, FE_READ_BER, &ber) < 0 && errno != ERANGE)
						eDebug("FE_READ_BER failed (%m)");
				}
				return ber;
			}
			break;
		case iFrontendInformation_ENUMS::snrValue:
			if (m_state == stateLock)
			{
				uint16_t snr = 0;
				if (!m_simulate)
				{
					ioctlMeasureStart;
					if (ioctl(m_fd, FE_READ_SNR, &snr) < 0 && errno != ERANGE)
						eDebug("FE_READ_SNR failed (%m)");
					ioctlMeasureEval("FE_READ_SNR");
				}
				return snr;
			}
			break;
		case iFrontendInformation_ENUMS::signalQuality:
		case iFrontendInformation_ENUMS::signalQualitydB: /* this moved into the driver on DVB API 5.10 */
			if (m_state == stateLock)
			{
				int signalquality = 0;
				int signalqualitydb = 0;
#if DVB_API_VERSION > 5 || DVB_API_VERSION == 5 && DVB_API_VERSION_MINOR >= 10
				if (m_dvbversion >= DVB_VERSION(5, 10))
				{
					dtv_property prop[1];
					memset(prop, 0, sizeof(prop));
					prop[0].cmd = DTV_STAT_CNR;
					dtv_properties props;
					props.props = prop;
					props.num = 1;

					ioctlMeasureStart;
					if (::ioctl(m_fd, FE_GET_PROPERTY, &props) < 0 && errno != ERANGE)
					{
						eDebug("[eDVBFrontend] DTV_STAT_CNR failed: %m");
					}
					else
					{
						ioctlMeasureEval("FE_GET_PROPERTY(DTV_STAT_CNR)");
						for(unsigned int i=0; i<prop[0].u.st.len; i++)
						{
							if (prop[0].u.st.stat[i].scale == FE_SCALE_DECIBEL &&
								type == iFrontendInformation_ENUMS::signalQualitydB)
							{
								signalqualitydb = prop[0].u.st.stat[i].svalue / 10;
								return signalqualitydb;
							}
							else if (prop[0].u.st.stat[i].scale == FE_SCALE_RELATIVE &&
								type == iFrontendInformation_ENUMS::signalQuality)
							{
								signalquality = prop[0].u.st.stat[i].svalue;
								return signalquality;
							}
						}
					}
				}
#endif
				/* fallback to old DVB API */
				int snr = readFrontendData(iFrontendInformation_ENUMS::snrValue);
				calculateSignalQuality(snr, signalquality, signalqualitydb);

				if (type == iFrontendInformation_ENUMS::signalQuality)
				{
					return signalquality;
				}
				else
				{
					return signalqualitydb;
				}
			}
			break;
		case iFrontendInformation_ENUMS::signalPower:
			if (m_state == stateLock)
			{
				uint16_t strength=0;
				if (!m_simulate)
				{
#if DVB_API_VERSION > 5 || DVB_API_VERSION == 5 && DVB_API_VERSION_MINOR >= 10
					if (m_dvbversion >= DVB_VERSION(5, 10))
					{
						dtv_property prop[1];
						memset(prop, 0, sizeof(prop));
						prop[0].cmd = DTV_STAT_SIGNAL_STRENGTH;
						dtv_properties props;
						props.props = prop;
						props.num = 1;

						ioctlMeasureStart;
						if (::ioctl(m_fd, FE_GET_PROPERTY, &props) < 0 && errno != ERANGE)
						{
							eDebug("[eDVBFrontend] DTV_STAT_SIGNAL_STRENGTH failed: %m");
						}
						else
						{
							ioctlMeasureEval("FE_GET_PROPERTY(DTV_STAT_SIGNAL_STRENGTH)");
							for(unsigned int i=0; i<prop[0].u.st.len; i++)
							{
								if (prop[0].u.st.stat[i].scale == FE_SCALE_RELATIVE)
									strength = prop[0].u.st.stat[i].uvalue;
							}
						}
					}
#endif
					// fallback to old DVB API
					ioctlMeasureStart;
					if (!strength && ioctl(m_fd, FE_READ_SIGNAL_STRENGTH, &strength) < 0 && errno != ERANGE)
						eDebug("FE_READ_SIGNAL_STRENGTH failed (%m)");
					ioctlMeasureEval("FE_READ_SIGNAL_STRENGTH");
				}
				return strength;
			}
			break;
		case iFrontendInformation_ENUMS::lockState:
			return !!(readFrontendData(iFrontendInformation_ENUMS::frontendStatus) & FE_HAS_LOCK);
		case iFrontendInformation_ENUMS::syncState:
			return !!(readFrontendData(iFrontendInformation_ENUMS::frontendStatus) & FE_HAS_SYNC);
		case iFrontendInformation_ENUMS::frontendNumber:
			return m_slotid;
		case iFrontendInformation_ENUMS::frontendStatus:
		{
			fe_status_t status;
			if (!m_simulate)
			{
				ioctlMeasureStart;
				if ( ioctl(m_fd, FE_READ_STATUS, &status) < 0 && errno != ERANGE )
					eDebug("FE_READ_STATUS failed (%m)");
				ioctlMeasureEval("FE_READ_STATUS");
				return (int)status;
			}
			return (FE_HAS_SYNC | FE_HAS_LOCK);
		}
		case iFrontendInformation_ENUMS::frequency:
		{
			struct dtv_property p;
			memset(&p, 0, sizeof(p));
			struct dtv_properties cmdseq;
			oparm.getSystem(type);
			cmdseq.props = &p;
			cmdseq.num = 1;
			p.cmd = DTV_FREQUENCY;
			ioctlMeasureStart;
			if (ioctl(m_fd, FE_GET_PROPERTY, &cmdseq) < 0)
			{
				ioctlMeasureEval("FE_GET_PROPERTY(DTV_FREQUENCY)");
				return 0;
			}
			ioctlMeasureEval("FE_GET_PROPERTY(DTV_FREQUENCY)");
			return p.u.data + m_data[FREQ_OFFSET];
		}
	}
	return 0;
}

void eDVBFrontend::getFrontendStatus(ePtr<iDVBFrontendStatus> &dest)
{
	ePtr<eDVBFrontend> fe = this;
	dest = new eDVBFrontendStatus(fe);
}

void eDVBFrontend::getTransponderData(ePtr<iDVBTransponderData> &dest, bool original)
{
	int type = -1;
	struct dtv_property p[16];
	memset(p, 0, sizeof(p));
	struct dtv_properties cmdseq;
	oparm.getSystem(type);
	cmdseq.props = p;
	cmdseq.num = 0;
	if (m_simulate || m_fd == -1 || original)
	{
		original = true;
	}
	else
	{
		p[cmdseq.num++].cmd = DTV_DELIVERY_SYSTEM;
		p[cmdseq.num++].cmd = DTV_FREQUENCY;
		p[cmdseq.num++].cmd = DTV_INVERSION;
		p[cmdseq.num++].cmd = DTV_MODULATION;
		if (type == feSatellite)
		{
			p[cmdseq.num++].cmd = DTV_SYMBOL_RATE;
			p[cmdseq.num++].cmd = DTV_INNER_FEC;
			p[cmdseq.num++].cmd = DTV_ROLLOFF;
			p[cmdseq.num++].cmd = DTV_PILOT;
			p[cmdseq.num++].cmd = DTV_STREAM_ID;
		}
		else if (type == feCable)
		{
			p[cmdseq.num++].cmd = DTV_SYMBOL_RATE;
			p[cmdseq.num++].cmd = DTV_INNER_FEC;
		}
		else if (type == feTerrestrial)
		{
			p[cmdseq.num++].cmd = DTV_BANDWIDTH_HZ;
			p[cmdseq.num++].cmd = DTV_CODE_RATE_HP;
			p[cmdseq.num++].cmd = DTV_CODE_RATE_LP;
			p[cmdseq.num++].cmd = DTV_TRANSMISSION_MODE;
			p[cmdseq.num++].cmd = DTV_GUARD_INTERVAL;
			p[cmdseq.num++].cmd = DTV_HIERARCHY;
			p[cmdseq.num++].cmd = DTV_STREAM_ID;
		}
		else if (type == feATSC)
		{
		}
		ioctlMeasureStart;
		if (ioctl(m_fd, FE_GET_PROPERTY, &cmdseq) < 0)
		{
			eDebug("FE_GET_PROPERTY failed (%m)");
			original = true;
		}
		ioctlMeasureEval("FE_GET_PROPERTY(&cmdseq)");
	}
	switch (type)
	{
	case feSatellite:
		{
			eDVBFrontendParametersSatellite s;
			oparm.getDVBS(s);
			dest = new eDVBSatelliteTransponderData(cmdseq.props, cmdseq.num, s, m_data[FREQ_OFFSET], m_data[SPECTINV_CNT], original);
			break;
		}
	case feCable:
		{
			eDVBFrontendParametersCable c;
			oparm.getDVBC(c);
			dest = new eDVBCableTransponderData(cmdseq.props, cmdseq.num, c, original);
			break;
		}
	case feTerrestrial:
		{
			eDVBFrontendParametersTerrestrial t;
			oparm.getDVBT(t);
			dest = new eDVBTerrestrialTransponderData(cmdseq.props, cmdseq.num, t, original);
			break;
		}
	case feATSC:
		{
			eDVBFrontendParametersATSC a;
			oparm.getATSC(a);
			dest = new eDVBATSCTransponderData(cmdseq.props, cmdseq.num, a, original);
			break;
		}
	}
}

void eDVBFrontend::getFrontendData(ePtr<iDVBFrontendData> &dest)
{
	ePtr<eDVBFrontend> fe = this;
	dest = new eDVBFrontendData(fe);
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
	sprintf(proc_name, "/proc/stb/frontend/%d/lnb_sense", m_slotid);

	if (CFile::parseInt(&power, proc_name) == 0)
		return power;

	sprintf(proc_name, "/proc/stb/fp/lnb_sense%d", m_slotid);
	if (CFile::parseInt(&power, proc_name) == 0)
		return power;

	// open front processor
	int fp=::open("/dev/dbox/fp0", O_RDWR);
	if (fp < 0)
	{
		eDebug("Failed to open /dev/dbox/fp0");
		return -1;
	}
	static bool old_fp = (::ioctl(fp, FP_IOCTL_GET_ID) < 0);
	if ( ioctl( fp, old_fp ? 9 : 0x100, &power ) < 0 )
	{
		eDebug("FP_IOCTL_GET_LNB_CURRENT failed (%m)");
		power = -1;
	}
	::close(fp);

	return power;
}

bool eDVBFrontend::setSecSequencePos(int steps)
{
//	eDebugNoSimulate("set sequence pos %d", steps);
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
	int regFE_cnt = 0;
	int delay=-1;
	eDVBFrontend *sec_fe = this;
	eDVBRegisteredFrontend *regFE[32];
	long tmp = m_data[LINKED_PREV_PTR];
	while ( tmp != -1 )
	{
		eDVBRegisteredFrontend *prev = (eDVBRegisteredFrontend *)tmp;
		sec_fe = prev->m_frontend;
		tmp = prev->m_frontend->m_data[LINKED_PREV_PTR];
//		eDebug("check tuner %d stats:%d in_use: %d tmp: %d", sec_fe->getDVBID(), sec_fe->m_state, prev->m_inuse, tmp);
		if (sec_fe != this && !prev->m_inuse)
		{
			int state = sec_fe->m_state;
			if (state != eDVBFrontend::stateIdle && state != stateClosed)
			{
				sec_fe->m_sn->stop();
				state = sec_fe->m_state = stateIdle;
			}
			// sec_fe is closed... we must reopen it here..
			if (state == stateClosed)
			{
				eDebug("tuner %d is closed, reopen ",sec_fe->m_dvbid);
				regFE[regFE_cnt++] = prev;
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
				eDebugNoSimulate("[SEC] tuner %d sleep %dms", m_dvbid, delay);
				break;
			case eSecCommand::GOTO:
				if ( !setSecSequencePos(m_sec_sequence.current()->steps) )
					++m_sec_sequence.current();
				break;
			case eSecCommand::SET_VOLTAGE:
			{
				int voltage = m_sec_sequence.current()++->voltage;
				eDebugNoSimulate("[SEC] tuner %d setVoltage %d", m_dvbid, voltage);
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
				eDebugNoSimulate("[SEC] tuner %d setTone %d", m_dvbid, m_sec_sequence.current()->tone);
				sec_fe->setTone(m_sec_sequence.current()++->tone);
				break;
			case eSecCommand::SEND_DISEQC:
				if (!m_simulate)
				{
					struct timeval start, end;
					int duration, duration_est;
					gettimeofday(&start, NULL);
					sec_fe->sendDiseqc(m_sec_sequence.current()->diseqc);
					gettimeofday(&end, NULL);
					eDebugNoSimulateNoNewLineStart("[SEC] tuner %d sendDiseqc: ", m_dvbid);
					for (int i=0; i < m_sec_sequence.current()->diseqc.len; ++i)
					eDebugNoSimulateNoNewLine("%02x", m_sec_sequence.current()->diseqc.data[i]);
					if (!memcmp(m_sec_sequence.current()->diseqc.data, "\xE0\x00\x00", 3))
						eDebugNoSimulateNoNewLineEnd("(DiSEqC reset)");
					else if (!memcmp(m_sec_sequence.current()->diseqc.data, "\xE0\x00\x03", 3))
						eDebugNoSimulateNoNewLineEnd("(DiSEqC peripherial power on)");
					else
						eDebugNoSimulateNoNewLineEnd("");
					duration = (((end.tv_usec - start.tv_usec)/1000) + 1000 ) % 1000;
					duration_est = (m_sec_sequence.current()->diseqc.len * 14) + 10;
					eDebugNoSimulateNoNewLineStart("[SEC] diseqc ioctl duration: %d ms", duration);
					if (duration < duration_est)
						delay = duration_est - duration;
					if (delay > 94) delay = 94;
					if (delay)
						eDebugNoSimulateNoNewLineEnd(" -> extra guard delay %d ms",delay);
					else
						eDebugNoSimulateNoNewLineEnd("");
				}
				++m_sec_sequence.current();
				break;
			case eSecCommand::SEND_TONEBURST:
			{
				if (!m_simulate)
				{
					struct timeval start, end;
					int duration, duration_est;
					eDebugNoSimulate("[SEC] tuner %d sendToneburst: %d", m_dvbid, m_sec_sequence.current()->toneburst);
					gettimeofday(&start, NULL);
					sec_fe->sendToneburst(m_sec_sequence.current()->toneburst);
					gettimeofday(&end, NULL);
					eDebugNoSimulateNoNewLineStart("[SEC] toneburst ioctl duration: %d ms",(end.tv_usec - start.tv_usec)/1000);
					duration = (((end.tv_usec - start.tv_usec)/1000) + 1000 ) % 1000;
					duration_est = 24;
					if (duration < duration_est)
						delay = duration_est - duration;
					if (delay > 24) delay = 24;
					if (delay)
						eDebugNoSimulateNoNewLineEnd(" -> extra quard delay %d ms",delay);
				}
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::SET_FRONTEND:
			{
				int enableEvents = (m_sec_sequence.current()++)->val;
				eDebugNoSimulate("[SEC] tuner %d setFrontend: events %s", m_dvbid, enableEvents ? "enabled":"disabled");
				setFrontend(enableEvents);
				break;
			}
			case eSecCommand::START_TUNE_TIMEOUT:
			{
				int tuneTimeout = m_sec_sequence.current()->timeout;
				eDebugNoSimulate("[SEC] tuner %d startTuneTimeout %d", m_dvbid, tuneTimeout);
				if (!m_simulate)
					m_timeout->start(tuneTimeout, 1);
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::SET_TIMEOUT:
				m_timeoutCount = m_sec_sequence.current()++->val;
				eDebugNoSimulate("[SEC] tuner %d set timeout %d", m_dvbid, m_timeoutCount);
				break;
			case eSecCommand::IF_TIMEOUT_GOTO:
				if (!m_timeoutCount)
				{
					eDebugNoSimulate("[SEC] tuner %d rotor timout", m_dvbid);
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
				int isLocked = readFrontendData(iFrontendInformation_ENUMS::lockState);
				m_idleInputpower[0] = m_idleInputpower[1] = 0;
				--m_timeoutCount;
				if (!m_timeoutCount && m_retryCount > 0)
					--m_retryCount;
				if (isLocked && ((abs((signal = readFrontendData(iFrontendInformation_ENUMS::signalQualitydB)) - cmd.lastSignal) < 40) || !cmd.lastSignal))
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
			case eSecCommand::IF_TUNER_UNLOCKED_GOTO:
			{
				if (!m_simulate)
				{
					if (readFrontendData(iFrontendInformation_ENUMS::lockState))
					{
						eDebugNoSimulate("tuner locked .. wait");
						if (m_timeoutCount)
							m_timeoutCount--;
						++m_sec_sequence.current();
					}
					else
					{
						eDebugNoSimulate("tuner unlocked .. goto %d", m_sec_sequence.current()->steps);
						setSecSequencePos(m_sec_sequence.current()->steps);
					}
				}
				else
					setSecSequencePos(m_sec_sequence.current()->steps);
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
					CFile f(proc_name, "w");
					if (f) // new interface exist?
					{
						bool slimiting = m_sec_sequence.current()->mode == eSecCommand::modeStatic;
						if (fprintf(f, "%s", slimiting ? "on" : "off") <= 0)
							eDebugNoSimulate("write %s failed!! (%m)", proc_name);
						else
							eDebugNoSimulate("[SEC] set %s current limiting", slimiting ? "static" : "dynamic");
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
				eDebugNoSimulate("[SEC] tuner %d delayed close frontend", m_dvbid);
				closeFrontend(false, true);
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::TAKEOVER:
			{
				if (!m_simulate)
				{
					if(!m_data[TAKEOVER_COUNTDOWN])
					{
						eDebugNoSimulate("[SEC-Slave] tuner %d start takeover frontend", m_dvbid);
						m_data[TAKEOVER_MASTER] = m_sec_sequence.current()->val;
						if (m_data[TAKEOVER_MASTER] && (m_data[TAKEOVER_MASTER] != -1))
						{
							((eDVBFrontend *)(m_data[TAKEOVER_MASTER]))->setData(TAKEOVER_SLAVE, (long)this);
						}
						m_data[TAKEOVER_COUNTDOWN] = 100;	//timeout 100 x 10 ms = 1sec
					}
					else
					{
						if(--m_data[TAKEOVER_COUNTDOWN])
							delay = 10;
						else
						{
							eDebugNoSimulate("[SEC-Slave] tuner %d timeout takeover frontend", m_dvbid);
							m_data[TAKEOVER_MASTER] = -1;
							m_data[TAKEOVER_SLAVE] = -1;
						}
					}
					if(m_data[TAKEOVER_MASTER] == -1)
					{
						eDebugNoSimulate("[SEC-Slave] tuner %d end takeover frontend", m_dvbid);
						m_data[TAKEOVER_MASTER] = -1;
						m_data[TAKEOVER_SLAVE] = -1;
						m_data[TAKEOVER_COUNTDOWN] = 0;
						++m_sec_sequence.current();
					}
				}
				else
					++m_sec_sequence.current();
				break;
			}
			case eSecCommand::WAIT_TAKEOVER:
			{
				if (!m_simulate)
				{
					if (m_data[TAKEOVER_SLAVE] && (m_data[TAKEOVER_SLAVE] != -1))	//ACK from slave
					{
						eDebug("[SEC-Master] tuner %d WAIT_TAKEOVER", m_dvbid);
						long t = -1;
						((eDVBFrontend *)(m_data[TAKEOVER_SLAVE]))->getData(TAKEOVER_MASTER, t);
						if (t == (long)this)
						{
							m_waitteakover = 0;
							m_break_waitteakover = 0;
						}
						else
							eDebugNoSimulate("[SEC-Master] tuner %d Takeover fail", m_dvbid);
						++m_sec_sequence.current();
					}
					else
					{
						if(!m_waitteakover)
						{
							m_waitteakover = 100;	//timeout
							eDebugNoSimulate("[SEC-Master] tuner %d start wait takeover frontend", m_dvbid);
						}
						else
						{
							if(--m_waitteakover)
								delay = 10;
							else
							{
								eDebugNoSimulate("[SEC-Master] tuner %d timeout wait takeover frontend", m_dvbid);
								m_break_waitteakover = 1;
							}
						}
						if(m_break_waitteakover)
						{
							eDebugNoSimulate("[SEC-Master] tuner %d end wait takeover frontend", m_dvbid);
							m_waitteakover = 0;
							m_break_waitteakover = 0;
							++m_sec_sequence.current();
						}
					}
				}
				else
					++m_sec_sequence.current();
				break;
			}
			case eSecCommand::RELEASE_TAKEOVER:
			{
				if (!m_simulate)
				{
					eDebug("[SEC-Master] tuner %d RELEASE", m_dvbid);
					if (m_data[TAKEOVER_SLAVE] && (m_data[TAKEOVER_SLAVE] != -1))	//ACK from slave
					{
						eDebugNoSimulate("[SEC-Master] tuner %d release frontend", m_dvbid);
						long t = -1;
						((eDVBFrontend *)(m_data[TAKEOVER_SLAVE]))->getData(TAKEOVER_MASTER, t);
						if (t == (long)this)
							((eDVBFrontend *)(m_data[TAKEOVER_SLAVE]))->setData(TAKEOVER_MASTER, -1);
					}
				}
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::CHANGE_TUNER_TYPE:
			{
				if (!m_simulate)
				{
					int newTunertype = m_sec_sequence.current()->val;
					eDebugNoSimulate("[SEC] tuner %d newTunertype %d", m_dvbid, newTunertype);
					changeType(newTunertype);
				}
				++m_sec_sequence.current();
				break;
			}
			default:
				eDebugNoSimulate("[SEC] tuner %d unhandled sec command %d", m_dvbid, m_sec_sequence.current()->cmd);
				++m_sec_sequence.current();
		}
		if (!m_simulate)
			m_tuneTimer->start(delay,true);
	}
	while(regFE_cnt)
	{
		regFE[--regFE_cnt]->dec_use();
	}
	if (m_simulate && m_sec_sequence.current() != m_sec_sequence.end())
		tuneLoop();
	return delay;
}

void eDVBFrontend::setFrontend(bool recvEvents)
{
	if (!m_simulate)
	{
		int type = -1;
		oparm.getSystem(type);
		eDebug("setting frontend %d events: %s", m_dvbid, recvEvents?"on":"off");
		if (recvEvents)
			m_sn->start();
		feEvent(-1); // flush events
		struct dtv_property p[17];
		memset(p, 0, sizeof(p));
		struct dtv_properties cmdseq;
		cmdseq.props = p;
		cmdseq.num = 0;
		p[cmdseq.num].cmd = DTV_CLEAR, cmdseq.num++;
		if (type == iDVBFrontend::feSatellite)
		{
			eDVBFrontendParametersSatellite parm;
			fe_rolloff_t rolloff = ROLLOFF_35;
			fe_pilot_t pilot = PILOT_OFF;
			fe_modulation_t modulation = QPSK;
			fe_delivery_system_t system = SYS_DVBS;
			oparm.getDVBS(parm);

			//p[cmdseq.num].cmd = DTV_LNA, p[cmdseq.num].u.data = 0, cmdseq.num++;
			p[cmdseq.num].cmd = DTV_INVERSION;
			switch (parm.inversion)
			{
				case eDVBFrontendParametersSatellite::Inversion_Off: p[cmdseq.num].u.data = INVERSION_OFF; break;
				case eDVBFrontendParametersSatellite::Inversion_On: p[cmdseq.num].u.data = INVERSION_ON; break;
				default:
				case eDVBFrontendParametersSatellite::Inversion_Unknown: p[cmdseq.num].u.data = INVERSION_AUTO; break;
			}
			cmdseq.num++;

			switch (parm.system)
			{
				default:
				case eDVBFrontendParametersSatellite::System_DVB_S: system = SYS_DVBS; break;
				case eDVBFrontendParametersSatellite::System_DVB_S2: system = SYS_DVBS2; break;
			}
			switch (parm.modulation)
			{
				case eDVBFrontendParametersSatellite::Modulation_QPSK: modulation = QPSK; break;
				case eDVBFrontendParametersSatellite::Modulation_8PSK: modulation = PSK_8; break;
				case eDVBFrontendParametersSatellite::Modulation_QAM16: modulation = QAM_16; break;
				case eDVBFrontendParametersSatellite::Modulation_16APSK: modulation = APSK_16; break;
				case eDVBFrontendParametersSatellite::Modulation_32APSK: modulation = APSK_32; break;
			}
			switch (parm.pilot)
			{
				case eDVBFrontendParametersSatellite::Pilot_Off: pilot = PILOT_OFF; break;
				case eDVBFrontendParametersSatellite::Pilot_On: pilot = PILOT_ON; break;
				default:
				case eDVBFrontendParametersSatellite::Pilot_Unknown: pilot = PILOT_AUTO; break;
			}
			switch (parm.rolloff)
			{
				case eDVBFrontendParametersSatellite::RollOff_alpha_0_20: rolloff = ROLLOFF_20; break;
				case eDVBFrontendParametersSatellite::RollOff_alpha_0_25: rolloff = ROLLOFF_25; break;
				case eDVBFrontendParametersSatellite::RollOff_alpha_0_35: rolloff = ROLLOFF_35; break;
				default:
				case eDVBFrontendParametersSatellite::RollOff_auto: rolloff = ROLLOFF_AUTO; break;
			}
			p[cmdseq.num].cmd = DTV_FREQUENCY, p[cmdseq.num].u.data = satfrequency, cmdseq.num++;
			p[cmdseq.num].cmd = DTV_DELIVERY_SYSTEM, p[cmdseq.num].u.data = system, cmdseq.num++;
			p[cmdseq.num].cmd = DTV_MODULATION, p[cmdseq.num].u.data = modulation, cmdseq.num++;
			p[cmdseq.num].cmd = DTV_SYMBOL_RATE, p[cmdseq.num].u.data = parm.symbol_rate, cmdseq.num++;

			p[cmdseq.num].cmd = DTV_INNER_FEC;
			switch (parm.fec)
			{
				case eDVBFrontendParametersSatellite::FEC_1_2: p[cmdseq.num].u.data = FEC_1_2; break;
				case eDVBFrontendParametersSatellite::FEC_2_3: p[cmdseq.num].u.data = FEC_2_3; break;
				case eDVBFrontendParametersSatellite::FEC_3_4: p[cmdseq.num].u.data = FEC_3_4; break;
				case eDVBFrontendParametersSatellite::FEC_3_5: p[cmdseq.num].u.data = FEC_3_5; break;
				case eDVBFrontendParametersSatellite::FEC_4_5: p[cmdseq.num].u.data = FEC_4_5; break;
				case eDVBFrontendParametersSatellite::FEC_5_6: p[cmdseq.num].u.data = FEC_5_6; break;
				case eDVBFrontendParametersSatellite::FEC_6_7: p[cmdseq.num].u.data = FEC_6_7; break;
				case eDVBFrontendParametersSatellite::FEC_7_8: p[cmdseq.num].u.data = FEC_7_8; break;
				case eDVBFrontendParametersSatellite::FEC_8_9: p[cmdseq.num].u.data = FEC_8_9; break;
				case eDVBFrontendParametersSatellite::FEC_9_10: p[cmdseq.num].u.data = FEC_9_10; break;
				case eDVBFrontendParametersSatellite::FEC_None: p[cmdseq.num].u.data = FEC_NONE; break;
				default:
				case eDVBFrontendParametersSatellite::FEC_Auto: p[cmdseq.num].u.data = FEC_AUTO; break;
			}
			cmdseq.num++;
			if (system == SYS_DVBS2)
			{
				p[cmdseq.num].cmd = DTV_ROLLOFF, p[cmdseq.num].u.data = rolloff, cmdseq.num++;
				p[cmdseq.num].cmd = DTV_PILOT, p[cmdseq.num].u.data = pilot, cmdseq.num++;
				if (m_dvbversion >= DVB_VERSION(5, 3))
				{
#if defined DTV_STREAM_ID
					p[cmdseq.num].cmd = DTV_STREAM_ID, p[cmdseq.num].u.data = parm.is_id | (parm.pls_code << 8) | (parm.pls_mode << 26), cmdseq.num++;
#endif
				}
			}
		}
		else if (type == iDVBFrontend::feCable)
		{
			eDVBFrontendParametersCable parm;
			oparm.getDVBC(parm);
			//p[cmdseq.num].cmd = DTV_LNA, p[cmdseq.num].u.data = 0, cmdseq.num++;
			p[cmdseq.num].cmd = DTV_FREQUENCY, p[cmdseq.num].u.data = parm.frequency * 1000, cmdseq.num++;

			p[cmdseq.num].cmd = DTV_INVERSION;
			switch (parm.inversion)
			{
				case eDVBFrontendParametersCable::Inversion_Off: p[cmdseq.num].u.data = INVERSION_OFF; break;
				case eDVBFrontendParametersCable::Inversion_On: p[cmdseq.num].u.data = INVERSION_ON; break;
				default:
				case eDVBFrontendParametersCable::Inversion_Unknown: p[cmdseq.num].u.data = INVERSION_AUTO; break;
			}
			cmdseq.num++;

			p[cmdseq.num].cmd = DTV_DELIVERY_SYSTEM;
#if DVB_API_VERSION > 5 || DVB_API_VERSION == 5 && DVB_API_VERSION_MINOR >= 6
			if (m_dvbversion >= DVB_VERSION(5, 6))
			{
				switch (parm.system)
				{
					default:
					case eDVBFrontendParametersCable::System_DVB_C_ANNEX_A: p[cmdseq.num].u.data = SYS_DVBC_ANNEX_A; break;
					case eDVBFrontendParametersCable::System_DVB_C_ANNEX_C: p[cmdseq.num].u.data = SYS_DVBC_ANNEX_C; break;
				}
			}
			else
			{
				p[cmdseq.num].u.data = SYS_DVBC_ANNEX_A; /* old value for SYS_DVBC_ANNEX_AC */
			}
#else
			p[cmdseq.num].u.data = SYS_DVBC_ANNEX_AC;
#endif
			cmdseq.num++;

			p[cmdseq.num].cmd = DTV_SYMBOL_RATE, p[cmdseq.num].u.data = parm.symbol_rate, cmdseq.num++;

			p[cmdseq.num].cmd = DTV_INNER_FEC;
			switch (parm.fec_inner)
			{
				default:
				case eDVBFrontendParametersCable::FEC_Auto: p[cmdseq.num].u.data = FEC_AUTO; break;
				case eDVBFrontendParametersCable::FEC_1_2: p[cmdseq.num].u.data = FEC_1_2; break;
				case eDVBFrontendParametersCable::FEC_2_3: p[cmdseq.num].u.data = FEC_2_3; break;
				case eDVBFrontendParametersCable::FEC_3_4: p[cmdseq.num].u.data = FEC_3_4; break;
				case eDVBFrontendParametersCable::FEC_5_6: p[cmdseq.num].u.data = FEC_5_6; break;
				case eDVBFrontendParametersCable::FEC_7_8: p[cmdseq.num].u.data = FEC_7_8; break;
				case eDVBFrontendParametersCable::FEC_8_9: p[cmdseq.num].u.data = FEC_8_9; break;
				case eDVBFrontendParametersCable::FEC_3_5: p[cmdseq.num].u.data = FEC_3_5; break;
				case eDVBFrontendParametersCable::FEC_4_5: p[cmdseq.num].u.data = FEC_4_5; break;
				case eDVBFrontendParametersCable::FEC_9_10: p[cmdseq.num].u.data = FEC_9_10; break;
				case eDVBFrontendParametersCable::FEC_6_7: p[cmdseq.num].u.data = FEC_6_7; break;
			}
			cmdseq.num++;

			p[cmdseq.num].cmd = DTV_MODULATION;
			switch (parm.modulation)
			{
				default:
				case eDVBFrontendParametersCable::Modulation_Auto: p[cmdseq.num].u.data = QAM_AUTO; break;
				case eDVBFrontendParametersCable::Modulation_QAM16: p[cmdseq.num].u.data = QAM_16; break;
				case eDVBFrontendParametersCable::Modulation_QAM32: p[cmdseq.num].u.data = QAM_32; break;
				case eDVBFrontendParametersCable::Modulation_QAM64: p[cmdseq.num].u.data = QAM_64; break;
				case eDVBFrontendParametersCable::Modulation_QAM128: p[cmdseq.num].u.data = QAM_128; break;
				case eDVBFrontendParametersCable::Modulation_QAM256: p[cmdseq.num].u.data = QAM_256; break;
			}
			cmdseq.num++;
		}
		else if (type == iDVBFrontend::feTerrestrial)
		{
			eDVBFrontendParametersTerrestrial parm;
			fe_delivery_system_t system = SYS_DVBT;
			oparm.getDVBT(parm);
			switch (parm.system)
			{
				default:
				case eDVBFrontendParametersTerrestrial::System_DVB_T: system = SYS_DVBT; break;
				case eDVBFrontendParametersTerrestrial::System_DVB_T2: system = SYS_DVBT2; break;
			}

			char configStr[256];
			snprintf(configStr, sizeof(configStr), "config.Nims.%d.dvbt.terrestrial_5V", m_slotid);
			//if (eConfigManager::getConfigBoolValue(configStr))
			//	p[cmdseq.num].cmd = DTV_LNA, p[cmdseq.num].u.data = 1, cmdseq.num++;
			//else
			//	p[cmdseq.num].cmd = DTV_LNA, p[cmdseq.num].u.data = 0, cmdseq.num++;

			p[cmdseq.num].cmd = DTV_DELIVERY_SYSTEM, p[cmdseq.num].u.data = system, cmdseq.num++;
			p[cmdseq.num].cmd = DTV_FREQUENCY, p[cmdseq.num].u.data = parm.frequency, cmdseq.num++;

			p[cmdseq.num].cmd = DTV_INVERSION;
			switch (parm.inversion)
			{
				case eDVBFrontendParametersTerrestrial::Inversion_Off: p[cmdseq.num].u.data = INVERSION_OFF; break;
				case eDVBFrontendParametersTerrestrial::Inversion_On: p[cmdseq.num].u.data = INVERSION_ON; break;
				default:
				case eDVBFrontendParametersTerrestrial::Inversion_Unknown: p[cmdseq.num].u.data = INVERSION_AUTO; break;
			}
			cmdseq.num++;

			p[cmdseq.num].cmd = DTV_CODE_RATE_LP;
			switch (parm.code_rate_LP)
			{
				case eDVBFrontendParametersTerrestrial::FEC_1_2: p[cmdseq.num].u.data = FEC_1_2; break;
				case eDVBFrontendParametersTerrestrial::FEC_2_3: p[cmdseq.num].u.data = FEC_2_3; break;
				case eDVBFrontendParametersTerrestrial::FEC_3_4: p[cmdseq.num].u.data = FEC_3_4; break;
				case eDVBFrontendParametersTerrestrial::FEC_5_6: p[cmdseq.num].u.data = FEC_5_6; break;
				case eDVBFrontendParametersTerrestrial::FEC_6_7: p[cmdseq.num].u.data = FEC_6_7; break;
				case eDVBFrontendParametersTerrestrial::FEC_7_8: p[cmdseq.num].u.data = FEC_7_8; break;
				case eDVBFrontendParametersTerrestrial::FEC_8_9: p[cmdseq.num].u.data = FEC_8_9; break;
				default:
				case eDVBFrontendParametersTerrestrial::FEC_Auto: p[cmdseq.num].u.data = FEC_AUTO; break;
			}
			cmdseq.num++;

			p[cmdseq.num].cmd = DTV_CODE_RATE_HP;
			switch (parm.code_rate_HP)
			{
				case eDVBFrontendParametersTerrestrial::FEC_1_2: p[cmdseq.num].u.data = FEC_1_2; break;
				case eDVBFrontendParametersTerrestrial::FEC_2_3: p[cmdseq.num].u.data = FEC_2_3; break;
				case eDVBFrontendParametersTerrestrial::FEC_3_4: p[cmdseq.num].u.data = FEC_3_4; break;
				case eDVBFrontendParametersTerrestrial::FEC_5_6: p[cmdseq.num].u.data = FEC_5_6; break;
				case eDVBFrontendParametersTerrestrial::FEC_6_7: p[cmdseq.num].u.data = FEC_6_7; break;
				case eDVBFrontendParametersTerrestrial::FEC_7_8: p[cmdseq.num].u.data = FEC_7_8; break;
				case eDVBFrontendParametersTerrestrial::FEC_8_9: p[cmdseq.num].u.data = FEC_8_9; break;
				default:
				case eDVBFrontendParametersTerrestrial::FEC_Auto: p[cmdseq.num].u.data = FEC_AUTO; break;
			}
			cmdseq.num++;

			p[cmdseq.num].cmd = DTV_MODULATION;
			switch (parm.modulation)
			{
				case eDVBFrontendParametersTerrestrial::Modulation_QPSK: p[cmdseq.num].u.data = QPSK; break;
				case eDVBFrontendParametersTerrestrial::Modulation_QAM16: p[cmdseq.num].u.data = QAM_16; break;
				case eDVBFrontendParametersTerrestrial::Modulation_QAM64: p[cmdseq.num].u.data = QAM_64; break;
				case eDVBFrontendParametersTerrestrial::Modulation_QAM256: p[cmdseq.num].u.data = QAM_256; break;
				default:
				case eDVBFrontendParametersTerrestrial::Modulation_Auto: p[cmdseq.num].u.data = QAM_AUTO; break;
			}
			cmdseq.num++;

			p[cmdseq.num].cmd = DTV_TRANSMISSION_MODE;
			switch (parm.transmission_mode)
			{
				case eDVBFrontendParametersTerrestrial::TransmissionMode_2k: p[cmdseq.num].u.data = TRANSMISSION_MODE_2K; break;
				case eDVBFrontendParametersTerrestrial::TransmissionMode_4k: p[cmdseq.num].u.data = TRANSMISSION_MODE_4K; break;
				case eDVBFrontendParametersTerrestrial::TransmissionMode_8k: p[cmdseq.num].u.data = TRANSMISSION_MODE_8K; break;
#if defined TRANSMISSION_MODE_1K
				case eDVBFrontendParametersTerrestrial::TransmissionMode_1k: p[cmdseq.num].u.data = TRANSMISSION_MODE_1K; break;
				case eDVBFrontendParametersTerrestrial::TransmissionMode_16k: p[cmdseq.num].u.data = TRANSMISSION_MODE_16K; break;
				case eDVBFrontendParametersTerrestrial::TransmissionMode_32k: p[cmdseq.num].u.data = TRANSMISSION_MODE_32K; break;
#endif
				default:
				case eDVBFrontendParametersTerrestrial::TransmissionMode_Auto: p[cmdseq.num].u.data = TRANSMISSION_MODE_AUTO; break;
			}
			cmdseq.num++;

			p[cmdseq.num].cmd = DTV_GUARD_INTERVAL;
			switch (parm.guard_interval)
			{
				case eDVBFrontendParametersTerrestrial::GuardInterval_1_32: p[cmdseq.num].u.data = GUARD_INTERVAL_1_32; break;
				case eDVBFrontendParametersTerrestrial::GuardInterval_1_16: p[cmdseq.num].u.data = GUARD_INTERVAL_1_16; break;
				case eDVBFrontendParametersTerrestrial::GuardInterval_1_8: p[cmdseq.num].u.data = GUARD_INTERVAL_1_8; break;
				case eDVBFrontendParametersTerrestrial::GuardInterval_1_4: p[cmdseq.num].u.data = GUARD_INTERVAL_1_4; break;
#if defined GUARD_INTERVAL_1_128
				case eDVBFrontendParametersTerrestrial::GuardInterval_1_128: p[cmdseq.num].u.data = GUARD_INTERVAL_1_128; break;
				case eDVBFrontendParametersTerrestrial::GuardInterval_19_128: p[cmdseq.num].u.data = GUARD_INTERVAL_19_128; break;
				case eDVBFrontendParametersTerrestrial::GuardInterval_19_256: p[cmdseq.num].u.data = GUARD_INTERVAL_19_256; break;
#endif
				default:
				case eDVBFrontendParametersTerrestrial::GuardInterval_Auto: p[cmdseq.num].u.data = GUARD_INTERVAL_AUTO; break;
			}
			cmdseq.num++;

			p[cmdseq.num].cmd = DTV_HIERARCHY;
			switch (parm.hierarchy)
			{
				case eDVBFrontendParametersTerrestrial::Hierarchy_None: p[cmdseq.num].u.data = HIERARCHY_NONE; break;
				case eDVBFrontendParametersTerrestrial::Hierarchy_1: p[cmdseq.num].u.data = HIERARCHY_1; break;
				case eDVBFrontendParametersTerrestrial::Hierarchy_2: p[cmdseq.num].u.data = HIERARCHY_2; break;
				case eDVBFrontendParametersTerrestrial::Hierarchy_4: p[cmdseq.num].u.data = HIERARCHY_4; break;
				default:
				case eDVBFrontendParametersTerrestrial::Hierarchy_Auto: p[cmdseq.num].u.data = HIERARCHY_AUTO; break;
			}
			cmdseq.num++;

			p[cmdseq.num].cmd = DTV_BANDWIDTH_HZ, p[cmdseq.num].u.data = parm.bandwidth, cmdseq.num++;
			if (system == SYS_DVBT2)
			{
				if (m_dvbversion >= DVB_VERSION(5, 3))
				{
#if defined DTV_STREAM_ID
					p[cmdseq.num].cmd = DTV_STREAM_ID, p[cmdseq.num].u.data = parm.plp_id, cmdseq.num++;
#elif defined DTV_DVBT2_PLP_ID
					p[cmdseq.num].cmd = DTV_DVBT2_PLP_ID, p[cmdseq.num].u.data = parm.plp_id, cmdseq.num++;
#endif
				}
			}
		}
		else if (type == iDVBFrontend::feATSC)
		{
			eDVBFrontendParametersATSC parm;
			oparm.getATSC(parm);
			//p[cmdseq.num].cmd = DTV_LNA, p[cmdseq.num].u.data = 0, cmdseq.num++;
			p[cmdseq.num].cmd = DTV_DELIVERY_SYSTEM;
			switch (parm.system)
			{
				default:
				case eDVBFrontendParametersATSC::System_ATSC: p[cmdseq.num].u.data = SYS_ATSC; break;
				case eDVBFrontendParametersATSC::System_DVB_C_ANNEX_B: p[cmdseq.num].u.data = SYS_DVBC_ANNEX_B; break;
			}
			cmdseq.num++;

			p[cmdseq.num].cmd = DTV_FREQUENCY, p[cmdseq.num].u.data = parm.frequency, cmdseq.num++;

			p[cmdseq.num].cmd = DTV_INVERSION;
			switch (parm.inversion)
			{
				case eDVBFrontendParametersATSC::Inversion_Off: p[cmdseq.num].u.data = INVERSION_OFF; break;
				case eDVBFrontendParametersATSC::Inversion_On: p[cmdseq.num].u.data = INVERSION_ON; break;
				default:
				case eDVBFrontendParametersATSC::Inversion_Unknown: p[cmdseq.num].u.data = INVERSION_AUTO; break;
			}
			cmdseq.num++;

			p[cmdseq.num].cmd = DTV_MODULATION;
			switch (parm.modulation)
			{
				default:
				case eDVBFrontendParametersATSC::Modulation_Auto: p[cmdseq.num].u.data = QAM_AUTO; break;
				case eDVBFrontendParametersATSC::Modulation_QAM16: p[cmdseq.num].u.data = QAM_16; break;
				case eDVBFrontendParametersATSC::Modulation_QAM32: p[cmdseq.num].u.data = QAM_32; break;
				case eDVBFrontendParametersATSC::Modulation_QAM64: p[cmdseq.num].u.data = QAM_64; break;
				case eDVBFrontendParametersATSC::Modulation_QAM128: p[cmdseq.num].u.data = QAM_128; break;
				case eDVBFrontendParametersATSC::Modulation_QAM256: p[cmdseq.num].u.data = QAM_256; break;
				case eDVBFrontendParametersATSC::Modulation_VSB_8: p[cmdseq.num].u.data = VSB_8; break;
				case eDVBFrontendParametersATSC::Modulation_VSB_16: p[cmdseq.num].u.data = VSB_16; break;
			}
			cmdseq.num++;
		}
//>>> adenin multistream patch for gb
		if(!strcmp(m_description, "GIGA DVB-S2 NIM (SP2246T)"))
		{
			if (type == iDVBFrontend::feSatellite)
			{
				int plasmid = ::open("/dev/plasmid", O_RDWR);
				if (plasmid > 0)
				{
					typedef struct _ioctl_stream
					{
						uint32_t	tuner;	//[0..1]
						uint32_t	cnt;	//[1..128]
						uint8_t 	*data;
					}_ioctl_stream;
					#define SET_MIS_I2C	_IOWR('p', 0x40, _ioctl_stream *)
					_ioctl_stream d;
					eDVBFrontendParametersSatellite parm;
					oparm.getDVBS(parm);
					uint32_t value = parm.pls_code | (parm.pls_mode & 0x3 << 18);
					uint8_t seq[6];
					if ((parm.is_id != NO_STREAM_ID_FILTER) && (parm.system == eDVBFrontendParametersSatellite::System_DVB_S2))
					{
						seq[0] = (value >> 16) & 0xFF;
						seq[1] = (value >> 8) & 0xFF;
						seq[2] = value & 0xFF;
						seq[3] = parm.is_id & 0xFF;
						seq[4] = 0xFF;
						seq[5] = 0x20;
					}
					else
					{
						seq[0] = 0;
						seq[1] = 0;
						seq[2] = 1;
						seq[3] = 1;
						seq[4] = 0xff;
						seq[5] = 0x00;
					}
					int pnp_offset = 0;
					int fd = open("/proc/stb/info/model", O_RDONLY);
					char tmp[16];
					int rd = fd >= 0 ? read(fd, tmp, sizeof(tmp)) : 0;
					if (fd >= 0)
						close(fd);
					if (rd)
					{
						if (!strncmp(tmp, "gb800seplus\n",rd))
							pnp_offset = 1;
						else if (!strncmp(tmp, "gb800se\n",rd))
							pnp_offset = 1;
						else if (!strncmp(tmp, "gbultraue\n",rd))
							pnp_offset = 1;
						else if (!strncmp(tmp, "gbx3\n",rd))
							pnp_offset = 1;
						else if (!strncmp(tmp, "gbquadplus\n",rd))
							pnp_offset = 2;
						else if (!strncmp(tmp, "gbquad\n",rd))
							pnp_offset = 2;
						else
							eDebug("[determine i2c-channel]Box not listed: %s", tmp);
					}
					int i2c_channel = m_slotid - pnp_offset;
					d.tuner = i2c_channel;
					d.data = seq;
					d.cnt = sizeof(seq);
					if (ioctl(plasmid, SET_MIS_I2C, &d) == -1)
						eDebug("plasmid ioctl failed: %m");
				}
				if (plasmid > 0)
					::close(plasmid);
			}
		}
//<<< adenin multistream patch for gb
		p[cmdseq.num].cmd = DTV_TUNE, cmdseq.num++;
		if (ioctl(m_fd, FE_SET_PROPERTY, &cmdseq) == -1)
		{
			eDebug("FE_SET_PROPERTY failed: %m");
			return;
		}
	}
}

RESULT eDVBFrontend::prepare_sat(const eDVBFrontendParametersSatellite &feparm, unsigned int tunetimeout)
{
	int res;
	if (!m_sec)
	{
		eWarning("no SEC module active!");
		return -ENOENT;
	}
	satfrequency = feparm.frequency;
	res = m_sec->prepare(*this, feparm, satfrequency, 1 << m_slotid, tunetimeout);
	if (!res)
	{
		eDebugNoSimulate("frontend %d prepare_sat System %d Freq %d Pol %d SR %d INV %d FEC %d orbpos %d system %d modulation %d pilot %d, rolloff %d, is_id %d, pls_mode %d, pls_code %d",
			m_dvbid,
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
			feparm.rolloff,
			feparm.is_id,
			feparm.pls_mode,
			feparm.pls_code);
		if ((unsigned int)satfrequency < m_fe_info[SYS_DVBS].frequency_min || (unsigned int)satfrequency > m_fe_info[SYS_DVBS].frequency_max)
		{
			eDebugNoSimulate("%d MHz out of tuner range.. dont tune (min: %d MHz max: %d MHz)", satfrequency / 1000, m_fe_info[SYS_DVBS].frequency_min/1000, m_fe_info[SYS_DVBS].frequency_max/1000);
			return -EINVAL;
		}
		eDebugNoSimulate("tuning to %d MHz", satfrequency / 1000);
	}
	oparm.setDVBS(feparm, feparm.no_rotor_command_on_tune);
	return res;
}

RESULT eDVBFrontend::prepare_cable(const eDVBFrontendParametersCable &feparm)
{
	if (!m_sec)
	{
		eWarning("no SEC module active!");
		return -ENOENT;
	}
	m_data[FREQ_OFFSET] = 0;
	eDebugNoSimulate("frontend %d tuning dvb-c to %d khz, sr %d, fec %d, modulation %d, inversion %d",
		m_dvbid,
		feparm.frequency,
		feparm.symbol_rate,
		feparm.fec_inner,
		feparm.modulation,
		feparm.inversion);
	oparm.setDVBC(feparm);
	return 0;
}

RESULT eDVBFrontend::prepare_terrestrial(const eDVBFrontendParametersTerrestrial &feparm)
{
	if (!m_sec)
	{
		eWarning("no SEC module active!");
		return -ENOENT;
	}
	m_data[FREQ_OFFSET] = 0;
	eDebugNoSimulate("frontend %d tuning dvb-t to %d khz, bandwidth %d, modulation %d, inversion %d",
	m_dvbid,
	feparm.frequency,
	feparm.bandwidth,
//	feparm.code_rate_HP,
//	feparm.code_rate_LP,
	feparm.modulation,
//	feparm.transmission_mode,
//	feparm.guard_interval,
//	feparm.hierarchy,
	feparm.inversion
//	feparm.system,
//	feparm.plp_id,
	);
	oparm.setDVBT(feparm);
	return 0;
}

RESULT eDVBFrontend::prepare_atsc(const eDVBFrontendParametersATSC &feparm)
{
	if (!m_sec)
	{
		eWarning("no SEC module active!");
		return -ENOENT;
	}
	m_data[FREQ_OFFSET] = 0;
	eDebugNoSimulate("frontend %d tuning atsc to %d khz, modulation %d, inversion %d",
	m_dvbid,
	feparm.frequency,
	feparm.modulation,
	feparm.inversion
//	feparm.system;
	);
	oparm.setATSC(feparm);
	return 0;
}

RESULT eDVBFrontend::tune(const iDVBFrontendParameters &where)
{
	unsigned int timeout = 5000;
	int type;
	eDebugNoSimulate("tune tuner %d", m_dvbid);

	m_timeout->stop();

	int res=0;

	if (where.getSystem(type) < 0)
	{
		res = -EINVAL;
		goto tune_error;
	}

	if (!m_sn && !m_simulate)
	{
		eDebug("no frontend device opened... do not try to tune !!!");
		res = -ENODEV;
		goto tune_error;
	}

	if (!m_simulate)
		m_sn->stop();

	m_sec_sequence.clear();

	if((m_type == feSatellite) && (type != feSatellite))
		m_sec_sequence.push_back( eSecCommand(eSecCommand::SET_TONE, iDVBFrontend::toneOff) );

	if((m_type == feSatellite) && (type != feSatellite) && (m_data[SATCR] != -1))
	{
		eDebug("unicable shutdown");
		long satcr, diction, pin;

		// check if voltage is disabled
		eSecCommand::pair compare;
		compare.steps = +6;	//only close frontend
		compare.voltage = iDVBFrontend::voltageOff;

		m_sec_sequence.push_back( eSecCommand(eSecCommand::IF_VOLTAGE_GOTO, compare) );
		m_sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, iDVBFrontend::voltage13) );
		m_sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 100 ));

		m_sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, iDVBFrontend::voltage18_5) );
		m_sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 100 ));

		eDVBDiseqcCommand diseqc;
		memset(diseqc.data, 0, MAX_DISEQC_LENGTH);
		getData(eDVBFrontend::SATCR, satcr);
		getData(eDVBFrontend::DICTION, diction);
		getData(eDVBFrontend::PIN, pin);

		switch (diction)
		{
			case 1:
				if(pin < 1)
				{
					diseqc.len = 4;
					diseqc.data[0] = 0x70;
				}
				else
				{
					diseqc.len = 5;
					diseqc.data[0] = 0x71;
					diseqc.data[4] = pin;
				}
				diseqc.data[1] = satcr << 3;
				diseqc.data[2] = 0x00;
				diseqc.data[3] = 0x00;
				break;
			case 0:
			default:
				if(pin < 1)
				{
					diseqc.len = 5;
					diseqc.data[2] = 0x5A;
				}
				else
				{
					diseqc.len = 6;
					diseqc.data[2] = 0x5C;
					diseqc.data[5] = pin;
				}
				diseqc.data[0] = 0xE0;
				diseqc.data[1] = 0x10;
				diseqc.data[3] = satcr << 5;
				diseqc.data[4] = 0x00;
				break;
		}

		m_sec_sequence.push_back( eSecCommand(eSecCommand::SEND_DISEQC, diseqc) );
		m_sec_sequence.push_back( eSecCommand(eSecCommand::SLEEP, 100 ));

		if(has_prev())
		{
			eDVBFrontend *fe = (eDVBFrontend *)this;
			getTop(this, fe);

			int state;
			fe->getState(state);
			if (state != eDVBFrontend::stateClosed)
			{
				eSecCommandList sec_takeover_sequence;
				sec_takeover_sequence.push_front(eSecCommand(eSecCommand::CHANGE_TUNER_TYPE, m_type));
				sec_takeover_sequence.push_front(eSecCommand(eSecCommand::TAKEOVER, (long)this));
				fe->setSecSequence(sec_takeover_sequence, (eDVBFrontend *)this);
				eDebug("takeover_sec %d",fe->getDVBID());

				m_sec_sequence.push_front( eSecCommand(eSecCommand::WAIT_TAKEOVER) );
				m_sec_sequence.push_back( eSecCommand(eSecCommand::RELEASE_TAKEOVER, (long)this) );
				eDebug("waittakeover_sec %d",getDVBID());
			}
			else
				eDebug("fail: tuner %d is closed",fe->getDVBID());
		}
	}


	where.calcLockTimeout(timeout);

	switch (type)
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
		{
			m_sec->setRotorMoving(m_slotid, false);
			changeType(feSatellite);
		}
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

		m_sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, iDVBFrontend::voltageOff) );
		m_sec_sequence.push_back(eSecCommand(eSecCommand::CHANGE_TUNER_TYPE, type));
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

		m_sec_sequence.push_back(eSecCommand(eSecCommand::CHANGE_TUNER_TYPE, type));
		m_sec_sequence.push_back( eSecCommand(eSecCommand::START_TUNE_TIMEOUT, timeout) );
		char configStr[256];
		snprintf(configStr, sizeof(configStr), "config.Nims.%d.dvbt.terrestrial_5V", m_slotid);
		if (eConfigManager::getConfigBoolValue(configStr))
			m_sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, iDVBFrontend::voltage13) );
		else
			m_sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, iDVBFrontend::voltageOff) );
		m_sec_sequence.push_back( eSecCommand(eSecCommand::SET_FRONTEND, 1) );
		break;
	}
	case feATSC:
	{
		eDVBFrontendParametersATSC feparm;
		if (where.getATSC(feparm))
		{
			res = -EINVAL;
			goto tune_error;
		}
		res=prepare_atsc(feparm);
		if (res)
			goto tune_error;

		m_sec_sequence.push_back( eSecCommand(eSecCommand::SET_VOLTAGE, iDVBFrontend::voltageOff) );
		m_sec_sequence.push_back(eSecCommand(eSecCommand::CHANGE_TUNER_TYPE, type));
		m_sec_sequence.push_back( eSecCommand(eSecCommand::START_TUNE_TIMEOUT, timeout) );
		m_sec_sequence.push_back( eSecCommand(eSecCommand::SET_FRONTEND, 1) );
		break;
	}
	default:
		res = -EINVAL;
		goto tune_error;
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
	bool increased=false;
	fe_sec_voltage_t vlt;
	m_data[CUR_VOLTAGE]=voltage;
	switch (voltage)
	{
		case voltageOff:
			m_data[CSW]=m_data[UCSW]=m_data[TONEBURST]=-1; // reset diseqc
			vlt = SEC_VOLTAGE_OFF;
			char filename[256];
			snprintf(filename, sizeof(filename), "/proc/stb/frontend/%d/active_antenna_power", m_slotid);
			CFile::writeStr(filename, "off");
			break;
		case voltage13_5:
			increased = true;
		case voltage13:
			vlt = SEC_VOLTAGE_13;
			if(m_type == feTerrestrial)
			{
				char filename[256];
				snprintf(filename, sizeof(filename), "/proc/stb/frontend/%d/active_antenna_power", m_slotid);
				CFile::writeStr(filename, "on");
			}
			break;
		case voltage18_5:
			increased = true;
		case voltage18:
			vlt = SEC_VOLTAGE_18;
			break;
		default:
			return -ENODEV;
	}
	if (m_simulate)
		return 0;
	::ioctl(m_fd, FE_ENABLE_HIGH_LNB_VOLTAGE, increased);
	return ::ioctl(m_fd, FE_SET_VOLTAGE, vlt);
}

RESULT eDVBFrontend::getState(int &state)
{
	state = m_state;
	return 0;
}

RESULT eDVBFrontend::setTone(int t)
{
	fe_sec_tone_mode_t tone;
	if (m_type != feSatellite)
	{
		eWarning("dvb-s mode not aktive!");
		return 0;
	}
	if (m_simulate)
		return 0;
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
	return ::ioctl(m_fd, FE_SET_TONE, tone);
}

RESULT eDVBFrontend::sendDiseqc(const eDVBDiseqcCommand &diseqc)
{
	struct dvb_diseqc_master_cmd cmd;
	if (m_type != feSatellite)
	{
		eWarning("dvb-s mode not aktive!");
		return 0;
	}
	if (m_simulate)
		return 0;
	memcpy(cmd.msg, diseqc.data, diseqc.len);
	cmd.msg_len = diseqc.len;
	if (::ioctl(m_fd, FE_DISEQC_SEND_MASTER_CMD, &cmd))
		return -EINVAL;
	return 0;
}

RESULT eDVBFrontend::sendToneburst(int burst)
{
	fe_sec_mini_cmd_t cmd;
	if (m_type != feSatellite)
	{
		eWarning("dvb-s mode not aktive!");
		return 0;
	}
	if (m_simulate)
		return 0;
	if (burst == eDVBSatelliteDiseqcParameters::B)
		cmd = SEC_MINI_B;
	else
		cmd = SEC_MINI_A;

	if (::ioctl(m_fd, FE_DISEQC_SEND_BURST, cmd))
		return -EINVAL;
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

RESULT eDVBFrontend::setSecSequence(eSecCommandList &list, iDVBFrontend *fe)
{
	if (m_data[SATCR] != -1 && m_sec_sequence.current() != m_sec_sequence.end())
		m_sec_sequence.push_back(list);
	else
		m_sec_sequence = list;

	if (fe != this)
	{
		if(!m_tuneTimer->isActive())
			m_tuneTimer->start(0, true);
	}
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

bool eDVBFrontend::isPreferred(int preferredFrontend, int slotid)
{
	if ((preferredFrontend >= 0) && (preferredFrontend & eDVBFrontend::preferredFrontendBinaryMode))
		return (preferredFrontend & 1<<slotid);
	else
		return (preferredFrontend >= 0 && slotid == preferredFrontend);
}

int eDVBFrontend::isCompatibleWith(ePtr<iDVBFrontendParameters> &feparm)
{
	int type;
	int types;
	int score = 0;
	int preferredFrontend = eDVBFrontend::getPreferredFrontend();
	bool preferred = eDVBFrontend::isPreferred(preferredFrontend,m_slotid);
	if ((preferredFrontend >= 0) && (preferredFrontend & eDVBFrontend::preferredFrontendPrioForced) && !preferred)
	{
		return 0;
	}
	if (feparm->getSystem(type) || feparm->getSystems(types) || !m_enabled)
	{
		eDebugDeliverySystem("m_dvbid:%d m_slotid:%d type:%d types:%d m_enabled:%d", m_dvbid, m_slotid, type, types, m_enabled);
		return 0;
	}
	if ((type == eDVBFrontend::feSatellite) || (types & (1 << eDVBFrontend::feSatellite)))
	{
		eDVBFrontendParametersSatellite parm;
		bool can_handle_dvbs, can_handle_dvbs2;
		if (feparm->getDVBS(parm) < 0)
		{
			return 0;
		}
		can_handle_dvbs = supportsDeliverySystem(SYS_DVBS, true);
		can_handle_dvbs2 = supportsDeliverySystem(SYS_DVBS2, true);
		if (parm.system == eDVBFrontendParametersSatellite::System_DVB_S2 && !can_handle_dvbs2)
		{
			return 0;
		}
		if (parm.system == eDVBFrontendParametersSatellite::System_DVB_S && !can_handle_dvbs)
		{
			return 0;
		}
		score = m_sec ? m_sec->canTune(parm, this, 1 << m_slotid) : 0;
		if (score > 1 && parm.system == eDVBFrontendParametersSatellite::System_DVB_S && can_handle_dvbs2)
		{
			/* prefer to use an S tuner, try to keep S2 free for S2 transponders */
			score--;
		}
	}
	else if ((type == eDVBFrontend::feCable) || (types & (1 << eDVBFrontend::feCable)))
	{
		eDVBFrontendParametersCable parm;
		bool can_handle_dvbc_annex_a, can_handle_dvbc_annex_c;
		if (feparm->getDVBC(parm) < 0)
		{
			return 0;
		}
#if DVB_API_VERSION > 5 || DVB_API_VERSION == 5 && DVB_API_VERSION_MINOR >= 6
		if (m_dvbversion >= DVB_VERSION(5, 6))
		{
			can_handle_dvbc_annex_a = supportsDeliverySystem(SYS_DVBC_ANNEX_A, true);
			can_handle_dvbc_annex_c = supportsDeliverySystem(SYS_DVBC_ANNEX_C, true);
		}
		else
		{
			can_handle_dvbc_annex_a = can_handle_dvbc_annex_c = supportsDeliverySystem(SYS_DVBC_ANNEX_A, true); /* new value for SYS_DVBC_ANNEX_AC */
		}
#else
		can_handle_dvbc_annex_a = can_handle_dvbc_annex_c = supportsDeliverySystem(SYS_DVBC_ANNEX_AC, true);
#endif
		if (parm.system == eDVBFrontendParametersCable::System_DVB_C_ANNEX_A && !can_handle_dvbc_annex_a)
		{
			return 0;
		}
		if (parm.system == eDVBFrontendParametersCable::System_DVB_C_ANNEX_C && !can_handle_dvbc_annex_c)
		{
			return 0;
		}
		score = 2;
	}
	else if ((type == eDVBFrontend::feTerrestrial) || (types & (1 << eDVBFrontend::feTerrestrial)))
	{
		eDVBFrontendParametersTerrestrial parm;
		bool can_handle_dvbt, can_handle_dvbt2;
		can_handle_dvbt = supportsDeliverySystem(SYS_DVBT, true);
		can_handle_dvbt2 = supportsDeliverySystem(SYS_DVBT2, true);
		if (feparm->getDVBT(parm) < 0)
		{
			return 0;
		}
		if (parm.system == eDVBFrontendParametersTerrestrial::System_DVB_T && !can_handle_dvbt)
		{
			return 0;
		}
		if (parm.system == eDVBFrontendParametersTerrestrial::System_DVB_T2 && !can_handle_dvbt2)
		{
			return 0;
		}
		if (parm.system == eDVBFrontendParametersTerrestrial::System_DVB_T_T2 && !can_handle_dvbt)
		{
			return 0;
		}
		score = 2;
		if (parm.system == eDVBFrontendParametersTerrestrial::System_DVB_T && can_handle_dvbt2)
		{
			/* prefer to use a T tuner, try to keep T2 free for T2 transponders */
			score--;
		}
		if (parm.system == eDVBFrontendParametersTerrestrial::System_DVB_T_T2 && can_handle_dvbt2)
		{
			// System_DVB_T_T2 is a generic T/T2 type, so we prefer a dvb-t2 tuner
			score++;
		}
	}
	else if ((type == eDVBFrontend::feATSC) || (types & (1 << eDVBFrontend::feATSC)))
	{
		eDVBFrontendParametersATSC parm;
		bool can_handle_atsc, can_handle_dvbc_annex_b;
		can_handle_dvbc_annex_b = supportsDeliverySystem(SYS_DVBC_ANNEX_B, true);
		can_handle_atsc = supportsDeliverySystem(SYS_ATSC, true);
		if (feparm->getATSC(parm) < 0)
		{
			return 0;
		}
		if (!can_handle_atsc && !can_handle_dvbc_annex_b)
		{
			return 0;
		}
		if (parm.system == eDVBFrontendParametersATSC::System_DVB_C_ANNEX_B && !can_handle_dvbc_annex_b)
		{
			return 0;
		}
		if (parm.system == eDVBFrontendParametersATSC::System_ATSC && !can_handle_atsc)
		{
			return 0;
		}
		score = 2;
	}

	if (score && preferred)
	{
		/* make 'sure' we always prefer this frontend */
		score += eDVBFrontend::preferredFrontendScore; /* the offset has to be so ridiculously high because of the high scores which are used for DVB-S(2) */
	}
	return score;
}

bool eDVBFrontend::changeType(int type)
{
	if (m_type == type)
		return true;
#if DVB_API_VERSION >= 5
	char mode[4];
	struct dtv_property p[2];
	memset(p, 0, sizeof(p));
	struct dtv_properties cmdseq;
	cmdseq.props = p;
	cmdseq.num = 2;
	p[0].cmd = DTV_CLEAR;
	p[1].cmd = DTV_DELIVERY_SYSTEM;
	p[1].u.data = SYS_UNDEFINED;

	switch (type)
	{
		case feSatellite:
			snprintf(mode, sizeof(mode), "%d", m_modelist[SYS_DVBS]);
			p[1].u.data = SYS_DVBS;
			break;
#ifdef feSatellite2
		case feSatellite2:
			snprintf(mode, sizeof(mode), "%d", m_modelist[SYS_DVBS2]);
			p[1].u.data = SYS_DVBS2;
			break;
#endif
		case feTerrestrial:
		{
			char configStr[255];
			snprintf(configStr, 255, "config.Nims.%d.dvbt.terrestrial_5V", m_slotid);
			if (eConfigManager::getConfigBoolValue(configStr))
				 setVoltage(iDVBFrontend::voltage13);
			else
				 setVoltage(iDVBFrontend::voltageOff);

			snprintf(mode, sizeof(mode), "%d", m_modelist[SYS_DVBT]);
			p[1].u.data = SYS_DVBT;
			break;
		}
		case feCable:
		{
			 setVoltage(iDVBFrontend::voltageOff);
#ifdef SYS_DVBC_ANNEX_A
			snprintf(mode, sizeof(mode), "%d", m_modelist[SYS_DVBC_ANNEX_A]);
			p[1].u.data = SYS_DVBC_ANNEX_A;
#else
			snprintf(mode, sizeof(mode), "%d", m_modelist[SYS_DVBC_ANNEX_AC]);
			p[1].u.data = SYS_DVBC_ANNEX_AC;
#endif
			break;
		}
#ifdef feATSC
		case feATSC:
			snprintf(mode, sizeof(mode), "%d", m_modelist[SYS_ATSC]);
			p[1].u.data = SYS_ATSC;
			break;
#endif
		default:
			eDebug("not supported delivery system type %i", type);
			return false;
	}

	eDebug("data %d",p[1].u.data );
	if (ioctl(m_fd, FE_SET_PROPERTY, &cmdseq) == -1)
	{
		eDebug("FE_SET_PROPERTY failed %m, -> use procfs to switch delivery system tuner %d mode %s",m_slotid ,mode);
		closeFrontend();
		char filename[256];
		snprintf(filename, sizeof(filename), "/proc/stb/frontend/%d/mode", m_slotid);
		CFile::writeStr(filename, mode);
		reopenFrontend();
		m_type = type;
		return true;
	}
	else
	{
		if(m_need_delivery_system_workaround)
		{
			eDebug("[adenin] m_need_delivery_system_workaround active");
			FILE *f = fopen("/sys/module/dvb_core/parameters/dvb_shutdown_timeout", "rw");
			int old;
			if (f)
			{
				if (fscanf(f, "%d", &old) != 1)
					eDebug("read dvb_shutdown_timeout failed");
				if (fprintf(f, "%d", 0) == 0)
					eDebug("write dvb_shutdown_timeout failed");
			}
			closeFrontend();
			reopenFrontend();
			if (f)
			{
				if (fprintf(f, "%d", old) == 0)
					eDebug("rewrite dvb_shutdown_timeout failed");
				fclose(f);
			}
		}
		else
			eDebug("[adenin] m_need_delivery_system_workaround NOT active");
	}
	m_type = type;
	return true;
#else //if DVB_API_VERSION < 5
	return false;
#endif
}

bool eDVBFrontend::supportsDeliverySystem(const fe_delivery_system_t &sys, bool obeywhitelist)
{
	std::map<fe_delivery_system_t, bool>::iterator it = m_delsys.find(sys);

	if (obeywhitelist && !m_delsys_whitelist.empty())
	{
		it = m_delsys_whitelist.find(sys);
		if (it != m_delsys_whitelist.end() && it->second)
			return true;
	}
	else
		if (it != m_delsys.end() && it->second)
			return true;

	return false;
}

void eDVBFrontend::setDeliverySystemWhitelist(const std::vector<fe_delivery_system_t> &whitelist, bool append)
{
	if(!append)
		m_delsys_whitelist.clear();

	for (unsigned int i = 0; i < whitelist.size(); i++)
	{
		m_delsys_whitelist[whitelist[i]] = true;
	}
	if (m_simulate_fe)
	{
		m_simulate_fe->setDeliverySystemWhitelist(whitelist, append);
	}
}

bool eDVBFrontend::setDeliverySystem(fe_delivery_system_t delsys)
{
	eDebugDeliverySystem("frontend %d setDeliverySystem %d", m_slotid, delsys);
	struct dtv_property p[2];
	memset(p, 0, sizeof(p));
	struct dtv_properties cmdseq;
	cmdseq.props = p;
	cmdseq.num = 2;
	p[0].cmd = DTV_CLEAR;
	p[1].cmd = DTV_DELIVERY_SYSTEM;
	p[1].u.data = delsys;
	if (ioctl(m_fd, FE_SET_PROPERTY, &cmdseq) == -1)
	{
		eDebug("FE_SET_PROPERTY failed %m");
	}
	return true;
}

bool eDVBFrontend::setSlotInfo(int id, const char *descr, bool enabled, bool isDVBS2, int frontendid)
{
	if (frontendid < 0 || frontendid != m_dvbid)
	{
		return false;
	}
	m_slotid = id;
	m_enabled = enabled;
	strncpy(m_description, descr, sizeof(m_description));

	// HACK.. the rotor workaround is neede for all NIMs with LNBP21 voltage regulator...
	m_need_rotor_workaround = !!strstr(m_description, "Alps BSBE1") ||
		!!strstr(m_description, "Alps BSBE2") ||
		!!strstr(m_description, "Alps -S") ||
		!!strstr(m_description, "BCM4501");
	if (isDVBS2)
	{
		/* HACK for legacy dvb api without DELSYS support */
		m_delsys[SYS_DVBS2] = true;
	}
	eDebugNoSimulate("setSlotInfo for dvb frontend %d to slotid %d, descr %s, need rotorworkaround %s, enabled %s, DVB-S2 %s",
		m_dvbid, m_slotid, m_description, m_need_rotor_workaround ? "Yes" : "No", m_enabled ? "Yes" : "No", isDVBS2 ? "Yes" : "No" );
	return true;
}

eDVBRegisteredFrontend *eDVBFrontend::getPrev(eDVBRegisteredFrontend *fe)
{
	eDVBRegisteredFrontend *prev_fe = NULL;
	long linked_prev_ptr = -1;
	fe->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, linked_prev_ptr);
	if (linked_prev_ptr != -1)
		prev_fe = (eDVBRegisteredFrontend *)linked_prev_ptr;
	return prev_fe;
}

eDVBRegisteredFrontend *eDVBFrontend::getNext(eDVBRegisteredFrontend *fe)
{
	eDVBRegisteredFrontend *next_fe = NULL;
	long linked_next_ptr = -1;
	fe->m_frontend->getData(eDVBFrontend::LINKED_NEXT_PTR, linked_next_ptr);
	if (linked_next_ptr != -1)
		next_fe = (eDVBRegisteredFrontend *)linked_next_ptr;
	return next_fe;
}


void eDVBFrontend::getTop(eDVBFrontend *fe, eDVBRegisteredFrontend* &top_fe)
{
	eDVBRegisteredFrontend *prev_fe = NULL;
	long linked_prev_ptr = -1;
	fe->getData(eDVBFrontend::LINKED_PREV_PTR, linked_prev_ptr);
	while(linked_prev_ptr != -1)
	{
		prev_fe = (eDVBRegisteredFrontend *)linked_prev_ptr;
		prev_fe->m_frontend->getData(eDVBFrontend::LINKED_PREV_PTR, linked_prev_ptr);
	}
	top_fe = prev_fe;
}

void eDVBFrontend::getTop(eDVBRegisteredFrontend *fe, eDVBRegisteredFrontend* &top_fe)
{
	getTop(fe->m_frontend, top_fe);
}

void eDVBFrontend::getTop(eDVBRegisteredFrontend *fe, eDVBFrontend* &top_fe)
{
	eDVBRegisteredFrontend *_top_fe;
	getTop(fe->m_frontend, _top_fe);
	if(_top_fe)
		top_fe = _top_fe->m_frontend;
}

void eDVBFrontend::getTop(eDVBFrontend *fe, eDVBFrontend* &top_fe)
{
	eDVBRegisteredFrontend *_top_fe;
	getTop(fe, _top_fe);
	if(_top_fe)
		top_fe = _top_fe->m_frontend;
}

void eDVBFrontend::getTop(iDVBFrontend &fe, eDVBFrontend* &top_fe)
{
	eDVBRegisteredFrontend *_top_fe;
	getTop((eDVBFrontend*)&fe, _top_fe);
	if(_top_fe)
		top_fe = _top_fe->m_frontend;
}

void eDVBFrontend::getTop(iDVBFrontend &fe, eDVBRegisteredFrontend* &top_fe)
{
	eDVBRegisteredFrontend *_top_fe;
	getTop((eDVBFrontend*)&fe, top_fe);
}

eDVBRegisteredFrontend *eDVBFrontend::getLast(eDVBRegisteredFrontend *fe)
{
	eDVBRegisteredFrontend *next_fe = fe;
	long linked_next_ptr = -1;
	fe->m_frontend->getData(eDVBFrontend::LINKED_NEXT_PTR, linked_next_ptr);
	while(linked_next_ptr != -1)
	{
		next_fe = (eDVBRegisteredFrontend *)linked_next_ptr;
		next_fe->m_frontend->getData(eDVBFrontend::LINKED_NEXT_PTR, linked_next_ptr);
	}
	return next_fe;
}

bool eDVBFrontend::is_multistream()
{
//#if DVB_API_VERSION > 5 || DVB_API_VERSION == 5 && DVB_API_VERSION_MINOR >= 8
#if DVB_API_VERSION >= 5
	if(!strcmp(m_description, "TBS-5925"))
		return true;
	if(!strcmp(m_description, "GIGA DVB-S2 NIM (SP2246T)"))
		return true;
	return fe_info.caps & FE_CAN_MULTISTREAM;
#else //if DVB_API_VERSION < 5
	return 0;
#endif
}

std::string eDVBFrontend::getCapabilities()
{
	std::stringstream ss;

	if (fe_info.caps == FE_IS_STUPID)			ss << "stupid FE" << std::endl;
	if (fe_info.caps &  FE_CAN_INVERSION_AUTO)		ss << "auto inversion" << std::endl;
	if (fe_info.caps &  FE_CAN_FEC_1_2)			ss << "FEC 1/2" << std::endl;
	if (fe_info.caps &  FE_CAN_FEC_2_3)			ss << "FEC 2/3" << std::endl;
	if (fe_info.caps &  FE_CAN_FEC_3_4)			ss << "FEC 3/4" << std::endl;
	if (fe_info.caps &  FE_CAN_FEC_4_5)			ss << "FEC 4/5" << std::endl;
	if (fe_info.caps &  FE_CAN_FEC_5_6)			ss << "FEC 5/6" << std::endl;
	if (fe_info.caps &  FE_CAN_FEC_6_7)			ss << "FEC 6/7" << std::endl;
	if (fe_info.caps &  FE_CAN_FEC_7_8)			ss << "FEC 7/8" << std::endl;
	if (fe_info.caps &  FE_CAN_FEC_8_9)			ss << "FEC 8/9" << std::endl;
	if (fe_info.caps &  FE_CAN_FEC_AUTO)			ss << "FEC AUTO" << std::endl;
	if (fe_info.caps &  FE_CAN_QPSK)			ss << "QPSK" << std::endl;
	if (fe_info.caps &  FE_CAN_QAM_16)			ss << "QAM 16" << std::endl;
	if (fe_info.caps &  FE_CAN_QAM_32)			ss << "QAM 32" << std::endl;
	if (fe_info.caps &  FE_CAN_QAM_64)			ss << "QAM 64" << std::endl;
	if (fe_info.caps &  FE_CAN_QAM_128)			ss << "QAM 128" << std::endl;
	if (fe_info.caps &  FE_CAN_QAM_256)			ss << "QAM 256" << std::endl;
	if (fe_info.caps &  FE_CAN_QAM_AUTO)			ss << "QAM AUTO" << std::endl;
	if (fe_info.caps &  FE_CAN_TRANSMISSION_MODE_AUTO)	ss << "auto transmission mode" << std::endl;
	if (fe_info.caps &  FE_CAN_BANDWIDTH_AUTO)             	ss << "auto bandwidth" << std::endl;
	if (fe_info.caps &  FE_CAN_GUARD_INTERVAL_AUTO)		ss << "auto guard interval" << std::endl;
	if (fe_info.caps &  FE_CAN_HIERARCHY_AUTO)		ss << "auto hierarchy" << std::endl;
	if (fe_info.caps &  FE_CAN_8VSB)			ss << "FE_CAN_8VSB" << std::endl;
	if (fe_info.caps &  FE_CAN_16VSB)			ss << "FE_CAN_16VSB" << std::endl;
	if (fe_info.caps &  FE_HAS_EXTENDED_CAPS)		ss << "FE_HAS_EXTENDED_CAPS" << std::endl;
//#if DVB_API_VERSION > 5 || DVB_API_VERSION == 5 && DVB_API_VERSION_MINOR >= 8
#if DVB_API_VERSION >= 5
	if (fe_info.caps &  FE_CAN_MULTISTREAM)			ss << "FE_CAN_MULTISTREAM" << std::endl;
#endif
	if (fe_info.caps &  FE_CAN_TURBO_FEC)			ss << "FE_CAN_TURBO_FEC" << std::endl;
	if (fe_info.caps &  FE_CAN_2G_MODULATION)		ss << "FE_CAN_2G_MODULATION" << std::endl;
	if (fe_info.caps &  FE_NEEDS_BENDING)			ss << "FE_NEEDS_BENDING" << std::endl;
	if (fe_info.caps &  FE_CAN_RECOVER)			ss << "FE_CAN_RECOVER" << std::endl;
	if (fe_info.caps &  FE_CAN_MUTE_TS)			ss << "FE_CAN_MUTE_TS" << std::endl;

	return ss.str();
}
std::string eDVBFrontend::getCapabilities(fe_delivery_system_t delsys)
{
	std::stringstream ss;

	if (m_fe_info[delsys].caps == FE_IS_STUPID)			ss << "stupid FE" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_INVERSION_AUTO)		ss << "auto inversion" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_FEC_1_2)			ss << "FEC 1/2" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_FEC_2_3)			ss << "FEC 2/3" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_FEC_3_4)			ss << "FEC 3/4" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_FEC_4_5)			ss << "FEC 4/5" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_FEC_5_6)			ss << "FEC 5/6" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_FEC_6_7)			ss << "FEC 6/7" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_FEC_7_8)			ss << "FEC 7/8" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_FEC_8_9)			ss << "FEC 8/9" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_FEC_AUTO)			ss << "FEC AUTO" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_QPSK)			ss << "QPSK" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_QAM_16)			ss << "QAM 16" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_QAM_32)			ss << "QAM 32" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_QAM_64)			ss << "QAM 64" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_QAM_128)			ss << "QAM 128" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_QAM_256)			ss << "QAM 256" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_QAM_AUTO)			ss << "QAM AUTO" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_TRANSMISSION_MODE_AUTO)	ss << "auto transmission mode" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_BANDWIDTH_AUTO)             	ss << "auto bandwidth" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_GUARD_INTERVAL_AUTO)		ss << "auto guard interval" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_HIERARCHY_AUTO)		ss << "auto hierarchy" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_8VSB)			ss << "FE_CAN_8VSB" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_16VSB)			ss << "FE_CAN_16VSB" << std::endl;
	if (m_fe_info[delsys].caps &  FE_HAS_EXTENDED_CAPS)		ss << "FE_HAS_EXTENDED_CAPS" << std::endl;
//#if DVB_API_VERSION > 5 || DVB_API_VERSION == 5 && DVB_API_VERSION_MINOR >= 8
#if DVB_API_VERSION >= 5
	if (m_fe_info[delsys].caps &  FE_CAN_MULTISTREAM)			ss << "FE_CAN_MULTISTREAM" << std::endl;
#endif
	if (m_fe_info[delsys].caps &  FE_CAN_TURBO_FEC)			ss << "FE_CAN_TURBO_FEC" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_2G_MODULATION)		ss << "FE_CAN_2G_MODULATION" << std::endl;
	if (m_fe_info[delsys].caps &  FE_NEEDS_BENDING)			ss << "FE_NEEDS_BENDING" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_RECOVER)			ss << "FE_CAN_RECOVER" << std::endl;
	if (m_fe_info[delsys].caps &  FE_CAN_MUTE_TS)			ss << "FE_CAN_MUTE_TS" << std::endl;

	return ss.str();
}
