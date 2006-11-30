#include <lib/base/eerror.h>
#include <lib/base/filepush.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/sec.h>

#include <errno.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>

DEFINE_REF(eDVBRegisteredFrontend);
DEFINE_REF(eDVBRegisteredDemux);

DEFINE_REF(eDVBAllocatedFrontend);

eDVBAllocatedFrontend::eDVBAllocatedFrontend(eDVBRegisteredFrontend *fe): m_fe(fe)
{
	m_fe->inc_use();
}

eDVBAllocatedFrontend::~eDVBAllocatedFrontend()
{
	m_fe->dec_use();
}

DEFINE_REF(eDVBAllocatedDemux);

eDVBAllocatedDemux::eDVBAllocatedDemux(eDVBRegisteredDemux *demux): m_demux(demux)
{
	m_demux->m_inuse++;
}

eDVBAllocatedDemux::~eDVBAllocatedDemux()
{
	--m_demux->m_inuse;
}

DEFINE_REF(eDVBResourceManager);

eDVBResourceManager *eDVBResourceManager::instance;

RESULT eDVBResourceManager::getInstance(ePtr<eDVBResourceManager> &ptr)
{
	if (instance)
	{
		ptr = instance;
		return 0;
	}
	return -1;
}

eDVBResourceManager::eDVBResourceManager()
	:m_releaseCachedChannelTimer(eApp)
{
	avail = 1;
	busy = 0;
	m_sec = new eDVBSatelliteEquipmentControl(m_frontend);
	if (!instance)
		instance = this;
		
		/* search available adapters... */

		// add linux devices
	
	int num_adapter = 0;
	while (eDVBAdapterLinux::exist(num_adapter))
	{
		addAdapter(new eDVBAdapterLinux(num_adapter));
		num_adapter++;
	}
	
	eDebug("found %d adapter, %d frontends and %d demux", 
		m_adapter.size(), m_frontend.size(), m_demux.size());

	CONNECT(m_releaseCachedChannelTimer.timeout, eDVBResourceManager::releaseCachedChannel);
}

void eDVBResourceManager::feStateChanged()
{
	int mask=0;
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(m_frontend.begin()); i != m_frontend.end(); ++i)
		if (i->m_inuse)
			mask |= ( 1 << i->m_frontend->getID() );
	/* emit */ frontendUseMaskChanged(mask);
}

DEFINE_REF(eDVBAdapterLinux);
eDVBAdapterLinux::eDVBAdapterLinux(int nr): m_nr(nr)
{
		// scan frontends
	int num_fe = 0;
	
	eDebug("scanning for frontends..");
	while (1)
	{
		struct stat s;
		char filename[128];
#if HAVE_DVB_API_VERSION < 3
		sprintf(filename, "/dev/dvb/card%d/frontend%d", m_nr, num_fe);
#else
		sprintf(filename, "/dev/dvb/adapter%d/frontend%d", m_nr, num_fe);
#endif
		if (stat(filename, &s))
			break;
		ePtr<eDVBFrontend> fe;

		int ok = 0;
		fe = new eDVBFrontend(m_nr, num_fe, ok);
		if (ok)
			m_frontend.push_back(fe);
		++num_fe;
	}
	
		// scan demux
	int num_demux = 0;
	while (1)
	{
		struct stat s;
		char filename[128];
#if HAVE_DVB_API_VERSION < 3
		sprintf(filename, "/dev/dvb/card%d/demux%d", m_nr, num_demux);
#else
		sprintf(filename, "/dev/dvb/adapter%d/demux%d", m_nr, num_demux);
#endif
		if (stat(filename, &s))
			break;
		ePtr<eDVBDemux> demux;
		
		demux = new eDVBDemux(m_nr, num_demux);
		m_demux.push_back(demux);
			
		++num_demux;
	}
}

int eDVBAdapterLinux::getNumDemux()
{
	return m_demux.size();
}

RESULT eDVBAdapterLinux::getDemux(ePtr<eDVBDemux> &demux, int nr)
{
	eSmartPtrList<eDVBDemux>::iterator i(m_demux.begin());
	while (nr && (i != m_demux.end()))
	{
		--nr;
		++i;
	}
	
	if (i != m_demux.end())
		demux = *i;
	else
		return -1;
		
	return 0;
}

int eDVBAdapterLinux::getNumFrontends()
{
	return m_frontend.size();
}

