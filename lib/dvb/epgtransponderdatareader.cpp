#include <lib/dvb/epgtransponderdatareader.h>

#include <fstream>

#include <lib/dvb/epgchanneldata.h>
#include <lib/dvb/pmt.h>


eEPGTransponderDataReader* eEPGTransponderDataReader::instance;
pthread_mutex_t eEPGTransponderDataReader::known_channel_lock = PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP;
pthread_mutex_t eEPGTransponderDataReader::last_channel_update_lock = PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP;

DEFINE_REF(eEPGTransponderDataReader)

eEPGTransponderDataReader::eEPGTransponderDataReader()
	:m_messages(this,1), m_running(false)
{
	eDebug("[eEPGTransponderDataReader] Initialized");

	CONNECT(m_messages.recv_msg, eEPGTransponderDataReader::gotMessage);
	CONNECT(eEPGCache::getInstance()->epgCacheStarted, eEPGTransponderDataReader::startThread);

	ePtr<eDVBResourceManager> res_mgr;
	eDVBResourceManager::getInstance(res_mgr);
	if (!res_mgr)
		eDebug("[eEPGTransponderDataReader] no resource manager !!!!!!!");
	else
		res_mgr->connectChannelAdded(sigc::mem_fun(*this,&eEPGTransponderDataReader::DVBChannelAdded), m_chanAddedConn);

	std::ifstream pid_file ("/etc/enigma2/epgpids.custom");
	if (pid_file.is_open())
	{
		eDebug("[eEPGTransponderDataReader] Custom pidfile found, parsing...");
		std::string line;
		char optsidonid[12];
		int op, tsid, onid, eitpid;
		while (!pid_file.eof())
		{
			getline(pid_file, line);
			if (line[0] == '#' || sscanf(line.c_str(), "%i %i %i %i", &op, &tsid, &onid, &eitpid) != 4)
				continue;
			if (op < 0)
				op += 3600;
			if (eitpid != 0)
			{
				snprintf(optsidonid, sizeof(optsidonid) - 1, "%x%04x%04x", op, tsid, onid);
				customeitpids[std::string(optsidonid)] = eitpid;
				eDebug("[eEPGTransponderDataReader] %s --> %#x", optsidonid, eitpid);
			}
		}
		pid_file.close();
		eDebug("[eEPGTransponderDataReader] Done");
	}

	instance=this;
}

eEPGTransponderDataReader::~eEPGTransponderDataReader()
{
	m_running = false;
	m_messages.send(Message::quit);
	kill(); // waiting for thread shutdown
	instance = nullptr;
}

void eEPGTransponderDataReader::startThread()
{
	if (!m_running)
	{
		eDebug("[eEPGTransponderDataReader] start Mainloop");
		run();
		m_running = true;
		singleLock s(known_channel_lock);
		for (ChannelMap::const_iterator it = m_knownChannels.begin(); it != m_knownChannels.end(); ++it)
		{
			if (it->second->state == -1)
			{
				it->second->state=0;
				m_messages.send(Message(Message::startChannel, it->first));
			}
		}
	}
}

void eEPGTransponderDataReader::thread()
{
	hasStarted();
	if (nice(4) == -1)
	{
		eDebug("[eEPGTransponderDataReader] thread failed to modify scheduling priority (%m)");
	}
	runLoop();
}

