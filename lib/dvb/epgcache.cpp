#include <lib/dvb/epgcache.h>
#include <lib/dvb/dvb.h>

#undef EPG_DEBUG  

#include <time.h>
#include <unistd.h>  // for usleep
#include <sys/vfs.h> // for statfs
// #include <libmd5sum.h>
#include <lib/base/eerror.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb/db.h>
#include <Python.h>

int eventData::CacheSize=0;
descriptorMap eventData::descriptors;
__u8 eventData::data[4108];
extern const uint32_t crc32_table[256];

eventData::eventData(const eit_event_struct* e, int size, int type)
	:ByteSize(size&0xFF), type(type&0xFF)
{
	if (!e)
		return;

	__u32 descr[65];
	__u32 *pdescr=descr;

	__u8 *data = (__u8*)e;
	int ptr=10;
	int descriptors_length = (data[ptr++]&0x0F) << 8;
	descriptors_length |= data[ptr++];
	while ( descriptors_length > 0 )
	{
		__u8 *descr = data+ptr;
		int descr_len = descr[1]+2;

		__u32 crc = 0;
		int cnt=0;
		while(cnt++ < descr_len)
			crc = (crc << 8) ^ crc32_table[((crc >> 24) ^ data[ptr++]) & 0xFF];

		descriptorMap::iterator it =
			descriptors.find(crc);
		if ( it == descriptors.end() )
		{
			CacheSize+=descr_len;
			__u8 *d = new __u8[descr_len];
			memcpy(d, descr, descr_len);
			descriptors[crc] = descriptorPair(1, d);
		}
		else
			++it->second.first;

		*pdescr++=crc;
		descriptors_length -= descr_len;
	}
	ByteSize = 12+((pdescr-descr)*4);
	EITdata = new __u8[ByteSize];
	CacheSize+=ByteSize;
	memcpy(EITdata, (__u8*) e, 12);
	memcpy(EITdata+12, descr, ByteSize-12);
}

const eit_event_struct* eventData::get() const
{
	int pos = 12;
	int tmp = ByteSize-12;
	memcpy(data, EITdata, 12);
	__u32 *p = (__u32*)(EITdata+12);
	while(tmp>0)
	{
		descriptorMap::iterator it =
			descriptors.find(*p++);
		if ( it != descriptors.end() )
		{
			int b = it->second.second[1]+2;
			memcpy(data+pos, it->second.second, b );
			pos += b;
		}
		tmp-=4;
	}

	return (const eit_event_struct*)data;
}

eventData::~eventData()
{
	if ( ByteSize )
	{
		CacheSize-=ByteSize;
		ByteSize-=12;
		__u32 *d = (__u32*)(EITdata+12);
		while(ByteSize)
		{
			descriptorMap::iterator it =
				descriptors.find(*d++);
			if ( it != descriptors.end() )
			{
				descriptorPair &p = it->second;
				if (!--p.first) // no more used descriptor
				{
					CacheSize -= it->second.second[1];
					delete [] it->second.second;  	// free descriptor memory
					descriptors.erase(it);	// remove entry from descriptor map
				}
			}
			ByteSize-=4;
		}
		delete [] EITdata;
	}
}

void eventData::load(FILE *f)
{
	int size=0;
	int id=0;
	__u8 header[2];
	descriptorPair p;
	fread(&size, sizeof(int), 1, f);
	while(size)
	{
		fread(&id, sizeof(__u32), 1, f);
		fread(&p.first, sizeof(int), 1, f);
		fread(header, 2, 1, f);
		int bytes = header[1]+2;
		p.second = new __u8[bytes];
		p.second[0] = header[0];
		p.second[1] = header[1];
		fread(p.second+2, bytes-2, 1, f);
		descriptors[id]=p;
		--size;
		CacheSize+=bytes;
	}
}

void eventData::save(FILE *f)
{
	int size=descriptors.size();
	descriptorMap::iterator it(descriptors.begin());
	fwrite(&size, sizeof(int), 1, f);
	while(size)
	{
		fwrite(&it->first, sizeof(__u32), 1, f);
		fwrite(&it->second.first, sizeof(int), 1, f);
		fwrite(it->second.second, it->second.second[1]+2, 1, f);
		++it;
		--size;
	}
}

eEPGCache* eEPGCache::instance;
pthread_mutex_t eEPGCache::cache_lock=
	PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP;
pthread_mutex_t eEPGCache::channel_map_lock=
	PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP;

DEFINE_REF(eEPGCache)

eEPGCache::eEPGCache()
	:messages(this,1), cleanTimer(this)//, paused(0)
{
	eDebug("[EPGC] Initialized EPGCache");

	CONNECT(messages.recv_msg, eEPGCache::gotMessage);
	CONNECT(eDVBLocalTimeHandler::getInstance()->m_timeUpdated, eEPGCache::timeUpdated);
	CONNECT(cleanTimer.timeout, eEPGCache::cleanLoop);

	ePtr<eDVBResourceManager> res_mgr;
	eDVBResourceManager::getInstance(res_mgr);
	if (!res_mgr)
		eDebug("[eEPGCache] no resource manager !!!!!!!");
	else
		res_mgr->connectChannelAdded(slot(*this,&eEPGCache::DVBChannelAdded), m_chanAddedConn);
	instance=this;
}

void eEPGCache::timeUpdated()
{
	if (!sync())
	{
		eDebug("[EPGC] time updated.. start EPG Mainloop");
		run();
	} else
		messages.send(Message(Message::timeChanged));
}

void eEPGCache::DVBChannelAdded(eDVBChannel *chan)
{
	if ( chan )
	{
//		eDebug("[eEPGCache] add channel %p", chan);
		channel_data *data = new channel_data(this);
		data->channel = chan;
		data->prevChannelState = -1;
#ifdef ENABLE_PRIVATE_EPG
		data->m_PrivatePid = -1;
#endif
		singleLock s(channel_map_lock);
		m_knownChannels.insert( std::pair<iDVBChannel*, channel_data* >(chan, data) );
		chan->connectStateChange(slot(*this, &eEPGCache::DVBChannelStateChanged), data->m_stateChangedConn);
	}
}

void eEPGCache::DVBChannelRunning(iDVBChannel *chan)
{
	singleLock s(channel_map_lock);
	channelMapIterator it =
		m_knownChannels.find(chan);
	if ( it == m_knownChannels.end() )
		eDebug("[eEPGCache] will start non existing channel %p !!!", chan);
	else
	{
		channel_data &data = *it->second;
		ePtr<eDVBResourceManager> res_mgr;
		if ( eDVBResourceManager::getInstance( res_mgr ) )
			eDebug("[eEPGCache] no res manager!!");
		else
		{
			ePtr<iDVBDemux> demux;
			if ( data.channel->getDemux(demux, 0) )
			{
				eDebug("[eEPGCache] no demux!!");
				return;
			}
			else
			{
				RESULT res = demux->createSectionReader( this, data.m_NowNextReader );
				if ( res )
				{
					eDebug("[eEPGCache] couldnt initialize nownext reader!!");
					return;
				}

				res = demux->createSectionReader( this, data.m_ScheduleReader );
				if ( res )
				{
					eDebug("[eEPGCache] couldnt initialize schedule reader!!");
					return;
				}

				res = demux->createSectionReader( this, data.m_ScheduleOtherReader );
				if ( res )
				{
					eDebug("[eEPGCache] couldnt initialize schedule other reader!!");
					return;
				}
#ifdef ENABLE_PRIVATE_EPG
				res = demux->createSectionReader( this, data.m_PrivateReader );
				if ( res )
				{
					eDebug("[eEPGCache] couldnt initialize private reader!!");
					return;
				}
#endif
				messages.send(Message(Message::startChannel, chan));
				// -> gotMessage -> changedService
			}
		}
	}
}

void eEPGCache::DVBChannelStateChanged(iDVBChannel *chan)
{
	channelMapIterator it =
		m_knownChannels.find(chan);
	if ( it != m_knownChannels.end() )
	{
		int state=0;
		chan->getState(state);
		if ( it->second->prevChannelState != state )
		{
			switch (state)
			{
				case iDVBChannel::state_ok:
				{
					eDebug("[eEPGCache] channel %p running", chan);
					DVBChannelRunning(chan);
					break;
				}
				case iDVBChannel::state_release:
				{
					eDebug("[eEPGCache] remove channel %p", chan);
					messages.send(Message(Message::leaveChannel, chan));
					while(!it->second->can_delete)
						usleep(1000);
					delete it->second;
					m_knownChannels.erase(it);
					// -> gotMessage -> abortEPG
					break;
				}
				default: // ignore all other events
					return;
			}
			it->second->prevChannelState = state;
		}
	}
}

