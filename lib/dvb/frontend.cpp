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
#define constellation Constellation
#define guard_interval guardInterval
#define hierarchy_information HierarchyInformation
#define code_rate_HP HP_CodeRate
#define code_rate_LP LP_CodeRate
#define parm.frequency parm.Frequency
#define parm.u.qam.symbol_rate parm.u.qam.SymbolRate
#define parm.u.qam.fec_inner parm.u.qam.FEC_inner
#define parm.u.qam.modulation parm.u.qam.MOD
#define parm.u.ofdm.bandwidth parm.u.ofdm.bandWidth
#define parm.u.ofdm.code_rate_LP parm.u.ofdm.LP_CodeRate
#define parm.u.ofdm.code_rate_HP parm.u.ofdm.HP_CodeRate
#define parm.u.ofdm.constellation parm.u.ofdm.Constellation
#define parm.u.ofdm.transmission_mode parm.u.ofdm.TransmissionMode
#define parm.u.ofdm.guard_interval parm.u.ofdm.guardInterval
#define parm.u.ofdm.hierarchy_information parm.u.ofdm.HierarchyInformation
#define parm.inversion parm.Inversion
#else
#include <linux/dvb/frontend.h>
#endif

#include <dvbsi++/satellite_delivery_system_descriptor.h>
#include <dvbsi++/cable_delivery_system_descriptor.h>
#include <dvbsi++/terrestrial_delivery_system_descriptor.h>

void eDVBFrontendParametersSatellite::set(const SatelliteDeliverySystemDescriptor &descriptor)
{
	frequency    = descriptor.getFrequency() * 10;
	symbol_rate  = descriptor.getSymbolRate() * 100;
	polarisation = descriptor.getPolarization();
	fec = descriptor.getFecInner();
	if ( fec == 0xF )
		fec = FEC::fNone;
	inversion = Inversion::Unknown;
	orbital_position  = ((descriptor.getOrbitalPosition() >> 12) & 0xF) * 1000;
	orbital_position += ((descriptor.getOrbitalPosition() >> 8) & 0xF) * 100;
	orbital_position += ((descriptor.getOrbitalPosition() >> 4) & 0xF) * 10;
	orbital_position += ((descriptor.getOrbitalPosition()) & 0xF);
	if (orbital_position && (!descriptor.getWestEastFlag()))
		orbital_position = 3600 - orbital_position;
}

void eDVBFrontendParametersCable::set(const CableDeliverySystemDescriptor &descriptor)
{
	frequency = descriptor.getFrequency() * 10;
	symbol_rate = descriptor.getSymbolRate() * 100;
	fec_inner = descriptor.getFecInner();
	if ( fec_inner == 0xF )
		fec_inner = FEC::fNone;
	modulation = descriptor.getModulation();
	if ( modulation > 0x5 )
		modulation = Modulation::Auto;
	inversion = Inversion::Unknown;
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
	if (transmission_mode > 2)
		transmission_mode = TransmissionMode::TMAuto;
	guard_interval = descriptor.getGuardInterval();
	if (guard_interval > 3)
		guard_interval = GuardInterval::GI_Auto;
	hierarchy = descriptor.getHierarchyInformation()&3;
	modulation = descriptor.getConstellation();
	if (modulation > 2)
		modulation = Modulation::Auto;
	inversion = Inversion::Unknown;
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

RESULT eDVBFrontendParameters::setDVBS(const eDVBFrontendParametersSatellite &p)
{
	sat = p;
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
	case iDVBFrontend::feTerrestrial:
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
	case iDVBFrontend::feTerrestrial:
	default:
		return -1;
	}
}

DEFINE_REF(eDVBFrontend);

eDVBFrontend::eDVBFrontend(int adap, int fe, int &ok)
	:m_type(-1), m_fe(fe), m_fd(-1), m_timeout(0), m_tuneTimer(0)
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

	int entries = sizeof(m_data) / sizeof(int);
	for (int i=0; i<entries; ++i)
		m_data[i] = -1;

	m_idleInputpower[0]=m_idleInputpower[1]=0;

	ok = !openFrontend();
	closeFrontend();
}