RESULT eDVBAdapterLinux::getFrontend(ePtr<eDVBFrontend> &fe, int nr)
{
	eSmartPtrList<eDVBFrontend>::iterator i(m_frontend.begin());
	while (nr && (i != m_frontend.end()))
	{
		--nr;
		++i;
	}
	
	if (i != m_frontend.end())
		fe = *i;
	else
		return -1;
		
	return 0;
}

int eDVBAdapterLinux::exist(int nr)
{
	struct stat s;
	char filename[128];
#if HAVE_DVB_API_VERSION < 3
	sprintf(filename, "/dev/dvb/card%d", nr);
#else
	sprintf(filename, "/dev/dvb/adapter%d", nr);
#endif
	if (!stat(filename, &s))
		return 1;
	return 0;
}

eDVBResourceManager::~eDVBResourceManager()
{
	if (instance == this)
		instance = 0;
}

void eDVBResourceManager::addAdapter(iDVBAdapter *adapter)
{
	int num_fe = adapter->getNumFrontends();
	int num_demux = adapter->getNumDemux();
	
	m_adapter.push_back(adapter);
	
	int i;
	for (i=0; i<num_demux; ++i)
	{
		ePtr<eDVBDemux> demux;
		if (!adapter->getDemux(demux, i))
			m_demux.push_back(new eDVBRegisteredDemux(demux, adapter));
	}

	ePtr<eDVBRegisteredFrontend> prev_dvbt_frontend;
	for (i=0; i<num_fe; ++i)
	{
		ePtr<eDVBFrontend> frontend;
		if (!adapter->getFrontend(frontend, i))
		{
			int frontendType=0;
			frontend->getFrontendType(frontendType);
			eDVBRegisteredFrontend *new_fe = new eDVBRegisteredFrontend(frontend, adapter);
			CONNECT(new_fe->stateChanged, eDVBResourceManager::feStateChanged);
			m_frontend.push_back(new_fe);
			frontend->setSEC(m_sec);
			// we must link all dvb-t frontends ( for active antenna voltage )
			if (frontendType == iDVBFrontend::feTerrestrial)
			{
				if (prev_dvbt_frontend)
				{
					prev_dvbt_frontend->m_frontend->setData(eDVBFrontend::LINKED_NEXT_PTR, (int)new_fe);
					frontend->setData(eDVBFrontend::LINKED_PREV_PTR, (int)&(*prev_dvbt_frontend));
				}
				prev_dvbt_frontend = new_fe;
			}
		}
	}
}

RESULT eDVBResourceManager::allocateFrontend(ePtr<eDVBAllocatedFrontend> &fe, ePtr<iDVBFrontendParameters> &feparm)
{
	ePtr<eDVBRegisteredFrontend> best;
	int bestval = 0;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(m_frontend.begin()); i != m_frontend.end(); ++i)
		if (!i->m_inuse)
		{
			int c = i->m_frontend->isCompatibleWith(feparm);
			if (c > bestval)
			{
				bestval = c;
				best = i;
			}
		}

	if (best)
	{
		fe = new eDVBAllocatedFrontend(best);
		return 0;
	}
	
	fe = 0;
	
	return -1;
}

RESULT eDVBResourceManager::allocateFrontendByIndex(ePtr<eDVBAllocatedFrontend> &fe, int nr)
{
	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(m_frontend.begin()); i != m_frontend.end(); ++i, --nr)
		if ((!nr) && !i->m_inuse)
		{
			fe = new eDVBAllocatedFrontend(i);
			return 0;
		}
	
	fe = 0;
	return -1;
}