void eEPGCache::sectionRead(const __u8 *data, int source, channel_data *channel)
{
	eit_t *eit = (eit_t*) data;

	int len=HILO(eit->section_length)-1;//+3-4;
	int ptr=EIT_SIZE;
	if ( ptr >= len )
		return;

	// This fixed the EPG on the Multichoice irdeto systems
	// the EIT packet is non-compliant.. their EIT packet stinks
	if ( data[ptr-1] < 0x40 )
		--ptr;

	uniqueEPGKey service( HILO(eit->service_id), HILO(eit->original_network_id), HILO(eit->transport_stream_id) );
	eit_event_struct* eit_event = (eit_event_struct*) (data+ptr);
	int eit_event_size;
	int duration;

	time_t TM = parseDVBtime( eit_event->start_time_1, eit_event->start_time_2,	eit_event->start_time_3, eit_event->start_time_4, eit_event->start_time_5);
	time_t now = time(0)+eDVBLocalTimeHandler::getInstance()->difference();

	if ( TM != 3599 && TM > -1)
		channel->haveData |= source;

	singleLock s(cache_lock);
	// hier wird immer eine eventMap zurück gegeben.. entweder eine vorhandene..
	// oder eine durch [] erzeugte
	std::pair<eventMap,timeMap> &servicemap = eventDB[service];
	eventMap::iterator prevEventIt = servicemap.first.end();
	timeMap::iterator prevTimeIt = servicemap.second.end();

	while (ptr<len)
	{
		eit_event_size = HILO(eit_event->descriptors_loop_length)+EIT_LOOP_SIZE;

		duration = fromBCD(eit_event->duration_1)*3600+fromBCD(eit_event->duration_2)*60+fromBCD(eit_event->duration_3);
		TM = parseDVBtime(
			eit_event->start_time_1,
			eit_event->start_time_2,
			eit_event->start_time_3,
			eit_event->start_time_4,
			eit_event->start_time_5);

		if ( TM == 3599 )
			goto next;

		if ( TM != 3599 && (TM+duration < now || TM > now+14*24*60*60) )
			goto next;

		if ( now <= (TM+duration) || TM == 3599 /*NVOD Service*/ )  // old events should not be cached
		{
			__u16 event_id = HILO(eit_event->event_id);
//			eDebug("event_id is %d sid is %04x", event_id, service.sid);

			eventData *evt = 0;
			int ev_erase_count = 0;
			int tm_erase_count = 0;

			// search in eventmap
			eventMap::iterator ev_it =
				servicemap.first.find(event_id);

			// entry with this event_id is already exist ?
			if ( ev_it != servicemap.first.end() )
			{
				if ( source > ev_it->second->type )  // update needed ?
					goto next; // when not.. the skip this entry

				// search this event in timemap
				timeMap::iterator tm_it_tmp = 
					servicemap.second.find(ev_it->second->getStartTime());

				if ( tm_it_tmp != servicemap.second.end() )
				{
					if ( tm_it_tmp->first == TM ) // correct eventData
					{
						// exempt memory
						delete ev_it->second;
						evt = new eventData(eit_event, eit_event_size, source);
						ev_it->second=evt;
						tm_it_tmp->second=evt;
						goto next;
					}
					else
					{
						tm_erase_count++;
						// delete the found record from timemap
						servicemap.second.erase(tm_it_tmp);
						prevTimeIt=servicemap.second.end();
					}
				}
			}

			// search in timemap, for check of a case if new time has coincided with time of other event 
			// or event was is not found in eventmap
			timeMap::iterator tm_it =
				servicemap.second.find(TM);

			if ( tm_it != servicemap.second.end() )
			{
				// i think, if event is not found on eventmap, but found on timemap updating nevertheless demands
#if 0
				if ( source > tm_it->second->type && tm_erase_count == 0 ) // update needed ?
					goto next; // when not.. the skip this entry
#endif

				// search this time in eventmap
				eventMap::iterator ev_it_tmp = 
					servicemap.first.find(tm_it->second->getEventID());

				if ( ev_it_tmp != servicemap.first.end() )
				{
					ev_erase_count++;				
					// delete the found record from eventmap
					servicemap.first.erase(ev_it_tmp);
					prevEventIt=servicemap.first.end();
				}
			}
			
			evt = new eventData(eit_event, eit_event_size, source);
#if EPG_DEBUG
			bool consistencyCheck=true;
#endif
			if (ev_erase_count > 0 && tm_erase_count > 0) // 2 different pairs have been removed
			{
				// exempt memory
				delete ev_it->second; 
				delete tm_it->second;
				ev_it->second=evt;
				tm_it->second=evt;
			}
			else if (ev_erase_count == 0 && tm_erase_count > 0) 
			{
				// exempt memory
				delete ev_it->second;
				tm_it=prevTimeIt=servicemap.second.insert( prevTimeIt, std::pair<const time_t, eventData*>( TM, evt ) );
				ev_it->second=evt;
			}
			else if (ev_erase_count > 0 && tm_erase_count == 0)
			{
				// exempt memory
				delete tm_it->second;
				ev_it=prevEventIt=servicemap.first.insert( prevEventIt, std::pair<const __u16, eventData*>( event_id, evt) );
				tm_it->second=evt;
			}
			else // added new eventData
			{
#if EPG_DEBUG
				consistencyCheck=false;
#endif
				prevEventIt=servicemap.first.insert( prevEventIt, std::pair<const __u16, eventData*>( event_id, evt) );
				prevTimeIt=servicemap.second.insert( prevTimeIt, std::pair<const time_t, eventData*>( TM, evt ) );
			}
#if EPG_DEBUG
			if ( consistencyCheck )
			{
				if ( tm_it->second != evt || ev_it->second != evt )
					eFatal("tm_it->second != ev_it->second");
				else if ( tm_it->second->getStartTime() != tm_it->first )
					eFatal("event start_time(%d) non equal timemap key(%d)", 
						tm_it->second->getStartTime(), tm_it->first );
				else if ( tm_it->first != TM )
					eFatal("timemap key(%d) non equal TM(%d)", 
						tm_it->first, TM);
				else if ( ev_it->second->getEventID() != ev_it->first )
					eFatal("event_id (%d) non equal event_map key(%d)",
						ev_it->second->getEventID(), ev_it->first);
				else if ( ev_it->first != event_id )
					eFatal("eventmap key(%d) non equal event_id(%d)", 
						ev_it->first, event_id );
			}
#endif
		}
next:
#if EPG_DEBUG
		if ( servicemap.first.size() != servicemap.second.size() )
		{
			FILE *f = fopen("/hdd/event_map.txt", "w+");
			int i=0;
			for (eventMap::iterator it(servicemap.first.begin())
				; it != servicemap.first.end(); ++it )
				fprintf(f, "%d(key %d) -> time %d, event_id %d, data %p\n", 
					i++, (int)it->first, (int)it->second->getStartTime(), (int)it->second->getEventID(), it->second );
			fclose(f);
			f = fopen("/hdd/time_map.txt", "w+");
			i=0;
			for (timeMap::iterator it(servicemap.second.begin())
				; it != servicemap.second.end(); ++it )
					fprintf(f, "%d(key %d) -> time %d, event_id %d, data %p\n", 
						i++, (int)it->first, (int)it->second->getStartTime(), (int)it->second->getEventID(), it->second );
			fclose(f);

			eFatal("(1)map sizes not equal :( sid %04x tsid %04x onid %04x size %d size2 %d", 
				service.sid, service.tsid, service.onid, 
				servicemap.first.size(), servicemap.second.size() );
		}
#endif
		ptr += eit_event_size;
		eit_event=(eit_event_struct*)(((__u8*)eit_event)+eit_event_size);
	}
}

void eEPGCache::flushEPG(const uniqueEPGKey & s)
{
	eDebug("[EPGC] flushEPG %d", (int)(bool)s);
	singleLock l(cache_lock);
	if (s)  // clear only this service
	{
		eventCache::iterator it = eventDB.find(s);
		if ( it != eventDB.end() )
		{
			eventMap &evMap = it->second.first;
			timeMap &tmMap = it->second.second;
			tmMap.clear();
			for (eventMap::iterator i = evMap.begin(); i != evMap.end(); ++i)
				delete i->second;
			evMap.clear();
			eventDB.erase(it);

			// TODO .. search corresponding channel for removed service and remove this channel from lastupdated map
#ifdef ENABLE_PRIVATE_EPG
			contentMaps::iterator it =
				content_time_tables.find(s);
			if ( it != content_time_tables.end() )
			{
				it->second.clear();
				content_time_tables.erase(it);
			}
#endif
		}
	}
	else // clear complete EPG Cache
	{
		for (eventCache::iterator it(eventDB.begin());
			it != eventDB.end(); ++it)
		{
			eventMap &evMap = it->second.first;
			timeMap &tmMap = it->second.second;
			for (eventMap::iterator i = evMap.begin(); i != evMap.end(); ++i)
				delete i->second;
			evMap.clear();
			tmMap.clear();
		}
		eventDB.clear();
#ifdef ENABLE_PRIVATE_EPG
		content_time_tables.clear();
#endif
		channelLastUpdated.clear();
		singleLock m(channel_map_lock);
		for (channelMapIterator it(m_knownChannels.begin()); it != m_knownChannels.end(); ++it)
			it->second->startEPG();
	}
	eDebug("[EPGC] %i bytes for cache used", eventData::CacheSize);
}

