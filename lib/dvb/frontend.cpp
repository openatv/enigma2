#include <config.h>
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
	switch (descriptor.getPolarization())
	{
	case 0:
		polarisation = Polarisation::Horizontal;
		break;
	case 1:
		polarisation = Polarisation::Vertical;
		break;
	case 2:
		polarisation = Polarisation::CircularLeft;
		break;
	case 3:
		polarisation = Polarisation::CircularRight;
		break;
	}
	switch (descriptor.getFecInner())
	{
	case 1:
		fec = FEC::f1_2;
		break;
	case 2:
		fec = FEC::f2_3;
		break;
	case 3:
		fec = FEC::f3_4;
		break;
	case 4:
		fec = FEC::f5_6;
		break;
	case 5:
		fec = FEC::f7_8;
		break;
	case 0xF:
		fec = FEC::fNone;
		break;
	default:
		fec = FEC::fAuto;
		break;
	}
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
	eFatal("nyi");
}

void eDVBFrontendParametersTerrestrial::set(const TerrestrialDeliverySystemDescriptor  &)
{
	eFatal("nyi");
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
			diff = abs(sat.frequency - osat.frequency);
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

eDVBFrontend::eDVBFrontend(int adap, int fe, int &ok): m_type(-1), m_fe(fe), m_curVoltage(-1)
{
#if HAVE_DVB_API_VERSION < 3
	char sec_filename[128];
#endif
	char filename[128];

	int result;

	m_sn = 0;
	m_timeout = 0;

#if HAVE_DVB_API_VERSION < 3
	sprintf(sec_filename, "/dev/dvb/card%d/sec%d", adap, fe);
	m_secfd = ::open(sec_filename, O_RDWR);
	if (m_secfd < 0)
	{
		eWarning("failed! (%s) %m", sec_filename);
		ok = 0;
		return;
	}
	else
		eDebug("m_secfd is %d", m_secfd);

	FrontendInfo fe_info;
	sprintf(filename, "/dev/dvb/card%d/frontend%d", adap, fe);
#else
	dvb_frontend_info fe_info;	
	sprintf(filename, "/dev/dvb/adapter%d/frontend%d", adap, fe);
#endif
	eDebug("opening frontend.");
	m_fd = ::open(filename, O_RDWR|O_NONBLOCK);
	if (m_fd < 0)
	{
		eWarning("failed! (%s) %m", filename);
		ok = 0;
		return;
	}

	result = ::ioctl(m_fd, FE_GET_INFO, &fe_info);
	
	if (result < 0) {
		eWarning("ioctl FE_GET_INFO failed");
		::close(m_fd);
		m_fd = -1;
		ok = 0;
		return;
	}

	switch (fe_info.type) 
	{
	case FE_QPSK:
		m_type = feSatellite;
		break;
	case FE_QAM:
		m_type = feCable;
		break;
	case FE_OFDM:
		m_type = feTerrestrial;
		break;
	default:
		eWarning("unknown frontend type.");
		::close(m_fd);
		m_fd = -1;
		ok = 0;
		return;
	}
	eDebug("detected %s frontend", "satellite\0cable\0    terrestrial"+fe_info.type*10);
	ok = 1;

	m_sn = new eSocketNotifier(eApp, m_fd, eSocketNotifier::Read);
	CONNECT(m_sn->activated, eDVBFrontend::feEvent);
	m_sn->start();

	m_timeout = new eTimer(eApp);
	CONNECT(m_timeout->timeout, eDVBFrontend::timeout);

	m_tuneTimer = new eTimer(eApp);
	CONNECT(m_tuneTimer->timeout, eDVBFrontend::tuneLoop);

	int entries = sizeof(m_data) / sizeof(int);
	for (int i=0; i<entries; ++i)
		m_data[i] = -1;

	m_data[7] = !m_fe;

	eDebug("m_data[7] = %d %d", m_data[7], m_fe);

	return;
}

eDVBFrontend::~eDVBFrontend()
{
	if (m_fd >= 0)
		::close(m_fd);
	if (m_sn)
		delete m_sn;
	if (m_timeout)
		delete m_timeout;
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

				if (m_state != stateLostLock)
					eDebug("FIXME: we lost lock, so we might have to retune.");
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
	int state;
	if (m_state == stateTuning)
	{
		state = stateFailed;
		eDebug("DVBFrontend: timeout");
		if (m_state != state)
		{
			m_state = state;
			m_stateChanged(this);
		}
		m_tuning = 0;
	} else
		m_tuning = 0;
}

#ifndef FP_IOCTL_GET_ID
#define FP_IOCTL_GET_ID 0
#endif
int eDVBFrontend::readInputpower()
{
	int power=0;
//	if ( eSystemInfo::getInstance()->canMeasureLNBCurrent() )
	{
//		switch ( eSystemInfo::getInstance()->getHwType() )
		{
//			case eSystemInfo::DM7000:
//			case eSystemInfo::DM7020:
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
//				break;
			}
//			default:
//				eDebug("Inputpower read for platform %d not yet implemented", eSystemInfo::getInstance()->getHwType());
		}
	}
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
				int voltage = m_sec_sequence.current()++->voltage;
				eDebug("[SEC] setVoltage %d", voltage);
				setVoltage(voltage);
				break;
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
			case eSecCommand::MEASURE_RUNNING_INPUTPOWER:
				m_runningInputpower = readInputpower();
				eDebug("[SEC] runningInputpower is %d", m_runningInputpower);
				++m_sec_sequence.current();
				break;
			case eSecCommand::SET_TIMEOUT:
				m_timeoutCount = m_sec_sequence.current()++->val;
				eDebug("[SEC] set timeout %d", m_timeoutCount);
				break;
			case eSecCommand::UPDATE_CURRENT_ROTORPARAMS:
				m_data[5] = m_data[3];
				m_data[6] = m_data[4];
				eDebug("[SEC] update current rotorparams %d %04x %d", m_timeoutCount, m_data[5], m_data[6]);
				++m_sec_sequence.current();
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
			case eSecCommand::SET_POWER_LIMITING_MODE:
			{
				int fd=::open("/dev/i2c/0", O_RDWR);
				unsigned char data[2];
				::ioctl(fd, I2C_SLAVE_FORCE, 0x10 >> 1);
				if(::read(fd, data, 1) != 1)
					eDebug("[SEC] error read lnbp (%m)");
				if ( m_sec_sequence.current()->mode == eSecCommand::modeStatic )
				{
					data[0] |= 0x90;  // enable static current limiting
					eDebug("[SEC] set static current limiting");
				}
				else
				{
					data[0] &= ~0x90;  // enable dynamic current limiting
					eDebug("[SEC] set dynamic current limiting");
				}
				if(::write(fd, data, 1) != 1)
					eDebug("[SEC] error write lnbp (%m)");
				::close(fd);
				++m_sec_sequence.current();
				break;
			}
			case eSecCommand::IF_IDLE_INPUTPOWER_AVAIL_GOTO:
				if (m_idleInputpower[0] && m_idleInputpower[1] && setSecSequencePos(m_sec_sequence.current()->steps))
					break;
				++m_sec_sequence.current();
				break;
			case eSecCommand::IF_INPUTPOWER_DELTA_GOTO:
			{
				int idleInputpower = m_idleInputpower[m_curVoltage == iDVBFrontend::voltage13 ? 0 : 1];
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
					cmd.okcount=0;
				}
				++m_sec_sequence.current();
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
			default:
				++m_sec_sequence.current();
				eDebug("[SEC] unhandled sec command");
		}
		m_tuneTimer->start(delay,true);
	}
}