void eEPGTransponderDataReader::gotMessage( const Message &msg )
{
	switch (msg.type)
	{
		case Message::quit:
			quit(0);
			break;
		case Message::startChannel:
		{
			singleLock s(known_channel_lock);
			ChannelMap::const_iterator channel = m_knownChannels.find(msg.channel);
			if ( channel != m_knownChannels.end() )
				channel->second->startChannel();
			break;
		}
		case Message::leaveChannel:
		{
			singleLock s(known_channel_lock);
			ChannelMap::const_iterator channel = m_knownChannels.find(msg.channel);
			if ( channel != m_knownChannels.end() )
				channel->second->abortEPG();
			break;
		}
#ifdef ENABLE_PRIVATE_EPG
		case Message::got_private_pid:
		{
			singleLock s(known_channel_lock);
			for (ChannelMap::const_iterator it(m_knownChannels.begin()); it != m_knownChannels.end(); ++it)
			{
				eDVBChannel *channel = (eDVBChannel*) it->first;
				eEPGChannelData *data = it->second;
				eDVBChannelID chid = channel->getChannelID();
				if ( chid.transport_stream_id.get() == msg.service.tsid &&
					chid.original_network_id.get() == msg.service.onid &&
					data->m_PrivatePid == -1 )
				{
					data->m_PrevVersion = -1;
					data->m_PrivatePid = msg.pid;
					data->m_PrivateService = msg.service;
					int onid = chid.original_network_id.get();
					onid |= 0x80000000;  // we use highest bit as private epg indicator
					chid.original_network_id = onid;
					singleLock l(last_channel_update_lock);
					updateMap::iterator It = m_channelLastUpdated.find( chid );
					int update = ( It != m_channelLastUpdated.end() ? ( UPDATE_INTERVAL - ( (::time(0)-It->second) * 1000 ) ) : ZAP_DELAY );
					if (update < ZAP_DELAY)
						update = ZAP_DELAY;
					data->startPrivateTimer->start(update, 1);
					if (update >= 60000)
						eDebug("[eEPGTransponderDataReader] next private update in %i min", update/60000);
					else if (update >= 1000)
						eDebug("[eEPGTransponderDataReader] next private update in %i sec", update/1000);
					break;
				}
			}
			break;
		}
#endif
#ifdef ENABLE_MHW_EPG
		case Message::got_mhw2_channel_pid:
		{
			singleLock s(known_channel_lock);
			for (ChannelMap::const_iterator it(m_knownChannels.begin()); it != m_knownChannels.end(); ++it)
			{
				eDVBChannel *channel = (eDVBChannel*) it->first;
				eEPGChannelData *data = it->second;
				eDVBChannelID chid = channel->getChannelID();
				if ( chid.transport_stream_id.get() == msg.service.tsid &&
					chid.original_network_id.get() == msg.service.onid )
				{
					data->m_mhw2_channel_pid = msg.pid;
					eDebug("[eEPGTransponderDataReader] got mhw2 channel pid %04x", msg.pid);
					break;
				}
			}
			break;
		}
		case Message::got_mhw2_title_pid:
		{
			singleLock s(known_channel_lock);
			for (ChannelMap::const_iterator it(m_knownChannels.begin()); it != m_knownChannels.end(); ++it)
			{
				eDVBChannel *channel = (eDVBChannel*) it->first;
				eEPGChannelData *data = it->second;
				eDVBChannelID chid = channel->getChannelID();
				if ( chid.transport_stream_id.get() == msg.service.tsid &&
					chid.original_network_id.get() == msg.service.onid )
				{
					data->m_mhw2_title_pid = msg.pid;
					eDebug("[eEPGTransponderDataReader] got mhw2 title pid %04x", msg.pid);
					break;
				}
			}
			break;
		}
		case Message::got_mhw2_summary_pid:
		{
			singleLock s(known_channel_lock);
			for (ChannelMap::const_iterator it(m_knownChannels.begin()); it != m_knownChannels.end(); ++it)
			{
				eDVBChannel *channel = (eDVBChannel*) it->first;
				eEPGChannelData *data = it->second;
				eDVBChannelID chid = channel->getChannelID();
				if ( chid.transport_stream_id.get() == msg.service.tsid &&
					chid.original_network_id.get() == msg.service.onid )
				{
					data->m_mhw2_summary_pid = msg.pid;
					eDebug("[eEPGTransponderDataReader] got mhw2 summary pid %04x", msg.pid);
					break;
				}
			}
			break;
		}
#endif
		default:
			eDebug("[eEPGTransponderDataReader] unhandled Message!!");
			break;
	}
}

void eEPGTransponderDataReader::restartReader()
{
	singleLock l(last_channel_update_lock);
	m_channelLastUpdated.clear();
	singleLock k(known_channel_lock);
	for (ChannelMap::const_iterator it(m_knownChannels.begin()); it != m_knownChannels.end(); ++it)
		it->second->startEPG();
}