RESULT eDVBResourceManager::allocateDemux(eDVBRegisteredFrontend *fe, ePtr<eDVBAllocatedDemux> &demux, int cap)
{
		/* find first unused demux which is on same adapter as frontend (or any, if PVR)
		   never use the first one unless we need a decoding demux. */

	eDebug("allocate demux");
	eSmartPtrList<eDVBRegisteredDemux>::iterator i(m_demux.begin());
	
	if (i == m_demux.end())
		return -1;
		
	int n=0;
		/* FIXME: hardware demux policy */
	if (!(cap & iDVBChannel::capDecode))
	{
		if (m_demux.size() > 2)  /* assumed to be true, otherwise we have lost anyway */
		{
			++i, ++n;
			++i, ++n;
		}
	}
	
	for (; i != m_demux.end(); ++i, ++n)
	{
		int is_decode = n < 2;
		
		int in_use = is_decode ? (i->m_demux->getRefCount() != 2) : i->m_inuse;
		
		if ((!in_use) && ((!fe) || (i->m_adapter == fe->m_adapter)))
		{
			if ((cap & iDVBChannel::capDecode) && !is_decode)
				continue;
			
			demux = new eDVBAllocatedDemux(i);
			if (fe)
				demux->get().setSourceFrontend(fe->m_frontend->getID());
			else
				demux->get().setSourcePVR(0);
			return 0;
		}
	}
	eDebug("demux not found");
	return -1;
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

RESULT eDVBResourceManager::allocateChannel(const eDVBChannelID &channelid, eUsePtr<iDVBChannel> &channel)
{
		/* first, check if a channel is already existing. */

	if (m_cached_channel)
	{
		eDVBChannel *cache_chan = (eDVBChannel*)&(*m_cached_channel);
		if(channelid==cache_chan->getChannelID())
		{
			eDebug("use cached_channel");
			channel = m_cached_channel;
			return 0;
		}
		m_cached_channel_state_changed_conn.disconnect();
		m_cached_channel=0;
		m_releaseCachedChannelTimer.stop();
	}

//	eDebug("allocate channel.. %04x:%04x", channelid.transport_stream_id.get(), channelid.original_network_id.get());
	for (std::list<active_channel>::iterator i(m_active_channels.begin()); i != m_active_channels.end(); ++i)
	{
//		eDebug("available channel.. %04x:%04x", i->m_channel_id.transport_stream_id.get(), i->m_channel_id.original_network_id.get());
		if (i->m_channel_id == channelid)
		{
//			eDebug("found shared channel..");
			channel = i->m_channel;
			return 0;
		}
	}
	
	/* no currently available channel is tuned to this channelid. create a new one, if possible. */

	if (!m_list)
	{
		eDebug("no channel list set!");
		return -ENOENT;
	}

	ePtr<iDVBFrontendParameters> feparm;
	if (m_list->getChannelFrontendData(channelid, feparm))
	{
		eDebug("channel not found!");
		return -ENOENT;
	}

	/* allocate a frontend. */
	
	ePtr<eDVBAllocatedFrontend> fe;
	
	if (allocateFrontend(fe, feparm))
		return errNoFrontend;

	RESULT res;
	ePtr<eDVBChannel> ch;
	ch = new eDVBChannel(this, fe);

	res = ch->setChannel(channelid, feparm);
	if (res)
	{
		channel = 0;
		return errChidNotFound;
	}
	m_cached_channel = channel = ch;
	m_cached_channel_state_changed_conn =
		CONNECT(ch->m_stateChanged,eDVBResourceManager::DVBChannelStateChanged);

	return 0;
}

void eDVBResourceManager::DVBChannelStateChanged(iDVBChannel *chan)
{
	int state=0;
	chan->getState(state);
	switch (state)
	{
		case iDVBChannel::state_release:
		case iDVBChannel::state_ok:
		{
			eDebug("stop release channel timer");
			m_releaseCachedChannelTimer.stop();
			break;
		}
		case iDVBChannel::state_last_instance:
		{
			eDebug("start release channel timer");
			m_releaseCachedChannelTimer.start(3000, true);
			break;
		}
		default: // ignore all other events
			break;
	}
}

void eDVBResourceManager::releaseCachedChannel()
{
	eDebug("release cached channel (timer timeout)");
	m_cached_channel=0;
}

RESULT eDVBResourceManager::allocateRawChannel(eUsePtr<iDVBChannel> &channel, int frontend_index)
{
	ePtr<eDVBAllocatedFrontend> fe;

	if (m_cached_channel)
	{
		m_cached_channel_state_changed_conn.disconnect();
		m_cached_channel=0;
		m_releaseCachedChannelTimer.stop();
	}

	if (allocateFrontendByIndex(fe, frontend_index))
		return errNoFrontend;
	
	eDVBChannel *ch;
	ch = new eDVBChannel(this, fe);

	channel = ch;
	return 0;
}


RESULT eDVBResourceManager::allocatePVRChannel(eUsePtr<iDVBPVRChannel> &channel)
{
	ePtr<eDVBAllocatedDemux> demux;

	if (m_cached_channel && m_releaseCachedChannelTimer.isActive())
	{
		m_cached_channel_state_changed_conn.disconnect();
		m_cached_channel=0;
		m_releaseCachedChannelTimer.stop();
	}

	eDVBChannel *ch;
	ch = new eDVBChannel(this, 0);

	channel = ch;
	return 0;
}

RESULT eDVBResourceManager::addChannel(const eDVBChannelID &chid, eDVBChannel *ch)
{
	m_active_channels.push_back(active_channel(chid, ch));
	/* emit */ m_channelAdded(ch);
	return 0;
}

RESULT eDVBResourceManager::removeChannel(eDVBChannel *ch)
{
	int cnt = 0;
	for (std::list<active_channel>::iterator i(m_active_channels.begin()); i != m_active_channels.end();)
	{
		if (i->m_channel == ch)
		{
			i = m_active_channels.erase(i);
			++cnt;
		} else
			++i;
	}
	ASSERT(cnt == 1);
	if (cnt == 1)
		return 0;
	return -ENOENT;
}

RESULT eDVBResourceManager::connectChannelAdded(const Slot1<void,eDVBChannel*> &channelAdded, ePtr<eConnection> &connection)
{
	connection = new eConnection((eDVBResourceManager*)this, m_channelAdded.connect(channelAdded));
	return 0;
}

int eDVBResourceManager::canAllocateFrontend(ePtr<iDVBFrontendParameters> &feparm)
{
	ePtr<eDVBRegisteredFrontend> best;
	int bestval = 0;

	for (eSmartPtrList<eDVBRegisteredFrontend>::iterator i(m_frontend.begin()); i != m_frontend.end(); ++i)
		if (!i->m_inuse)
		{
			int c = i->m_frontend->isCompatibleWith(feparm);
			if (c > bestval)
				bestval = c;
		}

	return bestval;
}

int eDVBResourceManager::canAllocateChannel(const eDVBChannelID &channelid, const eDVBChannelID& ignore)
{
	int ret=30000;
	if (m_cached_channel)
	{
		eDVBChannel *cache_chan = (eDVBChannel*)&(*m_cached_channel);
		if(channelid==cache_chan->getChannelID())
			return ret;
	}

		/* first, check if a channel is already existing. */
//	eDebug("allocate channel.. %04x:%04x", channelid.transport_stream_id.get(), channelid.original_network_id.get());
	for (std::list<active_channel>::iterator i(m_active_channels.begin()); i != m_active_channels.end(); ++i)
	{
//		eDebug("available channel.. %04x:%04x", i->m_channel_id.transport_stream_id.get(), i->m_channel_id.original_network_id.get());
		if (i->m_channel_id == channelid)
		{
//			eDebug("found shared channel..");
			return ret;
		}
	}

	int *decremented_cached_channel_fe_usecount=NULL,
		*decremented_fe_usecount=NULL;

	for (std::list<active_channel>::iterator i(m_active_channels.begin()); i != m_active_channels.end(); ++i)
	{
//		eDebug("available channel.. %04x:%04x", i->m_channel_id.transport_stream_id.get(), i->m_channel_id.original_network_id.get());
		if (i->m_channel_id == ignore)
		{
			eDVBChannel *channel = (eDVBChannel*) &(*i->m_channel);
			// one eUsePtr<iDVBChannel> is used in eDVBServicePMTHandler
			// another on eUsePtr<iDVBChannel> is used in the eDVBScan instance used in eDVBServicePMTHandler (for SDT scan)
			// so we must check here if usecount is 3 (when the channel is equal to the cached channel)
			// or 2 when the cached channel is not equal to the compared channel
			if (channel == &(*m_cached_channel) ? channel->getUseCount() == 3 : channel->getUseCount() == 2)  // channel only used once..
			{
				ePtr<iDVBFrontend> fe;
				if (!i->m_channel->getFrontend(fe))
				{
					for (eSmartPtrList<eDVBRegisteredFrontend>::iterator ii(m_frontend.begin()); ii != m_frontend.end(); ++ii)
					{
						if ( &(*fe) == &(*ii->m_frontend) )
						{
							--ii->m_inuse;
							decremented_fe_usecount = &ii->m_inuse;
							if (channel == &(*m_cached_channel))
								decremented_cached_channel_fe_usecount = decremented_fe_usecount;
							break;
						}
					}
				}
			}
			break;
		}
	}

	if (!decremented_cached_channel_fe_usecount)
	{
		if (m_cached_channel)
		{
			eDVBChannel *channel = (eDVBChannel*) &(*m_cached_channel);
			if (channel->getUseCount() == 1)
			{
				ePtr<iDVBFrontend> fe;
				if (!channel->getFrontend(fe))
				{
					for (eSmartPtrList<eDVBRegisteredFrontend>::iterator ii(m_frontend.begin()); ii != m_frontend.end(); ++ii)
					{
						if ( &(*fe) == &(*ii->m_frontend) )
						{
							--ii->m_inuse;
							decremented_cached_channel_fe_usecount = &ii->m_inuse;
							break;
						}
					}
				}
			}
		}
	}
	else
		decremented_cached_channel_fe_usecount=NULL;

	ePtr<iDVBFrontendParameters> feparm;

	if (!m_list)
	{
		eDebug("no channel list set!");
		ret = 0;
		goto error;
	}

	if (m_list->getChannelFrontendData(channelid, feparm))
	{
		eDebug("channel not found!");
		ret = 0;
		goto error;
	}

	ret = canAllocateFrontend(feparm);

error:
	if (decremented_fe_usecount)
		++(*decremented_fe_usecount);
	if (decremented_cached_channel_fe_usecount)
		++(*decremented_cached_channel_fe_usecount);

	return ret;
}

DEFINE_REF(eDVBChannel);

eDVBChannel::eDVBChannel(eDVBResourceManager *mgr, eDVBAllocatedFrontend *frontend): m_state(state_idle), m_mgr(mgr)
{
	m_frontend = frontend;

	m_pvr_thread = 0;
	
	m_skipmode_n = m_skipmode_m = 0;
	
	if (m_frontend)
		m_frontend->get().connectStateChange(slot(*this, &eDVBChannel::frontendStateChanged), m_conn_frontendStateChanged);
}

eDVBChannel::~eDVBChannel()
{
	if (m_channel_id)
		m_mgr->removeChannel(this);

	stopFile();
}

void eDVBChannel::frontendStateChanged(iDVBFrontend*fe)
{
	int state, ourstate = 0;
	
		/* if we are already in shutdown, don't change state. */
	if (m_state == state_release)
		return;
	
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
	} else if (state == iDVBFrontend::stateLostLock)
	{
			/* on managed channels, we try to retune in order to re-acquire lock. */
		if (m_current_frontend_parameters)
		{
			eDebug("OURSTATE: lost lock, trying to retune");
			ourstate = state_tuning;
			m_frontend->get().tune(*m_current_frontend_parameters);
		} else
			/* on unmanaged channels, we don't do this. the client will do this. */
		{
			eDebug("OURSTATE: lost lock, unavailable now.");
			ourstate = state_unavailable;
		}
	} else if (state == iDVBFrontend::stateFailed)
	{
		eDebug("OURSTATE: failed");
		ourstate = state_failed;
	} else
		eFatal("state unknown");
	
	if (ourstate != m_state)
	{
		m_state = ourstate;
		m_stateChanged(this);
	}
}

