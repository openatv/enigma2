#include <lib/dvb/epgcache.h>
#include <lib/dvb/dvb.h>

#undef EPG_DEBUG  

#include <time.h>
#include <unistd.h>  // for usleep
#include <sys/vfs.h> // for statfs
#include <libmd5sum.h>
#include <lib/base/eerror.h>

int eventData::CacheSize=0;

eEPGCache* eEPGCache::instance;
pthread_mutex_t eEPGCache::cache_lock=
	PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP;

DEFINE_REF(eEPGCache)

eEPGCache::eEPGCache()
	:messages(this,1), back_messages(this,1) ,paused(0)
	,CleanTimer(this), zapTimer(this), abortTimer(this)
{
	eDebug("[EPGC] Initialized EPGCache");
	isRunning=0;

	CONNECT(messages.recv_msg, eEPGCache::gotMessage);
	CONNECT(back_messages.recv_msg, eEPGCache::gotBackMessage);
//	CONNECT(eDVB::getInstance()->switchedService, eEPGCache::enterService);
//	CONNECT(eDVB::getInstance()->leaveService, eEPGCache::leaveService);
	CONNECT(eDVBLocalTimeHandler::getInstance()->m_timeUpdated, eEPGCache::timeUpdated);
	CONNECT(zapTimer.timeout, eEPGCache::startEPG);
	CONNECT(CleanTimer.timeout, eEPGCache::cleanLoop);
	CONNECT(abortTimer.timeout, eEPGCache::abortNonAvail);
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

int eEPGCache::sectionRead(const __u8 *data, int source)
{
	eit_t *eit = (eit_t*) data;

	int len=HILO(eit->section_length)-1;//+3-4;
	int ptr=EIT_SIZE;
	if ( ptr >= len )
		return 0;

	//
	// This fixed the EPG on the Multichoice irdeto systems
	// the EIT packet is non-compliant.. their EIT packet stinks
	if ( data[ptr-1] < 0x40 )
		--ptr;

	uniqueEPGKey service( HILO(eit->service_id), HILO(eit->original_network_id), HILO(eit->transport_stream_id) );
	eit_event_struct* eit_event = (eit_event_struct*) (data+ptr);
	int eit_event_size;
	int duration;

	time_t TM = parseDVBtime( eit_event->start_time_1, eit_event->start_time_2,	eit_event->start_time_3, eit_event->start_time_4, eit_event->start_time_5);
// FIXME !!! TIME CORRECTION !
	time_t now = time(0)+eDVBLocalTimeHandler::getInstance()->difference();

	if ( TM != 3599 && TM > -1)
	{
		switch(source)
		{
		case NOWNEXT:
			haveData |= 2;
			break;
		case SCHEDULE:
			haveData |= 1;
			break;
		case SCHEDULE_OTHER:
			haveData |= 4;
			break;
		}
	}

	Lock();
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

	tmpMap::iterator it = temp.find( service );
	if ( it != temp.end() )
	{
		if ( source > it->second.second )
		{
			it->second.first=now;
			it->second.second=source;
		}
	}
	else
		temp[service] = std::pair< time_t, int> (now, source);

	Unlock();

	return 0;
}

bool eEPGCache::finishEPG()
{
	if (!isRunning)  // epg ready
	{
		eDebug("[EPGC] stop caching events");
		zapTimer.start(UPDATE_INTERVAL, 1);
		eDebug("[EPGC] next update in %i min", UPDATE_INTERVAL / 60000);

		singleLock l(cache_lock);
		tmpMap::iterator It = temp.begin();
		abortTimer.stop();

		while (It != temp.end())
		{
//			eDebug("sid = %02x, onid = %02x, type %d", It->first.sid, It->first.onid, It->second.second );
			if ( It->second.second == SCHEDULE
				|| ( It->second.second == NOWNEXT && !(haveData&1) ) 
				)
			{
//				eDebug("ADD to last updated Map");
				serviceLastUpdated[It->first]=It->second.first;
			}
			if ( eventDB.find( It->first ) == eventDB.end() )
			{
//				eDebug("REMOVE from update Map");
				temp.erase(It++);
			}
			else
				It++;
		}
		if (!eventDB[current_service].first.empty())
			/*emit*/ EPGAvail(1);

		/*emit*/ EPGUpdated();

		return true;
	}
	return false;
}

void eEPGCache::flushEPG(const uniqueEPGKey & s)
{
	eDebug("[EPGC] flushEPG %d", (int)(bool)s);
	Lock();
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
			updateMap::iterator u = serviceLastUpdated.find(s);
			if ( u != serviceLastUpdated.end() )
				serviceLastUpdated.erase(u);
			startEPG();
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
		serviceLastUpdated.clear();
		eventDB.clear();
		startEPG();
	}
	eDebug("[EPGC] %i bytes for cache used", eventData::CacheSize);
	Unlock();
}