void eEPGCache::cleanLoop()
{
	singleLock s(cache_lock);
	if (!eventDB.empty())
	{
		eDebug("[EPGC] start cleanloop");

		time_t now = time(0)+eDVBLocalTimeHandler::getInstance()->difference();

		for (eventCache::iterator DBIt = eventDB.begin(); DBIt != eventDB.end(); DBIt++)
		{
			bool updated = false;
			for (timeMap::iterator It = DBIt->second.second.begin(); It != DBIt->second.second.end() && It->first < now;)
			{
				if ( now > (It->first+It->second->getDuration()) )  // outdated normal entry (nvod references to)
				{
					// remove entry from eventMap
					eventMap::iterator b(DBIt->second.first.find(It->second->getEventID()));
					if ( b != DBIt->second.first.end() )
					{
						// release Heap Memory for this entry   (new ....)
//						eDebug("[EPGC] delete old event (evmap)");
						DBIt->second.first.erase(b);
					}

					// remove entry from timeMap
//					eDebug("[EPGC] release heap mem");
					delete It->second;
					DBIt->second.second.erase(It++);
//					eDebug("[EPGC] delete old event (timeMap)");
					updated = true;
				}
				else
					++It;
			}
#ifdef ENABLE_PRIVATE_EPG
			if ( updated )
			{
				contentMaps::iterator x =
					content_time_tables.find( DBIt->first );
				if ( x != content_time_tables.end() )
				{
					timeMap &tmMap = eventDB[DBIt->first].second;
					for ( contentMap::iterator i = x->second.begin(); i != x->second.end(); )
					{
						for ( contentTimeMap::iterator it(i->second.begin());
							it != i->second.end(); )
						{
							if ( tmMap.find(it->second.first) == tmMap.end() )
								i->second.erase(it++);
							else
								++it;
						}
						if ( i->second.size() )
							++i;
						else
							x->second.erase(i++);
					}
				}
			}
#endif
		}
		eDebug("[EPGC] stop cleanloop");
		eDebug("[EPGC] %i bytes for cache used", eventData::CacheSize);
	}
	cleanTimer.start(CLEAN_INTERVAL,true);
}

eEPGCache::~eEPGCache()
{
	messages.send(Message::quit);
	kill(); // waiting for thread shutdown
	singleLock s(cache_lock);
	for (eventCache::iterator evIt = eventDB.begin(); evIt != eventDB.end(); evIt++)
		for (eventMap::iterator It = evIt->second.first.begin(); It != evIt->second.first.end(); It++)
			delete It->second;
}

void eEPGCache::gotMessage( const Message &msg )
{
	switch (msg.type)
	{
		case Message::flush:
			flushEPG(msg.service);
			break;
		case Message::startChannel:
		{
			singleLock s(channel_map_lock);
			channelMapIterator channel =
				m_knownChannels.find(msg.channel);
			if ( channel != m_knownChannels.end() )
				channel->second->startChannel();
			break;
		}
		case Message::leaveChannel:
		{
			singleLock s(channel_map_lock);
			channelMapIterator channel =
				m_knownChannels.find(msg.channel);
			if ( channel != m_knownChannels.end() )
				channel->second->abortEPG();
			break;
		}
		case Message::quit:
			quit(0);
			break;
#ifdef ENABLE_PRIVATE_EPG
		case Message::got_private_pid:
		{
			for (channelMapIterator it(m_knownChannels.begin()); it != m_knownChannels.end(); ++it)
			{
				eDVBChannel *channel = (eDVBChannel*) it->first;
				channel_data *data = it->second;
				eDVBChannelID chid = channel->getChannelID();
				if ( chid.transport_stream_id.get() == msg.service.tsid &&
					chid.original_network_id.get() == msg.service.onid &&
					data->m_PrivatePid == -1 )
				{
					data->m_PrivatePid = msg.pid;
					data->m_PrivateService = msg.service;
					data->startPrivateReader(msg.pid, -1);
					break;
				}
			}
			break;
		}
#endif
		case Message::timeChanged:
			cleanLoop();
			break;
		default:
			eDebug("unhandled EPGCache Message!!");
			break;
	}
}

void eEPGCache::thread()
{
	hasStarted();
	nice(4);
	load();
	cleanLoop();
	runLoop();
	save();
}

void eEPGCache::load()
{
	singleLock s(cache_lock);
	FILE *f = fopen("/hdd/epg.dat", "r");
	if (f)
	{
		int size=0;
		int cnt=0;
#if 0
		unsigned char md5_saved[16];
		unsigned char md5[16];
		bool md5ok=false;

		if (!md5_file("/hdd/epg.dat", 1, md5))
		{
			FILE *f = fopen("/hdd/epg.dat.md5", "r");
			if (f)
			{
				fread( md5_saved, 16, 1, f);
				fclose(f);
				if ( !memcmp(md5_saved, md5, 16) )
					md5ok=true;
			}
		}
		if ( md5ok )
#endif
		{
			unsigned int magic=0;
			fread( &magic, sizeof(int), 1, f);
			if (magic != 0x98765432)
			{
				eDebug("epg file has incorrect byte order.. dont read it");
				fclose(f);
				return;
			}
			char text1[13];
			fread( text1, 13, 1, f);
			if ( !strncmp( text1, "ENIGMA_EPG_V5", 13) )
			{
				fread( &size, sizeof(int), 1, f);
				while(size--)
				{
					uniqueEPGKey key;
					eventMap evMap;
					timeMap tmMap;
					int size=0;
					fread( &key, sizeof(uniqueEPGKey), 1, f);
					fread( &size, sizeof(int), 1, f);
					while(size--)
					{
						__u8 len=0;
						__u8 type=0;
						eventData *event=0;
						fread( &type, sizeof(__u8), 1, f);
						fread( &len, sizeof(__u8), 1, f);
						event = new eventData(0, len, type);
						event->EITdata = new __u8[len];
						eventData::CacheSize+=len;
						fread( event->EITdata, len, 1, f);
						evMap[ event->getEventID() ]=event;
						tmMap[ event->getStartTime() ]=event;
						++cnt;
					}
					eventDB[key]=std::pair<eventMap,timeMap>(evMap,tmMap);
				}
				eventData::load(f);
				eDebug("%d events read from /hdd/epg.dat", cnt);
#ifdef ENABLE_PRIVATE_EPG
				char text2[11];
				fread( text2, 11, 1, f);
				if ( !strncmp( text2, "PRIVATE_EPG", 11) )
				{
					size=0;
					fread( &size, sizeof(int), 1, f);
					while(size--)
					{
						int size=0;
						uniqueEPGKey key;
						fread( &key, sizeof(uniqueEPGKey), 1, f);
						fread( &size, sizeof(int), 1, f);
						while(size--)
						{
							int size;
							int content_id;
							fread( &content_id, sizeof(int), 1, f);
							fread( &size, sizeof(int), 1, f);
							while(size--)
							{
								time_t time1, time2;
								__u16 event_id;
								fread( &time1, sizeof(time_t), 1, f);
								fread( &time2, sizeof(time_t), 1, f);
								fread( &event_id, sizeof(__u16), 1, f);
								content_time_tables[key][content_id][time1]=std::pair<time_t, __u16>(time2, event_id);
							}
						}
					}
				}
#endif // ENABLE_PRIVATE_EPG
			}
			else
				eDebug("[EPGC] don't read old epg database");
			fclose(f);
		}
	}
}

void eEPGCache::save()
{
	struct statfs s;
	off64_t tmp;
	if (statfs("/hdd", &s)<0)
		tmp=0;
	else
	{
		tmp=s.f_blocks;
		tmp*=s.f_bsize;
	}

	// prevent writes to builtin flash
	if ( tmp < 1024*1024*50 ) // storage size < 50MB
		return;

	// check for enough free space on storage
	tmp=s.f_bfree;
	tmp*=s.f_bsize;
	if ( tmp < (eventData::CacheSize*12)/10 ) // 20% overhead
		return;

	FILE *f = fopen("/hdd/epg.dat", "w");
	int cnt=0;
	if ( f )
	{
		unsigned int magic = 0x98765432;
		fwrite( &magic, sizeof(int), 1, f);
		const char *text = "ENIGMA_EPG_V5";
		fwrite( text, 13, 1, f );
		int size = eventDB.size();
		fwrite( &size, sizeof(int), 1, f );
		for (eventCache::iterator service_it(eventDB.begin()); service_it != eventDB.end(); ++service_it)
		{
			timeMap &timemap = service_it->second.second;
			fwrite( &service_it->first, sizeof(uniqueEPGKey), 1, f);
			size = timemap.size();
			fwrite( &size, sizeof(int), 1, f);
			for (timeMap::iterator time_it(timemap.begin()); time_it != timemap.end(); ++time_it)
			{
				__u8 len = time_it->second->ByteSize;
				fwrite( &time_it->second->type, sizeof(__u8), 1, f );
				fwrite( &len, sizeof(__u8), 1, f);
				fwrite( time_it->second->EITdata, len, 1, f);
				++cnt;
			}
		}
		eDebug("%d events written to /hdd/epg.dat", cnt);
		eventData::save(f);
#ifdef ENABLE_PRIVATE_EPG
		const char* text3 = "PRIVATE_EPG";
		fwrite( text3, 11, 1, f );
		size = content_time_tables.size();
		fwrite( &size, sizeof(int), 1, f);
		for (contentMaps::iterator a = content_time_tables.begin(); a != content_time_tables.end(); ++a)
		{
			contentMap &content_time_table = a->second;
			fwrite( &a->first, sizeof(uniqueEPGKey), 1, f);
			int size = content_time_table.size();
			fwrite( &size, sizeof(int), 1, f);
			for (contentMap::iterator i = content_time_table.begin(); i != content_time_table.end(); ++i )
			{
				int size = i->second.size();
				fwrite( &i->first, sizeof(int), 1, f);
				fwrite( &size, sizeof(int), 1, f);
				for ( contentTimeMap::iterator it(i->second.begin());
					it != i->second.end(); ++it )
				{
					fwrite( &it->first, sizeof(time_t), 1, f);
					fwrite( &it->second.first, sizeof(time_t), 1, f);
					fwrite( &it->second.second, sizeof(__u16), 1, f);
				}
			}
		}
#endif
		fclose(f);
#if 0
		unsigned char md5[16];
		if (!md5_file("/hdd/epg.dat", 1, md5))
		{
			FILE *f = fopen("/hdd/epg.dat.md5", "w");
			if (f)
			{
				fwrite( md5, 16, 1, f);
				fclose(f);
			}
		}
#endif
	}
}

