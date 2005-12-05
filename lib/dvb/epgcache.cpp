#include <lib/dvb/epgcache.h>
#include <lib/dvb/dvb.h>

#undef EPG_DEBUG  

#include <time.h>
#include <unistd.h>  // for usleep
#include <sys/vfs.h> // for statfs
// #include <libmd5sum.h>
#include <lib/base/eerror.h>

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
	if ( !thread_running() )
	{
		eDebug("[EPGC] time updated.. start EPG Mainloop");
		run();
	}
	else
		messages.send(Message(Message::timeChanged));
}

void eEPGCache::DVBChannelAdded(eDVBChannel *chan)
{
	if ( chan )
	{
//		eDebug("[eEPGCache] add channel %p", chan);
		channel_data *data = new channel_data(this);
		data->channel = chan;
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
				}
				else
					++It;
			}
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
	nice(4);
	load();
	cleanLoop();
	exec();
	save();
}

void eEPGCache::load()
{
#if 0
	FILE *f = fopen("/hdd/epg.dat", "r");
	if (f)
	{
		unsigned char md5_saved[16];
		unsigned char md5[16];
		int size=0;
		int cnt=0;
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
		{
			char text1[13];
			fread( text1, 13, 1, f);
			if ( !strncmp( text1, "ENIGMA_EPG_V4", 13) )
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
			}
			else
				eDebug("[EPGC] don't read old epg database");
			fclose(f);
		}
	}
#endif
}

void eEPGCache::save()
{
#if 0
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
		const char *text = "ENIGMA_EPG_V4";
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
		fclose(f);
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
	}
#endif
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
		eDebug("[EPGC] stop caching events(%d)", time(0)+eDVBLocalTimeHandler::getInstance()->difference());
		zapTimer.start(UPDATE_INTERVAL, 1);
		eDebug("[EPGC] next update in %i min", UPDATE_INTERVAL / 60000);
		for (int i=0; i < 3; ++i)
		{
			seenSections[i].clear();
			calcedSections[i].clear();
		}
		singleLock l(cache->cache_lock);
		cache->channelLastUpdated[channel->getChannelID()] = time(0)+eDVBLocalTimeHandler::getInstance()->difference();
		can_delete=1;
		return true;
	}
	return false;
}

void eEPGCache::channel_data::startEPG()
{
	eDebug("[EPGC] start caching events(%d)", eDVBLocalTimeHandler::getInstance()->difference()+time(0));
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
		can_delete=1;
	}
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
			eDebug(" finished(%d)", time(0)+eDVBLocalTimeHandler::getInstance()->difference());
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

RESULT eEPGCache::lookupEventTime(const eServiceReference &service, time_t t, const eventData *&result )
// if t == 0 we search the current event...
{
	singleLock s(cache_lock);
	uniqueEPGKey key(service);

	// check if EPG for this service is ready...
	eventCache::iterator It = eventDB.find( key );
	if ( It != eventDB.end() && !It->second.first.empty() ) // entrys cached ?
	{
		if (!t)
			t = time(0)+eDVBLocalTimeHandler::getInstance()->difference();

		timeMap::iterator i = It->second.second.lower_bound(t);
		if ( i != It->second.second.end() && t <= i->first+i->second->getDuration() )
		{
			result = i->second;
			return 0;
		}
	}
	return -1;
}

RESULT eEPGCache::lookupEventTime(const eServiceReference &service, time_t t, const eit_event_struct *&result )
{
	singleLock s(cache_lock);
	const eventData *data=0;
	RESULT ret = lookupEventTime(service, t, data);
	if ( !ret && data )
		result = data->get();
	return ret;
}

RESULT eEPGCache::lookupEventTime(const eServiceReference &service, time_t t, Event *& result )
{
	singleLock s(cache_lock);
	const eventData *data=0;
	RESULT ret = lookupEventTime(service, t, data);
	if ( !ret && data )
		result = new Event((uint8_t*)data->get());
	return ret;
}

RESULT eEPGCache::lookupEventTime(const eServiceReference &service, time_t t, ePtr<eServiceEvent> &result )
{
	singleLock s(cache_lock);
	const eventData *data=0;
	RESULT ret = lookupEventTime(service, t, data);
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
			if ( m_timemap_cursor != It->second.second.end() && m_timemap_cursor != It->second.second.begin() )
			{
				timeMap::iterator it = m_timemap_cursor;
				--it;
				if ( (it->second->getStartTime() + it->second->getDuration()) > begin )
					m_timemap_cursor = it;
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