void eEPGCache::cleanLoop()
{
	singleLock s(cache_lock);
	if ( isRunning )
	{
		CleanTimer.start(5000,true);
		eDebug("[EPGC] schedule cleanloop");
		return;
	}
	if (!eventDB.empty() && !paused )
	{
		eDebug("[EPGC] start cleanloop");
		const eit_event_struct* cur_event;
		int duration;

// FIXME !!! TIME_CORRECTION
		time_t now = time(0)+eDVBLocalTimeHandler::getInstance()->difference();

		for (eventCache::iterator DBIt = eventDB.begin(); DBIt != eventDB.end(); DBIt++)
		{
			for (timeMap::iterator It = DBIt->second.second.begin(); It != DBIt->second.second.end() && It->first < now;)
			{
				cur_event = (*It->second).get();
				duration = fromBCD( cur_event->duration_1)*3600 + fromBCD(cur_event->duration_2)*60 + fromBCD(cur_event->duration_3);

				if ( now > (It->first+duration) )  // outdated normal entry (nvod references to)
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

					// add this (changed) service to temp map...
					if ( temp.find(DBIt->first) == temp.end() )
						temp[DBIt->first]=std::pair<time_t, int>(now, NOWNEXT);
				}
				else
					++It;
			}
			if ( DBIt->second.second.size() < 2 )  
			// less than two events for this service in cache.. 
			{
				updateMap::iterator u = serviceLastUpdated.find(DBIt->first);
				if ( u != serviceLastUpdated.end() )
				{
					// remove from lastupdated map.. 
					serviceLastUpdated.erase(u);
					// current service?
					if ( DBIt->first == current_service )
					{
					// immediate .. after leave cleanloop 
					// update epgdata for this service
						zapTimer.start(0,true);
					}
				}
			}
		}

		if (temp.size())
			/*emit*/ EPGUpdated();

		eDebug("[EPGC] stop cleanloop");
		eDebug("[EPGC] %i bytes for cache used", eventData::CacheSize);
	}
	CleanTimer.start(CLEAN_INTERVAL,true);
}

eEPGCache::~eEPGCache()
{
	messages.send(Message::quit);
	kill(); // waiting for thread shutdown
	Lock();
	for (eventCache::iterator evIt = eventDB.begin(); evIt != eventDB.end(); evIt++)
		for (eventMap::iterator It = evIt->second.first.begin(); It != evIt->second.first.end(); It++)
			delete It->second;
	Unlock();
}

Event *eEPGCache::lookupEvent(const eServiceReferenceDVB &service, int event_id, bool plain)
{
	singleLock s(cache_lock);
	uniqueEPGKey key( service );

	eventCache::iterator It = eventDB.find( key );
	if ( It != eventDB.end() && !It->second.first.empty() ) // entrys cached?
	{
		eventMap::iterator i( It->second.first.find( event_id ));
		if ( i != It->second.first.end() )
		{
			if ( service.getServiceType() == 4 ) // nvod ref
				return lookupEvent( service, i->second->getStartTime(), plain );
			else if ( plain )
		// get plain data... not in Event Format !!!
		// before use .. cast it to eit_event_struct*
				return (Event*) i->second->get();
			else
				return new Event( (uint8_t*)i->second->get() /*, (It->first.tsid<<16)|It->first.onid*/ );
		}
		else
			eDebug("event %04x not found in epgcache", event_id);
	}
	return 0;
}

Event *eEPGCache::lookupEvent(const eServiceReferenceDVB &service, time_t t, bool plain )
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
		if ( i != It->second.second.end() )
		{
			i--;
			if ( i != It->second.second.end() )
			{
				const eit_event_struct* eit_event = i->second->get();
				int duration = fromBCD(eit_event->duration_1)*3600+fromBCD(eit_event->duration_2)*60+fromBCD(eit_event->duration_3);
				if ( t <= i->first+duration )
				{
					if ( plain )
						// get plain data... not in Event Format !!!
						// before use .. cast it to eit_event_struct*
						return (Event*) i->second->get();
					return new Event( (uint8_t*)i->second->get() /*, (It->first.tsid<<16)|It->first.onid */ );
				}
			}
		}

		for ( eventMap::iterator i( It->second.first.begin() ); i != It->second.first.end(); i++)
		{
			const eit_event_struct* eit_event = i->second->get();
			int duration = fromBCD(eit_event->duration_1)*3600+fromBCD(eit_event->duration_2)*60+fromBCD(eit_event->duration_3);
			time_t begTime = parseDVBtime( eit_event->start_time_1, eit_event->start_time_2,	eit_event->start_time_3, eit_event->start_time_4,	eit_event->start_time_5);
			if ( t >= begTime && t <= begTime+duration) // then we have found
			{
				if ( plain )
					// get plain data... not in Event Format !!!
					// before use .. cast it to eit_event_struct*
					return (Event*) i->second->get();
				return new Event( (uint8_t*)i->second->get()/*, (It->first.tsid<<16)|It->first.onid*/ );
			}
		}
	}
	return 0;
}