int eDVBFrontend::openFrontend()
{
	if (m_fd >= 0)
		return -1;  // already opened

	m_state=0;
	m_tuning=0;

#if HAVE_DVB_API_VERSION < 3
	m_secfd = ::open(m_sec_filename, O_RDWR);
	if (m_secfd < 0)
	{
		eWarning("failed! (%s) %m", m_sec_filename);
		return -1;
	}
	FrontendInfo fe_info;
#else
	dvb_frontend_info fe_info;
#endif
	eDebug("opening frontend %d", m_fe);
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
	m_sn->start();

	return 0;
}

int eDVBFrontend::closeFrontend()
{
	if (!m_fe && m_data[7] != -1)
	{
		// try to close the first frontend.. but the second is linked to the first
		eDVBRegisteredFrontend *linked_fe = (eDVBRegisteredFrontend*)m_data[7];
		if (linked_fe->m_inuse)
		{
			eDebug("dont close frontend %d until the linked frontend %d is still in use",
				m_fe, linked_fe->m_frontend->getID());
			return -1;
		}
	}
	if (m_fd >= 0)
	{
		eDebug("close frontend %d", m_fe);
		setTone(iDVBFrontend::toneOff);
		setVoltage(iDVBFrontend::voltageOff);
		::close(m_fd);
		m_fd=-1;
		m_data[0] = m_data[1] = m_data[2] = -1;
	}
#if HAVE_DVB_API_VERSION < 3
	if (m_secfd >= 0)
	{
		::close(m_secfd);
		m_secfd=-1;
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
				m_data[0] = m_data[1] = m_data[2] = -1; // reset diseqc
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
	}
	return 0;
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
				if (m_data[5] != -1 && m_data[6] != -1)
					setSecSequencePos(m_sec_sequence.current()->steps);
				else
					++m_sec_sequence.current();
				break;
			case eSecCommand::INVALIDATE_CURRENT_ROTORPARMS:
				m_data[5] = m_data[6] = -1;
				eDebug("[SEC] invalidate current rotorparams");
				++m_sec_sequence.current();
				break;
			case eSecCommand::UPDATE_CURRENT_ROTORPARAMS:
				m_data[5] = m_data[3];
				m_data[6] = m_data[4];
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
	if (ioctl(m_fd, FE_SET_FRONTEND, &parm) == -1)
	{
		perror("FE_SET_FRONTEND failed");
		return;
	}
	m_timeout->start(5000, 1); // 5 sec timeout. TODO: symbolrate dependent
}

RESULT eDVBFrontend::getFrontendType(int &t)
{
	if (m_type == -1)
		return -ENODEV;
	t = m_type;
	return 0;
}

