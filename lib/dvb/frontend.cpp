#include <lib/dvb/dvb.h>
#include <lib/base/eerror.h>
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
#ifdef FEC_9_10
	#warning "FEC_9_10 already exist in dvb api ... it seems it is now ready for DVB-S2"
#else
	#define FEC_S2_1_2 (fe_code_rate_t)(FEC_AUTO+1)
	#define FEC_S2_2_3 (fe_code_rate_t)(FEC_S2_1_2+1)
	#define FEC_S2_3_4 (fe_code_rate_t)(FEC_S2_2_3+1)
	#define FEC_S2_5_6 (fe_code_rate_t)(FEC_S2_3_4+1)
	#define FEC_S2_7_8 (fe_code_rate_t)(FEC_S2_5_6+1)
	#define FEC_S2_8_9 (fe_code_rate_t)(FEC_S2_7_8+1)
	#define FEC_S2_3_5 (fe_code_rate_t)(FEC_S2_8_9+1)
	#define FEC_S2_4_5 (fe_code_rate_t)(FEC_S2_3_5+1)
	#define FEC_S2_9_10 (fe_code_rate_t)(FEC_S2_4_5+1)
#endif
#endif

#include <dvbsi++/satellite_delivery_system_descriptor.h>
#include <dvbsi++/cable_delivery_system_descriptor.h>
#include <dvbsi++/terrestrial_delivery_system_descriptor.h>

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
	if ( fec != FEC::fNone && fec > FEC::f9_10 )
		fec = FEC::fAuto;
	inversion = Inversion::Unknown;
	orbital_position  = ((descriptor.getOrbitalPosition() >> 12) & 0xF) * 1000;
	orbital_position += ((descriptor.getOrbitalPosition() >> 8) & 0xF) * 100;
	orbital_position += ((descriptor.getOrbitalPosition() >> 4) & 0xF) * 10;
	orbital_position += ((descriptor.getOrbitalPosition()) & 0xF);
	if (orbital_position && (!descriptor.getWestEastFlag()))
		orbital_position = 3600 - orbital_position;
	system = descriptor.getModulationSystem();
	modulation = descriptor.getModulation();
	if (system == System::DVB_S && modulation == Modulation::M8PSK)
	{
		eDebug("satellite_delivery_descriptor non valid modulation type.. force QPSK");
		modulation=QPSK;
	}
	roll_off = descriptor.getRollOff();
	if (system == System::DVB_S2)
	{
		eDebug("SAT DVB-S2 freq %d, %s, pos %d, sr %d, fec %d, modulation %d, roll_off %d",
			frequency,
			polarisation ? "hor" : "vert",
			orbital_position,
			symbol_rate, fec,
			modulation,
			roll_off);
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
	if ( fec_inner == 0xF )
		fec_inner = FEC::fNone;
	modulation = descriptor.getModulation();
	if ( modulation > 0x5 )
		modulation = Modulation::Auto;
	inversion = Inversion::Unknown;
	eDebug("Cable freq %d, mod %d, sr %d, fec %d",
		frequency,
		modulation, symbol_rate, fec_inner);
}

void eDVBFrontendParametersTerrestrial::set(const TerrestrialDeliverySystemDescriptor &descriptor)
{
	frequency = descriptor.getCentreFrequency() * 10;
	bandwidth = descriptor.getBandwidth();
	if ( bandwidth > 2 ) // 5Mhz forced to auto
		bandwidth = Bandwidth::BwAuto;
	code_rate_HP = descriptor.getCodeRateHpStream();
	if (code_rate_HP > 4)
		code_rate_HP = FEC::fAuto;
	code_rate_LP = descriptor.getCodeRateLpStream();
	if (code_rate_LP > 4)
		code_rate_LP = FEC::fAuto;
	transmission_mode = descriptor.getTransmissionMode();
	if (transmission_mode > 1) // TM4k forced to auto
		transmission_mode = TransmissionMode::TMAuto;
	guard_interval = descriptor.getGuardInterval();
	if (guard_interval > 3)
		guard_interval = GuardInterval::GI_Auto;
	hierarchy = descriptor.getHierarchyInformation()&3;
	modulation = descriptor.getConstellation();
	if (modulation > 2)
		modulation = Modulation::Auto;
	inversion = Inversion::Unknown;
	eDebug("Terr freq %d, bw %d, cr_hp %d, cr_lp %d, tm_mode %d, guard %d, hierarchy %d, const %d",
		frequency, bandwidth, code_rate_HP, code_rate_LP, transmission_mode,
		guard_interval, hierarchy, modulation);
}

eDVBFrontendParameters::eDVBFrontendParameters(): m_type(-1)
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

RESULT eDVBFrontendParameters::calculateDifference(const iDVBFrontendParameters *parm, int &diff) const
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
		
		if (cable.modulation != ocable.modulation && cable.modulation != eDVBFrontendParametersCable::Modulation::Auto && ocable.modulation != eDVBFrontendParametersCable::Modulation::Auto)
			diff = 1 << 29;
		else if (cable.inversion != ocable.inversion && cable.inversion != eDVBFrontendParametersCable::Inversion::Unknown && ocable.inversion != eDVBFrontendParametersCable::Inversion::Unknown)
			diff = 1 << 28;
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
		
		diff = abs(terrestrial.frequency - oterrestrial.frequency);

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
		return 0;
	case iDVBFrontend::feTerrestrial:
		hash = 0xEEEE0000;
		return 0;
	default:
		return -1;
	}
}

DEFINE_REF(eDVBFrontend);

eDVBFrontend::eDVBFrontend(int adap, int fe, int &ok)
	:m_type(-1), m_fe(fe), m_fd(-1), m_sn(0), m_timeout(0), m_tuneTimer(0)
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
	m_timeout = new eTimer(eApp);
	CONNECT(m_timeout->timeout, eDVBFrontend::timeout);

	m_tuneTimer = new eTimer(eApp);
	CONNECT(m_tuneTimer->timeout, eDVBFrontend::tuneLoop);

	for (int i=0; i<eDVBFrontend::NUM_DATA_ENTRIES; ++i)
		m_data[i] = -1;

	m_idleInputpower[0]=m_idleInputpower[1]=0;

	ok = !openFrontend();
	closeFrontend();
}