void eEPGCache::pauseEPG()
{
	if (!paused)
	{
		abortEPG();
		eDebug("[EPGC] paused]");
		paused=1;
	}
}

void eEPGCache::restartEPG()
{
	if (paused)
	{
		isRunning=0;
		eDebug("[EPGC] restarted");
		paused--;
		if (paused)
		{
			paused = 0;
			startEPG();   // updateEPG
		}
		cleanLoop();
	}
}

void eEPGCache::startEPG()
{
	if (paused)  // called from the updateTimer during pause...
	{
		paused++;
		return;
	}
	if (eDVBLocalTimeHandler::getInstance()->ready())
	{
		Lock();
		temp.clear();
		Unlock();
		eDebug("[EPGC] start caching events");
		state=0;
		haveData=0;

		eDVBSectionFilterMask mask;
		memset(&mask, 0, sizeof(mask));
		mask.pid = 0x12;
		mask.flags = eDVBSectionFilterMask::rfCRC;

		mask.data[0] = 0x4E;
		mask.mask[0] = 0xFE;
		m_NowNextReader->start(mask);
		isRunning |= 1;

		mask.data[0] = 0x50;
		mask.mask[0] = 0xF0;
		m_ScheduleReader->start(mask);
		isRunning |= 2;

		mask.data[0] = 0x60;
		mask.mask[0] = 0xF0;
		m_ScheduleOtherReader->start(mask);
		isRunning |= 4;

		abortTimer.start(5000,true);
	}
	else
	{
		eDebug("[EPGC] wait for clock update");
		zapTimer.start(1000, 1); // restart Timer
	}
}

void eEPGCache::abortNonAvail()
{
	if (!state)
	{
		if ( !(haveData&2) && (isRunning&2) )
		{
			eDebug("[EPGC] abort non avail nownext reading");
			isRunning &= ~2;
			if ( m_NowNextReader )
				m_NowNextReader->stop();
		}
		if ( !(haveData&1) && (isRunning&1) )
		{
			eDebug("[EPGC] abort non avail schedule reading");
			isRunning &= ~1;
			m_ScheduleReader->stop();
		}
		if ( !(haveData&4) && (isRunning&4) )
		{
			eDebug("[EPGC] abort non avail schedule_other reading");
			isRunning &= ~4;
			m_ScheduleOtherReader->stop();
		}
		abortTimer.start(20000, true);
	}
	++state;
}

void eEPGCache::startCache(const eServiceReferenceDVB& ref)
{
	if ( m_currentChannel )
	{
		next_service = ref;
		leaveChannel(m_currentChannel);
		return;
	}
	eDVBChannelID chid;
	ref.getChannelID( chid );
	ePtr<eDVBResourceManager> res_mgr;
	if ( eDVBResourceManager::getInstance( res_mgr ) )
		eDebug("[eEPGCache] no res manager!!");
	else
	{
		ePtr<iDVBDemux> demux;
		res_mgr->allocateChannel(chid, m_currentChannel);
		if ( m_currentChannel->getDemux(demux) )
		{
			eDebug("[eEPGCache] no demux!!");
			goto error4;
		}
		else
		{
			RESULT res;
			m_NowNextReader = new eDVBSectionReader( demux, this, res );
			if ( res )
			{
				eDebug("[eEPGCache] couldnt initialize nownext reader!!");
				goto error3;
			}
			m_NowNextReader->connectRead(slot(*this, &eEPGCache::readNowNextData), m_NowNextConn);
			m_ScheduleReader = new eDVBSectionReader( demux, this, res );
			if ( res )
			{
				eDebug("[eEPGCache] couldnt initialize schedule reader!!");
				goto error2;
			}
			m_ScheduleReader->connectRead(slot(*this, &eEPGCache::readScheduleData), m_ScheduleConn);
			m_ScheduleOtherReader = new eDVBSectionReader( demux, this, res );
			if ( res )
			{
				eDebug("[eEPGCache] couldnt initialize schedule other reader!!");
				goto error1;
			}
			m_ScheduleOtherReader->connectRead(slot(*this, &eEPGCache::readScheduleOtherData), m_ScheduleOtherConn);
			messages.send(Message(Message::startService, ref));
			// -> gotMessage -> changedService
		}
	}
	return;
error1:
	m_ScheduleOtherReader=0;
	m_ScheduleOtherConn=0;
error2:
	m_ScheduleReader=0;
	m_ScheduleConn=0;
error3:
	m_NowNextReader=0;
	m_NowNextConn=0;
error4:
	m_currentChannel=0;
}