eEPGCache::channel_data::channel_data(eEPGCache *ml)
	:cache(ml)
	,abortTimer(ml), zapTimer(ml)
	,state(0), isRunning(0), haveData(0), can_delete(1)
{
	CONNECT(zapTimer.timeout, eEPGCache::channel_data::startEPG);
	CONNECT(abortTimer.timeout, eEPGCache::channel_data::abortNonAvail);
}

bool eEPGCache::channel_data::finishEPG()
{
	if (!isRunning)  // epg ready
	{
		eDebug("[EPGC] stop caching events(%ld)", time(0)+eDVBLocalTimeHandler::getInstance()->difference());
		zapTimer.start(UPDATE_INTERVAL, 1);
		eDebug("[EPGC] next update in %i min", UPDATE_INTERVAL / 60000);
		for (int i=0; i < 3; ++i)
		{
			seenSections[i].clear();
			calcedSections[i].clear();
		}
		singleLock l(cache->cache_lock);
		cache->channelLastUpdated[channel->getChannelID()] = time(0)+eDVBLocalTimeHandler::getInstance()->difference();
#ifdef ENABLE_PRIVATE_EPG
		if (seenPrivateSections.empty())
#endif
		can_delete=1;
		return true;
	}
	return false;
}

void eEPGCache::channel_data::startEPG()
{
	eDebug("[EPGC] start caching events(%ld)", eDVBLocalTimeHandler::getInstance()->difference()+time(0));
	state=0;
	haveData=0;
	can_delete=0;
	for (int i=0; i < 3; ++i)
	{
		seenSections[i].clear();
		calcedSections[i].clear();
	}

	eDVBSectionFilterMask mask;
	memset(&mask, 0, sizeof(mask));
	mask.pid = 0x12;
	mask.flags = eDVBSectionFilterMask::rfCRC;

	mask.data[0] = 0x4E;
	mask.mask[0] = 0xFE;
	m_NowNextReader->connectRead(slot(*this, &eEPGCache::channel_data::readData), m_NowNextConn);
	m_NowNextReader->start(mask);
	isRunning |= NOWNEXT;

	mask.data[0] = 0x50;
	mask.mask[0] = 0xF0;
	m_ScheduleReader->connectRead(slot(*this, &eEPGCache::channel_data::readData), m_ScheduleConn);
	m_ScheduleReader->start(mask);
	isRunning |= SCHEDULE;

	mask.data[0] = 0x60;
	mask.mask[0] = 0xF0;
	m_ScheduleOtherReader->connectRead(slot(*this, &eEPGCache::channel_data::readData), m_ScheduleOtherConn);
	m_ScheduleOtherReader->start(mask);
	isRunning |= SCHEDULE_OTHER;

	abortTimer.start(7000,true);
}

void eEPGCache::channel_data::abortNonAvail()
{
	if (!state)
	{
		if ( !(haveData&eEPGCache::NOWNEXT) && (isRunning&eEPGCache::NOWNEXT) )
		{
			eDebug("[EPGC] abort non avail nownext reading");
			isRunning &= ~eEPGCache::NOWNEXT;
			m_NowNextReader->stop();
			m_NowNextConn=0;
		}
		if ( !(haveData&eEPGCache::SCHEDULE) && (isRunning&eEPGCache::SCHEDULE) )
		{
			eDebug("[EPGC] abort non avail schedule reading");
			isRunning &= ~SCHEDULE;
			m_ScheduleReader->stop();
			m_ScheduleConn=0;
		}
		if ( !(haveData&eEPGCache::SCHEDULE_OTHER) && (isRunning&eEPGCache::SCHEDULE_OTHER) )
		{
			eDebug("[EPGC] abort non avail schedule_other reading");
			isRunning &= ~SCHEDULE_OTHER;
			m_ScheduleOtherReader->stop();
			m_ScheduleOtherConn=0;
		}
		if ( isRunning )
			abortTimer.start(90000, true);
		else
		{
			++state;
			for (int i=0; i < 3; ++i)
			{
				seenSections[i].clear();
				calcedSections[i].clear();
			}
#ifdef ENABLE_PRIVATE_EPG
			if (seenPrivateSections.empty())
#endif
			can_delete=1;
		}
	}
	++state;
}

void eEPGCache::channel_data::startChannel()
{
	updateMap::iterator It = cache->channelLastUpdated.find( channel->getChannelID() );

	int update = ( It != cache->channelLastUpdated.end() ? ( UPDATE_INTERVAL - ( (time(0)+eDVBLocalTimeHandler::getInstance()->difference()-It->second) * 1000 ) ) : ZAP_DELAY );

	if (update < ZAP_DELAY)
		update = ZAP_DELAY;

	zapTimer.start(update, 1);
	if (update >= 60000)
		eDebug("[EPGC] next update in %i min", update/60000);
	else if (update >= 1000)
		eDebug("[EPGC] next update in %i sec", update/1000);
}

void eEPGCache::channel_data::abortEPG()
{
	for (int i=0; i < 3; ++i)
	{
		seenSections[i].clear();
		calcedSections[i].clear();
	}
	abortTimer.stop();
	zapTimer.stop();
	if (isRunning)
	{
		eDebug("[EPGC] abort caching events !!");
		if (isRunning & eEPGCache::SCHEDULE)
		{
			isRunning &= ~eEPGCache::SCHEDULE;
			m_ScheduleReader->stop();
			m_ScheduleConn=0;
		}
		if (isRunning & eEPGCache::NOWNEXT)
		{
			isRunning &= ~eEPGCache::NOWNEXT;
			m_NowNextReader->stop();
			m_NowNextConn=0;
		}
		if (isRunning & SCHEDULE_OTHER)
		{
			isRunning &= ~eEPGCache::SCHEDULE_OTHER;
			m_ScheduleOtherReader->stop();
			m_ScheduleOtherConn=0;
		}
	}
#ifdef ENABLE_PRIVATE_EPG
	if (m_PrivateReader)
		m_PrivateReader->stop();
	if (m_PrivateConn)
		m_PrivateConn=0;
#endif
	can_delete=1;
}

void eEPGCache::channel_data::readData( const __u8 *data)
{
	if (!data)
		eDebug("get Null pointer from section reader !!");
	else
	{
		int source;
		int map;
		iDVBSectionReader *reader=NULL;
		switch(data[0])
		{
			case 0x4E ... 0x4F:
				reader=m_NowNextReader;
				source=eEPGCache::NOWNEXT;
				map=0;
				break;
			case 0x50 ... 0x5F:
				reader=m_ScheduleReader;
				source=eEPGCache::SCHEDULE;
				map=1;
				break;
			case 0x60 ... 0x6F:
				reader=m_ScheduleOtherReader;
				source=eEPGCache::SCHEDULE_OTHER;
				map=2;
				break;
			default:
				eDebug("[EPGC] unknown table_id !!!");
				return;
		}
		tidMap &seenSections = this->seenSections[map];
		tidMap &calcedSections = this->calcedSections[map];
		if ( state == 1 && calcedSections == seenSections || state > 1 )
		{
			eDebugNoNewLine("[EPGC] ");
			switch (source)
			{
				case eEPGCache::NOWNEXT:
					m_NowNextConn=0;
					eDebugNoNewLine("nownext");
					break;
				case eEPGCache::SCHEDULE:
					m_ScheduleConn=0;
					eDebugNoNewLine("schedule");
					break;
				case eEPGCache::SCHEDULE_OTHER:
					m_ScheduleOtherConn=0;
					eDebugNoNewLine("schedule other");
					break;
				default: eDebugNoNewLine("unknown");break;
			}
			eDebug(" finished(%ld)", time(0)+eDVBLocalTimeHandler::getInstance()->difference());
			if ( reader )
				reader->stop();
			isRunning &= ~source;
			if (!isRunning)
				finishEPG();
		}
		else
		{
			eit_t *eit = (eit_t*) data;
			__u32 sectionNo = data[0] << 24;
			sectionNo |= data[3] << 16;
			sectionNo |= data[4] << 8;
			sectionNo |= eit->section_number;

			tidMap::iterator it =
				seenSections.find(sectionNo);

			if ( it == seenSections.end() )
			{
				seenSections.insert(sectionNo);
				calcedSections.insert(sectionNo);
				__u32 tmpval = sectionNo & 0xFFFFFF00;
				__u8 incr = source == NOWNEXT ? 1 : 8;
				for ( int i = 0; i <= eit->last_section_number; i+=incr )
				{
					if ( i == eit->section_number )
					{
						for (int x=i; x <= eit->segment_last_section_number; ++x)
							calcedSections.insert(tmpval|(x&0xFF));
					}
					else
						calcedSections.insert(tmpval|(i&0xFF));
				}
				cache->sectionRead(data, source, this);
			}
		}
	}
}