int eDVBFrontend::openFrontend()
{
	if (m_sn)
		return -1;  // already opened

	m_state=0;
	m_tuning=0;

#if HAVE_DVB_API_VERSION < 3
	if (m_secfd < 0)
	{
		m_secfd = ::open(m_sec_filename, O_RDWR);
		if (m_secfd < 0)
		{
			eWarning("failed! (%s) %m", m_sec_filename);
			return -1;
		}
	}
	else
		eWarning("sec %d already opened", m_fe);
	FrontendInfo fe_info;
#else
	dvb_frontend_info fe_info;
#endif
	eDebug("opening frontend %d", m_fe);
	if (m_fd < 0)
	{
		m_fd = ::open(m_filename, O_RDWR|O_NONBLOCK);
		if (m_fd < 0)
		{
			eWarning("failed! (%s) %m", m_filename);
#if HAVE_DVB_API_VERSION < 3
			::close(m_secfd);
			m_secfd=-1;
#endif
			return -1;
		}
	}
	else
		eWarning("frontend %d already opened", m_fe);
	if (m_type == -1)
	{
		if (::ioctl(m_fd, FE_GET_INFO, &fe_info) < 0)
		{
			eWarning("ioctl FE_GET_INFO failed");
			::close(m_fd);
			m_fd = -1;
#if HAVE_DVB_API_VERSION < 3
			::close(m_secfd);
			m_secfd=-1;
#endif
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
#if HAVE_DVB_API_VERSION < 3
			::close(m_secfd);
			m_secfd=-1;
#endif
			return -1;
		}
		eDebug("detected %s frontend", "satellite\0cable\0    terrestrial"+fe_info.type*10);
	}

	setTone(iDVBFrontend::toneOff);
	setVoltage(iDVBFrontend::voltageOff);

	m_sn = new eSocketNotifier(eApp, m_fd, eSocketNotifier::Read);
	CONNECT(m_sn->activated, eDVBFrontend::feEvent);

	return 0;
}

int eDVBFrontend::closeFrontend()
{
	eDVBRegisteredFrontend *linked_fe = (eDVBRegisteredFrontend*)m_data[LINKED_NEXT_PTR];
	while (linked_fe != (eDVBRegisteredFrontend*)-1)
	{
		if (linked_fe->m_inuse)
		{
			eDebug("dont close frontend %d until the linked frontend %d is still in use",
				m_fe, linked_fe->m_frontend->getID());
			return -1;
		}
		linked_fe->m_frontend->getData(LINKED_NEXT_PTR, (int&)linked_fe);
	}
	if (m_fd >= 0)
	{
		eDebug("close frontend %d", m_fe);
		m_tuneTimer->stop();
		setTone(iDVBFrontend::toneOff);
		setVoltage(iDVBFrontend::voltageOff);
		if (m_sec)
			m_sec->setRotorMoving(false);
		if (!::close(m_fd))
			m_fd=-1;
		else
			eWarning("couldnt close frontend %d", m_fe);
		m_data[CSW] = m_data[UCSW] = m_data[TONEBURST] = -1;
	}
#if HAVE_DVB_API_VERSION < 3
	if (m_secfd >= 0)
	{
		if (!::close(m_secfd))
			m_secfd=-1;
		else
			eWarning("couldnt close sec %d", m_fe);
	}
#endif
	delete m_sn;
	m_sn=0;

	return 0;
}

eDVBFrontend::~eDVBFrontend()
{
	closeFrontend();
	delete m_timeout;
	delete m_tuneTimer;
}