void eDVBFrontend::setFrontend()
{
	eDebug("setting frontend..\n");
	if (ioctl(m_fd, FE_SET_FRONTEND, &parm) == -1)
	{
		perror("FE_SET_FRONTEND failed");
		return;
	}

	if (m_state != stateTuning)
	{
		m_tuning = 1;
		m_state = stateTuning;
		m_stateChanged(this);
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
#if HAVE_DVB_API_VERSION < 3
		eDebug("tuning to %d mhz", parm.Frequency/1000);
#else
		eDebug("tuning to %d mhz", parm.frequency/1000);
#endif
		break;
	}
	case feCable:
	{
#if HAVE_DVB_API_VERSION >= 3
		eDVBFrontendParametersCable feparm;
		if (where.getDVBC(feparm))
			return -EINVAL;
#if HAVE_DVB_API_VERSION < 3
		parm.Frequency = feparm.frequency * 1000;
		parm.u.qam.SymbolRate = feparm.symbol_rate;
#else
		parm.frequency = feparm.frequency * 1000;
		parm.u.qam.symbol_rate = feparm.symbol_rate;
#endif
		fe_modulation_t mod;
		switch (feparm.modulation)
		{
		case eDVBFrontendParametersCable::Modulation::QAM16:
			mod = QAM_16;
			break;
		case eDVBFrontendParametersCable::Modulation::QAM32:
			mod = QAM_32;
			break;
		case eDVBFrontendParametersCable::Modulation::QAM64:
			mod = QAM_64;
			break;
		case eDVBFrontendParametersCable::Modulation::QAM128:
			mod = QAM_128;
			break;
		case eDVBFrontendParametersCable::Modulation::QAM256:
			mod = QAM_256;
			break;			
		case eDVBFrontendParametersCable::Modulation::Auto:
			mod = QAM_AUTO;
			break;			
		}
#if HAVE_DVB_API_VERSION < 3
		parm.u.qam.QAM = mod;
#else
		parm.u.qam.modulation = mod;
#endif
		switch (feparm.inversion)
		{		
		case eDVBFrontendParametersCable::Inversion::On:
			#if HAVE_DVB_API_VERSION < 3
			parm.Inversion =
			#else
			parm.inversion =
			#endif
				INVERSION_ON;
			break;
		case eDVBFrontendParametersCable::Inversion::Off:
			#if HAVE_DVB_API_VERSION < 3
			parm.Inversion =
			#else
			parm.inversion =
			#endif
				INVERSION_OFF;
			break;
		case eDVBFrontendParametersCable::Inversion::Unknown:
			#if HAVE_DVB_API_VERSION < 3
			parm.Inversion =
			#else
			parm.inversion =
			#endif
				INVERSION_AUTO;
			break;
		}
		
		fe_code_rate_t fec_inner;
		switch (feparm.fec_inner)
		{		
		case eDVBFrontendParametersCable::FEC::fNone:
			fec_inner = FEC_NONE;
			break;
		case eDVBFrontendParametersCable::FEC::f1_2:
			fec_inner = FEC_1_2;
			break;
		case eDVBFrontendParametersCable::FEC::f2_3:
			fec_inner = FEC_2_3;
			break;
		case eDVBFrontendParametersCable::FEC::f3_4:
			fec_inner = FEC_3_4;
			break;
		case eDVBFrontendParametersCable::FEC::f4_5:
			fec_inner = FEC_4_5;
			break;
		case eDVBFrontendParametersCable::FEC::f5_6:
			fec_inner = FEC_5_6;
			break;
		case eDVBFrontendParametersCable::FEC::f6_7:
			fec_inner = FEC_6_7;
			break;
		case eDVBFrontendParametersCable::FEC::f7_8:
			fec_inner = FEC_7_8;
			break;
		case eDVBFrontendParametersCable::FEC::f8_9:
			fec_inner = FEC_8_9;
			break;
		case eDVBFrontendParametersCable::FEC::fAuto:
			fec_inner = FEC_AUTO;
			break;
		}
#if HAVE_DVB_API_VERSION < 3
		parm.u.qam.FEC_inner = fec_inner;
#else
		parm.u.qam.fec_inner = fec_inner;
#endif
#else
		eFatal("Old API not fully supported");
#endif // old api
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
#if HAVE_DVB_API_VERSION < 3
		parm.Frequency = feparm.frequency;
#else
		parm.frequency = feparm.frequency;
#endif

		switch (feparm.bandwidth)
		{
		case eDVBFrontendParametersTerrestrial::Bandwidth::Bw8MHz:
#if HAVE_DVB_API_VERSION < 3
			parm.u.ofdm.bandWidth =
#else
			parm.u.ofdm.bandwidth =
#endif
				BANDWIDTH_8_MHZ;
			break;
		case eDVBFrontendParametersTerrestrial::Bandwidth::Bw7MHz:
#if HAVE_DVB_API_VERSION < 3
			parm.u.ofdm.bandWidth =
#else
			parm.u.ofdm.bandwidth =
#endif
				BANDWIDTH_7_MHZ;
			break;
		case eDVBFrontendParametersTerrestrial::Bandwidth::Bw6MHz:
#if HAVE_DVB_API_VERSION < 3
			parm.u.ofdm.bandWidth =
#else
			parm.u.ofdm.bandwidth =
#endif
				BANDWIDTH_6_MHZ;
			break;
		case eDVBFrontendParametersTerrestrial::Bandwidth::BwAuto:
#if HAVE_DVB_API_VERSION < 3
			parm.u.ofdm.bandWidth =
#else
			parm.u.ofdm.bandwidth =
#endif
				BANDWIDTH_AUTO;
			break;
		default:
			eWarning("invalid OFDM bandwith");
			return -EINVAL;
		}
		
		parm.u.ofdm.code_rate_HP = FEC_AUTO;
		parm.u.ofdm.code_rate_LP = FEC_AUTO;
		
		switch (feparm.modulation)
		{
		case eDVBFrontendParametersTerrestrial::Modulation::QPSK:
			parm.u.ofdm.constellation = QPSK;
			break;
		case eDVBFrontendParametersTerrestrial::Modulation::QAM16:
			parm.u.ofdm.constellation = QAM_16;
			break;
		case eDVBFrontendParametersTerrestrial::Modulation::Auto:
			parm.u.ofdm.constellation = QAM_AUTO;
			break;
		}
		
		switch (feparm.transmission_mode)
		{
		case eDVBFrontendParametersTerrestrial::TransmissionMode::TM2k:
#if HAVE_DVB_API_VERSION < 3
			parm.u.ofdm.TransmissionMode =
#else
			parm.u.ofdm.transmission_mode =
#endif
				TRANSMISSION_MODE_2K;
			break;
		case eDVBFrontendParametersTerrestrial::TransmissionMode::TM8k:
#if HAVE_DVB_API_VERSION < 3
			parm.u.ofdm.TransmissionMode =
#else
			parm.u.ofdm.transmission_mode =
#endif
				TRANSMISSION_MODE_8K;
			break;
		case eDVBFrontendParametersTerrestrial::TransmissionMode::TMAuto:
#if HAVE_DVB_API_VERSION < 3
			parm.u.ofdm.TransmissionMode =
#else
			parm.u.ofdm.transmission_mode =
#endif
				TRANSMISSION_MODE_AUTO;
			break;
		}
		
		parm.u.ofdm.guard_interval = GUARD_INTERVAL_AUTO;
		parm.u.ofdm.hierarchy_information = HIERARCHY_AUTO;
#if HAVE_DVB_API_VERSION < 3
		parm.Inversion =
#else
		parm.inversion =
#endif
			INVERSION_AUTO;
		break;
	}
	}

	m_sec_sequence.push_back( eSecCommand(eSecCommand::SET_FRONTEND) );
	m_tuneTimer->start(0,true);
	m_sec_sequence.current() = m_sec_sequence.begin();

	return 0;
}