RESULT eEPGCache::lookupEventTime(const eServiceReference &service, time_t t, const eventData *&result, int direction)
// if t == -1 we search the current event...
{
	singleLock s(cache_lock);
	uniqueEPGKey key(service);

	// check if EPG for this service is ready...
	eventCache::iterator It = eventDB.find( key );
	if ( It != eventDB.end() && !It->second.first.empty() ) // entrys cached ?
	{
		if (t==-1)
			t = time(0)+eDVBLocalTimeHandler::getInstance()->difference();
		timeMap::iterator i = direction <= 0 ? It->second.second.lower_bound(t) :  // find > or equal
			It->second.second.upper_bound(t); // just >
		if ( i != It->second.second.end() )
		{
			if ( direction < 0 || (direction == 0 && i->second->getStartTime() > t) )
			{
				timeMap::iterator x = i;
				--x;
				if ( x != It->second.second.end() )
				{
					time_t start_time = x->second->getStartTime();
					if (direction >= 0)
					{
						if (t < start_time)
							return -1;
						if (t > (start_time+x->second->getDuration()))
							return -1;
					}
					i = x;
				}
				else
					return -1;
			}
			result = i->second;
			return 0;
		}
	}
	return -1;
}

RESULT eEPGCache::lookupEventTime(const eServiceReference &service, time_t t, const eit_event_struct *&result, int direction)
{
	singleLock s(cache_lock);
	const eventData *data=0;
	RESULT ret = lookupEventTime(service, t, data, direction);
	if ( !ret && data )
		result = data->get();
	return ret;
}

RESULT eEPGCache::lookupEventTime(const eServiceReference &service, time_t t, Event *& result, int direction)
{
	singleLock s(cache_lock);
	const eventData *data=0;
	RESULT ret = lookupEventTime(service, t, data, direction);
	if ( !ret && data )
		result = new Event((uint8_t*)data->get());
	return ret;
}

RESULT eEPGCache::lookupEventTime(const eServiceReference &service, time_t t, ePtr<eServiceEvent> &result, int direction)
{
	singleLock s(cache_lock);
	const eventData *data=0;
	RESULT ret = lookupEventTime(service, t, data, direction);
	if ( !ret && data )
	{
		Event ev((uint8_t*)data->get());
		result = new eServiceEvent();
		const eServiceReferenceDVB &ref = (const eServiceReferenceDVB&)service;
		ret = result->parseFrom(&ev, (ref.getTransportStreamID().get()<<16)|ref.getOriginalNetworkID().get());
	}
	return ret;
}

RESULT eEPGCache::lookupEventId(const eServiceReference &service, int event_id, const eventData *&result )
{
	singleLock s(cache_lock);
	uniqueEPGKey key( service );

	eventCache::iterator It = eventDB.find( key );
	if ( It != eventDB.end() && !It->second.first.empty() ) // entrys cached?
	{
		eventMap::iterator i( It->second.first.find( event_id ));
		if ( i != It->second.first.end() )
		{
			result = i->second;
			return 0;
		}
		else
		{
			result = 0;
			eDebug("event %04x not found in epgcache", event_id);
		}
	}
	return -1;
}

RESULT eEPGCache::lookupEventId(const eServiceReference &service, int event_id, const eit_event_struct *&result)
{
	singleLock s(cache_lock);
	const eventData *data=0;
	RESULT ret = lookupEventId(service, event_id, data);
	if ( !ret && data )
		result = data->get();
	return ret;
}

RESULT eEPGCache::lookupEventId(const eServiceReference &service, int event_id, Event *& result)
{
	singleLock s(cache_lock);
	const eventData *data=0;
	RESULT ret = lookupEventId(service, event_id, data);
	if ( !ret && data )
		result = new Event((uint8_t*)data->get());
	return ret;
}

RESULT eEPGCache::lookupEventId(const eServiceReference &service, int event_id, ePtr<eServiceEvent> &result)
{
	singleLock s(cache_lock);
	const eventData *data=0;
	RESULT ret = lookupEventId(service, event_id, data);
	if ( !ret && data )
	{
		Event ev((uint8_t*)data->get());
		result = new eServiceEvent();
		const eServiceReferenceDVB &ref = (const eServiceReferenceDVB&)service;
		ret = result->parseFrom(&ev, (ref.getTransportStreamID().get()<<16)|ref.getOriginalNetworkID().get());
	}
	return ret;
}

RESULT eEPGCache::startTimeQuery(const eServiceReference &service, time_t begin, int minutes)
{
	eventCache::iterator It = eventDB.find( service );
	if ( It != eventDB.end() && It->second.second.size() )
	{
		m_timemap_end = minutes != -1 ? It->second.second.upper_bound(begin+minutes*60) : It->second.second.end();
		if ( begin != -1 )
		{
			m_timemap_cursor = It->second.second.lower_bound(begin);
			if ( m_timemap_cursor != It->second.second.end() )
			{
				if ( m_timemap_cursor->second->getStartTime() != begin )
				{
					timeMap::iterator x = m_timemap_cursor;
					--x;
					if ( x != It->second.second.end() )
					{
						time_t start_time = x->second->getStartTime();
						if ( begin > start_time && begin < (start_time+x->second->getDuration()))
							m_timemap_cursor = x;
					}
				}
			}
		}
		else
			m_timemap_cursor = It->second.second.begin();
		const eServiceReferenceDVB &ref = (const eServiceReferenceDVB&)service;
		currentQueryTsidOnid = (ref.getTransportStreamID().get()<<16) | ref.getOriginalNetworkID().get();
		return 0;
	}
	return -1;
}

RESULT eEPGCache::getNextTimeEntry(const eventData *& result)
{
	if ( m_timemap_cursor != m_timemap_end )
	{
		result = m_timemap_cursor++->second;
		return 0;
	}
	return -1;
}

RESULT eEPGCache::getNextTimeEntry(const eit_event_struct *&result)
{
	if ( m_timemap_cursor != m_timemap_end )
	{
		result = m_timemap_cursor++->second->get();
		return 0;
	}
	return -1;
}

RESULT eEPGCache::getNextTimeEntry(Event *&result)
{
	if ( m_timemap_cursor != m_timemap_end )
	{
		result = new Event((uint8_t*)m_timemap_cursor++->second->get());
		return 0;
	}
	return -1;
}

RESULT eEPGCache::getNextTimeEntry(ePtr<eServiceEvent> &result)
{
	if ( m_timemap_cursor != m_timemap_end )
	{
		Event ev((uint8_t*)m_timemap_cursor++->second->get());
		result = new eServiceEvent();
		return result->parseFrom(&ev, currentQueryTsidOnid);
	}
	return -1;
}

void fillTuple(PyObject *tuple, char *argstring, int argcount, PyObject *service, ePtr<eServiceEvent> &ptr, PyObject *nowTime, PyObject *service_name )
{
	PyObject *tmp=NULL;
	int pos=0;
	while(pos < argcount)
	{
		bool inc_refcount=false;
		switch(argstring[pos])
		{
			case '0': // PyLong 0
				tmp = PyLong_FromLong(0);
				break;
			case 'I': // Event Id
				tmp = ptr ? PyLong_FromLong(ptr->getEventId()) : NULL;
				break;
			case 'B': // Event Begin Time
				tmp = ptr ? PyLong_FromLong(ptr->getBeginTime()) : NULL;
				break;
			case 'D': // Event Duration
				tmp = ptr ? PyLong_FromLong(ptr->getDuration()) : NULL;
				break;
			case 'T': // Event Title
				tmp = ptr ? PyString_FromString(ptr->getEventName().c_str()) : NULL;
				break;
			case 'S': // Event Short Description
				tmp = ptr ? PyString_FromString(ptr->getShortDescription().c_str()) : NULL;
				break;
			case 'E': // Event Extended Description
				tmp = ptr ? PyString_FromString(ptr->getExtendedDescription().c_str()) : NULL;
				break;
			case 'C': // Current Time
				tmp = nowTime;
				inc_refcount = true;
				break;
			case 'R': // service reference string
				tmp = service;
				inc_refcount = true;
				break;
			case 'N': // service name
				tmp = service_name;
				inc_refcount = true;
		}
		if (!tmp)
		{
			tmp = Py_None;
			inc_refcount = true;
		}
		if (inc_refcount)
			Py_INCREF(tmp);
		PyTuple_SET_ITEM(tuple, pos++, tmp);
	}
}