void eEPGTransponderDataReader::DVBChannelAdded(eDVBChannel *chan)
{
	if ( chan )
	{
//		eDebug("[eEPGTransponderDataReader] add channel %p", chan);
		eEPGChannelData *data = new eEPGChannelData(this);
		data->channel = chan;
		data->prevChannelState = -1;
#ifdef ENABLE_PRIVATE_EPG
		data->m_PrivatePid = -1;
#endif
#ifdef ENABLE_MHW_EPG
		data->m_mhw2_channel_pid = 0x231; // defaults for astra 19.2 Movistar+
		if (eEPGCache::getInstance()->getEpgmaxdays() < 4){
			data->m_mhw2_title_pid = 0x234; // defaults for astra 19.2 Movistar+
			data->m_mhw2_summary_pid = 0x236; // defaults for astra 19.2 Movistar+
		} else {
			data->m_mhw2_title_pid = 0x284; // change for fix 7 days epg Movistar+
			data->m_mhw2_summary_pid = 0x282; // change for fix 7 days epg Movistar+
		}
#endif
		singleLock s(known_channel_lock);
		m_knownChannels.insert( std::pair<iDVBChannel*, eEPGChannelData* >(chan, data) );
		chan->connectStateChange(sigc::mem_fun(*this, &eEPGTransponderDataReader::DVBChannelStateChanged), data->m_stateChangedConn);
	}
}

void eEPGTransponderDataReader::DVBChannelStateChanged(iDVBChannel *chan)
{
	ChannelMap::iterator it = m_knownChannels.find(chan);
	if ( it != m_knownChannels.end() )
	{
		int state = 0;
		chan->getState(state);
		if ( it->second->prevChannelState != state )
		{
			switch (state)
			{
				case iDVBChannel::state_ok:
				{
					eDebug("[eEPGTransponderDataReader] channel %p running", chan);
					DVBChannelRunning(chan);
					break;
				}
				case iDVBChannel::state_release:
				{
					eDebug("[eEPGTransponderDataReader] remove channel %p", chan);
					if (it->second->state >= 0)
						m_messages.send(Message(Message::leaveChannel, chan));
					eEPGChannelData* cd = it->second;
					pthread_mutex_lock(&cd->channel_active);
					{
						singleLock s(known_channel_lock);
						m_knownChannels.erase(it);
					}
					pthread_mutex_unlock(&cd->channel_active);
					delete cd;
					// -> gotMessage -> abortEPG
					return;
				}
				default: // ignore all other events
					return;
			}
			if (it->second)
				it->second->prevChannelState = state;
		}
	}
}