void eEPGCache::leaveChannel(iDVBChannel * chan)
{
	if ( chan && chan == m_currentChannel )
	{
		messages.send(Message(Message::leaveChannel, chan));
	// -> gotMessage -> abortEPG
	}
}

void eEPGCache::changedService(const uniqueEPGKey &service)
{
	current_service = service;
	updateMap::iterator It = serviceLastUpdated.find( current_service );

	int update;

// check if this is a subservice and this is only a dbox2
// then we dont start epgcache on subservice change..
// ever and ever..

//	if ( !err || err == -ENOCASYS )
	{
		update = ( It != serviceLastUpdated.end() ? ( UPDATE_INTERVAL - ( (time(0)+eDVBLocalTimeHandler::getInstance()->difference()-It->second) * 1000 ) ) : ZAP_DELAY );

		if (update < ZAP_DELAY)
			update = ZAP_DELAY;

		zapTimer.start(update, 1);
		if (update >= 60000)
			eDebug("[EPGC] next update in %i min", update/60000);
		else if (update >= 1000)
			eDebug("[EPGC] next update in %i sec", update/1000);
	}

	Lock();
	bool empty=eventDB[current_service].first.empty();
	Unlock();

	if (!empty)
	{
		eDebug("[EPGC] yet cached");
		/*emit*/ EPGAvail(1);
	}
	else
	{
		eDebug("[EPGC] not cached yet");
		/*emit*/ EPGAvail(0);
	}
}

void eEPGCache::abortEPG()
{
	abortTimer.stop();
	zapTimer.stop();
	if (isRunning)
	{
		if (isRunning & 1)
		{
			isRunning &= ~1;
			if ( m_ScheduleReader )
				m_ScheduleReader->stop();
		}
		if (isRunning & 2)
		{
			isRunning &= ~2;
			if ( m_NowNextReader )
				m_NowNextReader->stop();
		}
		if (isRunning & 4)
		{
			isRunning &= ~4;
			if ( m_ScheduleOtherReader )
				m_ScheduleOtherReader->stop();
		}
		eDebug("[EPGC] abort caching events !!");
		Lock();
		temp.clear();
		Unlock();
	}
}

void eEPGCache::gotMessage( const Message &msg )
{
	switch (msg.type)
	{
		case Message::flush:
			flushEPG(msg.service);
			break;
		case Message::startService:
			changedService(msg.service);
			break;
		case Message::leaveChannel:
			abortEPG();
			back_messages.send(Message(Message::leaveChannelFinished));
			break;
		case Message::pause:
			pauseEPG();
			break;
		case Message::restart:
			restartEPG();
			break;
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

void eEPGCache::gotBackMessage( const Message &msg )
{
	switch (msg.type)
	{
		case Message::leaveChannelFinished:
			m_ScheduleOtherReader=0;
			m_ScheduleOtherConn=0;
			m_ScheduleReader=0;
			m_ScheduleConn=0;
			m_NowNextReader=0;
			m_NowNextConn=0;
			m_currentChannel=0;
			eDebug("[eEPGC] channel leaved");
			if (next_service)
			{
				startCache(next_service);
				next_service = eServiceReferenceDVB();
			}
			break;
		default:
			eDebug("unhandled EPGCache BackMessage!!");
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
					int len=0;
					int type=0;
					eventData *event=0;
					fread( &type, sizeof(int), 1, f);
					fread( &len, sizeof(int), 1, f);
					event = new eventData(0, len, type);
					fread( event->EITdata, len, 1, f);
					evMap[ event->getEventID() ]=event;
					tmMap[ event->getStartTime() ]=event;
					++cnt;
				}
				eventDB[key]=std::pair<eventMap,timeMap>(evMap,tmMap);
			}
			eDebug("%d events read from /hdd/epg.dat.md5", cnt);
		}
		fclose(f);
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
				int len = time_it->second->ByteSize;
				fwrite( &time_it->second->type, sizeof(int), 1, f );
				fwrite( &len, sizeof(int), 1, f);
				fwrite( time_it->second->EITdata, len, 1, f);
				++cnt;
			}
		}
		eDebug("%d events written to /hdd/epg.dat", cnt);
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
}

RESULT eEPGCache::getInstance(ePtr<eEPGCache> &ptr)
{
	ptr = instance;
	if (!ptr)
		return -1;
	return 0;
}