void eDVBChannel::pvrEvent(int event)
{
	switch (event)
	{
	case eFilePushThread::evtEOF:
		eDebug("eDVBChannel: End of file!");
		m_event(this, evtEOF);
		break;
	case eFilePushThread::evtUser: /* start */
		eDebug("SOF");
		m_event(this, evtSOF);
		break;
	}
}

void eDVBChannel::cueSheetEvent(int event)
{
	switch (event)
	{
	case eCueSheet::evtSeek:
		eDebug("seek.");
		flushPVR(m_cue->m_decoding_demux);
		break;
	case eCueSheet::evtSkipmode:
	{
		{
			eSingleLocker l(m_cue->m_lock);
			m_cue->m_seek_requests.push_back(std::pair<int, pts_t>(1, 0)); /* resync */
			if (m_cue->m_skipmode_ratio)
			{
				int bitrate = m_tstools.calcBitrate(); /* in bits/s */
				eDebug("skipmode ratio is %lld:90000, bitrate is %d bit/s", m_cue->m_skipmode_ratio, bitrate);
						/* i agree that this might look a bit like black magic. */
				m_skipmode_n = 512*1024; /* must be 1 iframe at least. */
				m_skipmode_m = bitrate / 8 / 90000 * m_cue->m_skipmode_ratio / 8;
				
				if (m_cue->m_skipmode_ratio < 0)
					m_skipmode_m -= m_skipmode_n;
	
				eDebug("resolved to: %d %d", m_skipmode_m, m_skipmode_n);
				
				if (abs(m_skipmode_m) < abs(m_skipmode_n))
				{
					eWarning("something is wrong with this calculation");
					m_skipmode_n = m_skipmode_m = 0;
				}
				
			} else
			{
				eDebug("skipmode ratio is 0, normal play");
				m_skipmode_n = m_skipmode_m = 0;
			}
		}
		flushPVR(m_cue->m_decoding_demux);
		break;
	}
	case eCueSheet::evtSpanChanged:
	{
		m_source_span.clear();
		for (std::list<std::pair<pts_t, pts_t> >::const_iterator i(m_cue->m_spans.begin()); i != m_cue->m_spans.end(); ++i)
		{
			off_t offset_in, offset_out;
			pts_t pts_in = i->first, pts_out = i->second;
			if (m_tstools.getOffset(offset_in, pts_in) || m_tstools.getOffset(offset_out, pts_out))
			{
				eDebug("span translation failed.\n");
				continue;
			}
			eDebug("source span: %llx .. %llx, translated to %llx..%llx", pts_in, pts_out, offset_in, offset_out);
			m_source_span.push_back(std::pair<off_t, off_t>(offset_in, offset_out));
		}
		break;
	}
	}
}

	/* remember, this gets called from another thread. */