void eEPGTransponderDataReader::DVBChannelRunning(iDVBChannel *chan)
{
	ChannelMap::const_iterator it = m_knownChannels.find(chan);
	if ( it == m_knownChannels.end() )
		eDebug("[eEPGTransponderDataReader] will start non existing channel %p !!!", chan);
	else
	{
		eEPGChannelData &data = *it->second;
		ePtr<eDVBResourceManager> res_mgr;
		if ( eDVBResourceManager::getInstance( res_mgr ) )
			eDebug("[eEPGTransponderDataReader] no res manager!!");
		else
		{
			ePtr<iDVBDemux> demux;
			if ( data.channel->getDemux(demux, 0) )
			{
				eDebug("[eEPGTransponderDataReader] no demux!!");
				return;
			}
			else
			{
				RESULT res = demux->createSectionReader( this, data.m_NowNextReader );
				if ( res )
				{
					eDebug("[eEPGTransponderDataReader] couldnt initialize nownext reader!!");
					return;
				}

				res = demux->createSectionReader( this, data.m_ScheduleReader );
				if ( res )
				{
					eDebug("[eEPGTransponderDataReader] couldnt initialize schedule reader!!");
					return;
				}

				res = demux->createSectionReader( this, data.m_ScheduleOtherReader );
				if ( res )
				{
					eDebug("[eEPGTransponderDataReader] couldnt initialize schedule other reader!!");
					return;
				}

#ifdef ENABLE_VIRGIN
				res = demux->createSectionReader( this, data.m_VirginNowNextReader );
				if ( res )
				{
					eDebug("[eEPGTransponderDataReader] couldnt initialize virgin nownext reader!!");
					return;
				}

				res = demux->createSectionReader( this, data.m_VirginScheduleReader );
				if ( res )
				{
					eDebug("[eEPGTransponderDataReader] couldnt initialize virgin schedule reader!!");
					return;
				}
#endif
#ifdef ENABLE_NETMED
				res = demux->createSectionReader( this, data.m_NetmedScheduleReader );
				if ( res )
				{
					eDebug("[eEPGTransponderDataReader] couldnt initialize netmed schedule reader!!");
					return;
				}

				res = demux->createSectionReader( this, data.m_NetmedScheduleOtherReader );
				if ( res )
				{
					eDebug("[eEPGTransponderDataReader] couldnt initialize netmed schedule other reader!!");
					return;
				}
#endif
				res = demux->createSectionReader( this, data.m_ViasatReader );
				if ( res )
				{
					eDebug("[eEPGTransponderDataReader] couldnt initialize viasat reader!!");
					return;
				}
#ifdef ENABLE_PRIVATE_EPG
				res = demux->createSectionReader( this, data.m_PrivateReader );
				if ( res )
				{
					eDebug("[eEPGTransponderDataReader] couldnt initialize private reader!!");
					return;
				}
#endif
#ifdef ENABLE_MHW_EPG
				res = demux->createSectionReader( this, data.m_MHWReader );
				if ( res )
				{
					eDebug("[eEPGTransponderDataReader] couldnt initialize mhw reader!!");
					return;
				}
				res = demux->createSectionReader( this, data.m_MHWReader2 );
				if ( res )
				{
					eDebug("[eEPGTransponderDataReader] couldnt initialize mhw reader!!");
					return;
				}
#endif
#if ENABLE_FREESAT
				res = demux->createSectionReader( this, data.m_FreeSatScheduleOtherReader );
				if ( res )
				{
					eDebug("[eEPGTransponderDataReader] couldnt initialize FreeSat reader!!");
					return;
				}
				res = demux->createSectionReader( this, data.m_FreeSatScheduleOtherReader2 );
				if ( res )
				{
					eDebug("[eEPGTransponderDataReader] couldnt initialize FreeSat reader 2!!");
					return;
				}
#endif
#ifdef ENABLE_ATSC
				{
					int system = iDVBFrontend::feSatellite;
					ePtr<iDVBFrontendParameters> parms;
					chan->getCurrentFrontendParameters(parms);
					if (parms)
					{
						parms->getSystem(system);
					}
					if (system == iDVBFrontend::feATSC)
					{
						res = demux->createSectionReader( this, data.m_ATSC_VCTReader );
						if ( res )
						{
							eDebug("[eEPGTransponderDataReader] couldnt initialize ATSC VCT reader!!");
							return;
						}
						res = demux->createSectionReader( this, data.m_ATSC_MGTReader );
						if ( res )
						{
							eDebug("[eEPGTransponderDataReader] couldnt initialize ATSC MGT reader!!");
							return;
						}
						res = demux->createSectionReader( this, data.m_ATSC_EITReader );
						if ( res )
						{
							eDebug("[eEPGTransponderDataReader] couldnt initialize ATSC EIT reader!!");
							return;
						}
						res = demux->createSectionReader( this, data.m_ATSC_ETTReader );
						if ( res )
						{
							eDebug("[eEPGTransponderDataReader] couldnt initialize ATSC ETT reader!!");
							return;
						}
					}
				}
#endif
#ifdef ENABLE_OPENTV
				res = demux->createSectionReader( this, data.m_OPENTV_ChannelsReader );
				if ( res )
				{
					eDebug("[eEPGTransponderDataReader] couldnt initialize OpenTV channels reader!!");
					return;
				}
				res = demux->createSectionReader( this, data.m_OPENTV_TitlesReader );
				if ( res )
				{
					eDebug("[eEPGTransponderDataReader] couldnt initialize OpenTV titles reader!!");
					return;
				}
				res = demux->createSectionReader( this, data.m_OPENTV_SummariesReader );
				if ( res )
				{
					eDebug("[eEPGTransponderDataReader] couldnt initialize OpenTV summaries reader!!");
					return;
				}
#endif
				if (m_running)
				{
					data.state = 0;
					m_messages.send(Message(Message::startChannel, chan));
					// -> gotMessage -> changedService
				}
				else
					data.state=-1;
			}
		}
	}
}

