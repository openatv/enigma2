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

#ifndef I2C_SLAVE_FORCE
#define I2C_SLAVE_FORCE	0x0706
#endif

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
	if (system == System_DVB_S && modulation == Modulation_8PSK)
	{
		eDebug("satellite_delivery_descriptor invalid modulation type.. force QPSK");
		modulation = Modulation_QPSK;
	}
	rolloff = descriptor.getRollOff();
	if (system == System_DVB_S2)
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
	plpid = 0;
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
	t = m_type;
	return (m_type == -1) ? -1 : 0;
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

RESULT eDVBFrontendParameters::getATSC(eDVBFrontendParametersATSC &p) const
{
	if (m_type != iDVBFrontend::feATSC)
		return -1;
	p = atsc;
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

RESULT eDVBFrontendParameters::setATSC(const eDVBFrontendParametersATSC &p)
{
	atsc = p;
	m_type = iDVBFrontend::feATSC;
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
			else if (oterrestrial.plpid != terrestrial.plpid)
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
			hash = 0xDDDD0000;
			hash |= (atsc.frequency/1000)&0xFFFF;
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
	:m_simulate(simulate), m_enabled(false), m_simulate_fe(simulate_fe), m_dvbid(fe), m_slotid(fe)
	,m_fd(-1), m_dvbversion(0), m_rotor_mode(false), m_need_rotor_workaround(false)
	,m_state(stateClosed), m_timeout(0), m_tuneTimer(0)
{
	m_filename = devicenodename;

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
	m_delsys.clear();
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
			struct dtv_properties cmdseq;
			cmdseq.props = &p;
			cmdseq.num = 1;
			p.cmd = DTV_API_VERSION;
			if (ioctl(m_fd, FE_GET_PROPERTY, &cmdseq) >= 0)
			{
				m_dvbversion = p.u.data;
			}
#endif
		}
		if (m_delsys.empty())
		{
			if (::ioctl(m_fd, FE_GET_INFO, &fe_info) < 0)
			{
				eWarning("ioctl FE_GET_INFO failed");
				::close(m_fd);
				m_fd = -1;
				return -1;
			}
			strncpy(m_description, fe_info.name, sizeof(m_description));
#if defined DTV_ENUM_DELSYS
			struct dtv_property p[1];
			p[0].cmd = DTV_ENUM_DELSYS;
			struct dtv_properties cmdseq;
			cmdseq.num = 1;
			cmdseq.props = p;
			if (::ioctl(m_fd, FE_GET_PROPERTY, &cmdseq) >= 0)
			{
				m_delsys.clear();
				for (; p[0].u.buffer.len > 0; p[0].u.buffer.len--)
				{
					fe_delivery_system_t delsys = (fe_delivery_system_t)p[0].u.buffer.data[p[0].u.buffer.len - 1];
					m_delsys[delsys] = true;
				}
			}
			else
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
#if DVB_API_VERSION >= 5
						if (m_dvbversion >= DVB_VERSION(5, 0))
						{
							if (fe_info.caps & FE_CAN_2G_MODULATION) m_delsys[SYS_DVBS2] = true;
						}
#endif
						break;
					}
					case FE_QAM:
					{
#if DVB_API_VERSION > 5 || DVB_API_VERSION == 5 && DVB_API_VERSION_MINOR >= 6
						/* no need for a m_dvbversion check, SYS_DVBC_ANNEX_A replaced SYS_DVBC_ANNEX_AC (same value) */
						m_delsys[SYS_DVBC_ANNEX_A] = true;
#else
						m_delsys[SYS_DVBC_ANNEX_AC] = true;
#endif
						break;
					}
					case FE_OFDM:
					{
						m_delsys[SYS_DVBT] = true;
#if DVB_API_VERSION > 5 || DVB_API_VERSION == 5 && DVB_API_VERSION_MINOR >= 3
						if (m_dvbversion >= DVB_VERSION(5, 3))
						{
							if (fe_info.caps & FE_CAN_2G_MODULATION) m_delsys[SYS_DVBT2] = true;
						}
#endif
						break;
					}
					case FE_ATSC:	// placeholder to prevent warning
					{
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
		dvb_frontend_event event;
		int res;
		int state;
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
	int sat_max = 1600; // for stv0288 / bsbe2
	int ret = 0x12345678;
	if (!strcmp(m_description, "AVL2108")) // ET9000
	{
		ret = (int)(snr / 40.5);
		sat_max = 1618;
	}
	if (!strcmp(m_description, "AVL6211")) // ET10000
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
	}
	else if (strstr(m_description, "BCM4506") || strstr(m_description, "BCM4505"))
	{
		ret = (snr * 100) >> 8;
	}
	else if (!strcmp(m_description, "Vuplus DVB-S NIM(AVL2108)")) // VU+Ultimo/VU+Uno DVB-S2 NIM
	{
		ret = (int)((((double(snr) / (65536.0 / 100.0)) * 0.1600) + 0.2100) * 100);
	}
	else if (!strcmp(m_description, "Vuplus DVB-S NIM(AVL6222)")) // VU+ DVB-S2 Dual NIM
	{
		ret = (int)((((double(snr) / (65536.0 / 100.0)) * 0.1244) + 2.5079) * 100);
	}
	else if (!strcmp(m_description, "Vuplus DVB-S NIM(AVL6211)")) // VU+ DVB-S2 Dual NIM
	{
		ret = (int)((((double(snr) / (65536.0 / 100.0)) * 0.1244) + 2.5079) * 100);
	}
	else if (!strcmp(m_description, "BCM7335 DVB-S2 NIM (internal)")) // VU+DUO DVB-S2 NIM
	{
		ret = (int)((((double(snr) / (65536.0 / 100.0)) * 0.1244) + 2.5079) * 100);
	}
	else if (!strcmp(m_description, "BCM7356 DVB-S2 NIM (internal)")) // VU+ Solo2
	{
		ret = (int)((((double(snr) / (65536.0 / 100.0)) * 0.1800) - 1.0000) * 100);
	}
	else if (!strcmp(m_description, "BCM7346 (internal)")) // MaxDigital XP1000
	{
		ret = (int)((((double(snr) / (65536.0 / 100.0)) * 0.1880) + 0.1959) * 100);
	}
	else if (!strcmp(m_description, "BCM7346 DVB-S2 NIM (internal)")) // Gigablue
	{
		ret = (int)((((double(snr) / (65536.0 / 100.0)) * 0.1800) - 1.0000) * 100);
	}
	else if (!strcmp(m_description, "BCM7358 DVB-S2 NIM (internal)")) // Gigablue
	{
		ret = (int)((((double(snr) / (65536.0 / 100.0)) * 0.1710) - 1.0000) * 100);
	}
	else if (!strcmp(m_description, "GIGA DVB-S2 NIM (Internal)")) // Gigablue
	{
		ret = (int)((((double(snr) / (65536.0 / 100.0)) * 0.1710) - 1.0000) * 100);
	}
	else if (!strcmp(m_description, "Genpix"))
	{
		ret = (int)((snr << 1) / 5);
	}
	else if (!strcmp(m_description, "CXD1981"))
	{
		eDVBFrontendParametersCable parm;
		int mse = (~snr) & 0xFF;
		oparm.getDVBC(parm);
		switch (parm.modulation)
		{
		case eDVBFrontendParametersCable::Modulation_QAM16:
		case eDVBFrontendParametersCable::Modulation_QAM64:
		case eDVBFrontendParametersCable::Modulation_QAM256: ret = (int)(-950 * log(((double)mse) / 760)); break;
		case eDVBFrontendParametersCable::Modulation_QAM32:
		case eDVBFrontendParametersCable::Modulation_QAM128: ret = (int)(-875 * log(((double)mse) / 650)); break;
		default: break;
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
			signalquality = (ret >= sat_max ? 65536 : ret * 65536 / sat_max);
			break;
		case feCable: // we assume a max of 42db here
			signalquality = (ret >= 4200 ? 65536 : ret * 65536 / 4200);
			break;
		case feTerrestrial: // we assume a max of 29db here
			signalquality = (ret >= 2900 ? 65536 : ret * 65536 / 2900);
			break;
		case feATSC: // we assume a max of 42db here
			signalquality = (ret >= 4200 ? 65536 : ret * 65536 / 4200);
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
					if (ioctl(m_fd, FE_READ_SNR, &snr) < 0 && errno != ERANGE)
						eDebug("FE_READ_SNR failed (%m)");
				}
				return snr;
			}
			break;
		case iFrontendInformation_ENUMS::signalQuality:
		case iFrontendInformation_ENUMS::signalQualitydB: /* this will move into the driver */
			if (m_state == stateLock)
			{
				int snr = readFrontendData(iFrontendInformation_ENUMS::snrValue);
				int signalquality = 0;
				int signalqualitydb = 0;
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
					if (ioctl(m_fd, FE_READ_SIGNAL_STRENGTH, &strength) < 0 && errno != ERANGE)
						eDebug("FE_READ_SIGNAL_STRENGTH failed (%m)");
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
				if ( ioctl(m_fd, FE_READ_STATUS, &status) < 0 && errno != ERANGE )
					eDebug("FE_READ_STATUS failed (%m)");
				return (int)status;
			}
			return (FE_HAS_SYNC | FE_HAS_LOCK);
		}
		case iFrontendInformation_ENUMS::frequency:
		{
			struct dtv_property p;
			struct dtv_properties cmdseq;
			oparm.getSystem(type);
			cmdseq.props = &p;
			cmdseq.num = 1;
			p.cmd = DTV_FREQUENCY;
			if (ioctl(m_fd, FE_GET_PROPERTY, &cmdseq) < 0)
			{
				return 0;
			}
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
		}
		else if (type == feATSC)
		{
		}
		if (ioctl(m_fd, FE_GET_PROPERTY, &cmdseq) < 0)
		{
			eDebug("FE_GET_PROPERTY failed (%m)");
			original = true;
		}
	}
	switch (type)
	{
	case feSatellite:
		{
			eDVBFrontendParametersSatellite s;
			oparm.getDVBS(s);
			dest = new eDVBSatelliteTransponderData(cmdseq.props, cmdseq.num, s, m_data[FREQ_OFFSET], original);
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
					eDebugNoSimulate("(?)");
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
		int type = -1;
		oparm.getSystem(type);
		eDebug("setting frontend %d", m_dvbid);
		if (recvEvents)
			m_sn->start();
		feEvent(-1); // flush events
		struct dtv_property p[16];
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
			}
		}
		else if (type == iDVBFrontend::feCable)
		{
			eDVBFrontendParametersCable parm;
			oparm.getDVBC(parm);
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
					p[cmdseq.num].cmd = DTV_STREAM_ID, p[cmdseq.num].u.data = parm.plpid, cmdseq.num++;
#elif defined DTV_DVBT2_PLP_ID
					p[cmdseq.num].cmd = DTV_DVBT2_PLP_ID, p[cmdseq.num].u.data = parm.plpid, cmdseq.num++;
#endif
				}
			}
		}
		else if (type == iDVBFrontend::feATSC)
		{
			eDVBFrontendParametersATSC parm;
			oparm.getATSC(parm);
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
		p[cmdseq.num].cmd = DTV_TUNE, cmdseq.num++;
		if (ioctl(m_fd, FE_SET_PROPERTY, &cmdseq) == -1)
		{
			perror("FE_SET_PROPERTY failed");
			return;
		}
	}
}