void eDVBChannel::getNextSourceSpan(off_t current_offset, size_t bytes_read, off_t &start, size_t &size)
{
	unsigned int max = 10*1024*1024;
	
	if (!m_cue)
	{
		eDebug("no cue sheet. forcing normal play");
		start = current_offset;
		size = max;
		return;
	}

	eSingleLocker l(m_cue->m_lock);
	
	if (!m_cue->m_decoding_demux)
	{
		start = current_offset;
		size = max;
		eDebug("getNextSourceSpan, no decoding demux. forcing normal play");
		return;
	}
	
	if (m_skipmode_n)
	{
		eDebug("skipmode %d:%d", m_skipmode_m, m_skipmode_n);
		max = m_skipmode_n;
	}
	
	eDebug("getNextSourceSpan, current offset is %08llx!", current_offset);
	
	current_offset += m_skipmode_m;
	
	while (!m_cue->m_seek_requests.empty())
	{
		std::pair<int, pts_t> seek = m_cue->m_seek_requests.front();
		m_cue->m_seek_requests.pop_front();
		int relative = seek.first;
		pts_t pts = seek.second;

		pts_t now = 0;
		if (relative)
		{
			if (!m_cue->m_decoder)
			{
				eDebug("no decoder - can't seek relative");
				continue;
			}
			if (m_cue->m_decoder->getPTS(0, now))
			{
				eDebug("decoder getPTS failed, can't seek relative");
				continue;
			}
			if (getCurrentPosition(m_cue->m_decoding_demux, now, 1))
			{
				eDebug("seekTo: getCurrentPosition failed!");
				continue;
			}
		}
		
		if (relative == 1) /* pts relative */
		{
			pts += now;
			if (pts < 0)
				pts = 0;
		}

		if (relative != 2)
			if (pts < 0)
				pts = 0;
		
		if (relative == 2) /* AP relative */
		{
			eDebug("AP relative seeking: %lld, at %lld", pts, now);
			pts_t nextap;
			if (m_tstools.getNextAccessPoint(nextap, now, pts))
			{
				pts = now;
				eDebug("AP relative seeking failed!");
			} else
			{
				eDebug("next ap is %llx\n", pts);
				pts = nextap;
			}
		}
		
		off_t offset = 0;
		if (m_tstools.getOffset(offset, pts))
			continue;

		eDebug("ok, resolved skip (rel: %d, diff %lld), now at %08llx", relative, pts, offset);
		current_offset = offset;
	}
	
	for (std::list<std::pair<off_t, off_t> >::const_iterator i(m_source_span.begin()); i != m_source_span.end(); ++i)
	{
		if ((current_offset >= i->first) && (current_offset < i->second))
		{
			start = current_offset;
				/* max can not exceed max(size_t). i->second - current_offset, however, can. */
			if ((i->second - current_offset) > max)
				size = max;
			else
				size = i->second - current_offset;
			eDebug("HIT, %lld < %lld < %lld, size: %d", i->first, current_offset, i->second, size);
			return;
		}
		if (current_offset < i->first)
		{
				/* ok, our current offset is in an 'out' zone. */
			if ((m_skipmode_m >= 0) || (i == m_source_span.begin()))
			{
					/* in normal playback, just start at the next zone. */
				start = i->first;
				
					/* size is not 64bit! */
				if ((i->second - i->first) > max)
					size = max;
				else
					size = i->second - i->first;

				eDebug("skip");
				if (m_skipmode_m < 0)
				{
					eDebug("reached SOF");
						/* reached SOF */
					m_skipmode_m = 0;
					m_pvr_thread->sendEvent(eFilePushThread::evtUser);
				}
			} else
			{
					/* when skipping reverse, however, choose the zone before. */
				--i;
				eDebug("skip to previous block, which is %llx..%llx", i->first, i->second);
				size_t len;
				
				if ((i->second - i->first) > max)
					len = max;
				else
					len = i->second - i->first;

				start = i->second - len;
				eDebug("skipping to %llx, %d", start, len);
			}
			return;
		}
	}
	
	if ((current_offset < -m_skipmode_m) && (m_skipmode_m < 0))
	{
		eDebug("reached SOF");
		m_skipmode_m = 0;
		m_pvr_thread->sendEvent(eFilePushThread::evtUser);
	}
	
	start = current_offset;
	size = max;
	eDebug("END OF CUESHEET. (%08llx, %d)", start, size);
	return;
}

