#include <lib/dvb/dvb.h>
#include <lib/base/eerror.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

#include <linux/dvb/frontend.h>

#include <lib/dvb_si/satellite_delivery_system_descriptor.h>
#include <lib/dvb_si/cable_delivery_system_descriptor.h>
#include <lib/dvb_si/terrestrial_delivery_system_descriptor.h>

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

eDVBFrontendParameters::eDVBFrontendParameters(): ref(0), m_type(-1)
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

RESULT eDVBFrontendParameters::setDVBS(eDVBFrontendParametersSatellite &p)
{
	sat = p;
	m_type = iDVBFrontend::feSatellite;
	return 0;
}

RESULT eDVBFrontendParameters::setDVBC(eDVBFrontendParametersCable &p)
{
	cable = p;
	m_type = iDVBFrontend::feCable;
	return 0;
}

RESULT eDVBFrontendParameters::setDVBT(eDVBFrontendParametersTerrestrial &p)
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
		hash  = sat.frequency & 0xFFFF;
		hash |= sat.orbital_position << 16;
		return 0;
	}
	case iDVBFrontend::feCable:
	case iDVBFrontend::feTerrestrial:
	default:
		return -1;
	}
}

DEFINE_REF(eDVBFrontend);

eDVBFrontend::eDVBFrontend(int adap, int fe, int &ok): ref(0), m_type(-1)
{
	char filename[128];
	int result;
	dvb_frontend_info fe_info;
	
	m_sn = 0;
	m_timeout = 0;
	
	sprintf(filename, "/dev/dvb/adapter%d/frontend%d", adap, fe);
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
	eDebug("detected %s frontend", "satellite\0cable\0    terrestrial"+feSatellite*9);
	ok = 1;

	m_sn = new eSocketNotifier(eApp, m_fd, eSocketNotifier::Read);
	CONNECT(m_sn->activated, eDVBFrontend::feEvent);
	m_sn->start();
	
	m_timeout = new eTimer(eApp);
	CONNECT(m_timeout->timeout, eDVBFrontend::timeout);
	
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
		dvb_frontend_event event;
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
		
		eDebug("fe event: status %x, inversion %s", event.status, (event.parameters.inversion == INVERSION_ON) ? "on" : "off");
		if (event.status & FE_HAS_LOCK)
		{
			state = stateLock;
		} else
		{
			if (m_tuning)
				state = stateTuning;
			else
				state = stateFailed;
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
	} else
		m_tuning = 0;
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
	if (m_type == -1)
		return -ENODEV;

	dvb_frontend_parameters parm;
	
	feEvent(-1);
	
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
		
		res = m_sec->prepare(*this, parm, feparm);
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
		eFatal("cable tuning nyi");
	}
	case feTerrestrial:
	{
		eDVBFrontendParametersTerrestrial feparm;
		if (where.getDVBT(feparm))
			return -EINVAL;
		eFatal("terrestrial tuning nyi");
	}
	}
	
	if (ioctl(m_fd, FE_SET_FRONTEND, &parm) == -1)
	{
		perror("FE_SET_FRONTEND failed");
		return errno;
	}
	
	if (m_state != stateTuning)
	{
		m_tuning = 1;
		m_state = stateTuning;
		m_stateChanged(this);
	}
	
	m_timeout->start(5000, 1); // 5 sec timeout. TODO: symbolrate dependent

	return 0;
}

RESULT eDVBFrontend::connectStateChange(const Slot1<void,iDVBFrontend*> &stateChange, ePtr<eConnection> &connection)
{
	connection = new eConnection(m_stateChanged.connect(stateChange));
	return 0;
}

RESULT eDVBFrontend::setVoltage(int voltage)
{
	fe_sec_voltage_t vlt;
	
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
	if (::ioctl(m_fd, FE_SET_TONE, SEC_TONE_OFF))
		return -EINVAL;
	usleep(15 * 1000);
	memcpy(cmd.msg, diseqc.data, diseqc.len);
	cmd.msg_len = diseqc.len;
	
	if (::ioctl(m_fd, FE_DISEQC_SEND_MASTER_CMD, &cmd))
		return -EINVAL;
	usleep(15 * 1000);
	eDebug("diseqc ok");
	return 0;
}

RESULT eDVBFrontend::setSEC(iDVBSatelliteEquipmentControl *sec)
{
	m_sec = sec;
	return 0;
}