RESULT eDVBFrontend::prepare_sat(const eDVBFrontendParametersSatellite &feparm, unsigned int tunetimeout)
{
	int res;
	satfrequency = feparm.frequency;
	if (!m_sec)
	{
		eWarning("no SEC module active!");
		return -ENOENT;
	}
	res = m_sec->prepare(*this, feparm, satfrequency, 1 << m_slotid, tunetimeout);
	if (!res)
	{
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
		if ((unsigned int)satfrequency < fe_info.frequency_min || (unsigned int)satfrequency > fe_info.frequency_max)
		{
			eDebugNoSimulate("%d mhz out of tuner range.. dont tune", satfrequency / 1000);
			return -EINVAL;
		}
		eDebugNoSimulate("tuning to %d mhz", satfrequency / 1000);
	}
	oparm.setDVBS(feparm, feparm.no_rotor_command_on_tune);
	return res;
}

RESULT eDVBFrontend::prepare_cable(const eDVBFrontendParametersCable &feparm)
{
	eDebugNoSimulate("tuning to %d khz, sr %d, fec %d, modulation %d, inversion %d",
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
	oparm.setDVBT(feparm);
	return 0;
}

RESULT eDVBFrontend::prepare_atsc(const eDVBFrontendParametersATSC &feparm)
{
	oparm.setATSC(feparm);
	return 0;
}

RESULT eDVBFrontend::tune(const iDVBFrontendParameters &where)
{
	unsigned int timeout = 5000;
	int type;
	eDebugNoSimulate("(%d)tune", m_dvbid);

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

		char configStr[255];
		snprintf(configStr, 255, "config.Nims.%d.terrestrial_5V", m_slotid);
		m_sec_sequence.push_back( eSecCommand(eSecCommand::START_TUNE_TIMEOUT, timeout) );
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
			break;
		case voltage13_5:
			increased = true;
		case voltage13:
			vlt = SEC_VOLTAGE_13;
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
	int score = 0;
	bool preferred = (eDVBFrontend::getPreferredFrontend() >= 0 && m_slotid == eDVBFrontend::getPreferredFrontend());
	if (feparm->getSystem(type) || !m_enabled)
	{
		return 0;
	}
	if (type == eDVBFrontend::feSatellite)
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
	else if (type == eDVBFrontend::feCable)
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
			can_handle_dvbc_annex_a = can_handle_dvbc_annex_c = supportsDeliverySystem(SYS_DVBC_ANNEX_A, true); /* new value for SYS_DVB_ANNEX_AC */
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
	else if (type == eDVBFrontend::feTerrestrial)
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
	else if (type == eDVBFrontend::feATSC)
	{
		eDVBFrontendParametersATSC parm;
		bool can_handle_atsc, can_handle_dvbc_annex_b;
		can_handle_dvbc_annex_b = supportsDeliverySystem(SYS_DVBC_ANNEX_B, true);
		can_handle_atsc = supportsDeliverySystem(SYS_ATSC, true);
		if (feparm->getATSC(parm) < 0)
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
		score += 100000; /* the offset has to be so ridiculously high because of the high scores which are used for DVB-S(2) */
	}
	return score;
}

bool eDVBFrontend::supportsDeliverySystem(const fe_delivery_system_t &sys, bool obeywhitelist)
{
	std::map<fe_delivery_system_t, bool>::iterator it = m_delsys.find(sys);
	if (it != m_delsys.end() && it->second)
	{
		if (obeywhitelist && !m_delsys_whitelist.empty())
		{
			it = m_delsys_whitelist.find(sys);
			if (it == m_delsys_whitelist.end() || !it->second) return false;
		}
		return true;
	}
	return false;
}

void eDVBFrontend::setDeliverySystemWhitelist(const std::vector<fe_delivery_system_t> &whitelist)
{
	m_delsys_whitelist.clear();
	for (unsigned int i = 0; i < whitelist.size(); i++)
	{
		m_delsys_whitelist[whitelist[i]] = true;
	}
	if (m_simulate_fe)
	{
		m_simulate_fe->setDeliverySystemWhitelist(whitelist);
	}
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