void eDVBChannel::AddUse()
{
	if (++m_use_count > 1 && m_state == state_last_instance)
	{
		m_state = state_ok;
		m_stateChanged(this);
	}
}

void eDVBChannel::ReleaseUse()
{
	if (!--m_use_count)
	{
		m_state = state_release;
		m_stateChanged(this);
	}
	else if (m_use_count == 1)
	{
		m_state = state_last_instance;
		m_stateChanged(this);
	}
}

RESULT eDVBChannel::setChannel(const eDVBChannelID &channelid, ePtr<iDVBFrontendParameters> &feparm)
{
	if (m_channel_id)
		m_mgr->removeChannel(this);
		
	if (!channelid)
		return 0;

	if (!m_frontend)
	{
		eDebug("no frontend to tune!");
		return -ENODEV;
	}
	
	m_channel_id = channelid;
	m_mgr->addChannel(channelid, this);
	m_state = state_tuning;
			/* if tuning fails, shutdown the channel immediately. */
	int res;
	res = m_frontend->get().tune(*feparm);
	m_current_frontend_parameters = feparm;
	
	if (res)
	{
		m_state = state_release;
		m_stateChanged(this);
		return res;
	}
	
	return 0;
}

RESULT eDVBChannel::connectStateChange(const Slot1<void,iDVBChannel*> &stateChange, ePtr<eConnection> &connection)
{
	connection = new eConnection((iDVBChannel*)this, m_stateChanged.connect(stateChange));
	return 0;
}