void eDVBFrontend::feEvent(int w)
{
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

		if (res)
		{
			eWarning("FE_GET_EVENT failed! %m");
			return;
		}
		
		if (w < 0)
			continue;

#if HAVE_DVB_API_VERSION < 3
		if (event.type == FE_COMPLETION_EV)
#else
		eDebug("(%d)fe event: status %x, inversion %s", m_fe, event.status, (event.parameters.inversion == INVERSION_ON) ? "on" : "off");
		if (event.status & FE_HAS_LOCK)
#endif
		{
			state = stateLock;
		} else
		{
			if (m_tuning)
				state = stateTuning;
			else
			{
				state = stateLostLock;
				m_data[CSW] = m_data[UCSW] = m_data[TONEBURST] = -1; // reset diseqc
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
		m_stateChanged(this);
	}
}

int eDVBFrontend::readFrontendData(int type)
{
	switch(type)
	{
		case bitErrorRate:
		{
			uint32_t ber=0;
			if (ioctl(m_fd, FE_READ_BER, &ber) < 0 && errno != ERANGE)
				eDebug("FE_READ_BER failed (%m)");
			return ber;
		}
		case signalPower:
		{
			uint16_t snr=0;
			if (ioctl(m_fd, FE_READ_SNR, &snr) < 0 && errno != ERANGE)
				eDebug("FE_READ_SNR failed (%m)");
			return snr;
		}
		case signalQuality:
		{
			uint16_t strength=0;
			if (ioctl(m_fd, FE_READ_SIGNAL_STRENGTH, &strength) < 0 && errno != ERANGE)
				eDebug("FE_READ_SIGNAL_STRENGTH failed (%m)");
			return strength;
		}
		case locked:
		{
#if HAVE_DVB_API_VERSION < 3
			FrontendStatus status=0;
#else
			fe_status_t status;
#endif
			if ( ioctl(m_fd, FE_READ_STATUS, &status) < 0 && errno != ERANGE )
				eDebug("FE_READ_STATUS failed (%m)");
			return !!(status&FE_HAS_LOCK);
		}
		case synced:
		{
#if HAVE_DVB_API_VERSION < 3
			FrontendStatus status=0;
#else
			fe_status_t status;
#endif
			if ( ioctl(m_fd, FE_READ_STATUS, &status) < 0 && errno != ERANGE )
				eDebug("FE_READ_STATUS failed (%m)");
			return !!(status&FE_HAS_SYNC);
		}
		case frontendNumber:
			return m_fe;
	}
	return 0;
}

void PutToDict(PyObject *dict, const char*key, long value)
{
	PyObject *item = PyInt_FromLong(value);
	if (item)
	{
		if (PyDict_SetItemString(dict, key, item))
			eDebug("put %s to dict failed", key);
		Py_DECREF(item);
	}
	else
		eDebug("could not create PyObject for %s", key);
}

void PutToDict(PyObject *dict, const char*key, const char *value)
{
	PyObject *item = PyString_FromString(value);
	if (item)
	{
		if (PyDict_SetItemString(dict, key, item))
			eDebug("put %s to dict failed", key);
		Py_DECREF(item);
	}
	else
		eDebug("could not create PyObject for %s", key);
}

void fillDictWithSatelliteData(PyObject *dict, const FRONTENDPARAMETERS &parm, eDVBFrontend *fe)
{
	int freq_offset=0;
	int csw=0;
	const char *tmp=0;
	fe->getData(eDVBFrontend::CSW, csw);
	fe->getData(eDVBFrontend::FREQ_OFFSET, freq_offset);
	int frequency = parm_frequency + freq_offset;
	PutToDict(dict, "frequency", frequency);
	PutToDict(dict, "symbol_rate", parm_u_qpsk_symbol_rate);
	switch(parm_u_qpsk_fec_inner)
	{
	case FEC_1_2:
		tmp = "FEC_1_2";
		break;
	case FEC_2_3:
		tmp = "FEC_2_3";
		break;
	case FEC_3_4:
		tmp = "FEC_3_4";
		break;
	case FEC_5_6:
		tmp = "FEC_5_6";
		break;
	case FEC_7_8:
		tmp = "FEC_7_8";
		break;
	case FEC_NONE:
		tmp = "FEC_NONE";
	default:
	case FEC_AUTO:
		tmp = "FEC_AUTO";
		break;
#if HAVE_DVB_API_VERSION >=3
	case FEC_S2_1_2:
		tmp = "FEC_1_2";
		break;
	case FEC_S2_2_3:
		tmp = "FEC_2_3";
		break;
	case FEC_S2_3_4:
		tmp = "FEC_3_4";
		break;
	case FEC_S2_5_6:
		tmp = "FEC_5_6";
		break;
	case FEC_S2_7_8:
		tmp = "FEC_7_8";
		break;
	case FEC_S2_8_9:
		tmp = "FEC_8_9";
		break;
	case FEC_S2_3_5:
		tmp = "FEC_3_5";
		break;
	case FEC_S2_4_5:
		tmp = "FEC_4_5";
		break;
	case FEC_S2_9_10:
		tmp = "FEC_9_10";
		break;
#endif
	}
	PutToDict(dict, "fec_inner", tmp);
	tmp = parm_u_qpsk_fec_inner > FEC_AUTO ?
		"DVB-S2" : "DVB-S";
	PutToDict(dict, "system", tmp);
}

void fillDictWithCableData(PyObject *dict, const FRONTENDPARAMETERS &parm)
{
	const char *tmp=0;
	PutToDict(dict, "frequency", parm_frequency/1000);
	PutToDict(dict, "symbol_rate", parm_u_qam_symbol_rate);
	switch(parm_u_qam_fec_inner)
	{
	case FEC_NONE:
		tmp = "FEC_NONE";
		break;
	case FEC_1_2:
		tmp = "FEC_1_2";
		break;
	case FEC_2_3:
		tmp = "FEC_2_3";
		break;
	case FEC_3_4:
		tmp = "FEC_3_4";
		break;
	case FEC_5_6:
		tmp = "FEC_5_6";
		break;
	case FEC_7_8:
		tmp = "FEC_7_8";
		break;
#if HAVE_DVB_API_VERSION >= 3
	case FEC_8_9:
		tmp = "FEC_8_9";
		break;
#endif
	default:
	case FEC_AUTO:
		tmp = "FEC_AUTO";
		break;
	}
	PutToDict(dict, "fec_inner", tmp);
	switch(parm_u_qam_modulation)
	{
	case QAM_16:
		tmp = "QAM_16";
		break;
	case QAM_32:
		tmp = "QAM_32";
		break;
	case QAM_64:
		tmp = "QAM_64";
		break;
	case QAM_128:
		tmp = "QAM_128";
		break;
	case QAM_256:
		tmp = "QAM_256";
		break;
	default:
	case QAM_AUTO:
		tmp = "QAM_AUTO";
		break;
	}
	PutToDict(dict, "modulation", tmp);
}

void fillDictWithTerrestrialData(PyObject *dict, const FRONTENDPARAMETERS &parm)
{
	const char *tmp=0;
	PutToDict(dict, "frequency", parm_frequency);
	switch (parm_u_ofdm_bandwidth)
	{
	case BANDWIDTH_8_MHZ:
		tmp = "BANDWIDTH_8_MHZ";
		break;
	case BANDWIDTH_7_MHZ:
		tmp = "BANDWIDTH_7_MHZ";
		break;
	case BANDWIDTH_6_MHZ:
		tmp = "BANDWIDTH_6_MHZ";
		break;
	default:
	case BANDWIDTH_AUTO:
		tmp = "BANDWIDTH_AUTO";
		break;
	}
	PutToDict(dict, "bandwidth", tmp);
	switch (parm_u_ofdm_code_rate_LP)
	{
	case FEC_1_2:
		tmp = "FEC_1_2";
		break;
	case FEC_2_3:
		tmp = "FEC_2_3";
		break;
	case FEC_3_4:
		tmp = "FEC_3_4";
		break;
	case FEC_5_6:
		tmp = "FEC_5_6";
		break;
	case FEC_7_8:
		tmp = "FEC_7_8";
		break;
	default:
	case FEC_AUTO:
		tmp = "FEC_AUTO";
		break;
	}
	PutToDict(dict, "code_rate_lp", tmp);
	switch (parm_u_ofdm_code_rate_HP)
	{
	case FEC_1_2:
		tmp = "FEC_1_2";
		break;
	case FEC_2_3:
		tmp = "FEC_2_3";
		break;
	case FEC_3_4:
		tmp = "FEC_3_4";
		break;
	case FEC_5_6:
		tmp = "FEC_5_6";
		break;
	case FEC_7_8:
		tmp = "FEC_7_8";
		break;
	default:
	case FEC_AUTO:
		tmp = "FEC_AUTO";
		break;
	}
	PutToDict(dict, "code_rate_hp", tmp);
	switch (parm_u_ofdm_constellation)
	{
	case QPSK:
		tmp = "QPSK";
		break;
	case QAM_16:
		tmp = "QAM_16";
		break;
	case QAM_64:
		tmp = "QAM_64";
		break;
	default:
	case QAM_AUTO:
		tmp = "QAM_AUTO";
		break;
	}
	PutToDict(dict, "constellation", tmp);
	switch (parm_u_ofdm_transmission_mode)
	{
	case TRANSMISSION_MODE_2K:
		tmp = "TRANSMISSION_MODE_2K";
		break;
	case TRANSMISSION_MODE_8K:
		tmp = "TRANSMISSION_MODE_8K";
		break;
	default:
	case TRANSMISSION_MODE_AUTO:
		tmp = "TRANSMISSION_MODE_AUTO";
		break;
	}
	PutToDict(dict, "transmission_mode", tmp);
	switch (parm_u_ofdm_guard_interval)
	{
		case GUARD_INTERVAL_1_32:
			tmp = "GUARD_INTERVAL_1_32";
			break;
		case GUARD_INTERVAL_1_16:
			tmp = "GUARD_INTERVAL_1_16";
			break;
		case GUARD_INTERVAL_1_8:
			tmp = "GUARD_INTERVAL_1_8";
			break;
		case GUARD_INTERVAL_1_4:
			tmp = "GUARD_INTERVAL_1_4";
			break;
		default:
		case GUARD_INTERVAL_AUTO:
			tmp = "GUARD_INTERVAL_AUTO";
			break;
	}
	PutToDict(dict, "guard_interval", tmp);
	switch (parm_u_ofdm_hierarchy_information)
	{
		case HIERARCHY_NONE:
			tmp = "HIERARCHY_NONE";
			break;
		case HIERARCHY_1:
			tmp = "HIERARCHY_1";
			break;
		case HIERARCHY_2:
			tmp = "HIERARCHY_2";
			break;
		case HIERARCHY_4:
			tmp = "HIERARCHY_4";
			break;
		default:
		case HIERARCHY_AUTO:
			tmp = "HIERARCHY_AUTO";
			break;
	}
	PutToDict(dict, "hierarchy_information", tmp);
}

PyObject *eDVBFrontend::readTransponderData(bool original)
{
	PyObject *ret=PyDict_New();

	if (ret)
	{
		bool read=m_fd != -1;
		const char *tmp=0;

		PutToDict(ret, "tuner_number", m_fe);

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
				read=false;
				break;
		}
		PutToDict(ret, "tuner_type", tmp);

		if (read)
		{
			FRONTENDPARAMETERS front;

			tmp = "UNKNOWN";
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
			PutToDict(ret, "tuner_state", tmp);

			PutToDict(ret, "tuner_locked", readFrontendData(locked));
			PutToDict(ret, "tuner_synced", readFrontendData(synced));
			PutToDict(ret, "tuner_bit_error_rate", readFrontendData(bitErrorRate));
			PutToDict(ret, "tuner_signal_power", readFrontendData(signalPower));
			PutToDict(ret, "tuner_signal_quality", readFrontendData(signalQuality));

			if (!original && ioctl(m_fd, FE_GET_FRONTEND, &front)<0)
				eDebug("FE_GET_FRONTEND (%m)");
			else
			{
				tmp = "INVERSION_AUTO";
				switch(parm_inversion)
				{
					case INVERSION_ON:
						tmp = "INVERSION_ON";
						break;
					case INVERSION_OFF:
						tmp = "INVERSION_OFF";
						break;
					default:
						break;
				}
				if (tmp)
					PutToDict(ret, "inversion", tmp);

				switch(m_type)
				{
					case feSatellite:
						fillDictWithSatelliteData(ret, original?parm:front, this);
						break;
					case feCable:
						fillDictWithCableData(ret, original?parm:front);
						break;
					case feTerrestrial:
						fillDictWithTerrestrialData(ret, original?parm:front);
						break;
				}
			}
		}
	}
	else
	{
		Py_INCREF(Py_None);
		ret = Py_None;
	}
	return ret;
}