PyObject *handleEvent(ePtr<eServiceEvent> &ptr, PyObject *dest_list, char* argstring, int argcount, PyObject *service, PyObject *nowTime, PyObject *service_name, PyObject *convertFunc, PyObject *convertFuncArgs)
{
	if (convertFunc)
	{
		fillTuple(convertFuncArgs, argstring, argcount, service, ptr, nowTime, service_name);
		PyObject *result = PyObject_CallObject(convertFunc, convertFuncArgs);
		if (result == NULL)
		{
			if (service_name)
				Py_DECREF(service_name);
			if (nowTime)
				Py_DECREF(nowTime);
			Py_DECREF(convertFuncArgs);
			Py_DECREF(dest_list);
			return result;
		}
		PyList_Append(dest_list, result);
		Py_DECREF(result);
	}
	else
	{
		PyObject *tuple = PyTuple_New(argcount);
		fillTuple(tuple, argstring, argcount, service, ptr, nowTime, service_name);
		PyList_Append(dest_list, tuple);
		Py_DECREF(tuple);
	}
	return 0;
}

// here we get a python list
// the first entry in the list is a python string to specify the format of the returned tuples (in a list)
//   0 = PyLong(0)
//   I = Event Id
//   B = Event Begin Time
//   D = Event Duration
//   T = Event Title
//   S = Event Short Description
//   E = Event Extended Description
//   C = Current Time
//   R = Service Reference
//   N = Service Name
// then for each service follows a tuple
//   first tuple entry is the servicereference (as string... use the ref.toString() function)
//   the second is the type of query
//     2 = event_id
//    -1 = event before given start_time
//     0 = event intersects given start_time
//    +1 = event after given start_time
//   the third
//      when type is eventid it is the event_id
//      when type is time then it is the start_time ( 0 for now_time )
//   the fourth is the end_time .. ( optional .. for query all events in time range)

PyObject *eEPGCache::lookupEvent(PyObject *list, PyObject *convertFunc)
{
	PyObject *convertFuncArgs=NULL;
	int argcount=0;
	char *argstring=NULL;
	if (!PyList_Check(list))
	{
		PyErr_SetString(PyExc_StandardError,
			"type error");
		eDebug("no list");
		return NULL;
	}
	int listIt=0;
	int listSize=PyList_Size(list);
	if (!listSize)
	{
		PyErr_SetString(PyExc_StandardError,
			"not params given");
		eDebug("not params given");
		return NULL;
	}
	else 
	{
		PyObject *argv=PyList_GET_ITEM(list, 0); // borrowed reference!
		if (PyString_Check(argv))
		{
			argstring = PyString_AS_STRING(argv);
			++listIt;
		}
		else
			argstring = "I"; // just event id as default
		argcount = strlen(argstring);
//		eDebug("have %d args('%s')", argcount, argstring);
	}
	if (convertFunc)
	{
		if (!PyCallable_Check(convertFunc))
		{
			PyErr_SetString(PyExc_StandardError,
				"convertFunc must be callable");
			eDebug("convertFunc is not callable");
			return NULL;
		}
		convertFuncArgs = PyTuple_New(argcount);
	}

	PyObject *nowTime = strchr(argstring, 'C') ?
		PyLong_FromLong(time(0)+eDVBLocalTimeHandler::getInstance()->difference()) :
		NULL;

	bool must_get_service_name = strchr(argstring, 'N') ? true : false;

	// create dest list
	PyObject *dest_list=PyList_New(0);
	while(listSize > listIt)
	{
		PyObject *item=PyList_GET_ITEM(list, listIt++); // borrowed reference!
		if (PyTuple_Check(item))
		{
			int type=0;
			long event_id=-1;
			time_t stime=-1;
			int minutes=0;
			int tupleSize=PyTuple_Size(item);
			int tupleIt=0;
			PyObject *service=NULL;
			while(tupleSize > tupleIt)  // parse query args
			{
				PyObject *entry=PyTuple_GET_ITEM(item, tupleIt); // borrowed reference!
				switch(tupleIt++)
				{
					case 0:
					{
						if (!PyString_Check(entry))
						{
							eDebug("tuple entry 0 is no a string");
							goto skip_entry;
						}
						service = entry;
						break;
					}
					case 1:
						type=PyInt_AsLong(entry);
						if (type < -1 || type > 2)
						{
							eDebug("unknown type %d", type);
							goto skip_entry;
						}
						break;
					case 2:
						event_id=stime=PyInt_AsLong(entry);
						break;
					case 3:
						minutes=PyInt_AsLong(entry);
						break;
					default:
						eDebug("unneeded extra argument");
						break;
				}
			}
			eServiceReference ref(PyString_AS_STRING(service));
			if (ref.type != eServiceReference::idDVB)
			{
				eDebug("service reference for epg query is not valid");
				continue;
			}
			PyObject *service_name=NULL;
			if (must_get_service_name)
			{
				ePtr<iStaticServiceInformation> sptr;
				eServiceCenterPtr service_center;
				eServiceCenter::getPrivInstance(service_center);
				if (service_center)
				{
					service_center->info(ref, sptr);
					if (sptr)
					{
						std::string name;
						sptr->getName(ref, name);
						if (name.length())
							service_name = PyString_FromString(name.c_str());
					}
				}
				if (!service_name)
					service_name = PyString_FromString("<n/a>");
			}
			if (minutes)
			{
				Lock();
				if (!startTimeQuery(ref, stime, minutes))
				{
					ePtr<eServiceEvent> ptr;
					while (!getNextTimeEntry(ptr))
					{
						PyObject *ret = handleEvent(ptr, dest_list, argstring, argcount, service, nowTime, service_name, convertFunc, convertFuncArgs);
						if (ret)
							return ret;
					}
				}
				Unlock();
			}
			else
			{
				ePtr<eServiceEvent> ptr;
				if (stime)
				{
					if (type == 2)
						lookupEventId(ref, event_id, ptr);
					else
						lookupEventTime(ref, stime, ptr, type);
				}
				PyObject *ret = handleEvent(ptr, dest_list, argstring, argcount, service, nowTime, service_name, convertFunc, convertFuncArgs);
				if (ret)
					return ret;
			}
			if (service_name)
				Py_DECREF(service_name);
		}
skip_entry:
		;
	}
	if (convertFuncArgs)
		Py_DECREF(convertFuncArgs);
	if (nowTime)
		Py_DECREF(nowTime);
	return dest_list;
}

void fillTuple2(PyObject *tuple, const char *argstring, int argcount, eventData *evData, ePtr<eServiceEvent> &ptr, PyObject *service_name, PyObject *service_reference)
{
	PyObject *tmp=NULL;
	int pos=0;
	while(pos < argcount)
	{
		bool inc_refcount=false;
		switch(argstring[pos])
		{
			case '0': // PyLong 0
				tmp = PyLong_FromLong(0);
				break;
			case 'I': // Event Id
				tmp = PyLong_FromLong(evData->getEventID());
				break;
			case 'B': // Event Begin Time
				if (ptr)
					tmp = ptr ? PyLong_FromLong(ptr->getBeginTime()) : NULL;
				else
					tmp = PyLong_FromLong(evData->getStartTime());
				break;
			case 'D': // Event Duration
				if (ptr)
					tmp = ptr ? PyLong_FromLong(ptr->getDuration()) : NULL;
				else
					tmp = PyLong_FromLong(evData->getDuration());
				break;
			case 'T': // Event Title
				tmp = ptr ? PyString_FromString(ptr->getEventName().c_str()) : NULL;
				break;
			case 'S': // Event Short Description
				tmp = ptr ? PyString_FromString(ptr->getShortDescription().c_str()) : NULL;
				break;
			case 'E': // Event Extended Description
				tmp = ptr ? PyString_FromString(ptr->getExtendedDescription().c_str()) : NULL;
				break;
			case 'R': // service reference string
				tmp = service_reference;
				inc_refcount = true;
				break;
			case 'N': // service name
				tmp = service_name;
				inc_refcount = true;
				break;
		}
		if (!tmp)
		{
			tmp = Py_None;
			inc_refcount = true;
		}
		if (inc_refcount)
			Py_INCREF(tmp);
		PyTuple_SET_ITEM(tuple, pos++, tmp);
	}
}