RESULT eDVBFrontend::tune(const iDVBFrontendParameters &where)
{
	eDebug("(%d)tune", m_fe);

	if (m_type == -1)
		return -ENODEV;

	feEvent(-1);

	m_sec_sequence.clear();

	switch (m_type)
	{
	case feSatellite:
	{
		int res;
		eDVBFrontendParametersSatellite feparm;
		if (where.getDVBS(feparm))
		{
			eDebug("no dvbs data!");
			return -EINVAL;
		}
		if (!m_sec)
		{
			eWarning("no SEC module active!");
			return -ENOENT;
		}
		
		res = m_sec->prepare(*this, parm, feparm, 1 << m_fe);
		if (res)
			return res;
		eDebug("tuning to %d mhz", parm.frequency/1000);
		break;
	}
	case feCable:
	{
		eDVBFrontendParametersCable feparm;
		if (where.getDVBC(feparm))
			return -EINVAL;
		parm.frequency = feparm.frequency * 1000;
		parm.u.qam.symbol_rate = feparm.symbol_rate;
		switch (feparm.modulation)
		{
		case eDVBFrontendParametersCable::Modulation::QAM16:
			parm.u.qam.modulation = QAM_16;
			break;
		case eDVBFrontendParametersCable::Modulation::QAM32:
			parm.u.qam.modulation = QAM_32;
			break;
		case eDVBFrontendParametersCable::Modulation::QAM64:
			parm.u.qam.modulation = QAM_64;
			break;
		case eDVBFrontendParametersCable::Modulation::QAM128:
			parm.u.qam.modulation = QAM_128;
			break;
		case eDVBFrontendParametersCable::Modulation::QAM256:
			parm.u.qam.modulation = QAM_256;
			break;
		default:
		case eDVBFrontendParametersCable::Modulation::Auto:
			parm.u.qam.modulation = QAM_AUTO;
			break;
		}
		switch (feparm.inversion)
		{
		case eDVBFrontendParametersCable::Inversion::On:
			parm.inversion = INVERSION_ON;
			break;
		case eDVBFrontendParametersCable::Inversion::Off:
			parm.inversion = INVERSION_OFF;
			break;
		default:
		case eDVBFrontendParametersCable::Inversion::Unknown:
			parm.inversion = INVERSION_AUTO;
			break;
		}
		switch (feparm.fec_inner)
		{
		case eDVBFrontendParametersCable::FEC::fNone:
			parm.u.qam.fec_inner = FEC_NONE;
			break;
		case eDVBFrontendParametersCable::FEC::f1_2:
			parm.u.qam.fec_inner = FEC_1_2;
			break;
		case eDVBFrontendParametersCable::FEC::f2_3:
			parm.u.qam.fec_inner = FEC_2_3;
			break;
		case eDVBFrontendParametersCable::FEC::f3_4:
			parm.u.qam.fec_inner = FEC_3_4;
			break;
		case eDVBFrontendParametersCable::FEC::f5_6:
			parm.u.qam.fec_inner = FEC_5_6;
			break;
		case eDVBFrontendParametersCable::FEC::f7_8:
			parm.u.qam.fec_inner = FEC_7_8;
			break;
		case eDVBFrontendParametersCable::FEC::f8_9:
			parm.u.qam.fec_inner = FEC_8_9;
			break;
		default:
		case eDVBFrontendParametersCable::FEC::fAuto:
			parm.u.qam.fec_inner = FEC_AUTO;
			break;
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
		parm.frequency = feparm.frequency;

		switch (feparm.bandwidth)
		{
		case eDVBFrontendParametersTerrestrial::Bandwidth::Bw8MHz:
			parm.u.ofdm.bandwidth = BANDWIDTH_8_MHZ;
			break;
		case eDVBFrontendParametersTerrestrial::Bandwidth::Bw7MHz:
			parm.u.ofdm.bandwidth = BANDWIDTH_7_MHZ;
			break;
		case eDVBFrontendParametersTerrestrial::Bandwidth::Bw6MHz:
			parm.u.ofdm.bandwidth = BANDWIDTH_6_MHZ;
			break;
		default:
		case eDVBFrontendParametersTerrestrial::Bandwidth::BwAuto:
			parm.u.ofdm.bandwidth = BANDWIDTH_AUTO;
			break;
		}
		switch (feparm.code_rate_LP)
		{
		case eDVBFrontendParametersCable::FEC::f1_2:
			parm.u.ofdm.code_rate_LP = FEC_1_2;
			break;
		case eDVBFrontendParametersCable::FEC::f2_3:
			parm.u.ofdm.code_rate_LP = FEC_2_3;
			break;
		case eDVBFrontendParametersCable::FEC::f3_4:
			parm.u.ofdm.code_rate_LP = FEC_3_4;
			break;
		case eDVBFrontendParametersCable::FEC::f5_6:
			parm.u.ofdm.code_rate_LP = FEC_5_6;
			break;
		case eDVBFrontendParametersCable::FEC::f7_8:
			parm.u.ofdm.code_rate_LP = FEC_7_8;
			break;
		default:
		case eDVBFrontendParametersCable::FEC::fAuto:
		case eDVBFrontendParametersCable::FEC::fNone:
			parm.u.ofdm.code_rate_LP = FEC_AUTO;
			break;
		}
		switch (feparm.code_rate_HP)
		{
		case eDVBFrontendParametersCable::FEC::f1_2:
			parm.u.ofdm.code_rate_HP = FEC_1_2;
			break;
		case eDVBFrontendParametersCable::FEC::f2_3:
			parm.u.ofdm.code_rate_HP = FEC_2_3;
			break;
		case eDVBFrontendParametersCable::FEC::f3_4:
			parm.u.ofdm.code_rate_HP = FEC_3_4;
			break;
		case eDVBFrontendParametersCable::FEC::f5_6:
			parm.u.ofdm.code_rate_HP = FEC_5_6;
			break;
		case eDVBFrontendParametersCable::FEC::f7_8:
			parm.u.ofdm.code_rate_HP = FEC_7_8;
			break;
		default:
		case eDVBFrontendParametersCable::FEC::fAuto:
		case eDVBFrontendParametersCable::FEC::fNone:
			parm.u.ofdm.code_rate_HP = FEC_AUTO;
			break;
		}
		switch (feparm.modulation)
		{
		case eDVBFrontendParametersTerrestrial::Modulation::QPSK:
			parm.u.ofdm.constellation = QPSK;
			break;
		case eDVBFrontendParametersTerrestrial::Modulation::QAM16:
			parm.u.ofdm.constellation = QAM_16;
			break;
		default:
		case eDVBFrontendParametersTerrestrial::Modulation::Auto:
			parm.u.ofdm.constellation = QAM_AUTO;
			break;
		}
		switch (feparm.transmission_mode)
		{
		case eDVBFrontendParametersTerrestrial::TransmissionMode::TM2k:
			parm.u.ofdm.transmission_mode = TRANSMISSION_MODE_2K;
			break;
		case eDVBFrontendParametersTerrestrial::TransmissionMode::TM8k:
			parm.u.ofdm.transmission_mode = TRANSMISSION_MODE_8K;
			break;
		default:
		case eDVBFrontendParametersTerrestrial::TransmissionMode::TMAuto:
			parm.u.ofdm.transmission_mode = TRANSMISSION_MODE_AUTO;
			break;
		}
		switch (feparm.guard_interval)
		{
			case eDVBFrontendParametersTerrestrial::GuardInterval::GI_1_32:
				parm.u.ofdm.guard_interval = GUARD_INTERVAL_1_32;
				break;
			case eDVBFrontendParametersTerrestrial::GuardInterval::GI_1_16:
				parm.u.ofdm.guard_interval = GUARD_INTERVAL_1_16;
				break;
			case eDVBFrontendParametersTerrestrial::GuardInterval::GI_1_8:
				parm.u.ofdm.guard_interval = GUARD_INTERVAL_1_8;
				break;
			case eDVBFrontendParametersTerrestrial::GuardInterval::GI_1_4:
				parm.u.ofdm.guard_interval = GUARD_INTERVAL_1_4;
				break;
			default:
			case eDVBFrontendParametersTerrestrial::GuardInterval::GI_Auto:
				parm.u.ofdm.guard_interval = GUARD_INTERVAL_AUTO;
				break;
		}
		switch (feparm.hierarchy)
		{
			case eDVBFrontendParametersTerrestrial::Hierarchy::H1:
				parm.u.ofdm.hierarchy_information = HIERARCHY_1;
				break;
			case eDVBFrontendParametersTerrestrial::Hierarchy::H2:
				parm.u.ofdm.hierarchy_information = HIERARCHY_2;
				break;
			case eDVBFrontendParametersTerrestrial::Hierarchy::H4:
				parm.u.ofdm.hierarchy_information = HIERARCHY_4;
				break;
			default:
			case eDVBFrontendParametersTerrestrial::Hierarchy::HAuto:
				parm.u.ofdm.hierarchy_information = HIERARCHY_AUTO;
				break;
		}
	}
	}

	m_sec_sequence.push_back( eSecCommand(eSecCommand::SET_FRONTEND) );
	m_tuneTimer->start(0,true);
	m_timeout->stop();
	m_sec_sequence.current() = m_sec_sequence.begin();

	if (m_state != stateTuning)
	{
		m_tuning = 1;
		m_state = stateTuning;
		m_stateChanged(this);
	}

	return 0;
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
	if ( num < (int)(sizeof(m_data)/sizeof(int)) )
	{
		data = m_data[num];
		return 0;
	}
	return -EINVAL;
}

RESULT eDVBFrontend::setData(int num, int val)
{
	if ( num < (int)(sizeof(m_data)/sizeof(int)) )
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
