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

eDVBResourceManager::eDVBResourceManager()
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

	for (i=0; i<num_fe; ++i)
	{
		ePtr<eDVBFrontend> frontend;

		if (!adapter->getFrontend(frontend, i))
		{
			frontend->setSEC(m_sec);
			m_frontend.push_back(new eDVBRegisteredFrontend(frontend, adapter));
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
		++i, ++n;
	
	for (; i != m_demux.end(); ++i, ++n)
		if ((!i->m_inuse) && ((!fe) || (i->m_adapter == fe->m_adapter)))
		{
			if ((cap & iDVBChannel::capDecode) && n)
				continue;
			
			demux = new eDVBAllocatedDemux(i);
			if (fe)
				demux->get().setSourceFrontend(fe->m_frontend->getID());
			else
				demux->get().setSourcePVR(0);
			return 0;
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
			channel=m_cached_channel;
			return 0;
		}
		m_cached_channel=0;
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

	return 0;
}

RESULT eDVBResourceManager::allocateRawChannel(eUsePtr<iDVBChannel> &channel, int frontend_index)
{
	ePtr<eDVBAllocatedFrontend> fe;

	if (m_cached_channel)
		m_cached_channel=0;

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

	if (m_cached_channel)
		m_cached_channel=0;

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

bool eDVBResourceManager::canAllocateFrontend(ePtr<iDVBFrontendParameters> &feparm)
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

	return bestval>0;
}

bool eDVBResourceManager::canAllocateChannel(const eDVBChannelID &channelid, const eDVBChannelID& ignore)
{
	bool ret=true;
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
			if (channel == &(*m_cached_channel) ? channel->getUseCount() == 2 : channel->getUseCount() == 1)  // channel only used once..
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
		ret = false;
		goto error;
	}

	if (m_list->getChannelFrontendData(channelid, feparm))
	{
		eDebug("channel not found!");
		ret = false;
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
	
	if (m_frontend)
		m_frontend->get().connectStateChange(slot(*this, &eDVBChannel::frontendStateChanged), m_conn_frontendStateChanged);
}

eDVBChannel::~eDVBChannel()
{
	if (m_channel_id)
		m_mgr->removeChannel(this);
	
	if (m_pvr_thread)
	{
		m_pvr_thread->stop();
		::close(m_pvr_fd_src);
		::close(m_pvr_fd_dst);
		delete m_pvr_thread;
	}
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
		eDebug("OURSTATE: lost lock");
		ourstate = state_unavailable;
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
	}
}

void eDVBChannel::AddUse()
{
	++m_use_count;
}

void eDVBChannel::ReleaseUse()
{
	if (!--m_use_count)
	{
		m_state = state_release;
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
	if (cap & capDecode)
		our_demux = 0;
	return 0;
}

RESULT eDVBChannel::getFrontend(ePtr<iDVBFrontend> &frontend)
{
	frontend = &m_frontend->get();
	if (frontend)
		return 0;
	else
		return -ENODEV;
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
	m_pvr_fd_dst = open("/dev/misc/pvr", O_WRONLY);
	if (m_pvr_fd_dst < 0)
	{
		eDebug("can't open /dev/misc/pvr - you need to buy the new(!) $$$ box! (%m)"); // or wait for the driver to be improved.
		return -ENODEV;
	}
	
	m_pvr_fd_src = open(file, O_RDONLY|O_LARGEFILE);
	if (m_pvr_fd_src < 0)
	{
		eDebug("can't open PVR m_pvr_fd_src file %s (%m)", file);
		close(m_pvr_fd_dst);
		return -ENOENT;
	}
	
	m_state = state_ok;
	m_stateChanged(this);
	
	m_pvr_thread = new eFilePushThread();
	m_pvr_thread->enablePVRCommit(1);
	m_pvr_thread->start(m_pvr_fd_src, m_pvr_fd_dst);
	CONNECT(m_pvr_thread->m_event, eDVBChannel::pvrEvent);

	return 0;
}

RESULT eDVBChannel::getLength(pts_t &len)
{
	return m_tstools.calcLen(len);
}

RESULT eDVBChannel::getCurrentPosition(iDVBDemux *decoding_demux, pts_t &pos, int mode)
{
	if (!decoding_demux)
		return -1;
	
	off_t begin = 0;
		/* getPTS for offset 0 is cached, so it doesn't harm. */
	int r = m_tstools.getPTS(begin, pos);
	if (r)
	{
		eDebug("tstools getpts(0) failed!");
		return r;
	}
	
	pts_t now;
	
			/* TODO: this is a gross hack. */
	r = decoding_demux->getSTC(now, mode ? 128 : 0);

	if (r)
	{
		eDebug("demux getSTC failed");
		return -1;
	}
	
//	eDebug("STC: %08llx PTS: %08llx, diff %lld", now, pos, now - pos);
		/* when we are less than 10 seconds before the start, return 0. */
		/* (we're just waiting for the timespam to start) */
	if ((now < pos) && ((pos - now) < 90000 * 10))
	{
		pos = 0;
		return 0;
	}
	
	if (now < pos) /* wrap around */
		pos = now + ((pts_t)1)<<33 - pos;
	else
		pos = now - pos;
	
	return 0;
}

RESULT eDVBChannel::seekTo(iDVBDemux *decoding_demux, int relative, pts_t &pts)
{
	int bitrate = m_tstools.calcBitrate(); /* in bits/s */
	
	if (bitrate == -1)
		return -1;
	
	if (relative)
	{
		pts_t now;
		if (getCurrentPosition(decoding_demux, now, 0))
		{
			eDebug("seekTo: getCurrentPosition failed!");
			return -1;
		}
		pts += now;
	}
	
	if (pts < 0)
		pts = 0;
	
	off_t offset = (pts * (pts_t)bitrate) / 8ULL / 90000ULL;
	
	seekToPosition(decoding_demux, offset);
	return 0;
}

RESULT eDVBChannel::seekToPosition(iDVBDemux *decoding_demux, const off_t &r)
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
	eDebug("eDVBChannel: seekToPosition .. %llx", r);
	m_pvr_thread->pause();

		/* flush internal filepush buffer */
	m_pvr_thread->flush();

		/* HACK: flush PVR buffer */
	::ioctl(m_pvr_fd_dst, 0);
	
		/* flush ratebuffers (video, audio) */
	if (decoding_demux)
		decoding_demux->flush();

		/* demux will also flush all decoder.. */
	m_pvr_thread->seek(SEEK_SET, r);
	m_pvr_thread->resume();
	return 0;
}