// here we get a python tuple
// the first entry in the tuple is a python string to specify the format of the returned tuples (in a list)
//   I = Event Id
//   B = Event Begin Time
//   D = Event Duration
//   T = Event Title
//   S = Event Short Description
//   E = Event Extended Description
//   R = Service Reference
//   N = Service Name
//  the second tuple entry is the MAX matches value
//  the third tuple entry is the type of query
//     0 = search for similar broadcastings (SIMILAR_BROADCASTINGS_SEARCH)
//     1 = search events with exactly title name (EXAKT_TITLE_SEARCH)
//     2 = search events with text in title name (PARTIAL_TITLE_SEARCH)
//  when type is 0 (SIMILAR_BROADCASTINGS_SEARCH)
//   the fourth is the servicereference string
//   the fifth is the eventid
//  when type is 1 or 2 (EXAKT_TITLE_SEARCH or PARTIAL_TITLE_SEARCH)
//   the fourth is the search text
//   the fifth is
//     0 = case sensitive (CASE_CHECK)
//     1 = case insensitive (NO_CASECHECK)

PyObject *eEPGCache::search(PyObject *arg)
{
	PyObject *ret = 0;
	int descridx = -1;
	__u32 descr[512];
	int eventid = -1;
	const char *argstring=0;
	char *refstr=0;
	int argcount=0;
	int querytype=-1;
	bool needServiceEvent=false;
	int maxmatches=0;

	if (PyTuple_Check(arg))
	{
		int tuplesize=PyTuple_Size(arg);
		if (tuplesize > 0)
		{
			PyObject *obj = PyTuple_GET_ITEM(arg,0);
			if (PyString_Check(obj))
			{
				argcount = PyString_GET_SIZE(obj);
				argstring = PyString_AS_STRING(obj);
				for (int i=0; i < argcount; ++i)
					switch(argstring[i])
					{
					case 'S':
					case 'E':
					case 'T':
						needServiceEvent=true;
					default:
						break;
					}
			}
			else
			{
				PyErr_SetString(PyExc_StandardError,
					"type error");
				eDebug("tuple arg 0 is not a string");
				return NULL;
			}
		}
		if (tuplesize > 1)
			maxmatches = PyLong_AsLong(PyTuple_GET_ITEM(arg, 1));
		if (tuplesize > 2)
		{
			querytype = PyLong_AsLong(PyTuple_GET_ITEM(arg, 2));
			if (tuplesize > 4 && querytype == 0)
			{
				PyObject *obj = PyTuple_GET_ITEM(arg, 3);
				if (PyString_Check(obj))
				{
					refstr = PyString_AS_STRING(obj);
					eServiceReferenceDVB ref(refstr);
					if (ref.valid())
					{
						eventid = PyLong_AsLong(PyTuple_GET_ITEM(arg, 4));
						singleLock s(cache_lock);
						const eventData *evData = 0;
						lookupEventId(ref, eventid, evData);
						if (evData)
						{
							__u8 *data = evData->EITdata;
							int tmp = evData->ByteSize-12;
							__u32 *p = (__u32*)(data+12);
								// search short and extended event descriptors
							while(tmp>0)
							{
								__u32 crc = *p++;
								descriptorMap::iterator it =
									eventData::descriptors.find(crc);
								if (it != eventData::descriptors.end())
								{
									__u8 *descr_data = it->second.second;
									switch(descr_data[0])
									{
									case 0x4D ... 0x4E:
										descr[++descridx]=crc;
									default:
										break;
									}
								}
								tmp-=4;
							}
						}
						if (descridx<0)
							eDebug("event not found");
					}
					else
					{
						PyErr_SetString(PyExc_StandardError,
							"type error");
						eDebug("tuple arg 4 is not a valid service reference string");
						return NULL;
					}
				}
				else
				{
					PyErr_SetString(PyExc_StandardError,
					"type error");
					eDebug("tuple arg 4 is not a string");
					return NULL;
				}
			}
			else if (tuplesize > 4 && (querytype == 1 || querytype == 2) )
			{
				PyObject *obj = PyTuple_GET_ITEM(arg, 3);
				if (PyString_Check(obj))
				{
					int casetype = PyLong_AsLong(PyTuple_GET_ITEM(arg, 4));
					const char *str = PyString_AS_STRING(obj);
					int textlen = PyString_GET_SIZE(obj);
					if (querytype == 1)
						eDebug("lookup for events with '%s' as title(%s)", str, casetype?"ignore case":"case sensitive");
					else
						eDebug("lookup for events with '%s' in title(%s)", str, casetype?"ignore case":"case sensitive");
					singleLock s(cache_lock);
					for (descriptorMap::iterator it(eventData::descriptors.begin());
						it != eventData::descriptors.end() && descridx < 511; ++it)
					{
						__u8 *data = it->second.second;
						if ( data[0] == 0x4D ) // short event descriptor
						{
							int title_len = data[5];
							if ( querytype == 1 )
							{
								if (title_len > textlen)
									continue;
								else if (title_len < textlen)
									continue;
								if ( casetype )
								{
									if ( !strncasecmp((const char*)data+6, str, title_len) )
									{
//										std::string s((const char*)data+6, title_len);
//										eDebug("match1 %s %s", str, s.c_str() );
										descr[++descridx] = it->first;
									}
								}
								else if ( !strncmp((const char*)data+6, str, title_len) )
								{
//									std::string s((const char*)data+6, title_len);
//									eDebug("match2 %s %s", str, s.c_str() );
									descr[++descridx] = it->first;
								}
							}
							else
							{
								int idx=0;
								while((title_len-idx) >= textlen)
								{
									if (casetype)
									{
										if (!strncasecmp((const char*)data+6+idx, str, textlen) )
										{
											descr[++descridx] = it->first;
//											std::string s((const char*)data+6, title_len);
//											eDebug("match 3 %s %s", str, s.c_str() );
											break;
										}
										else if (!strncmp((const char*)data+6+idx, str, textlen) )
										{
											descr[++descridx] = it->first;
//											std::string s((const char*)data+6, title_len);
//											eDebug("match 4 %s %s", str, s.c_str() );
											break;
										}
									}
									++idx;
								}
							}
						}
					}
				}
				else
				{
					PyErr_SetString(PyExc_StandardError,
						"type error");
					eDebug("tuple arg 4 is not a string");
					return NULL;
				}
			}
			else
			{
				PyErr_SetString(PyExc_StandardError,
					"type error");
				eDebug("tuple arg 3(%d) is not a known querytype(0, 1, 2)", querytype);
				return NULL;
			}
		}
		else
		{
			PyErr_SetString(PyExc_StandardError,
				"type error");
			eDebug("not enough args in tuple");
			return NULL;
		}
	}
	else
	{
		PyErr_SetString(PyExc_StandardError,
			"type error");
		eDebug("arg 0 is not a tuple");
		return NULL;
	}

	if (descridx > -1)
	{
		int maxcount=maxmatches;
		eServiceReferenceDVB ref(refstr?refstr:"");
		// ref is only valid in SIMILAR_BROADCASTING_SEARCH
		// in this case we start searching with the base service
		bool first = ref.valid() ? true : false;
		singleLock s(cache_lock);
		eventCache::iterator cit(ref.valid() ? eventDB.find(ref) : eventDB.begin());
		while(cit != eventDB.end() && maxcount)
		{
			if ( ref.valid() && !first && cit->first == ref )
			{
				// do not scan base service twice ( only in SIMILAR BROADCASTING SEARCH )
				++cit;
				continue;
			}
			PyObject *service_name=0;
			PyObject *service_reference=0;
			timeMap &evmap = cit->second.second;
			// check all events
			for (timeMap::iterator evit(evmap.begin()); evit != evmap.end() && maxcount; ++evit)
			{
				if (evit->second->getEventID() == eventid)
					continue;
				__u8 *data = evit->second->EITdata;
				int tmp = evit->second->ByteSize-12;
				__u32 *p = (__u32*)(data+12);
				// check if any of our descriptor used by this event
				int cnt=-1;
				while(tmp>0)
				{
					__u32 crc32 = *p++;
					for ( int i=0; i <= descridx; ++i)
					{
						if (descr[i] == crc32)  // found...
							++cnt;
					}
					tmp-=4;
				}
				if ( (querytype == 0 && cnt == descridx) ||
					 ((querytype == 1 || querytype == 2) && cnt != -1) )
				{
					const uniqueEPGKey &service = cit->first;
					eServiceReference ref =
						eDVBDB::getInstance()->searchReference(service.tsid, service.onid, service.sid);
					if (ref.valid())
					{
					// create servive event
						ePtr<eServiceEvent> ptr;
						if (needServiceEvent)
						{
							lookupEventId(ref, evit->first, ptr);
							if (!ptr)
								eDebug("event not found !!!!!!!!!!!");
						}
					// create service name
						if (!service_name && strchr(argstring,'N'))
						{
							ePtr<iStaticServiceInformation> sptr;
							eServiceCenterPtr service_center;
							eServiceCenter::getPrivInstance(service_center);
							if (service_center)
							{
								service_center->info(ref, sptr);
								if (sptr)
								{
									std::string name;
									sptr->getName(ref, name);
									if (name.length())
										service_name = PyString_FromString(name.c_str());
								}
							}
							if (!service_name)
								service_name = PyString_FromString("<n/a>");
						}
					// create servicereference string
						if (!service_reference && strchr(argstring,'R'))
							service_reference = PyString_FromString(ref.toString().c_str());
					// create list
						if (!ret)
							ret = PyList_New(0);
					// create tuple
						PyObject *tuple = PyTuple_New(argcount);
					// fill tuple
						fillTuple2(tuple, argstring, argcount, evit->second, ptr, service_name, service_reference);
						PyList_Append(ret, tuple);
						Py_DECREF(tuple);
						--maxcount;
					}
				}
			}
			if (service_name)
				Py_DECREF(service_name);
			if (service_reference)
				Py_DECREF(service_reference);
			if (first)
			{
				// now start at first service in epgcache database ( only in SIMILAR BROADCASTING SEARCH )
				first=false;
				cit=eventDB.begin();
			}
			else
				++cit;
		}
	}

	if (!ret)
	{
		Py_INCREF(Py_None);
		ret=Py_None;
	}

	return ret;
}