RESULT eDVBChannel::connectEvent(const Slot2<void,iDVBChannel*,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection((iDVBChannel*)this, m_event.connect(event));
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

RESULT eDVBChannel::getDemux(ePtr<iDVBDemux> &demux, int cap)
{
	ePtr<eDVBAllocatedDemux> &our_demux = (cap & capDecode) ? m_decoder_demux : m_demux;
	
	if (!our_demux)
	{
		demux = 0;
		
		if (m_mgr->allocateDemux(m_frontend ? (eDVBRegisteredFrontend*)*m_frontend : (eDVBRegisteredFrontend*)0, our_demux, cap))
			return -1;
	}
	
	demux = *our_demux;
		/* don't hold a reference to the decoding demux, we don't need it. */
		
		/* FIXME: by dropping the 'allocated demux' in favour of the 'iDVBDemux',
		   the refcount is lost. thus, decoding demuxes are never allocated. 
		   
		   this poses a big problem for PiP. */
	if (cap & capDecode)
		our_demux = 0;
	return 0;
}

RESULT eDVBChannel::getFrontend(ePtr<iDVBFrontend> &frontend)
{
	frontend = 0;
	if (!m_frontend)
		return -ENODEV;
	frontend = &m_frontend->get();
	if (frontend)
		return 0;
	return -ENODEV;
}

RESULT eDVBChannel::getCurrentFrontendParameters(ePtr<iDVBFrontendParameters> &param)
{
	param = m_current_frontend_parameters;
	return 0;
}

RESULT eDVBChannel::playFile(const char *file)
{
	ASSERT(!m_frontend);
	if (m_pvr_thread)
	{
		m_pvr_thread->stop();
		delete m_pvr_thread;
		m_pvr_thread = 0;
	}
	
	m_tstools.openFile(file);
	
		/* DON'T EVEN THINK ABOUT FIXING THIS. FIX THE ATI SOURCES FIRST,
		   THEN DO A REAL FIX HERE! */
	
		/* (this codepath needs to be improved anyway.) */
#if HAVE_DVB_API_VERSION < 3
	m_pvr_fd_dst = open("/dev/pvr", O_WRONLY);
#else
	m_pvr_fd_dst = open("/dev/misc/pvr", O_WRONLY);
#endif
	if (m_pvr_fd_dst < 0)
	{
		eDebug("can't open /dev/misc/pvr - you need to buy the new(!) $$$ box! (%m)"); // or wait for the driver to be improved.
		return -ENODEV;
	}

	m_pvr_thread = new eFilePushThread();
	m_pvr_thread->enablePVRCommit(1);
	m_pvr_thread->setScatterGather(this);

	if (m_pvr_thread->start(file, m_pvr_fd_dst))
	{
		delete m_pvr_thread;
		m_pvr_thread = 0;
		eDebug("can't open PVR file %s (%m)", file);
		return -ENOENT;
	}
	CONNECT(m_pvr_thread->m_event, eDVBChannel::pvrEvent);

	m_state = state_ok;
	m_stateChanged(this);

	return 0;
}

void eDVBChannel::stopFile()
{
	if (m_pvr_thread)
	{
		m_pvr_thread->stop();
		::close(m_pvr_fd_dst);
		delete m_pvr_thread;
		m_pvr_thread = 0;
	}
}

void eDVBChannel::setCueSheet(eCueSheet *cuesheet)
{
	m_conn_cueSheetEvent = 0;
	m_cue = cuesheet;
	if (m_cue)
		m_cue->connectEvent(slot(*this, &eDVBChannel::cueSheetEvent), m_conn_cueSheetEvent);
}

RESULT eDVBChannel::getLength(pts_t &len)
{
	return m_tstools.calcLen(len);
}

RESULT eDVBChannel::getCurrentPosition(iDVBDemux *decoding_demux, pts_t &pos, int mode)
{
	if (!decoding_demux)
		return -1;
	
	pts_t now;
	
	int r;
	
	if (mode == 0) /* demux */
	{
		r = decoding_demux->getSTC(now, 0);
		if (r)
		{
			eDebug("demux getSTC failed");
			return -1;
		}
	} else
		now = pos; /* fixup supplied */
	
	off_t off = 0; /* TODO: fixme */
	r = m_tstools.fixupPTS(off, now);
	if (r)
	{
		eDebug("fixup PTS failed");
		return -1;
	}
	
	pos = now;
	
	return 0;
}

void eDVBChannel::flushPVR(iDVBDemux *decoding_demux)
{
			/* when seeking, we have to ensure that all buffers are flushed.
			   there are basically 3 buffers:
			   a.) the filepush's internal buffer
			   b.) the PVR buffer (before demux)
			   c.) the ratebuffer (after demux)
			   
			   it's important to clear them in the correct order, otherwise
			   the ratebuffer (for example) would immediately refill from
			   the not-yet-flushed PVR buffer.
			*/

	m_pvr_thread->pause();
		/* flush internal filepush buffer */
	m_pvr_thread->flush();
		/* HACK: flush PVR buffer */
	::ioctl(m_pvr_fd_dst, 0);
	
		/* flush ratebuffers (video, audio) */
	if (decoding_demux)
		decoding_demux->flush();

		/* demux will also flush all decoder.. */
		/* resume will re-query the SG */
	m_pvr_thread->resume();
}

DEFINE_REF(eCueSheet);

eCueSheet::eCueSheet()
{
	m_skipmode_ratio = 0;
}

void eCueSheet::seekTo(int relative, const pts_t &pts)
{
	{
		eSingleLock l(m_lock);
		m_seek_requests.push_back(std::pair<int, pts_t>(relative, pts));
	}
	m_event(evtSeek);
}
	
void eCueSheet::clear()
{
	eSingleLock l(m_lock);
	m_spans.clear();
}

void eCueSheet::addSourceSpan(const pts_t &begin, const pts_t &end)
{
	{
		eSingleLock l(m_lock);
		m_spans.push_back(std::pair<pts_t, pts_t>(begin, end));
	}
}

void eCueSheet::commitSpans()
{
	m_event(evtSpanChanged);
}

void eCueSheet::setSkipmode(const pts_t &ratio)
{
	{
		eSingleLock l(m_lock);
		m_skipmode_ratio = ratio;
	}
	m_event(evtSkipmode);
}

void eCueSheet::setDecodingDemux(iDVBDemux *demux, iTSMPEGDecoder *decoder)
{
	m_decoding_demux = demux;
	m_decoder = decoder;
}

RESULT eCueSheet::connectEvent(const Slot1<void,int> &event, ePtr<eConnection> &connection)
{
	connection = new eConnection(this, m_event.connect(event));
	return 0;
}