#ifdef ENABLE_PRIVATE_EPG
#include <dvbsi++/descriptor_tag.h>
#include <dvbsi++/unknown_descriptor.h>
#include <dvbsi++/private_data_specifier_descriptor.h>

void eEPGTransponderDataReader::PMTready(eDVBServicePMTHandler *pmthandler)
{
	ePtr<eTable<ProgramMapSection> > ptr;
	if (!pmthandler->getPMT(ptr) && ptr)
	{
		std::vector<ProgramMapSection*>::const_iterator i;
		for (i = ptr->getSections().begin(); i != ptr->getSections().end(); ++i)
		{
			const ProgramMapSection &pmt = **i;

			ElementaryStreamInfoConstIterator es;
			for (es = pmt.getEsInfo()->begin(); es != pmt.getEsInfo()->end(); ++es)
			{
				int tmp=0;
				switch ((*es)->getType())
				{
				case 0xC1: // user private
					for (DescriptorConstIterator desc = (*es)->getDescriptors()->begin();
						desc != (*es)->getDescriptors()->end(); ++desc)
					{
						switch ((*desc)->getTag())
						{
							case 0xC2: // user defined
								if ((*desc)->getLength() == 8)
								{
									uint8_t buffer[10];
									(*desc)->writeToBuffer(buffer);
									if (!memcmp((const char *)buffer+2, "EPGDATA", 7))
									{
										eServiceReferenceDVB ref;
										if (!pmthandler->getServiceReference(ref))
										{
											int pid = (*es)->getPid();
											m_messages.send(Message(Message::got_mhw2_channel_pid, ref, pid));
										}
									}
									else if(!memcmp((const char *)buffer+2, "FICHAS", 6))
									{
										eServiceReferenceDVB ref;
										if (!pmthandler->getServiceReference(ref))
										{
											int pid = (*es)->getPid();
											m_messages.send(Message(Message::got_mhw2_summary_pid, ref, pid));
										}
									}
									else if(!memcmp((const char *)buffer+2, "GENEROS", 7))
									{
										eServiceReferenceDVB ref;
										if (!pmthandler->getServiceReference(ref))
										{
											int pid = (*es)->getPid();
											m_messages.send(Message(Message::got_mhw2_title_pid, ref, pid));
										}
									}
								}
								break;
							default:
								break;
						}
					}
					break;
				case 0x05: // private
					for (DescriptorConstIterator desc = (*es)->getDescriptors()->begin();
						desc != (*es)->getDescriptors()->end(); ++desc)
					{
						switch ((*desc)->getTag())
						{
							case PRIVATE_DATA_SPECIFIER_DESCRIPTOR:
								if (((PrivateDataSpecifierDescriptor*)(*desc))->getPrivateDataSpecifier() == 190)
									tmp |= 1;
								break;
							case 0x90: // OpenTV module descriptor?
							{
								Descriptor *descr = (Descriptor*)*desc;
								int descr_len = descr->getLength();
								if (descr_len == 4)
								{
									uint8_t data[descr_len+2];
									descr->writeToBuffer(data);
									if ( !data[2] && !data[3] && data[4] == 0xFF && data[5] == 0xFF )
										tmp |= 2;
								}
								break;
							}
							default:
								break;
						}
					}
				default:
					break;
				}
				if (tmp==3)
				{
					eServiceReferenceDVB ref;
					if (!pmthandler->getServiceReference(ref))
					{
						int pid = (*es)->getPid();
						m_messages.send(Message(Message::got_private_pid, ref, pid));
						return;
					}
				}
			}
		}
	}
	else
		eDebug("[eEPGTransponderDataReader] PMTready but no pmt!!");
}
#endif // ENABLE_PRIVATE_EPG