#ifndef FP_IOCTL_GET_ID
#define FP_IOCTL_GET_ID 0
#endif
int eDVBFrontend::readInputpower()
{
	int power=m_fe;  // this is needed for read inputpower from the correct tuner !

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

	return power;
}

bool eDVBFrontend::setSecSequencePos(int steps)
{
	eDebug("set sequence pos %d", steps);
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

void eDVBFrontend::tuneLoop()  // called by m_tuneTimer
{
	int delay=0;
	if ( m_sec_sequence && m_sec_sequence.current() != m_sec_sequence.end() )
	{
//		eDebug("tuneLoop %d\n", m_sec_sequence.current()->cmd);
		switch (m_sec_sequence.current()->cmd)
		{
			case eSecCommand::SLEEP:
				delay = m_sec_sequence.current()++->msec;
				eDebug("[SEC] sleep %dms", delay);
				break;
			case eSecCommand::GOTO:
				if ( !setSecSequencePos(m_sec_sequence.current()->steps) )
					++m_sec_sequence.current();
				break;
			case eSecCommand::SET_VOLTAGE:
			{
				int voltage = m_sec_sequence.current()++->voltage;
				eDebug("[SEC] setVoltage %d", voltage);
				setVoltage(voltage);
				break;
			}
			case eSecCommand::IF_VOLTAGE_GOTO:
			{
				eSecCommand::pair &compare = m_sec_sequence.current()->compare;
				if ( compare.voltage == m_curVoltage && setSecSequencePos(compare.steps) )
					break;
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::IF_NOT_VOLTAGE_GOTO:
			{
				eSecCommand::pair &compare = m_sec_sequence.current()->compare;
				if ( compare.voltage != m_curVoltage && setSecSequencePos(compare.steps) )
					break;
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::SET_TONE:
				eDebug("[SEC] setTone %d", m_sec_sequence.current()->tone);
				setTone(m_sec_sequence.current()++->tone);
				break;
			case eSecCommand::SEND_DISEQC:
				sendDiseqc(m_sec_sequence.current()->diseqc);
				eDebugNoNewLine("[SEC] sendDiseqc: ");
				for (int i=0; i < m_sec_sequence.current()->diseqc.len; ++i)
				    eDebugNoNewLine("%02x", m_sec_sequence.current()->diseqc.data[i]);
				eDebug("");
				++m_sec_sequence.current();
				break;
			case eSecCommand::SEND_TONEBURST:
				eDebug("[SEC] sendToneburst: %d", m_sec_sequence.current()->toneburst);
				sendToneburst(m_sec_sequence.current()++->toneburst);
				break;
			case eSecCommand::SET_FRONTEND:
				eDebug("[SEC] setFrontend");
				setFrontend();
				++m_sec_sequence.current();
				break;
			case eSecCommand::START_TUNE_TIMEOUT:
				m_timeout->start(5000, 1); // 5 sec timeout. TODO: symbolrate dependent
				++m_sec_sequence.current();
				break;
			case eSecCommand::SET_TIMEOUT:
				m_timeoutCount = m_sec_sequence.current()++->val;
				eDebug("[SEC] set timeout %d", m_timeoutCount);
				break;
			case eSecCommand::IF_TIMEOUT_GOTO:
				if (!m_timeoutCount)
				{
					eDebug("[SEC] rotor timout");
					m_sec->setRotorMoving(false);
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
					m_idleInputpower[idx] = readInputpower();
					eDebug("[SEC] idleInputpower[%d] is %d", idx, m_idleInputpower[idx]);
				}
				else
					eDebug("[SEC] idleInputpower measure index(%d) out of bound !!!", idx);
				break;
			}
			case eSecCommand::IF_MEASURE_IDLE_WAS_NOT_OK_GOTO:
			{
				eSecCommand::pair &compare = m_sec_sequence.current()->compare;
				int idx = compare.voltage;
				if ( idx == 0 || idx == 1 )
				{
					int idle = readInputpower();
					int diff = abs(idle-m_idleInputpower[idx]);
					if ( diff > 0)
					{
						eDebug("measure idle(%d) was not okay.. (%d - %d = %d) retry", idx, m_idleInputpower[idx], idle, diff);
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
				if (readFrontendData(locked))
				{
					eDebug("[SEC] locked step %d ok", cmd.okcount);
					++cmd.okcount;
					if (cmd.okcount > 12)
					{
						eDebug("ok > 12 .. goto %d\n",m_sec_sequence.current()->steps);
						setSecSequencePos(cmd.steps);
						break;
					}
				}
				else
				{
					eDebug("[SEC] rotor locked step %d failed", cmd.okcount);
					--m_timeoutCount;
					if (!m_timeoutCount && m_retryCount > 0)
						--m_retryCount;
					cmd.okcount=0;
				}
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::MEASURE_RUNNING_INPUTPOWER:
				m_runningInputpower = readInputpower();
				eDebug("[SEC] runningInputpower is %d", m_runningInputpower);
				++m_sec_sequence.current();
				break;
			case eSecCommand::IF_INPUTPOWER_DELTA_GOTO:
			{
				int idleInputpower = m_idleInputpower[ (m_curVoltage&1) ? 0 : 1];
				eSecCommand::rotor &cmd = m_sec_sequence.current()->measure;
				const char *txt = cmd.direction ? "running" : "stopped";
				eDebug("[SEC] waiting for rotor %s %d, idle %d, delta %d",
					txt,
					m_runningInputpower,
					idleInputpower,
					cmd.deltaA);
				if ( (cmd.direction && abs(m_runningInputpower - idleInputpower) >= cmd.deltaA)
					|| (!cmd.direction && abs(m_runningInputpower - idleInputpower) <= cmd.deltaA) )
				{
					++cmd.okcount;
					eDebug("[SEC] rotor %s step %d ok", txt, cmd.okcount);
					if ( cmd.okcount > 6 )
					{
						m_sec->setRotorMoving(cmd.direction);
						eDebug("[SEC] rotor is %s", txt);
						if (setSecSequencePos(cmd.steps))
							break;
					}
				}
				else
				{
					eDebug("[SEC] rotor not %s... reset counter.. increase timeout", txt);
					--m_timeoutCount;
					if (!m_timeoutCount && m_retryCount > 0)
						--m_retryCount;
					cmd.okcount=0;
				}
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::IF_ROTORPOS_VALID_GOTO:
				if (m_data[ROTOR_CMD] != -1 && m_data[ROTOR_POS] != -1)
					setSecSequencePos(m_sec_sequence.current()->steps);
				else
					++m_sec_sequence.current();
				break;
			case eSecCommand::INVALIDATE_CURRENT_ROTORPARMS:
				m_data[ROTOR_CMD] = m_data[ROTOR_POS] = -1;
				eDebug("[SEC] invalidate current rotorparams");
				++m_sec_sequence.current();
				break;
			case eSecCommand::UPDATE_CURRENT_ROTORPARAMS:
				m_data[ROTOR_CMD] = m_data[NEW_ROTOR_CMD];
				m_data[ROTOR_POS] = m_data[NEW_ROTOR_POS];
				eDebug("[SEC] update current rotorparams %d %04x %d", m_timeoutCount, m_data[5], m_data[6]);
				++m_sec_sequence.current();
				break;
			case eSecCommand::SET_ROTOR_DISEQC_RETRYS:
				m_retryCount = m_sec_sequence.current()++->val;
				eDebug("[SEC] set rotor retries %d", m_retryCount);
				break;
			case eSecCommand::IF_NO_MORE_ROTOR_DISEQC_RETRYS_GOTO:
				if (!m_retryCount)
				{
					eDebug("[SEC] no more rotor retrys");
					setSecSequencePos(m_sec_sequence.current()->steps);
				}
				else
					++m_sec_sequence.current();
				break;
			case eSecCommand::SET_POWER_LIMITING_MODE:
			{
				int fd = m_fe ?
					::open("/dev/i2c/1", O_RDWR) :
					::open("/dev/i2c/0", O_RDWR);

				unsigned char data[2];
				::ioctl(fd, I2C_SLAVE_FORCE, 0x10 >> 1);
				if(::read(fd, data, 1) != 1)
					eDebug("[SEC] error read lnbp (%m)");
				if ( m_sec_sequence.current()->mode == eSecCommand::modeStatic )
				{
					data[0] |= 0x80;  // enable static current limiting
					eDebug("[SEC] set static current limiting");
				}
				else
				{
					data[0] &= ~0x80;  // enable dynamic current limiting
					eDebug("[SEC] set dynamic current limiting");
				}
				if(::write(fd, data, 1) != 1)
					eDebug("[SEC] error write lnbp (%m)");
				::close(fd);
				++m_sec_sequence.current();
				break;
			}
			default:
				++m_sec_sequence.current();
				eDebug("[SEC] unhandled sec command");
		}
		m_tuneTimer->start(delay,true);
	}
}

void eDVBFrontend::setFrontend()
{
	eDebug("setting frontend %d", m_fe);
	m_sn->start();
	feEvent(-1);
	if (ioctl(m_fd, FE_SET_FRONTEND, &parm) == -1)
	{
		perror("FE_SET_FRONTEND failed");
		return;
	}
}

RESULT eDVBFrontend::getFrontendType(int &t)
{
	if (m_type == -1)
		return -ENODEV;
	t = m_type;
	return 0;
}

RESULT eDVBFrontend::prepare_sat(const eDVBFrontendParametersSatellite &feparm)
{
	int res;
	if (!m_sec)
	{
		eWarning("no SEC module active!");
		return -ENOENT;
	}
	res = m_sec->prepare(*this, parm, feparm, 1 << m_fe);
	if (!res)
	{
		eDebug("prepare_sat System %d Freq %d Pol %d SR %d INV %d FEC %d",
			feparm.system,
			feparm.frequency,
			feparm.polarisation,
			feparm.symbol_rate,
			feparm.inversion,
			feparm.fec);
		parm_u_qpsk_symbol_rate = feparm.symbol_rate;
		switch (feparm.inversion)
		{
			case eDVBFrontendParametersSatellite::Inversion::On:
				parm_inversion = INVERSION_ON;
				break;
			case eDVBFrontendParametersSatellite::Inversion::Off:
				parm_inversion = INVERSION_OFF;
				break;
			default:
			case eDVBFrontendParametersSatellite::Inversion::Unknown:
				parm_inversion = INVERSION_AUTO;
				break;
		}
		if (feparm.system == eDVBFrontendParametersSatellite::System::DVB_S)
			switch (feparm.fec)
			{
				case eDVBFrontendParametersSatellite::FEC::fNone:
					parm_u_qpsk_fec_inner = FEC_NONE;
					break;
				case eDVBFrontendParametersSatellite::FEC::f1_2:
					parm_u_qpsk_fec_inner = FEC_1_2;
					break;
				case eDVBFrontendParametersSatellite::FEC::f2_3:
					parm_u_qpsk_fec_inner = FEC_2_3;
					break;
				case eDVBFrontendParametersSatellite::FEC::f3_4:
					parm_u_qpsk_fec_inner = FEC_3_4;
					break;
				case eDVBFrontendParametersSatellite::FEC::f5_6:
					parm_u_qpsk_fec_inner = FEC_5_6;
					break;
				case eDVBFrontendParametersSatellite::FEC::f7_8:
					parm_u_qpsk_fec_inner = FEC_7_8;
					break;
				default:
					eDebug("no valid fec for DVB-S set.. assume auto");
				case eDVBFrontendParametersSatellite::FEC::fAuto:
					parm_u_qpsk_fec_inner = FEC_AUTO;
					break;
			}
#if HAVE_DVB_API_VERSION >= 3
		else // DVB_S2
			switch (feparm.fec)
			{
				case eDVBFrontendParametersSatellite::FEC::f1_2:
					parm_u_qpsk_fec_inner = FEC_S2_1_2;
					break;
				case eDVBFrontendParametersSatellite::FEC::f2_3:
					parm_u_qpsk_fec_inner = FEC_S2_2_3;
					break;
				case eDVBFrontendParametersSatellite::FEC::f3_4:
					parm_u_qpsk_fec_inner = FEC_S2_3_4;
					break;
				case eDVBFrontendParametersSatellite::FEC::f3_5:
					parm_u_qpsk_fec_inner = FEC_S2_3_5;
					break;
				case eDVBFrontendParametersSatellite::FEC::f4_5:
					parm_u_qpsk_fec_inner = FEC_S2_4_5;
					break;
				case eDVBFrontendParametersSatellite::FEC::f5_6:
					parm_u_qpsk_fec_inner = FEC_S2_5_6;
					break;
				case eDVBFrontendParametersSatellite::FEC::f7_8:
					parm_u_qpsk_fec_inner = FEC_S2_7_8;
					break;
				case eDVBFrontendParametersSatellite::FEC::f8_9:
					parm_u_qpsk_fec_inner = FEC_S2_8_9;
					break;
				case eDVBFrontendParametersSatellite::FEC::f9_10:
					parm_u_qpsk_fec_inner = FEC_S2_9_10;
					break;
				default:
					eDebug("no valid fec for DVB-S2 set.. abort !!");
					return -EINVAL;
			}
#endif
		// FIXME !!! get frequency range from tuner
		if ( parm_frequency < 900000 || parm_frequency > 2200000 )
		{
			eDebug("%d mhz out of tuner range.. dont tune", parm_frequency/1000);
			return -EINVAL;
		}
		eDebug("tuning to %d mhz", parm_frequency/1000);
	}
	return res;
}

RESULT eDVBFrontend::prepare_cable(const eDVBFrontendParametersCable &feparm)
{
	parm_frequency = feparm.frequency * 1000;
	parm_u_qam_symbol_rate = feparm.symbol_rate;
	switch (feparm.modulation)
	{
	case eDVBFrontendParametersCable::Modulation::QAM16:
		parm_u_qam_modulation = QAM_16;
		break;
	case eDVBFrontendParametersCable::Modulation::QAM32:
		parm_u_qam_modulation = QAM_32;
		break;
	case eDVBFrontendParametersCable::Modulation::QAM64:
		parm_u_qam_modulation = QAM_64;
		break;
	case eDVBFrontendParametersCable::Modulation::QAM128:
		parm_u_qam_modulation = QAM_128;
		break;
	case eDVBFrontendParametersCable::Modulation::QAM256:
		parm_u_qam_modulation = QAM_256;
		break;
	default:
	case eDVBFrontendParametersCable::Modulation::Auto:
		parm_u_qam_modulation = QAM_AUTO;
		break;
	}
	switch (feparm.inversion)
	{
	case eDVBFrontendParametersCable::Inversion::On:
		parm_inversion = INVERSION_ON;
		break;
	case eDVBFrontendParametersCable::Inversion::Off:
		parm_inversion = INVERSION_OFF;
		break;
	default:
	case eDVBFrontendParametersCable::Inversion::Unknown:
		parm_inversion = INVERSION_AUTO;
		break;
	}
	switch (feparm.fec_inner)
	{
	case eDVBFrontendParametersCable::FEC::fNone:
		parm_u_qam_fec_inner = FEC_NONE;
		break;
	case eDVBFrontendParametersCable::FEC::f1_2:
		parm_u_qam_fec_inner = FEC_1_2;
		break;
	case eDVBFrontendParametersCable::FEC::f2_3:
		parm_u_qam_fec_inner = FEC_2_3;
		break;
	case eDVBFrontendParametersCable::FEC::f3_4:
		parm_u_qam_fec_inner = FEC_3_4;
		break;
	case eDVBFrontendParametersCable::FEC::f5_6:
		parm_u_qam_fec_inner = FEC_5_6;
		break;
	case eDVBFrontendParametersCable::FEC::f7_8:
		parm_u_qam_fec_inner = FEC_7_8;
		break;
#if HAVE_DVB_API_VERSION >= 3
	case eDVBFrontendParametersCable::FEC::f8_9:
		parm_u_qam_fec_inner = FEC_8_9;
		break;
#endif
	default:
	case eDVBFrontendParametersCable::FEC::fAuto:
		parm_u_qam_fec_inner = FEC_AUTO;
		break;
	}
	return 0;
}

RESULT eDVBFrontend::prepare_terrestrial(const eDVBFrontendParametersTerrestrial &feparm)
{
	parm_frequency = feparm.frequency;

	switch (feparm.bandwidth)
	{
	case eDVBFrontendParametersTerrestrial::Bandwidth::Bw8MHz:
		parm_u_ofdm_bandwidth = BANDWIDTH_8_MHZ;
		break;
	case eDVBFrontendParametersTerrestrial::Bandwidth::Bw7MHz:
		parm_u_ofdm_bandwidth = BANDWIDTH_7_MHZ;
		break;
	case eDVBFrontendParametersTerrestrial::Bandwidth::Bw6MHz:
		parm_u_ofdm_bandwidth = BANDWIDTH_6_MHZ;
		break;
	default:
	case eDVBFrontendParametersTerrestrial::Bandwidth::BwAuto:
		parm_u_ofdm_bandwidth = BANDWIDTH_AUTO;
		break;
	}
	switch (feparm.code_rate_LP)
	{
	case eDVBFrontendParametersTerrestrial::FEC::f1_2:
		parm_u_ofdm_code_rate_LP = FEC_1_2;
		break;
	case eDVBFrontendParametersTerrestrial::FEC::f2_3:
		parm_u_ofdm_code_rate_LP = FEC_2_3;
		break;
	case eDVBFrontendParametersTerrestrial::FEC::f3_4:
		parm_u_ofdm_code_rate_LP = FEC_3_4;
		break;
	case eDVBFrontendParametersTerrestrial::FEC::f5_6:
		parm_u_ofdm_code_rate_LP = FEC_5_6;
		break;
	case eDVBFrontendParametersTerrestrial::FEC::f7_8:
		parm_u_ofdm_code_rate_LP = FEC_7_8;
		break;
	default:
	case eDVBFrontendParametersTerrestrial::FEC::fAuto:
		parm_u_ofdm_code_rate_LP = FEC_AUTO;
		break;
	}
	switch (feparm.code_rate_HP)
	{
	case eDVBFrontendParametersTerrestrial::FEC::f1_2:
		parm_u_ofdm_code_rate_HP = FEC_1_2;
		break;
	case eDVBFrontendParametersTerrestrial::FEC::f2_3:
		parm_u_ofdm_code_rate_HP = FEC_2_3;
		break;
	case eDVBFrontendParametersTerrestrial::FEC::f3_4:
		parm_u_ofdm_code_rate_HP = FEC_3_4;
		break;
	case eDVBFrontendParametersTerrestrial::FEC::f5_6:
		parm_u_ofdm_code_rate_HP = FEC_5_6;
		break;
	case eDVBFrontendParametersTerrestrial::FEC::f7_8:
		parm_u_ofdm_code_rate_HP = FEC_7_8;
		break;
	default:
	case eDVBFrontendParametersTerrestrial::FEC::fAuto:
		parm_u_ofdm_code_rate_HP = FEC_AUTO;
		break;
	}
	switch (feparm.modulation)
	{
	case eDVBFrontendParametersTerrestrial::Modulation::QPSK:
		parm_u_ofdm_constellation = QPSK;
		break;
	case eDVBFrontendParametersTerrestrial::Modulation::QAM16:
		parm_u_ofdm_constellation = QAM_16;
		break;
	case eDVBFrontendParametersTerrestrial::Modulation::QAM64:
		parm_u_ofdm_constellation = QAM_64;
		break;
	default:
	case eDVBFrontendParametersTerrestrial::Modulation::Auto:
		parm_u_ofdm_constellation = QAM_AUTO;
		break;
	}
	switch (feparm.transmission_mode)
	{
	case eDVBFrontendParametersTerrestrial::TransmissionMode::TM2k:
		parm_u_ofdm_transmission_mode = TRANSMISSION_MODE_2K;
		break;
	case eDVBFrontendParametersTerrestrial::TransmissionMode::TM8k:
		parm_u_ofdm_transmission_mode = TRANSMISSION_MODE_8K;
		break;
	default:
	case eDVBFrontendParametersTerrestrial::TransmissionMode::TMAuto:
		parm_u_ofdm_transmission_mode = TRANSMISSION_MODE_AUTO;
		break;
	}
	switch (feparm.guard_interval)
	{
		case eDVBFrontendParametersTerrestrial::GuardInterval::GI_1_32:
			parm_u_ofdm_guard_interval = GUARD_INTERVAL_1_32;
			break;
		case eDVBFrontendParametersTerrestrial::GuardInterval::GI_1_16:
			parm_u_ofdm_guard_interval = GUARD_INTERVAL_1_16;
			break;
		case eDVBFrontendParametersTerrestrial::GuardInterval::GI_1_8:
			parm_u_ofdm_guard_interval = GUARD_INTERVAL_1_8;
			break;
		case eDVBFrontendParametersTerrestrial::GuardInterval::GI_1_4:
			parm_u_ofdm_guard_interval = GUARD_INTERVAL_1_4;
			break;
		default:
		case eDVBFrontendParametersTerrestrial::GuardInterval::GI_Auto:
			parm_u_ofdm_guard_interval = GUARD_INTERVAL_AUTO;
			break;
	}
	switch (feparm.hierarchy)
	{
		case eDVBFrontendParametersTerrestrial::Hierarchy::HNone:
			parm_u_ofdm_hierarchy_information = HIERARCHY_NONE;
			break;
		case eDVBFrontendParametersTerrestrial::Hierarchy::H1:
			parm_u_ofdm_hierarchy_information = HIERARCHY_1;
			break;
		case eDVBFrontendParametersTerrestrial::Hierarchy::H2:
			parm_u_ofdm_hierarchy_information = HIERARCHY_2;
			break;
		case eDVBFrontendParametersTerrestrial::Hierarchy::H4:
			parm_u_ofdm_hierarchy_information = HIERARCHY_4;
			break;
		default:
		case eDVBFrontendParametersTerrestrial::Hierarchy::HAuto:
			parm_u_ofdm_hierarchy_information = HIERARCHY_AUTO;
			break;
	}
	switch (feparm.inversion)
	{
	case eDVBFrontendParametersTerrestrial::Inversion::On:
		parm_inversion = INVERSION_ON;
		break;
	case eDVBFrontendParametersTerrestrial::Inversion::Off:
		parm_inversion = INVERSION_OFF;
		break;
	default:
	case eDVBFrontendParametersTerrestrial::Inversion::Unknown:
		parm_inversion = INVERSION_AUTO;
		break;
	}
	return 0;
}

RESULT eDVBFrontend::tune(const iDVBFrontendParameters &where)
{
	eDebug("(%d)tune", m_fe);

	m_timeout->stop();

	int res=0;

	if (m_type == -1)
		return -ENODEV;

	m_sn->stop();
	m_sec_sequence.clear();

	switch (m_type)
	{
	case feSatellite:
	{
		eDVBFrontendParametersSatellite feparm;
		if (where.getDVBS(feparm))
		{
			eDebug("no dvbs data!");
			return -EINVAL;
		}
		res=prepare_sat(feparm);
		m_sec->setRotorMoving(false);
		break;
	}
	case feCable:
	{
		eDVBFrontendParametersCable feparm;
		if (where.getDVBC(feparm))
			return -EINVAL;
		res=prepare_cable(feparm);
		if (!res)
		{
			m_sec_sequence.push_back( eSecCommand(eSecCommand::START_TUNE_TIMEOUT) );
			m_sec_sequence.push_back( eSecCommand(eSecCommand::SET_FRONTEND) );
		}
		break;
	}
	case feTerrestrial:
	{
		eDVBFrontendParametersTerrestrial feparm;
		if (where.getDVBT(feparm))
		{
			eDebug("no -T data");
			return -EINVAL;
		}
		res=prepare_terrestrial(feparm);
		if (!res)
		{
			m_sec_sequence.push_back( eSecCommand(eSecCommand::START_TUNE_TIMEOUT) );
			m_sec_sequence.push_back( eSecCommand(eSecCommand::SET_FRONTEND) );
		}
		break;
	}
	}

	if (!res)  // prepare ok
	{
		m_tuneTimer->start(0,true);
		m_sec_sequence.current() = m_sec_sequence.begin();

		if (m_state != stateTuning)
		{
			m_tuning = 1;
			m_state = stateTuning;
			m_stateChanged(this);
		}
	}

	return res;
}

RESULT eDVBFrontend::connectStateChange(const Slot1<void,iDVBFrontend*> &stateChange, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_stateChanged.connect(stateChange));
	return 0;
}

RESULT eDVBFrontend::setVoltage(int voltage)
{
	if (m_type != feSatellite)
		return -1;
#if HAVE_DVB_API_VERSION < 3
	secVoltage vlt;
#else
	bool increased=false;
	fe_sec_voltage_t vlt;
#endif
	m_curVoltage=voltage;
	switch (voltage)
	{
	case voltageOff:
		for (int i=0; i < 3; ++i)  // reset diseqc
			m_data[i]=-1;
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
#if HAVE_DVB_API_VERSION < 3
	return ::ioctl(m_secfd, SEC_SET_VOLTAGE, vlt);
#else
	if (::ioctl(m_fd, FE_ENABLE_HIGH_LNB_VOLTAGE, increased) < 0)
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

RESULT eDVBFrontend::setSecSequence(const eSecCommandList &list)
{
	m_sec_sequence = list;
	return 0;
}

RESULT eDVBFrontend::getData(int num, int &data)
{
	if ( num < NUM_DATA_ENTRIES )
	{
		data = m_data[num];
		return 0;
	}
	return -EINVAL;
}

RESULT eDVBFrontend::setData(int num, int val)
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
	if (feparm->getSystem(type) || type != m_type)
		return 0;

	if (m_type == eDVBFrontend::feSatellite)
	{
		ASSERT(m_sec);
		eDVBFrontendParametersSatellite sat_parm;
		ASSERT(!feparm->getDVBS(sat_parm));
		return m_sec->canTune(sat_parm, this, 1 << m_fe);
	}
	return 1;
}
