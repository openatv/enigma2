#include <lib/dvb/idvb.h>
#include <lib/base/eerror.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/sec.h>
#include <errno.h>

DEFINE_REF(eDVBResourceManager);

eDVBResourceManager *eDVBResourceManager::instance;

eDVBResourceManager::eDVBResourceManager()
{
	avail = 1;
	busy = 0;
	m_sec = new eDVBSatelliteEquipmentControl;
	if (!instance)
		instance = this;
}

eDVBResourceManager::~eDVBResourceManager()
{
	if (instance == this)
		instance = 0;
}

RESULT eDVBResourceManager::setChannelList(iDVBChannelList *list)
{
	m_list = list;
	return 0;
}

RESULT eDVBResourceManager::getChannelList(ePtr<iDVBChannelList> &list)
{
	list = m_list;
	if (list)
		return 0;
	else
		return -ENOENT;
}


RESULT eDVBResourceManager::allocateChannel(const eDVBChannelID &channelid, ePtr<iDVBChannel> &channel)
{
	RESULT res;
	eDVBChannel *ch;
	channel = ch = new eDVBChannel(this, 0, 0, 0);

	ePtr<iDVBFrontend> fe;
	if (!channel->getFrontend(fe))
		fe->setSEC(m_sec);

	res = ch->setChannel(channelid);
	if (res)
	{
		channel = 0;
		return res;
	}
	return 0;
}

RESULT eDVBResourceManager::allocateRawChannel(ePtr<iDVBChannel> &channel)
{
	channel = new eDVBChannel(this, 0, 0, 0);
	ePtr<iDVBFrontend> fe;
	if (!channel->getFrontend(fe))
		fe->setSEC(m_sec);
	
	return 0;
}

RESULT eDVBResourceManager::allocatePVRChannel(int caps)
{
	return -1; // will nicht, mag nicht, und das interface ist auch kaputt
}

RESULT eDVBResourceManager::addChannel(const eDVBChannelID &chid, eDVBChannel *ch)
{
	eDebug("add channel %p", ch);
	m_active_channels.insert(std::pair<eDVBChannelID,eDVBChannel*>(chid, ch));
	return 0;
}

RESULT eDVBResourceManager::removeChannel(const eDVBChannelID &chid, eDVBChannel *)
{
	int cnt = m_active_channels.erase(chid);
	eDebug("remove channel: removed %d channels", cnt);
	ASSERT(cnt <= 1);
	if (cnt == 1)
		return 0;
	return -ENOENT;
}

DEFINE_REF(eDVBChannel);

eDVBChannel::eDVBChannel(eDVBResourceManager *mgr, int adapter, int frontend, int demux): eDVBDemux(adapter, demux), m_state(state_idle), m_mgr(mgr)
{
	if (frontend >= 0)
	{
		int ok;
		m_frontend = new eDVBFrontend(adapter, frontend, ok);
		if (!ok)
		{
			eDebug("warning, frontend failed");
			m_frontend = 0;
			return;
		}
		m_frontend->connectStateChange(slot(*this, &eDVBChannel::frontendStateChanged), m_conn_frontendStateChanged);
	}
}

eDVBChannel::~eDVBChannel()
{
	if (m_channel_id)
		m_mgr->removeChannel(m_channel_id, this);
}

void eDVBChannel::frontendStateChanged(iDVBFrontend*fe)
{
	eDebug("fe state changed!");
	int state, ourstate = 0;
	if (fe->getState(state))
		return;
	
	if (state == iDVBFrontend::stateLock)
	{
		eDebug("OURSTATE: ok");
		ourstate = state_ok;
	} else if (state == iDVBFrontend::stateTuning)
	{
		eDebug("OURSTATE: tuning");
		ourstate = state_tuning;
	} else if (state == iDVBFrontend::stateFailed)
	{
		eDebug("OURSTATE: failed/unavailable");
		ourstate = state_unavailable;
	} else
		eFatal("state unknown");
	
	if (ourstate != m_state)
	{
		m_state = ourstate;
		m_stateChanged(this);
	}
}

RESULT eDVBChannel::setChannel(const eDVBChannelID &channelid)
{
	ePtr<iDVBChannelList> list;
	
	if (m_mgr->getChannelList(list))
	{
		eDebug("no channel list set!");
		return -ENOENT;
	}
	
	eDebug("tuning to chid: ns: %08x tsid %04x onid %04x",
		channelid.dvbnamespace.get(), channelid.transport_stream_id.get(), channelid.original_network_id.get());
		

	ePtr<iDVBFrontendParameters> feparm;
	if (list->getChannelFrontendData(channelid, feparm))
	{
		eDebug("channel not found!");
		return -ENOENT;
	}
	eDebug("allocateChannel: channel found..");
	
	if (!m_frontend)
	{
		eDebug("no frontend to tune!");
		return -ENODEV;
	}
	
	if (m_channel_id)
		m_mgr->removeChannel(m_channel_id, this);
	m_channel_id = channelid;
	m_mgr->addChannel(m_channel_id, this);
	m_state = state_tuning;
	eDebug("%p", &*feparm);
	return m_frontend->tune(*feparm);
}

RESULT eDVBChannel::connectStateChange(const Slot1<void,iDVBChannel*> &stateChange, ePtr<eConnection> &connection)
{
	connection = new eConnection((iDVBChannel*)this, m_stateChanged.connect(stateChange));
	return 0;
}

RESULT eDVBChannel::getState(int &state)
{
	state = m_state;
	return 0;
}

RESULT eDVBChannel::setCIRouting(const eDVBCIRouting &routing)
{
	return -1;
}

RESULT eDVBChannel::getDemux(ePtr<iDVBDemux> &demux)
{
	demux = this;
	return 0;
}

RESULT eDVBChannel::getFrontend(ePtr<iDVBFrontend> &frontend)
{
	frontend = m_frontend;
	if (frontend)
		return 0;
	else
		return -ENODEV;
}