#ifdef ENABLE_PRIVATE_EPG
#include <dvbsi++/descriptor_tag.h>
#include <dvbsi++/unknown_descriptor.h>
#include <dvbsi++/private_data_specifier_descriptor.h>

void eEPGCache::PMTready(eDVBServicePMTHandler *pmthandler)
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
							case 0x90:
							{
								UnknownDescriptor *descr = (UnknownDescriptor*)*desc;
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
					if (!pmthandler->getService(ref))
					{
						int pid = (*es)->getPid();
						messages.send(Message(Message::got_private_pid, ref, pid));
						return;
					}
				}
			}
		}
	}
	else
		eDebug("PMTready but no pmt!!");
}

struct date_time
{
	__u8 data[5];
	time_t tm;
	date_time( const date_time &a )
	{
		memcpy(data, a.data, 5);
		tm = a.tm;
	}
	date_time( const __u8 data[5])
	{
		memcpy(this->data, data, 5);
		tm = parseDVBtime(data[0], data[1], data[2], data[3], data[4]);
	}
	date_time()
	{
	}
	const __u8& operator[](int pos) const
	{
		return data[pos];
	}
};

struct less_datetime
{
	bool operator()( const date_time &a, const date_time &b ) const
	{
		return abs(a.tm-b.tm) < 360 ? false : a.tm < b.tm;
	}
};

void eEPGCache::privateSectionRead(const uniqueEPGKey &current_service, const __u8 *data)
{
	contentMap &content_time_table = content_time_tables[current_service];
	singleLock s(cache_lock);
	std::map< date_time, std::list<uniqueEPGKey>, less_datetime > start_times;
	eventMap &evMap = eventDB[current_service].first;
	timeMap &tmMap = eventDB[current_service].second;
	int ptr=8;
	int content_id = data[ptr++] << 24;
	content_id |= data[ptr++] << 16;
	content_id |= data[ptr++] << 8;
	content_id |= data[ptr++];

	contentTimeMap &time_event_map =
		content_time_table[content_id];
	for ( contentTimeMap::iterator it( time_event_map.begin() );
		it != time_event_map.end(); ++it )
	{
		eventMap::iterator evIt( evMap.find(it->second.second) );
		if ( evIt != evMap.end() )
		{
			delete evIt->second;
			evMap.erase(evIt);
		}
		tmMap.erase(it->second.first);
	}
	time_event_map.clear();

	__u8 duration[3];
	memcpy(duration, data+ptr, 3);
	ptr+=3;
	int duration_sec =
		fromBCD(duration[0])*3600+fromBCD(duration[1])*60+fromBCD(duration[2]);

	const __u8 *descriptors[65];
	const __u8 **pdescr = descriptors;

	int descriptors_length = (data[ptr++]&0x0F) << 8;
	descriptors_length |= data[ptr++];
	while ( descriptors_length > 0 )
	{
		int descr_type = data[ptr];
		int descr_len = data[ptr+1];
		descriptors_length -= (descr_len+2);
		if ( descr_type == 0xf2 )
		{
			ptr+=2;
			int tsid = data[ptr++] << 8;
			tsid |= data[ptr++];
			int onid = data[ptr++] << 8;
			onid |= data[ptr++];
			int sid = data[ptr++] << 8;
			sid |= data[ptr++];
			uniqueEPGKey service( sid, onid, tsid );
			descr_len -= 6;
			while( descr_len > 0 )
			{
				__u8 datetime[5];
				datetime[0] = data[ptr++];
				datetime[1] = data[ptr++];
				int tmp_len = data[ptr++];
				descr_len -= 3;
				while( tmp_len > 0 )
				{
					memcpy(datetime+2, data+ptr, 3);
					ptr+=3;
					descr_len -= 3;
					tmp_len -= 3;
					start_times[datetime].push_back(service);
				}
			}
		}
		else
		{
			*pdescr++=data+ptr;
			ptr += 2;
			ptr += descr_len;
		}
	}
	__u8 event[4098];
	eit_event_struct *ev_struct = (eit_event_struct*) event;
	ev_struct->running_status = 0;
	ev_struct->free_CA_mode = 1;
	memcpy(event+7, duration, 3);
	ptr = 12;
	const __u8 **d=descriptors;
	while ( d < pdescr )
	{
		memcpy(event+ptr, *d, ((*d)[1])+2);
		ptr+=(*d++)[1];
		ptr+=2;
	}
	for ( std::map< date_time, std::list<uniqueEPGKey> >::iterator it(start_times.begin()); it != start_times.end(); ++it )
	{
		time_t now = eDVBLocalTimeHandler::getInstance()->nowTime();
		if ( (it->first.tm + duration_sec) < now )
			continue;
		memcpy(event+2, it->first.data, 5);
		int bptr = ptr;
		int cnt=0;
		for (std::list<uniqueEPGKey>::iterator i(it->second.begin()); i != it->second.end(); ++i)
		{
			event[bptr++] = 0x4A;
			__u8 *len = event+(bptr++);
			event[bptr++] = (i->tsid & 0xFF00) >> 8;
			event[bptr++] = (i->tsid & 0xFF);
			event[bptr++] = (i->onid & 0xFF00) >> 8;
			event[bptr++] = (i->onid & 0xFF);
			event[bptr++] = (i->sid & 0xFF00) >> 8;
			event[bptr++] = (i->sid & 0xFF);
			event[bptr++] = 0xB0;
			bptr += sprintf((char*)(event+bptr), "Option %d", ++cnt);
			*len = ((event+bptr) - len)-1;
		}
		int llen = bptr - 12;
		ev_struct->descriptors_loop_length_hi = (llen & 0xF00) >> 8;
		ev_struct->descriptors_loop_length_lo = (llen & 0xFF);

		time_t stime = it->first.tm;
		while( tmMap.find(stime) != tmMap.end() )
			++stime;
		event[6] += (stime - it->first.tm);
		__u16 event_id = 0;
		while( evMap.find(event_id) != evMap.end() )
			++event_id;
		event[0] = (event_id & 0xFF00) >> 8;
		event[1] = (event_id & 0xFF);
		time_event_map[it->first.tm]=std::pair<time_t, __u16>(stime, event_id);
		eventData *d = new eventData( ev_struct, bptr, eEPGCache::SCHEDULE );
		evMap[event_id] = d;
		tmMap[stime] = d;
	}
}

void eEPGCache::channel_data::startPrivateReader(int pid, int version)
{
	eDVBSectionFilterMask mask;
	memset(&mask, 0, sizeof(mask));
	mask.pid = pid;
	mask.flags = eDVBSectionFilterMask::rfCRC;
	mask.data[0] = 0xA0;
	mask.mask[0] = 0xFF;
	eDebug("start privatefilter for pid %04x and version %d", pid, version);
	if (version != -1)
	{
		mask.data[3] = version << 1;
		mask.mask[3] = 0x3E;
		mask.mode[3] = 0x3E;
	}
	seenPrivateSections.clear();
	m_PrivateReader->connectRead(slot(*this, &eEPGCache::channel_data::readPrivateData), m_PrivateConn);
	m_PrivateReader->start(mask);
#ifdef NEED_DEMUX_WORKAROUND
	m_PrevVersion=version;
#endif
}

void eEPGCache::channel_data::readPrivateData( const __u8 *data)
{
	if (!data)
		eDebug("get Null pointer from section reader !!");
	else
	{
		if ( seenPrivateSections.find( data[6] ) == seenPrivateSections.end() )
		{
#ifdef NEED_DEMUX_WORKAROUND
			int version = data[5];
			version = ((version & 0x3E) >> 1);
			can_delete = 0;
			if ( m_PrevVersion != version )
			{
				cache->privateSectionRead(m_PrivateService, data);
				seenPrivateSections.insert(data[6]);
			}
			else
				eDebug("ignore");
#else
			can_delete = 0;
			cache->privateSectionRead(m_PrivateService, data);
			seenPrivateSections.insert(data[6]);
#endif
		}
		if ( seenPrivateSections.size() == (unsigned int)(data[7] + 1) )
		{
			eDebug("[EPGC] private finished");
			if (!isRunning)
				can_delete = 1;
			int version = data[5];
			version = ((version & 0x3E) >> 1);
			startPrivateReader(m_PrivatePid, version);
		}
	}
}

#endif // ENABLE_PRIVATE_EPG