RESULT eDVBFrontend::connectStateChange(const Slot1<void,iDVBFrontend*> &stateChange, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_stateChanged.connect(stateChange));
	return 0;
}

RESULT eDVBFrontend::setVoltage(int voltage)
{
#if HAVE_DVB_API_VERSION < 3
	secVoltage vlt;
#else
	fe_sec_voltage_t vlt;
#endif

	m_curVoltage=voltage;
	switch (voltage)
	{
	case voltageOff:
		vlt = SEC_VOLTAGE_OFF;
		break;
	case voltage13:
		vlt = SEC_VOLTAGE_13;
		break;
	case voltage18:
		vlt = SEC_VOLTAGE_18;
		break;
	default:
		return -ENODEV;
	}
#if HAVE_DVB_API_VERSION < 3
	return ::ioctl(m_secfd, SEC_SET_VOLTAGE, vlt);
#else
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
	if ( burst == eDVBSatelliteDiseqcParameters::A )
		cmd = SEC_MINI_A;
	else if ( burst == eDVBSatelliteDiseqcParameters::B )
		cmd = SEC_MINI_B;
	if (::ioctl(m_secfd, SEC_DISEQC_SEND_BURST, cmd))
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
		if ( num == 0 )
			eDebug("(%d) set csw %02x", m_fe, val);
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
