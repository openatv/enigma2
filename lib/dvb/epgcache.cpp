#include <lib/dvb/epgcache.h>
#include <lib/dvb/dvb.h>
#include <lib/dvb/lowlevel/eit.h>

#undef EPG_DEBUG

#ifdef EPG_DEBUG
#include <lib/service/event.h>
#endif

#include <deque>
#include <fstream>
#include <time.h>
#include <unistd.h>  // for usleep
#include <sys/vfs.h> // for statfs
#include <lib/base/cfile.h>
#include <lib/base/eerror.h>
#include <lib/base/encoding.h>
#include <lib/base/estring.h>
#include <lib/dvb/pmt.h>
#include <lib/dvb/db.h>
#include <lib/python/python.h>
#include <lib/base/nconfig.h>
#include <dvbsi++/descriptor_tag.h>

#define HILO(x) (x##_hi << 8 | x##_lo)

/* Interval between "garbage collect" cycles */
#define CLEAN_INTERVAL 60000    //  1 min
/* Restart EPG data capture */
#define UPDATE_INTERVAL 3600000  // 60 min
/* Time to wait after tuning in before EPG data capturing starts */
#define ZAP_DELAY 2000          // 2 sec

struct DescriptorPair
{
	int reference_count;
	__u8* data;

	DescriptorPair() {}
	DescriptorPair(int c, __u8* d): reference_count(c), data(d) {}
};

typedef std::map<uint32_t, DescriptorPair> DescriptorMap;

struct eventData
{
	uint8_t rawEITdata[10];
	uint8_t n_crc;
	uint8_t type;
	uint32_t *crc_list;
	static DescriptorMap descriptors;
	static uint8_t data[];
	static unsigned int CacheSize;
	static bool isCacheCorrupt;
	eventData(const eit_event_struct* e = NULL, int size = 0, int type = 0, int tsidonid = 0);
	~eventData();
	static void load(FILE *);
	static void save(FILE *);
	static void cacheCorrupt(const char* context);
	const eit_event_struct* get() const;
	int getEventID() const
	{
		return (rawEITdata[0] << 8) | rawEITdata[1];
	}
	time_t getStartTime() const
	{
		return parseDVBtime(&rawEITdata[2]);
	}
	int getDuration() const
	{
		return fromBCD(rawEITdata[7])*3600+fromBCD(rawEITdata[8])*60+fromBCD(rawEITdata[9]);
	}
};

unsigned int eventData::CacheSize = 0;
bool eventData::isCacheCorrupt = 0;
DescriptorMap eventData::descriptors;
uint8_t eventData::data[2 * 4096 + 12];
extern const uint32_t crc32_table[256];

const eServiceReference &handleGroup(const eServiceReference &ref)
{
	if (ref.flags & eServiceReference::isGroup)
	{
		ePtr<eDVBResourceManager> res;
		if (!eDVBResourceManager::getInstance(res))
		{
			ePtr<iDVBChannelList> db;
			if (!res->getChannelList(db))
			{
				eBouquet *bouquet=0;
				if (!db->getBouquet(ref, bouquet))
				{
					std::list<eServiceReference>::iterator it(bouquet->m_services.begin());
					if (it != bouquet->m_services.end())
						return *it;
				}
			}
		}
	}
	return ref;
}

static uint32_t calculate_crc_hash(const uint8_t *data, int size)
{
	uint32_t crc = 0;
	for (int i = 0; i < size; ++i)
		crc = (crc << 8) ^ crc32_table[((crc >> 24) ^ data[i]) & 0xFF];
	return crc;
}

eventData::eventData(const eit_event_struct* e, int size, int _type, int tsidonid)
	:n_crc(0), type(_type & 0xFF), crc_list(NULL)
{
	if (!e)
		return; /* Used when loading from file */

	uint32_t descr[65];
	uint32_t *pdescr=descr;

	uint8_t *data = (uint8_t*)e;
	int ptr=12;
	size -= 12;

	while(size > 1)
	{
		uint8_t *descr = data + ptr;
		int descr_len = descr[1];
		descr_len += 2;
		if (size >= descr_len)
		{
			switch (descr[0])
			{
				case EXTENDED_EVENT_DESCRIPTOR:
				case LINKAGE_DESCRIPTOR:
				case COMPONENT_DESCRIPTOR:
				case CONTENT_DESCRIPTOR:
				case PARENTAL_RATING_DESCRIPTOR:
				{
					uint32_t crc = calculate_crc_hash(descr, descr_len);
					DescriptorMap::iterator it = descriptors.find(crc);
					if ( it == descriptors.end() )
					{
						CacheSize+=descr_len;
						uint8_t *d = new uint8_t[descr_len];
						memcpy(d, descr, descr_len);
						descriptors[crc] = DescriptorPair(1, d);
					}
					else
						++it->second.reference_count;
					*pdescr++ = crc;
					break;
				}
				case SHORT_EVENT_DESCRIPTOR:
				{
					//parse the data out from the short event descriptor
					//get the country code, which will be used for converting to UTF8
					std::string cc( (const char*)&descr[2], 3);
					std::transform(cc.begin(), cc.end(), cc.begin(), tolower);
					int table = encodingHandler.getCountryCodeDefaultMapping(cc);

					int eventNameLen = descr[5];
					int eventTextLen = descr[6 + eventNameLen];

					//convert our strings to UTF8
					std::string eventNameUTF8 = convertDVBUTF8((const unsigned char*)&descr[6], eventNameLen, table, tsidonid);
					std::string textUTF8 = convertDVBUTF8((const unsigned char*)&descr[7 + eventNameLen], eventTextLen, table, tsidonid);
					unsigned int eventNameUTF8len = eventNameUTF8.length();
					unsigned int textUTF8len = textUTF8.length();

					//Rebuild the short event descriptor with UTF-8 strings

					//Save the title first
					if( eventNameUTF8len > 0 ) //only store the data if there is something to store
					{
						/*this will actually cause us to save some memory
						 previously some descriptors didnt match because there text was different and titles the same.
						 Now that we store them seperatly we can save some space on title data some rough calculation show anywhere from 20 - 40% savings
						*/
						eventNameUTF8len = truncateUTF8(eventNameUTF8, 255 - 6);
						int title_len = 6 + eventNameUTF8len;
						uint8_t *title_data = new uint8_t[title_len + 2];
						title_data[0] = SHORT_EVENT_DESCRIPTOR;
						title_data[1] = title_len;
						title_data[2] = descr[2];
						title_data[3] = descr[3];
						title_data[4] = descr[4];
						title_data[5] = eventNameUTF8len + 1;
						title_data[6] = 0x15; //identify event name as UTF-8
						memcpy(&title_data[7], eventNameUTF8.data(), eventNameUTF8len);
						title_data[7 + eventNameUTF8len] = 0;

						//Calculate the CRC, based on our new data
						title_len += 2; //add 2 the length to include the 2 bytes in the header
						uint32_t title_crc = calculate_crc_hash(title_data, title_len);

						DescriptorMap::iterator it = descriptors.find(title_crc);
						if ( it == descriptors.end() )
						{
							CacheSize += title_len;
							descriptors[title_crc] = DescriptorPair(1, title_data);
						}
						else
						{
							++it->second.reference_count;
							delete [] title_data;
						}
						*pdescr++ = title_crc;
					}

					//save the text
					if( textUTF8len > 0 ) //only store the data if there is something to store
					{
						textUTF8len = truncateUTF8(textUTF8, 255 - 6);
						int text_len = 6 + textUTF8len;
						uint8_t *text_data = new uint8_t[text_len + 2];
						text_data[0] = SHORT_EVENT_DESCRIPTOR;
						text_data[1] = text_len;
						text_data[2] = descr[2];
						text_data[3] = descr[3];
						text_data[4] = descr[4];
						text_data[5] = 0;
						text_data[6] = textUTF8len + 1; //identify text as UTF-8
						text_data[7] = 0x15; //identify text as UTF-8
						memcpy(&text_data[8], textUTF8.data(), textUTF8len);

						text_len += 2; //add 2 the length to include the 2 bytes in the header
						uint32_t text_crc = calculate_crc_hash(text_data, text_len);

						DescriptorMap::iterator it = descriptors.find(text_crc);
						if ( it == descriptors.end() )
						{
							CacheSize += text_len;
							descriptors[text_crc] = DescriptorPair(1, text_data);
						}
						else
						{
							++it->second.reference_count;
							delete [] text_data;
						}
						*pdescr++ = text_crc;
					}
					break;
				}
				default: // do not cache all other descriptors
					break;
			}
			ptr += descr_len;
			size -= descr_len;
		}
		else
			break;
	}
	memcpy(rawEITdata, (uint8_t*)e, 10);
	ASSERT(pdescr <= &descr[65]);
	n_crc = pdescr - descr;
	if (n_crc)
	{
		crc_list = new uint32_t[n_crc];
		memcpy(crc_list, descr, n_crc * sizeof(uint32_t));
	}
	CacheSize += sizeof(*this) + n_crc * sizeof(uint32_t);
}

const eit_event_struct* eventData::get() const
{
	unsigned int pos = 12;
	memcpy(data, rawEITdata, 10);
	unsigned int descriptors_length = 0;
	for (uint8_t i = 0; i < n_crc; ++i)
	{
		DescriptorMap::iterator it = descriptors.find(crc_list[i]);
		if (it != descriptors.end())
		{
			unsigned int b = it->second.data[1] + 2;
			if (pos + b < sizeof(data))
			{
				memcpy(data + pos, it->second.data, b);
				pos += b;
				descriptors_length += b;
			}
		}
		else
			cacheCorrupt("eventData::get");
	}
	data[10] = (descriptors_length >> 8) & 0x0F;
	data[11] = descriptors_length & 0xFF;
	return (eit_event_struct*)data;
}

eventData::~eventData()
{
	for ( uint8_t i = 0; i < n_crc; ++i )
	{
		DescriptorMap::iterator it = descriptors.find(crc_list[i]);
		if ( it != descriptors.end() )
		{
			DescriptorPair &p = it->second;
			if (!--p.reference_count) // no more used descriptor
			{
				CacheSize -= it->second.data[1];
				delete [] it->second.data;  	// free descriptor memory
				descriptors.erase(it);	// remove entry from descriptor map
			}
		}
		else
		{
			cacheCorrupt("eventData::~eventData");
		}
	}
	delete [] crc_list;
	CacheSize -= sizeof(*this) + n_crc * sizeof(uint32_t);
}

void eventData::load(FILE *f)
{
	int size=0;
	int id=0;
	uint8_t header[2];
	DescriptorPair p;
	fread(&size, sizeof(int), 1, f);
	while(size)
	{
		fread(&id, sizeof(uint32_t), 1, f);
		fread(&p.reference_count, sizeof(int), 1, f);
		fread(header, 2, 1, f);
		int bytes = header[1]+2;
		p.data = new uint8_t[bytes];
		p.data[0] = header[0];
		p.data[1] = header[1];
		fread(p.data+2, bytes-2, 1, f);
		descriptors[id] = p;
		--size;
		CacheSize += bytes;
	}
}

void eventData::save(FILE *f)
{
	if (isCacheCorrupt)
		return;
	int size=descriptors.size();
	DescriptorMap::iterator it(descriptors.begin());
	fwrite(&size, sizeof(int), 1, f);
	while(size)
	{
		fwrite(&it->first, sizeof(uint32_t), 1, f);
		fwrite(&it->second.reference_count, sizeof(int), 1, f);
		fwrite(it->second.data, it->second.data[1]+2, 1, f);
		++it;
		--size;
	}
}

void eventData::cacheCorrupt(const char* context)
{

	eDebug("WARNING: EPG Cache is corrupt (%s), you should restart Enigma!", context);
	if (!isCacheCorrupt)
	{
		isCacheCorrupt = true;
		if (!eEPGCache::instance->m_filename.empty())
			unlink(eEPGCache::instance->m_filename.c_str()); // Remove corrupt EPG data
	}
}


eEPGCache* eEPGCache::instance;
static pthread_mutex_t cache_lock =
	PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP;
static pthread_mutex_t channel_map_lock =
	PTHREAD_RECURSIVE_MUTEX_INITIALIZER_NP;

DEFINE_REF(eEPGCache)

eEPGCache::eEPGCache()
	:messages(this,1), cleanTimer(eTimer::create(this)), m_running(false)
{
	eDebug("[EPGC] Initialized EPGCache (wait for setCacheFile call now)");

	enabledSources = 0;
	historySeconds = 0;

	CONNECT(messages.recv_msg, eEPGCache::gotMessage);
	CONNECT(eDVBLocalTimeHandler::getInstance()->m_timeUpdated, eEPGCache::timeUpdated);
	CONNECT(cleanTimer->timeout, eEPGCache::cleanLoop);

	std::ifstream onid_file;
	onid_file.open("/etc/enigma2/blacklist.onid");
	int tmp_onid;

	while (onid_file >> std::hex >>tmp_onid)
	         onid_blacklist.insert(onid_blacklist.end(),1,tmp_onid);
	onid_file.close();

	ePtr<eDVBResourceManager> res_mgr;
	eDVBResourceManager::getInstance(res_mgr);
	if (!res_mgr)
		eDebug("[eEPGCache] no resource manager !!!!!!!");
	else
		res_mgr->connectChannelAdded(slot(*this,&eEPGCache::DVBChannelAdded), m_chanAddedConn);

	instance=this;
}

void eEPGCache::setCacheFile(const char *path)
{
	bool inited = !m_filename.empty();
	m_filename = path;
	if (!inited)
	{
		eDebug("[EPGC] setCacheFile read/write epg data from/to '%s'", m_filename.c_str());
		if (eDVBLocalTimeHandler::getInstance()->ready())
			timeUpdated();
	}
}

void eEPGCache::timeUpdated()
{
	if (!m_filename.empty())
	{
		if (!m_running)
		{
			eDebug("[EPGC] time updated.. start EPG Mainloop");
			run();
			m_running = true;
			singleLock s(channel_map_lock);
			channelMapIterator it = m_knownChannels.begin();
			for (; it != m_knownChannels.end(); ++it)
			{
				if (it->second->state == -1) {
					it->second->state=0;
					messages.send(Message(Message::startChannel, it->first));
				}
			}
		} else
			messages.send(Message(Message::timeChanged));
	}
	else
		eDebug("[EPGC] time updated.. but cache file not set yet.. dont start epg!!");
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
#ifdef ENABLE_MHW_EPG
		data->m_mhw2_channel_pid = 0x231; // defaults for astra 19.2 D+
		data->m_mhw2_title_pid = 0x234; // defaults for astra 19.2 D+
		data->m_mhw2_summary_pid = 0x236; // defaults for astra 19.2 D+
#endif
		singleLock s(channel_map_lock);
		m_knownChannels.insert( std::pair<iDVBChannel*, channel_data* >(chan, data) );
		chan->connectStateChange(slot(*this, &eEPGCache::DVBChannelStateChanged), data->m_stateChangedConn);
	}
}

void eEPGCache::DVBChannelRunning(iDVBChannel *chan)
{
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

#ifdef ENABLE_VIRGIN
				res = demux->createSectionReader( this, data.m_VirginNowNextReader );
				if ( res )
				{
					eDebug("[eEPGCache] couldnt initialize virgin nownext reader!!");
					return;
				}

				res = demux->createSectionReader( this, data.m_VirginScheduleReader );
				if ( res )
				{
					eDebug("[eEPGCache] couldnt initialize virgin schedule reader!!");
					return;
				}
#endif
#ifdef ENABLE_NETMED
				res = demux->createSectionReader( this, data.m_NetmedScheduleReader );
				if ( res )
				{
					eDebug("[eEPGCache] couldnt initialize netmed schedule reader!!");
					return;
				}

				res = demux->createSectionReader( this, data.m_NetmedScheduleOtherReader );
				if ( res )
				{
					eDebug("[eEPGCache] couldnt initialize netmed schedule other reader!!");
					return;
				}
#endif
				res = demux->createSectionReader( this, data.m_ViasatReader );
				if ( res )
				{
					eDebug("[eEPGCache] couldnt initialize viasat reader!!");
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
#ifdef ENABLE_MHW_EPG
				res = demux->createSectionReader( this, data.m_MHWReader );
				if ( res )
				{
					eDebug("[eEPGCache] couldnt initialize mhw reader!!");
					return;
				}
				res = demux->createSectionReader( this, data.m_MHWReader2 );
				if ( res )
				{
					eDebug("[eEPGCache] couldnt initialize mhw reader!!");
					return;
				}
#endif
#if ENABLE_FREESAT
				res = demux->createSectionReader( this, data.m_FreeSatScheduleOtherReader );
				if ( res )
				{
					eDebug("[eEPGCache] couldnt initialize FreeSat reader!!");
					return;
				}
				res = demux->createSectionReader( this, data.m_FreeSatScheduleOtherReader2 );
				if ( res )
				{
					eDebug("[eEPGCache] couldnt initialize FreeSat reader 2!!");
					return;
				}
#endif
				if (m_running)
				{
					data.state = 0;
					messages.send(Message(Message::startChannel, chan));
					// -> gotMessage -> changedService
				}
				else
					data.state=-1;
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
					if (it->second->state >= 0)
						messages.send(Message(Message::leaveChannel, chan));
					pthread_mutex_lock(&it->second->channel_active);
					{
						singleLock s(channel_map_lock);
						m_knownChannels.erase(it);
					}
					pthread_mutex_unlock(&it->second->channel_active);
					delete it->second;
					it->second = 0;
					// -> gotMessage -> abortEPG
					break;
				}
				default: // ignore all other events
					return;
			}
			if (it->second)
				it->second->prevChannelState = state;
		}
	}
}

bool eEPGCache::FixOverlapping(std::pair<eventMap,timeMap> &servicemap, time_t TM, int duration, const timeMap::iterator &tm_it, const uniqueEPGKey &service)
{
	bool ret = false;
	timeMap::iterator tmp = tm_it;
	while ((tmp->first+tmp->second->getDuration()-300) > TM)
	{
		if(tmp->first != TM
#ifdef ENABLE_PRIVATE_EPG
			&& tmp->second->type != PRIVATE
#endif
#ifdef ENABLE_MHW_EPG
			&& tmp->second->type != MHW
#endif
			)
		{
			uint16_t event_id = tmp->second->getEventID();
			servicemap.first.erase(event_id);
#ifdef EPG_DEBUG
			Event evt((uint8_t*)tmp->second->get());
			eServiceEvent event;
			event.parseFrom(&evt, service.sid<<16|service.onid);
			eDebug("(1)erase no more used event %04x %d\n%s %s\n%s",
				service.sid, event_id,
				event.getBeginTimeString().c_str(),
				event.getEventName().c_str(),
				event.getExtendedDescription().c_str());
#endif
			delete tmp->second;
			if (tmp == servicemap.second.begin())
			{
				servicemap.second.erase(tmp);
				break;
			}
			else
				servicemap.second.erase(tmp--);
			ret = true;
		}
		else
		{
			if (tmp == servicemap.second.begin())
				break;
			--tmp;
		}
	}

	tmp = tm_it;
	while(tmp->first < (TM+duration-300))
	{
		if (tmp->first != TM && tmp->second->type != PRIVATE)
		{
			uint16_t event_id = tmp->second->getEventID();
			servicemap.first.erase(event_id);
#ifdef EPG_DEBUG
			Event evt((uint8_t*)tmp->second->get());
			eServiceEvent event;
			event.parseFrom(&evt, service.sid<<16|service.onid);
			eDebug("(2)erase no more used event %04x %d\n%s %s\n%s",
				service.sid, event_id,
				event.getBeginTimeString().c_str(),
				event.getEventName().c_str(),
				event.getExtendedDescription().c_str());
#endif
			delete tmp->second;
			servicemap.second.erase(tmp++);
			ret = true;
		}
		else
			++tmp;
		if (tmp == servicemap.second.end())
			break;
	}
	return ret;
}

void eEPGCache::sectionRead(const uint8_t *data, int source, channel_data *channel)
{
	const eit_t *eit = (const eit_t*) data;

	int len = HILO(eit->section_length) - 1;
	int ptr = EIT_SIZE;
	if ( ptr >= len )
		return;

#if 0
		/*
		 * disable for now, as this hack breaks EIT parsing for
		 * services with a low segment_last_table_id
		 *
		 * Multichoice should be the exception, not the rule...
		 */

	// This fixed the EPG on the Multichoice irdeto systems
	// the EIT packet is non-compliant.. their EIT packet stinks
	if ( data[ptr-1] < 0x40 )
		--ptr;
#endif

	int onid = HILO(eit->original_network_id);
	int tsid  = HILO(eit->transport_stream_id);

	// Cablecom HACK .. tsid / onid in eit data are incorrect.. so we use
	// it from running channel (just for current transport stream eit data)
	/*
	 * Make an exception for BEV (onid 0x100, 0x101), which doesn't use
	 * SCHEDULE_OTHER. As a result SCHEDULE will contain data for different tsid's,
	 * so we should not replace it with the current tsid.
	 */
	bool use_transponder_chid = onid != 0x101 && onid != 0x100 && (source == SCHEDULE || (source == NOWNEXT && data[0] == 0x4E));

	if (use_transponder_chid && channel)
	{
		eDVBChannelID chid = channel->channel->getChannelID();

		onid = chid.original_network_id.get();
		tsid = chid.transport_stream_id.get();
	}
	uniqueEPGKey service( HILO(eit->service_id), onid, tsid);

	eit_event_struct* eit_event = (eit_event_struct*) (data+ptr);
	int eit_event_size;
	int duration;

	time_t TM = parseDVBtime((const uint8_t*)eit_event + 2);
	time_t now = ::time(0);

	if ( TM != 3599 && TM > -1 && channel)
		channel->haveData |= source;

	singleLock s(cache_lock);
	// hier wird immer eine eventMap zurck gegeben.. entweder eine vorhandene..
	// oder eine durch [] erzeugte
	std::pair<eventMap,timeMap> &servicemap = eventDB[service];
	eventMap::iterator prevEventIt = servicemap.first.end();
	timeMap::iterator prevTimeIt = servicemap.second.end();

	while (ptr<len)
	{
		uint16_t event_hash;
		eit_event_size = HILO(eit_event->descriptors_loop_length)+EIT_LOOP_SIZE;

		duration = fromBCD(eit_event->duration_1)*3600+fromBCD(eit_event->duration_2)*60+fromBCD(eit_event->duration_3);
		TM = parseDVBtime((const uint8_t*)eit_event + 2, &event_hash);

		std::vector<int>::iterator m_it=find(onid_blacklist.begin(),onid_blacklist.end(),onid);
		if (m_it != onid_blacklist.end())
			goto next;

		if ( (TM != 3599) &&		// NVOD Service
		     (now <= (TM+duration)) &&	// skip old events
		     (TM < (now+28*24*60*60)) &&	// no more than 4 weeks in future
		     ( (onid != 1714) || (duration != (24*3600-1)) )	// PlatformaHD invalid event
		   )
		{
			uint16_t event_id = HILO(eit_event->event_id);
			eventData *evt = 0;
			int ev_erase_count = 0;
			int tm_erase_count = 0;

			if (event_id == 0) {
				// hack for some polsat services on 13.0E..... but this also replaces other valid event_ids with value 0..
				// but we dont care about it...
				event_id = event_hash;
				eit_event->event_id_hi = event_hash >> 8;
				eit_event->event_id_lo = event_hash & 0xFF;
			}

			// search in eventmap
			eventMap::iterator ev_it =
				servicemap.first.find(event_id);

//			eDebug("event_id is %d sid is %04x", event_id, service.sid);

			// entry with this event_id is already exist ?
			if ( ev_it != servicemap.first.end() )
			{
				if ( source > ev_it->second->type )  // update needed ?
					goto next; // when not.. then skip this entry

				// search this event in timemap
				timeMap::iterator tm_it_tmp =
					servicemap.second.find(ev_it->second->getStartTime());

				if ( tm_it_tmp != servicemap.second.end() )
				{
					if ( tm_it_tmp->first == TM ) // just update eventdata
					{
						// exempt memory
						eventData *tmp = ev_it->second;
						ev_it->second = tm_it_tmp->second =
							new eventData(eit_event, eit_event_size, source, (tsid<<16)|onid);
						if (FixOverlapping(servicemap, TM, duration, tm_it_tmp, service))
						{
							prevEventIt = servicemap.first.end();
							prevTimeIt = servicemap.second.end();
						}
						delete tmp;
						goto next;
					}
					else  // event has new event begin time
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
				// event with same start time but another event_id...
				if ( source > tm_it->second->type &&
					ev_it == servicemap.first.end() )
					goto next; // when not.. then skip this entry

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
			evt = new eventData(eit_event, eit_event_size, source, (tsid<<16)|onid);
#ifdef EPG_DEBUG
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
				ev_it=prevEventIt=servicemap.first.insert( prevEventIt, std::pair<const uint16_t, eventData*>( event_id, evt) );
				tm_it->second=evt;
			}
			else // added new eventData
			{
#ifdef EPG_DEBUG
				consistencyCheck=false;
#endif
				ev_it=prevEventIt=servicemap.first.insert( prevEventIt, std::pair<const uint16_t, eventData*>( event_id, evt) );
				tm_it=prevTimeIt=servicemap.second.insert( prevTimeIt, std::pair<const time_t, eventData*>( TM, evt ) );
			}

#ifdef EPG_DEBUG
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
			if (FixOverlapping(servicemap, TM, duration, tm_it, service))
			{
				prevEventIt = servicemap.first.end();
				prevTimeIt = servicemap.second.end();
			}
		}
next:
#ifdef EPG_DEBUG
		if ( servicemap.first.size() != servicemap.second.size() )
		{
			{
				CFile f("/hdd/event_map.txt", "w+");
				int i = 0;
				for (eventMap::iterator it(servicemap.first.begin()); it != servicemap.first.end(); ++it )
				{
					fprintf(f, "%d(key %d) -> time %d, event_id %d, data %p\n",
					i++, (int)it->first, (int)it->second->getStartTime(), (int)it->second->getEventID(), it->second );
				}
			}
			{
				CFile f("/hdd/time_map.txt", "w+");
				int i = 0;
				for (timeMap::iterator it(servicemap.second.begin()); it != servicemap.second.end(); ++it )
				{
					fprintf(f, "%d(key %d) -> time %d, event_id %d, data %p\n",
						i++, (int)it->first, (int)it->second->getStartTime(), (int)it->second->getEventID(), it->second );
				}
			}
			eFatal("(1)map sizes not equal :( sid %04x tsid %04x onid %04x size %d size2 %d",
				service.sid, service.tsid, service.onid,
				servicemap.first.size(), servicemap.second.size() );
		}
#endif
		ptr += eit_event_size;
		eit_event=(eit_event_struct*)(((uint8_t*)eit_event)+eit_event_size);
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
}

void eEPGCache::cleanLoop()
{
	{ /* scope for cache lock */
		time_t now = ::time(0) - historySeconds;
		singleLock s(cache_lock);

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
					timeMap &tmMap = DBIt->second.second;
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
	} /* release lock */
	cleanTimer->start(CLEAN_INTERVAL,true);
}

eEPGCache::~eEPGCache()
{
	m_running = false;
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
			singleLock s(channel_map_lock);
			for (channelMapIterator it(m_knownChannels.begin()); it != m_knownChannels.end(); ++it)
			{
				eDVBChannel *channel = (eDVBChannel*) it->first;
				channel_data *data = it->second;
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
					updateMap::iterator It = channelLastUpdated.find( chid );
					int update = ( It != channelLastUpdated.end() ? ( UPDATE_INTERVAL - ( (::time(0)-It->second) * 1000 ) ) : ZAP_DELAY );
					if (update < ZAP_DELAY)
						update = ZAP_DELAY;
					data->startPrivateTimer->start(update, 1);
					if (update >= 60000)
						eDebug("[EPGC] next private update in %i min", update/60000);
					else if (update >= 1000)
						eDebug("[EPGC] next private update in %i sec", update/1000);
					break;
				}
			}
			break;
		}
#endif
#ifdef ENABLE_MHW_EPG
		case Message::got_mhw2_channel_pid:
		{
			singleLock s(channel_map_lock);
			for (channelMapIterator it(m_knownChannels.begin()); it != m_knownChannels.end(); ++it)
			{
				eDVBChannel *channel = (eDVBChannel*) it->first;
				channel_data *data = it->second;
				eDVBChannelID chid = channel->getChannelID();
				if ( chid.transport_stream_id.get() == msg.service.tsid &&
					chid.original_network_id.get() == msg.service.onid )
				{
					data->m_mhw2_channel_pid = msg.pid;
					eDebug("[EPGC] got mhw2 channel pid %04x", msg.pid);
					break;
				}
			}
			break;
		}
		case Message::got_mhw2_title_pid:
		{
			singleLock s(channel_map_lock);
			for (channelMapIterator it(m_knownChannels.begin()); it != m_knownChannels.end(); ++it)
			{
				eDVBChannel *channel = (eDVBChannel*) it->first;
				channel_data *data = it->second;
				eDVBChannelID chid = channel->getChannelID();
				if ( chid.transport_stream_id.get() == msg.service.tsid &&
					chid.original_network_id.get() == msg.service.onid )
				{
					data->m_mhw2_title_pid = msg.pid;
					eDebug("[EPGC] got mhw2 title pid %04x", msg.pid);
					break;
				}
			}
			break;
		}
		case Message::got_mhw2_summary_pid:
		{
			singleLock s(channel_map_lock);
			for (channelMapIterator it(m_knownChannels.begin()); it != m_knownChannels.end(); ++it)
			{
				eDVBChannel *channel = (eDVBChannel*) it->first;
				channel_data *data = it->second;
				eDVBChannelID chid = channel->getChannelID();
				if ( chid.transport_stream_id.get() == msg.service.tsid &&
					chid.original_network_id.get() == msg.service.onid )
				{
					data->m_mhw2_summary_pid = msg.pid;
					eDebug("[EPGC] got mhw2 summary pid %04x", msg.pid);
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

static const char* EPGDAT_IN_FLASH = "/epg.dat";

void eEPGCache::load()
{
	if (m_filename.empty())
		m_filename = "/hdd/epg.dat";
	const char* EPGDAT = m_filename.c_str();
	std::string filenamex = m_filename + ".loading";
	const char* EPGDATX = filenamex.c_str();
	FILE *f = fopen(EPGDAT, "rb");
	int renameResult;
	if (f == NULL)
	{
		/* No EPG on harddisk, so try internal flash */
		eDebug("[EPGC] %s not found, try /epg.dat", EPGDAT);
		EPGDAT = EPGDAT_IN_FLASH;
		f = fopen(EPGDAT, "rb");
		if (f == NULL)
			return;
		renameResult = -1;
	}
	else
	{
		unlink(EPGDATX);
		renameResult = rename(EPGDAT, EPGDATX);
		if (renameResult) eDebug("[EPGC] failed to rename %s", EPGDAT);
	}
	{
		int size=0;
		int cnt=0;
		unsigned int magic=0;
		unlink(EPGDAT_IN_FLASH);/* Don't keep it around when in flash */
		fread( &magic, sizeof(int), 1, f);
		if (magic != 0x98765432)
		{
			eDebug("[EPGC] epg file has incorrect byte order.. dont read it");
			fclose(f);
			return;
		}
		char text1[13];
		fread( text1, 13, 1, f);
		if ( !memcmp( text1, "ENIGMA_EPG_V7", 13) )
		{
			singleLock s(cache_lock);
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
					uint8_t len=0;
					uint8_t type=0;
					eventData *event=0;
					fread( &type, sizeof(uint8_t), 1, f);
					fread( &len, sizeof(uint8_t), 1, f);
					event = new eventData(0, len, type);
					event->n_crc = (len-10) / sizeof(uint32_t);
					fread( event->rawEITdata, 10, 1, f);
					if (event->n_crc)
					{
						event->crc_list = new uint32_t[event->n_crc];
						fread( event->crc_list, event->n_crc, sizeof(uint32_t), f);
					}
					eventData::CacheSize += sizeof(eventData) + event->n_crc * sizeof(uint32_t);
					evMap[ event->getEventID() ]=event;
					tmMap[ event->getStartTime() ]=event;
					++cnt;
				}
				eventDB[key]=std::pair<eventMap,timeMap>(evMap,tmMap);
			}
			eventData::load(f);
			eDebug("[EPGC] %d events read from %s", cnt, EPGDAT);
#ifdef ENABLE_PRIVATE_EPG
			char text2[11];
			fread( text2, 11, 1, f);
			if ( !memcmp( text2, "PRIVATE_EPG", 11) )
			{
				size=0;
				fread( &size, sizeof(int), 1, f);
				while(size--)
				{
					int size=0;
					uniqueEPGKey key;
					fread( &key, sizeof(uniqueEPGKey), 1, f);
					eventMap &evMap=eventDB[key].first;
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
							uint16_t event_id;
							fread( &time1, sizeof(time_t), 1, f);
							fread( &time2, sizeof(time_t), 1, f);
							fread( &event_id, sizeof(uint16_t), 1, f);
							content_time_tables[key][content_id][time1]=std::pair<time_t, uint16_t>(time2, event_id);
							eventMap::iterator it =
								evMap.find(event_id);
							if (it != evMap.end())
								it->second->type = PRIVATE;
						}
					}
				}
			}
#endif // ENABLE_PRIVATE_EPG
		}
		else
			eDebug("[EPGC] don't read old epg database");
		posix_fadvise(fileno(f), 0, 0, POSIX_FADV_DONTNEED);
		fclose(f);
		// We got this far, so the EPG file is okay.
		if (renameResult == 0)
		{
			renameResult = rename(EPGDATX, EPGDAT);
			if (renameResult) eDebug("[EPGC] failed to rename epg.dat back");
		}
	}
}

void eEPGCache::save()
{
	const char* EPGDAT = m_filename.c_str();
	if (eventData::isCacheCorrupt)
		return;
	// only save epg.dat if it's worth the trouble...
	if (eventData::CacheSize < 10240)
		return;

	/* create empty file */
	FILE *f = fopen(EPGDAT, "wb");
	if (!f)
	{
		eDebug("[EPGC] Failed to open '%s' (%m)", EPGDAT);
		EPGDAT = EPGDAT_IN_FLASH;
		f = fopen(EPGDAT, "wb");
		if (!f)
			return;
	}

	char* buf = realpath(EPGDAT, NULL);
	if (!buf)
	{
		eDebug("[EPGC] realpath to '%s' failed in save (%m)", EPGDAT);
		fclose(f);
		return;
	}

	eDebug("[EPGC] store epg to realpath '%s'", buf);

	struct statfs s;
	off64_t tmp;
	if (statfs(buf, &s) < 0) {
		eDebug("[EPGC] statfs '%s' failed in save (%m)", buf);
		fclose(f);
		free(buf);
		return;
	}

	free(buf);

	// check for enough free space on storage
	tmp=s.f_bfree;
	tmp*=s.f_bsize;
	if ( tmp < (eventData::CacheSize*12)/10 ) // 20% overhead
	{
		eDebug("[EPGC] not enough free space at '%s' %lld bytes available but %u needed", buf, tmp, (eventData::CacheSize*12)/10);
		fclose(f);
		return;
	}

	int cnt=0;
	unsigned int magic = 0x98765432;
	fwrite( &magic, sizeof(int), 1, f);
	const char *text = "UNFINISHED_V7";
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
			uint8_t len = time_it->second->n_crc * sizeof(uint32_t) + 10;
			fwrite( &time_it->second->type, sizeof(uint8_t), 1, f );
			fwrite( &len, sizeof(uint8_t), 1, f);
			fwrite( time_it->second->rawEITdata, 10, 1, f);
			fwrite( time_it->second->crc_list, time_it->second->n_crc, sizeof(uint32_t), f);
			++cnt;
		}
	}
	eDebug("[EPGC] %d events written to %s", cnt, EPGDAT);
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
				fwrite( &it->second.second, sizeof(uint16_t), 1, f);
			}
		}
	}
#endif
	// write version string after binary data
	// has been written to disk.
	fsync(fileno(f));
	fseek(f, sizeof(int), SEEK_SET);
	fwrite("ENIGMA_EPG_V7", 13, 1, f);
	fclose(f);
}

eEPGCache::channel_data::channel_data(eEPGCache *ml)
	:cache(ml)
	,abortTimer(eTimer::create(ml)), zapTimer(eTimer::create(ml)), state(-2)
	,isRunning(0), haveData(0)
#ifdef ENABLE_PRIVATE_EPG
	,startPrivateTimer(eTimer::create(ml))
#endif
#ifdef ENABLE_MHW_EPG
	,m_MHWTimeoutTimer(eTimer::create(ml))
#endif
{
#ifdef ENABLE_MHW_EPG
	CONNECT(m_MHWTimeoutTimer->timeout, eEPGCache::channel_data::MHWTimeout);
#endif
	CONNECT(zapTimer->timeout, eEPGCache::channel_data::startEPG);
	CONNECT(abortTimer->timeout, eEPGCache::channel_data::abortNonAvail);
#ifdef ENABLE_PRIVATE_EPG
	CONNECT(startPrivateTimer->timeout, eEPGCache::channel_data::startPrivateReader);
#endif
	pthread_mutex_init(&channel_active, 0);
}

void eEPGCache::channel_data::finishEPG()
{
	if (!isRunning)  // epg ready
	{
		eDebug("[EPGC] stop caching events(%ld)", ::time(0));
		zapTimer->start(UPDATE_INTERVAL, 1);
		eDebug("[EPGC] next update in %i min", UPDATE_INTERVAL / 60000);
		for (unsigned int i=0; i < sizeof(seenSections)/sizeof(tidMap); ++i)
		{
			seenSections[i].clear();
			calcedSections[i].clear();
		}
#ifdef ENABLE_MHW_EPG
		cleanupMHW();
#endif
#ifdef ENABLE_FREESAT
		cleanupFreeSat();
#endif
		singleLock l(cache_lock);
		cache->channelLastUpdated[channel->getChannelID()] = ::time(0);
	}
}

void eEPGCache::channel_data::startEPG()
{
	eDebug("[EPGC] start caching events(%ld)", ::time(0));
	state=0;
	haveData=0;
	for (unsigned int i=0; i < sizeof(seenSections)/sizeof(tidMap); ++i)
	{
		seenSections[i].clear();
		calcedSections[i].clear();
	}
#ifdef ENABLE_MHW_EPG
		cleanupMHW();
#endif
#ifdef ENABLE_FREESAT
		cleanupFreeSat();
#endif

	eDVBSectionFilterMask mask;
	memset(&mask, 0, sizeof(mask));

#ifdef ENABLE_MHW_EPG
	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::MHW)
	{
		mask.pid = 0xD3;
		mask.data[0] = 0x91;
		mask.mask[0] = 0xFF;
		m_MHWReader->connectRead(slot(*this, &eEPGCache::channel_data::readMHWData), m_MHWConn);
		m_MHWReader->start(mask);
		isRunning |= MHW;
		memcpy(&m_MHWFilterMask, &mask, sizeof(eDVBSectionFilterMask));

		mask.pid = m_mhw2_channel_pid;
		mask.data[0] = 0xC8;
		mask.mask[0] = 0xFF;
		mask.data[1] = 0;
		mask.mask[1] = 0xFF;
		m_MHWReader2->connectRead(slot(*this, &eEPGCache::channel_data::readMHWData2), m_MHWConn2);
		m_MHWReader2->start(mask);
		isRunning |= MHW;
		memcpy(&m_MHWFilterMask2, &mask, sizeof(eDVBSectionFilterMask));
		mask.data[1] = 0;
		mask.mask[1] = 0;
		m_MHWTimeoutet=false;
	}
#endif
#ifdef ENABLE_FREESAT
	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::FREESAT_SCHEDULE_OTHER)
	{
		mask.pid = 3842;
		mask.flags = eDVBSectionFilterMask::rfCRC;
		mask.data[0] = 0x60;
		mask.mask[0] = 0xFE;
		m_FreeSatScheduleOtherReader->connectRead(slot(*this, &eEPGCache::channel_data::readFreeSatScheduleOtherData), m_FreeSatScheduleOtherConn);
		m_FreeSatScheduleOtherReader->start(mask);

		/*
		 * faster pid, available on ITV HD transponder.
		 * We rely on the fact that we have either of the two,
		 * never both. (both readers share the same data callback
		 * and status maps)
		 */
		mask.pid = 3003;
		m_FreeSatScheduleOtherReader2->connectRead(slot(*this, &eEPGCache::channel_data::readFreeSatScheduleOtherData), m_FreeSatScheduleOtherConn2);
		m_FreeSatScheduleOtherReader2->start(mask);
		isRunning |= FREESAT_SCHEDULE_OTHER;
	}
#endif
	mask.pid = 0x12;
	mask.flags = eDVBSectionFilterMask::rfCRC;

	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::NOWNEXT)
	{
		mask.data[0] = 0x4E;
		mask.mask[0] = 0xFE;
		m_NowNextReader->connectRead(bind(slot(*this, &eEPGCache::channel_data::readData), (int)eEPGCache::NOWNEXT), m_NowNextConn);
		m_NowNextReader->start(mask);
		isRunning |= NOWNEXT;
	}

	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::SCHEDULE)
	{
		mask.data[0] = 0x50;
		mask.mask[0] = 0xF0;
		m_ScheduleReader->connectRead(bind(slot(*this, &eEPGCache::channel_data::readData), (int)eEPGCache::SCHEDULE), m_ScheduleConn);
		m_ScheduleReader->start(mask);
		isRunning |= SCHEDULE;
	}

	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::SCHEDULE_OTHER)
	{
		mask.data[0] = 0x60;
		mask.mask[0] = 0xF0;
		m_ScheduleOtherReader->connectRead(bind(slot(*this, &eEPGCache::channel_data::readData), (int)eEPGCache::SCHEDULE_OTHER), m_ScheduleOtherConn);
		m_ScheduleOtherReader->start(mask);
		isRunning |= SCHEDULE_OTHER;
	}

#ifdef ENABLE_VIRGIN
	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::VIRGIN_NOWNEXT)
	{
		mask.pid = 0x2bc;
		mask.data[0] = 0x4E;
		mask.mask[0] = 0xFE;
		m_VirginNowNextReader->connectRead(bind(slot(*this, &eEPGCache::channel_data::readData), (int)eEPGCache::VIRGIN_NOWNEXT), m_VirginNowNextConn);
		m_VirginNowNextReader->start(mask);
		isRunning |= VIRGIN_NOWNEXT;
	}

	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::VIRGIN_SCHEDULE)
	{
		mask.pid = 0x2bc;
		mask.data[0] = 0x50;
		mask.mask[0] = 0xFE;
		m_VirginScheduleReader->connectRead(bind(slot(*this, &eEPGCache::channel_data::readData), (int)eEPGCache::VIRGIN_SCHEDULE), m_VirginScheduleConn);
		m_VirginScheduleReader->start(mask);
		isRunning |= VIRGIN_SCHEDULE;
	}
#endif
#ifdef ENABLE_NETMED
	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::NETMED_SCHEDULE)
	{
		mask.pid = 0x1388;
		mask.data[0] = 0x50;
		mask.mask[0] = 0xF0;
		m_NetmedScheduleReader->connectRead(bind(slot(*this, &eEPGCache::channel_data::readData), (int)eEPGCache::NETMED_SCHEDULE), m_NetmedScheduleConn);
		m_NetmedScheduleReader->start(mask);
		isRunning |= NETMED_SCHEDULE;
	}

	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::NETMED_SCHEDULE_OTHER)
	{
		mask.pid = 0x1388;
		mask.data[0] = 0x60;
		mask.mask[0] = 0xF0;
		m_NetmedScheduleOtherReader->connectRead(bind(slot(*this, &eEPGCache::channel_data::readData), (int)eEPGCache::NETMED_SCHEDULE_OTHER), m_NetmedScheduleOtherConn);
		m_NetmedScheduleOtherReader->start(mask);
		isRunning |= NETMED_SCHEDULE_OTHER;
	}
#endif
	if (eEPGCache::getInstance()->getEpgSources() & eEPGCache::VIASAT)
	{
		mask.pid = 0x39;

		mask.data[0] = 0x40;
		mask.mask[0] = 0x40;
		m_ViasatReader->connectRead(bind(slot(*this, &eEPGCache::channel_data::readData), (int)eEPGCache::VIASAT), m_ViasatConn);
		m_ViasatReader->start(mask);
		isRunning |= VIASAT;
	}

	abortTimer->start(7000,true);
}

void eEPGCache::channel_data::abortNonAvail()
{
	if (!state)
	{
		if ( !(haveData&NOWNEXT) && (isRunning&NOWNEXT) )
		{
			eDebug("[EPGC] abort non avail nownext reading");
			isRunning &= ~NOWNEXT;
			m_NowNextReader->stop();
			m_NowNextConn=0;
		}
		if ( !(haveData&SCHEDULE) && (isRunning&SCHEDULE) )
		{
			eDebug("[EPGC] abort non avail schedule reading");
			isRunning &= ~SCHEDULE;
			m_ScheduleReader->stop();
			m_ScheduleConn=0;
		}
		if ( !(haveData&SCHEDULE_OTHER) && (isRunning&SCHEDULE_OTHER) )
		{
			eDebug("[EPGC] abort non avail schedule other reading");
			isRunning &= ~SCHEDULE_OTHER;
			m_ScheduleOtherReader->stop();
			m_ScheduleOtherConn=0;
		}
#ifdef ENABLE_VIRGIN
		if ( !(haveData&VIRGIN_NOWNEXT) && (isRunning&VIRGIN_NOWNEXT) )
		{
			eDebug("[EPGC] abort non avail virgin nownext reading");
			isRunning &= ~VIRGIN_NOWNEXT;
			m_VirginNowNextReader->stop();
			m_VirginNowNextConn=0;
		}
		if ( !(haveData&VIRGIN_SCHEDULE) && (isRunning&VIRGIN_SCHEDULE) )
		{
			eDebug("[EPGC] abort non avail virgin schedule reading");
			isRunning &= ~VIRGIN_SCHEDULE;
			m_VirginScheduleReader->stop();
			m_VirginScheduleConn=0;
		}
#endif
#ifdef ENABLE_NETMED
		if ( !(haveData&NETMED_SCHEDULE) && (isRunning&NETMED_SCHEDULE) )
		{
			eDebug("[EPGC] abort non avail netmed schedule reading");
			isRunning &= ~NETMED_SCHEDULE;
			m_NetmedScheduleReader->stop();
			m_NetmedScheduleConn=0;
		}
		if ( !(haveData&NETMED_SCHEDULE_OTHER) && (isRunning&NETMED_SCHEDULE_OTHER) )
		{
			eDebug("[EPGC] abort non avail netmed schedule other reading");
			isRunning &= ~NETMED_SCHEDULE_OTHER;
			m_NetmedScheduleOtherReader->stop();
			m_NetmedScheduleOtherConn=0;
		}
#endif
#ifdef ENABLE_FREESAT
		if ( !(haveData&FREESAT_SCHEDULE_OTHER) && (isRunning&FREESAT_SCHEDULE_OTHER) )
		{
			eDebug("[EPGC] abort non avail FreeSat schedule_other reading");
			isRunning &= ~FREESAT_SCHEDULE_OTHER;
			m_FreeSatScheduleOtherReader->stop();
			m_FreeSatScheduleOtherReader2->stop();
			m_FreeSatScheduleOtherConn=0;
			m_FreeSatScheduleOtherConn2=0;
			cleanupFreeSat();
		}
#endif
		if ( !(haveData&VIASAT) && (isRunning&VIASAT) )
		{
			eDebug("[EPGC] abort non avail viasat reading");
			isRunning &= ~VIASAT;
			m_ViasatReader->stop();
			m_ViasatConn=0;
		}
#ifdef ENABLE_MHW_EPG
		if ( !(haveData&MHW) && (isRunning&MHW) )
		{
			eDebug("[EPGC] abort non avail mhw reading");
			isRunning &= ~MHW;
			m_MHWReader->stop();
			m_MHWConn=0;
			m_MHWReader2->stop();
			m_MHWConn2=0;
		}
#endif
		if ( isRunning & VIASAT )
			abortTimer->start(300000, true);
		else if ( isRunning )
			abortTimer->start(90000, true);
		else
		{
			++state;
			for (unsigned int i=0; i < sizeof(seenSections)/sizeof(tidMap); ++i)
			{
				seenSections[i].clear();
				calcedSections[i].clear();
			}
#ifdef ENABLE_MHW_EPG
			cleanupMHW();
#endif
#ifdef ENABLE_FREESAT
			cleanupFreeSat();
#endif
		}
	}
	++state;
}

void eEPGCache::channel_data::startChannel()
{
	pthread_mutex_lock(&channel_active);
	updateMap::iterator It = cache->channelLastUpdated.find( channel->getChannelID() );

	int update = ( It != cache->channelLastUpdated.end() ? ( UPDATE_INTERVAL - ( (::time(0)-It->second) * 1000 ) ) : ZAP_DELAY );

	if (update < ZAP_DELAY)
		update = ZAP_DELAY;

	zapTimer->start(update, 1);
	if (update >= 60000)
		eDebug("[EPGC] next update in %i min", update/60000);
	else if (update >= 1000)
		eDebug("[EPGC] next update in %i sec", update/1000);
}

void eEPGCache::channel_data::abortEPG()
{
	for (unsigned int i=0; i < sizeof(seenSections)/sizeof(tidMap); ++i)
	{
		seenSections[i].clear();
		calcedSections[i].clear();
	}
#ifdef ENABLE_MHW_EPG
	cleanupMHW();
#endif
#ifdef ENABLE_FREESAT
	cleanupFreeSat();
#endif
	abortTimer->stop();
	zapTimer->stop();
	if (isRunning)
	{
		eDebug("[EPGC] abort caching events !!");
		if (isRunning & SCHEDULE)
		{
			isRunning &= ~SCHEDULE;
			m_ScheduleReader->stop();
			m_ScheduleConn=0;
		}
		if (isRunning & NOWNEXT)
		{
			isRunning &= ~NOWNEXT;
			m_NowNextReader->stop();
			m_NowNextConn=0;
		}
		if (isRunning & SCHEDULE_OTHER)
		{
			isRunning &= ~SCHEDULE_OTHER;
			m_ScheduleOtherReader->stop();
			m_ScheduleOtherConn=0;
		}
#ifdef ENABLE_VIRGIN
		if (isRunning & VIRGIN_NOWNEXT)
		{
			isRunning &= ~VIRGIN_NOWNEXT;
			m_VirginNowNextReader->stop();
			m_VirginNowNextConn=0;
		}
		if (isRunning & VIRGIN_SCHEDULE)
		{
			isRunning &= ~VIRGIN_SCHEDULE;
			m_VirginScheduleReader->stop();
			m_VirginScheduleConn=0;
		}
#endif
#ifdef ENABLE_NETMED
		if (isRunning & NETMED_SCHEDULE)
		{
			isRunning &= ~NETMED_SCHEDULE;
			m_NetmedScheduleReader->stop();
			m_NetmedScheduleConn=0;
		}
		if (isRunning & NETMED_SCHEDULE_OTHER)
		{
			isRunning &= ~NETMED_SCHEDULE_OTHER;
			m_NetmedScheduleOtherReader->stop();
			m_NetmedScheduleOtherConn=0;
		}
#endif
#ifdef ENABLE_FREESAT
		if (isRunning & FREESAT_SCHEDULE_OTHER)
		{
			isRunning &= ~FREESAT_SCHEDULE_OTHER;
			m_FreeSatScheduleOtherReader->stop();
			m_FreeSatScheduleOtherReader2->stop();
			m_FreeSatScheduleOtherConn=0;
			m_FreeSatScheduleOtherConn2=0;
		}
#endif
		if (isRunning & VIASAT)
		{
			isRunning &= ~VIASAT;
			m_ViasatReader->stop();
			m_ViasatConn=0;
		}
#ifdef ENABLE_MHW_EPG
		if (isRunning & MHW)
		{
			isRunning &= ~MHW;
			m_MHWReader->stop();
			m_MHWConn=0;
			m_MHWReader2->stop();
			m_MHWConn2=0;
		}
#endif
	}
#ifdef ENABLE_PRIVATE_EPG
	if (m_PrivateReader)
		m_PrivateReader->stop();
	if (m_PrivateConn)
		m_PrivateConn=0;
#endif
	pthread_mutex_unlock(&channel_active);
}

void eEPGCache::channel_data::readData( const uint8_t *data, int source)
{
	int map;
	iDVBSectionReader *reader = NULL;
	switch (source)
	{
		case NOWNEXT:
			reader = m_NowNextReader;
			map = 0;
			break;
		case SCHEDULE:
			reader = m_ScheduleReader;
			map = 1;
			break;
		case SCHEDULE_OTHER:
			reader = m_ScheduleOtherReader;
			map = 2;
			break;
		case VIASAT:
			reader = m_ViasatReader;
			map = 3;
			break;
#ifdef ENABLE_NETMED
		case NETMED_SCHEDULE:
			reader = m_NetmedScheduleReader;
			map = 1;
			break;
		case NETMED_SCHEDULE_OTHER:
			reader = m_NetmedScheduleOtherReader;
			map = 2;
			break;
#endif
#ifdef ENABLE_VIRGIN
		case VIRGIN_NOWNEXT:
			reader = m_VirginNowNextReader;
			map = 0;
			break;
		case VIRGIN_SCHEDULE:
			reader = m_VirginScheduleReader;
			map = 1;
			break;
#endif
		default:
			eDebug("[EPGC] unknown source");
			return;
	}
	tidMap &seenSections = this->seenSections[map];
	tidMap &calcedSections = this->calcedSections[map];
	if ( (state == 1 && calcedSections == seenSections) || state > 1 )
	{
		eDebugNoNewLine("[EPGC] ");
		switch (source)
		{
			case NOWNEXT:
				m_NowNextConn=0;
				eDebugNoNewLine("nownext");
				break;
			case SCHEDULE:
				m_ScheduleConn=0;
				eDebugNoNewLine("schedule");
				break;
			case SCHEDULE_OTHER:
				m_ScheduleOtherConn=0;
				eDebugNoNewLine("schedule other");
				break;
			case VIASAT:
				m_ViasatConn=0;
				eDebugNoNewLine("viasat");
				break;
#ifdef ENABLE_NETMED
			case NETMED_SCHEDULE:
				m_NetmedScheduleConn=0;
				eDebugNoNewLine("netmed schedule");
				break;
			case NETMED_SCHEDULE_OTHER:
				m_NetmedScheduleOtherConn=0;
				eDebugNoNewLine("netmed schedule other");
				break;
#endif
#ifdef ENABLE_VIRGIN
			case VIRGIN_NOWNEXT:
				m_VirginNowNextConn=0;
				eDebugNoNewLine("virgin nownext");
				break;
			case VIRGIN_SCHEDULE:
				m_VirginScheduleConn=0;
				eDebugNoNewLine("virgin schedule");
				break;
#endif
			default: eDebugNoNewLine("unknown");break;
		}
		eDebug(" finished(%ld)", ::time(0));
		if ( reader )
			reader->stop();
		isRunning &= ~source;
		if (!isRunning)
			finishEPG();
	}
	else
	{
		eit_t *eit = (eit_t*) data;
		uint32_t sectionNo = data[0] << 24;
		sectionNo |= data[3] << 16;
		sectionNo |= data[4] << 8;
		sectionNo |= eit->section_number;

		tidMap::iterator it =
			seenSections.find(sectionNo);

		if ( it == seenSections.end() )
		{
			seenSections.insert(sectionNo);
			calcedSections.insert(sectionNo);
			uint32_t tmpval = sectionNo & 0xFFFFFF00;
			uint8_t incr = source == NOWNEXT ? 1 : 8;
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

#if ENABLE_FREESAT

freesatEITSubtableStatus::freesatEITSubtableStatus(u_char version, uint8_t maxSection) : version(version)
{
	initMap(maxSection);
}

void freesatEITSubtableStatus::initMap(uint8_t maxSection)
{
	int i, maxSectionIdx = maxSection / 8;
	for (i = 0; i < 32; i++)
	{
		sectionMap[i] = (i <= maxSectionIdx ? 0x0100 : 0x0000 );
	}
}

bool freesatEITSubtableStatus::isSectionPresent(uint8_t sectionNo)
{
	uint8_t sectionIdx = sectionNo / 8;
	uint8_t bitOffset = sectionNo % 8;

	return ((sectionMap[sectionIdx] & (1 << bitOffset)) != 0);
}

bool freesatEITSubtableStatus::isCompleted()
{
	uint32_t i = 0;
	uint8_t calc;

	while ( i < 32 )
	{
		calc = sectionMap[i] >> 8;
		if (! calc) return true; // Last segment passed
		if (calc ^ ( sectionMap[i] & 0xFF ) ) // Segment not fully found
			return false;
		i++;
	}
	return true; // All segments ok
}

void freesatEITSubtableStatus::seen(uint8_t sectionNo, uint8_t maxSegmentSection)
{
	uint8_t sectionIdx = sectionNo / 8;
	uint8_t bitOffset = sectionNo % 8;
	uint8_t maxBitOffset = maxSegmentSection % 8;

	sectionMap[sectionIdx] &= 0x00FF; // Clear calc map
	sectionMap[sectionIdx] |= ((0x01FF << maxBitOffset) & 0xFF00); // Set calc map
	sectionMap[sectionIdx] |= (1 << bitOffset); // Set seen map
}

bool freesatEITSubtableStatus::isVersionChanged(u_char testVersion)
{
	return version != testVersion;
}

void freesatEITSubtableStatus::updateVersion(u_char newVersion, uint8_t maxSection)
{
	version = newVersion;
	initMap(maxSection);
}

void eEPGCache::channel_data::cleanupFreeSat()
{
	m_FreeSatSubTableStatus.clear();
	m_FreesatTablesToComplete = 0;
}

void eEPGCache::channel_data::readFreeSatScheduleOtherData( const uint8_t *data)
{
	eit_t *eit = (eit_t*) data;
	uint32_t subtableNo = data[0] << 24; // Table ID
	subtableNo |= data[3] << 16; // Service ID Hi
	subtableNo |= data[4] << 8; // Service ID Lo

	// Check for sub-table version in map
	std::map<uint32_t, freesatEITSubtableStatus> &freeSatSubTableStatus = this->m_FreeSatSubTableStatus;
	std::map<uint32_t, freesatEITSubtableStatus>::iterator itmap = freeSatSubTableStatus.find(subtableNo);

	freesatEITSubtableStatus *fsstatus;
	if ( itmap == freeSatSubTableStatus.end() )
	{
		// New sub table. Store version.
		//eDebug("[EPGC] New subtable (%x) version (%d) now/next (%d) tsid (%x/%x) onid (%x/%x)", subtableNo, eit->version_number, eit->current_next_indicator, eit->transport_stream_id_hi, eit->transport_stream_id_lo, eit->original_network_id_hi, eit->original_network_id_lo);
		fsstatus = new freesatEITSubtableStatus(eit->version_number, eit->last_section_number);
		m_FreesatTablesToComplete++;
		freeSatSubTableStatus.insert(std::pair<uint32_t,freesatEITSubtableStatus>(subtableNo, *fsstatus));
	}
	else
	{
		fsstatus = &itmap->second;
		// Existing subtable. Check version. Should check current / next as well? Seems to always be current for Freesat
		if ( fsstatus->isVersionChanged(eit->version_number) )
		{
			eDebug("[EPGC] FS subtable (%x) version changed (%d) now/next (%d)", subtableNo, eit->version_number, eit->current_next_indicator);
			m_FreesatTablesToComplete++;
			fsstatus->updateVersion(eit->version_number, eit->last_section_number);
		}
		else
		{
			if ( fsstatus->isSectionPresent(eit->section_number) )
			{
//				eDebug("[EPGC] DUP FS sub/sec/ver (%x/%d/%d)", subtableNo, eit->section_number, eit->version_number);
				return;
			}
		}
	}

//	eDebug("[EPGC] New FS sub/sec/ls/lss/ver (%x/%d/%d/%d/%d)", subtableNo, eit->section_number, eit->last_section_number, eit->segment_last_section_number, eit->version_number);
	fsstatus->seen(eit->section_number, eit->segment_last_section_number);
	if (fsstatus->isCompleted())
	{
		m_FreesatTablesToComplete--;
	}
	cache->sectionRead(data, FREESAT_SCHEDULE_OTHER, this);
}
#endif

RESULT eEPGCache::lookupEventTime(const eServiceReference &service, time_t t, const eventData *&result, int direction)
// if t == -1 we search the current event...
{
	uniqueEPGKey key(handleGroup(service));

	// check if EPG for this service is ready...
	eventCache::iterator It = eventDB.find( key );
	if ( It != eventDB.end() && !It->second.first.empty() ) // entrys cached ?
	{
		if (t==-1)
			t = ::time(0);
		timeMap::iterator i = direction <= 0 ? It->second.second.lower_bound(t) :  // find > or equal
			It->second.second.upper_bound(t); // just >
		if ( i != It->second.second.end() )
		{
			if ( direction < 0 || (direction == 0 && i->first > t) )
			{
				timeMap::iterator x = i;
				--x;
				if ( x != It->second.second.end() )
				{
					time_t start_time = x->first;
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
	result = NULL;
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
	uniqueEPGKey key(handleGroup(service));

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
			eDebug("[EPGC] event %04x not found in epgcache", event_id);
		}
	}
	return -1;
}

RESULT eEPGCache::saveEventToFile(const char* filename, const eServiceReference &service, int eit_event_id, time_t begTime, time_t endTime)
{
	RESULT ret = -1;
	singleLock s(cache_lock);
	const eventData *data = NULL;
	if ( eit_event_id != -1 )
	{
		eDebug("[EPGC] %s epg event id %x", __func__, eit_event_id);
		ret = lookupEventId(service, eit_event_id, data);
	}
	if ( (ret != 0) && (begTime != -1) )
	{
		time_t queryTime = begTime;
		if (endTime != -1)
			queryTime += (endTime - begTime) / 2;
		ret = lookupEventTime(service, queryTime, data);
	}
	if (ret == 0)
	{
		int fd = open(filename, O_CREAT|O_WRONLY, 0666);
		if (fd < 0)
		{
			eDebug("[EPGC] Failed to create file: %s", filename);
			return fd;
		}
		const eit_event_struct *event = data->get();
		int evLen = HILO(event->descriptors_loop_length) + 12/*EIT_LOOP_SIZE*/;
		int wr = ::write( fd, event, evLen );
		::close(fd);
		if ( wr != evLen )
		{
			::unlink(filename); /* Remove faulty file */
			eDebug("[EPGC] eit write error (%m) writing %s", filename);
			ret = (wr < 0) ? wr : -1;
		}
	}
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
	result = NULL;
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
	singleLock s(cache_lock);
	const eServiceReferenceDVB &ref = (const eServiceReferenceDVB&)handleGroup(service);
	if (begin == -1)
		begin = ::time(0);
	eventCache::iterator It = eventDB.find(ref);
	if ( It != eventDB.end() && It->second.second.size() )
	{
		m_timemap_cursor = It->second.second.lower_bound(begin);
		if ( m_timemap_cursor != It->second.second.end() )
		{
			if ( m_timemap_cursor->first != begin )
			{
				timeMap::iterator x = m_timemap_cursor;
				--x;
				if ( x != It->second.second.end() )
				{
					time_t start_time = x->first;
					if ( begin > start_time && begin < (start_time+x->second->getDuration()))
						m_timemap_cursor = x;
				}
			}
		}

		if (minutes != -1)
			m_timemap_end = It->second.second.lower_bound(begin+minutes*60);
		else
			m_timemap_end = It->second.second.end();

		currentQueryTsidOnid = (ref.getTransportStreamID().get()<<16) | ref.getOriginalNetworkID().get();
		return m_timemap_cursor == m_timemap_end ? -1 : 0;
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

void fillTuple(ePyObject tuple, const char *argstring, int argcount, ePyObject service_reference, eServiceEvent *ptr, ePyObject service_name, ePyObject nowTime, eventData *evData )
{
	// eDebug("[EPGC] fillTuple arg=%s argcnt=%d, ptr=%d evData=%d", argstring, argcount, ptr ? 1 : 0, evData ? 1 : 0);
	ePyObject tmp;
	int spos=0, tpos=0;
	char c;
	while(spos < argcount)
	{
		bool inc_refcount=false;
		switch((c=argstring[spos++]))
		{
			case '0': // PyLong 0
				tmp = PyLong_FromLong(0);
				break;
			case 'I': // Event Id
				tmp = evData ? PyLong_FromLong(evData->getEventID()) : (ptr ? PyLong_FromLong(ptr->getEventId()) : ePyObject());
				break;
			case 'B': // Event Begin Time
				tmp = ptr ? PyLong_FromLong(ptr->getBeginTime()) : (evData ? PyLong_FromLong(evData->getStartTime()) : ePyObject());
				break;
			case 'D': // Event Duration
				tmp = ptr ? PyLong_FromLong(ptr->getDuration()) : (evData ? PyLong_FromLong(evData->getDuration()) : ePyObject());
				break;
			case 'T': // Event Title
				tmp = ptr ? PyString_FromString(ptr->getEventName().c_str()) : ePyObject();
				break;
			case 'S': // Event Short Description
				tmp = ptr ? PyString_FromString(ptr->getShortDescription().c_str()) : ePyObject();
				break;
			case 'E': // Event Extended Description
				tmp = ptr ? PyString_FromString(ptr->getExtendedDescription().c_str()) : ePyObject();
				break;
			case 'P': // Event Parental Rating
				tmp = ptr ? ePyObject(ptr->getParentalData()) : ePyObject();
				break;
			case 'W': // Event Content Description
				tmp = ptr ? ePyObject(ptr->getGenreData()) : ePyObject();
				break;
			case 'C': // Current Time
				tmp = nowTime;
				inc_refcount = true;
				break;
			case 'R': // service reference string
				tmp = service_reference;
				inc_refcount = true;
				break;
			case 'n': // short service name
			case 'N': // service name
				tmp = service_name;
				inc_refcount = true;
				break;
			case 'X':
				++argcount;
				continue;
			default:  // ignore unknown
				tmp = ePyObject();
				eDebug("fillTuple unknown '%c'... insert 'None' in result", c);
		}
		if (!tmp)
		{
			tmp = Py_None;
			inc_refcount = true;
		}
		if (inc_refcount)
			Py_INCREF(tmp);
		PyTuple_SET_ITEM(tuple, tpos++, tmp);
	}
}

int handleEvent(eServiceEvent *ptr, ePyObject dest_list, const char* argstring, int argcount, ePyObject service, ePyObject nowTime, ePyObject service_name, ePyObject convertFunc, ePyObject convertFuncArgs)
{
	if (convertFunc)
	{
		fillTuple(convertFuncArgs, argstring, argcount, service, ptr, service_name, nowTime, 0);
		ePyObject result = PyObject_CallObject(convertFunc, convertFuncArgs);
		if (!result)
		{
			if (service_name)
				Py_DECREF(service_name);
			if (nowTime)
				Py_DECREF(nowTime);
			Py_DECREF(convertFuncArgs);
			Py_DECREF(dest_list);
			PyErr_SetString(PyExc_StandardError,
				"error in convertFunc execute");
			eDebug("error in convertFunc execute");
			return -1;
		}
		PyList_Append(dest_list, result);
		Py_DECREF(result);
	}
	else
	{
		ePyObject tuple = PyTuple_New(argcount);
		fillTuple(tuple, argstring, argcount, service, ptr, service_name, nowTime, 0);
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
//   P = Event Parental Rating
//   W = Event Content Description ('W'hat)
//   C = Current Time
//   R = Service Reference
//   N = Service Name
//   n = Short Service Name
//   X = Return a minimum of one tuple per service in the result list... even when no event was found.
//       The returned tuple is filled with all available infos... non avail is filled as None
//       The position and existence of 'X' in the format string has no influence on the result tuple... its completely ignored..
// then for each service follows a tuple
//   first tuple entry is the servicereference (as string... use the ref.toString() function)
//   the second is the type of query
//     2 = event_id
//    -1 = event before given start_time
//     0 = event intersects given start_time
//    +1 = event after given start_time
//   the third
//      when type is eventid it is the event_id
//      when type is time then it is the start_time ( -1 for now_time )
//   the fourth is the end_time .. ( optional .. for query all events in time range)

PyObject *eEPGCache::lookupEvent(ePyObject list, ePyObject convertFunc)
{
	ePyObject convertFuncArgs;
	int argcount=0;
	const char *argstring=NULL;
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
		ePyObject argv=PyList_GET_ITEM(list, 0); // borrowed reference!
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

	bool forceReturnOne = strchr(argstring, 'X') ? true : false;
	if (forceReturnOne)
		--argcount;

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

	ePyObject nowTime = strchr(argstring, 'C') ?
		PyLong_FromLong(::time(0)) :
		ePyObject();

	int must_get_service_name = strchr(argstring, 'N') ? 1 : strchr(argstring, 'n') ? 2 : 0;

	// create dest list
	ePyObject dest_list=PyList_New(0);
	while(listSize > listIt)
	{
		ePyObject item=PyList_GET_ITEM(list, listIt++); // borrowed reference!
		if (PyTuple_Check(item))
		{
			bool service_changed=false;
			int type=0;
			long event_id=-1;
			time_t stime=-1;
			int minutes=0;
			int tupleSize=PyTuple_Size(item);
			int tupleIt=0;
			ePyObject service;
			while(tupleSize > tupleIt)  // parse query args
			{
				ePyObject entry=PyTuple_GET_ITEM(item, tupleIt); // borrowed reference!
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

			if (minutes && stime == -1)
				stime = ::time(0);

			eServiceReference ref(handleGroup(eServiceReference(PyString_AS_STRING(service))));
			if (ref.type != eServiceReference::idDVB && ref.type != eServiceReference::idServiceMP3)
			{
				eDebug("service reference for epg query is not valid");
				continue;
			}

			// redirect subservice querys to parent service
			eServiceReferenceDVB &dvb_ref = (eServiceReferenceDVB&)ref;
			if (dvb_ref.getParentTransportStreamID().get()) // linkage subservice
			{
				eServiceCenterPtr service_center;
				if (!eServiceCenter::getPrivInstance(service_center))
				{
					dvb_ref.setTransportStreamID( dvb_ref.getParentTransportStreamID() );
					dvb_ref.setServiceID( dvb_ref.getParentServiceID() );
					dvb_ref.setParentTransportStreamID(eTransportStreamID(0));
					dvb_ref.setParentServiceID(eServiceID(0));
					dvb_ref.name="";
					service = PyString_FromString(dvb_ref.toString().c_str());
					service_changed = true;
				}
			}

			ePyObject service_name;
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

						if (must_get_service_name == 1)
						{
							size_t pos;
							// filter short name brakets
							while((pos = name.find("\xc2\x86")) != std::string::npos)
								name.erase(pos,2);
							while((pos = name.find("\xc2\x87")) != std::string::npos)
								name.erase(pos,2);
						}
						else
							name = buildShortName(name);

						if (name.length())
							service_name = PyString_FromString(name.c_str());
					}
				}
				if (!service_name)
					service_name = PyString_FromString("<n/a>");
			}
			if (minutes)
			{
				singleLock s(cache_lock);
				if (!startTimeQuery(ref, stime, minutes))
				{
					while ( m_timemap_cursor != m_timemap_end )
					{
						Event ev((uint8_t*)m_timemap_cursor++->second->get());
						eServiceEvent evt;
						evt.parseFrom(&ev, currentQueryTsidOnid);
						if (handleEvent(&evt, dest_list, argstring, argcount, service, nowTime, service_name, convertFunc, convertFuncArgs))
							return 0;  // error
					}
				}
				else if (forceReturnOne && handleEvent(0, dest_list, argstring, argcount, service, nowTime, service_name, convertFunc, convertFuncArgs))
					return 0;  // error
			}
			else
			{
				eServiceEvent evt;
				const eventData *ev_data=0;
				if (stime)
				{
					singleLock s(cache_lock);
					if (type == 2)
						lookupEventId(ref, event_id, ev_data);
					else
						lookupEventTime(ref, stime, ev_data, type);
					if (ev_data)
					{
						const eServiceReferenceDVB &dref = (const eServiceReferenceDVB&)ref;
						Event ev((uint8_t*)ev_data->get());
						evt.parseFrom(&ev, (dref.getTransportStreamID().get()<<16)|dref.getOriginalNetworkID().get());
					}
				}
				if (ev_data)
				{
					if (handleEvent(&evt, dest_list, argstring, argcount, service, nowTime, service_name, convertFunc, convertFuncArgs))
						return 0; // error
				}
				else if (forceReturnOne && handleEvent(0, dest_list, argstring, argcount, service, nowTime, service_name, convertFunc, convertFuncArgs))
					return 0; // error
			}
			if (service_changed)
				Py_DECREF(service);
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

static void fill_eit_start(eit_event_struct *evt, time_t t)
{
    tm *time = gmtime(&t);

    int l = 0;
    int month = time->tm_mon + 1;
    if (month == 1 || month == 2)
        l = 1;
    int mjd = 14956 + time->tm_mday + (int)((time->tm_year - l) * 365.25) + (int)((month + 1 + l*12) * 30.6001);
    evt->start_time_1 = mjd >> 8;
    evt->start_time_2 = mjd & 0xFF;

    evt->start_time_3 = toBCD(time->tm_hour);
    evt->start_time_4 = toBCD(time->tm_min);
    evt->start_time_5 = toBCD(time->tm_sec);

}

static void fill_eit_duration(eit_event_struct *evt, int time)
{
    //time is given in second
    //convert to hour, minutes, seconds
    evt->duration_1 = toBCD(time / 3600);
    evt->duration_2 = toBCD((time % 3600) / 60);
    evt->duration_3 = toBCD((time % 3600) % 60);
}

static inline uint8_t HI(int x) { return (uint8_t) ((x >> 8) & 0xFF); }
static inline uint8_t LO(int x) { return (uint8_t) (x & 0xFF); }
#define SET_HILO(x, val) {x##_hi = ((val) >> 8); x##_lo = (val) & 0xff; }
// convert from set of strings to DVB format (EIT)
void eEPGCache::submitEventData(const std::vector<eServiceReferenceDVB>& serviceRefs, long start,
	long duration, const char* title, const char* short_summary,
	const char* long_description, char event_type)
{
	if (!title)
		return;
	static const int EIT_LENGTH = 4108;
	static const uint8_t codePage = 0x15; // UTF-8 encoding
	uint8_t data[EIT_LENGTH];

	eit_t *packet = (eit_t *) data;
	packet->table_id = 0x50;
	packet->section_syntax_indicator = 1;

	packet->version_number = 0;	// eEPGCache::sectionRead() will dig this for the moment
	packet->current_next_indicator = 0;
	packet->section_number = 0;	// eEPGCache::sectionRead() will dig this for the moment
	packet->last_section_number = 0;	// eEPGCache::sectionRead() will dig this for the moment

	packet->segment_last_section_number = 0; // eEPGCache::sectionRead() will dig this for the moment
	packet->segment_last_table_id = 0x50;

	eit_event_t *evt_struct = (eit_event_t*) (data + EIT_SIZE);

	uint16_t eventId = start & 0xFFFF;
	SET_HILO(evt_struct->event_id, eventId);

	//6 bytes start time, 3 bytes duration
	fill_eit_start(evt_struct, start);
	fill_eit_duration(evt_struct, duration);

	evt_struct->running_status = 0;
	evt_struct->free_CA_mode = 0;

	//no support for different code pages, only DVB's latin1 character set
	//TODO: convert text to correct character set (data is probably passed in as UTF-8)
	uint8_t *x = (uint8_t *) evt_struct;
	x += EIT_LOOP_SIZE;
	int nameLength = strnlen(title, 246);
	int descLength = short_summary ? strnlen(short_summary, 246 - nameLength) : 0;

	eit_short_event_descriptor_struct *short_evt = (eit_short_event_descriptor_struct*) x;
	short_evt->descriptor_tag = SHORT_EVENT_DESCRIPTOR;
	short_evt->descriptor_length = EIT_SHORT_EVENT_DESCRIPTOR_SIZE + nameLength + descLength + 1 - 2; //+1 for length of short description, -2 for tag and length
	if (nameLength) ++short_evt->descriptor_length; // +1 for codepage byte
	if (descLength) ++short_evt->descriptor_length;
	short_evt->language_code_1 = 'e';
	short_evt->language_code_2 = 'n';
	short_evt->language_code_3 = 'g';
	short_evt->event_name_length = nameLength ? nameLength + 1 : 0;
	x = (uint8_t *) short_evt;
	x += EIT_SHORT_EVENT_DESCRIPTOR_SIZE;
	*x = codePage;
	++x;
	memcpy(x, title, nameLength);
	x += nameLength;
	if (descLength)
	{
		*x = descLength + 1;
		++x;
		*x = codePage;
		++x;
		memcpy(x, short_summary, descLength);
		x += descLength;
	}
	else
	{
		*x = 0;
		++x;
	}

	//Content type
	if (event_type != 0)
	{
		x[0] = 0x54;
		x[1] = 2;
		x[2] = event_type;
		x[3] = 0;
		x += 4;
	}

	//Long description
	int currentLoopLength = x - (uint8_t*)short_evt;
	static const int overheadPerDescriptor = 9; //increase if codepages are added!!!
	static const int MAX_LEN = 256 - overheadPerDescriptor;

	int textLength = long_description ? strnlen(long_description, EIT_LENGTH) : 0;//EIT_LENGTH is a bit too much, but it's only here as a reasonable end point
	int lastDescriptorNumber = (textLength + MAX_LEN-1) / MAX_LEN - 1;
	int remainingTextLength = textLength - lastDescriptorNumber * MAX_LEN;

	//if long description is too long, just try to fill as many descriptors as possible
	while ( (lastDescriptorNumber+1) * 256 + currentLoopLength > EIT_LENGTH - EIT_LOOP_SIZE)
	{
		lastDescriptorNumber--;
		remainingTextLength = MAX_LEN;
	}

	for (int descrIndex = 0; descrIndex <= lastDescriptorNumber; ++descrIndex)
	{
		eit_extended_descriptor_struct *ext_evt = (eit_extended_descriptor_struct*) x;
		ext_evt->descriptor_tag = EIT_EXTENDED_EVENT_DESCRIPOR;
		//descriptor header length is 6, including the 2 tag and length bytes
		//so the length field must be: stringlength + 1 (2 4-bits numbers) + 3 (lang code) + 2 bytes for item info length field and text length field
		int currentTextLength = descrIndex < lastDescriptorNumber ? MAX_LEN : remainingTextLength;
		ext_evt->descriptor_length = 6 + currentTextLength + 1;

		ext_evt->descriptor_number = descrIndex;
		ext_evt->last_descriptor_number = lastDescriptorNumber;
		ext_evt->iso_639_2_language_code_1 = 'e';
		ext_evt->iso_639_2_language_code_2 = 'n';
		ext_evt->iso_639_2_language_code_3 = 'g';

		x[6] = 0; //item information (car, year, director, etc. Unsupported for now)
		x[7] = currentTextLength + 1; //length of description string (part in this message)
		x[8] = codePage;
		memcpy(x + 9, &long_description[descrIndex*MAX_LEN], currentTextLength);

		x += 2 + ext_evt->descriptor_length;
	}

	//TODO: add age and more
	int desc_loop_length = x - ((uint8_t*)evt_struct + EIT_LOOP_SIZE);
	SET_HILO(evt_struct->descriptors_loop_length, desc_loop_length);

	int packet_length = (x - data) - 3; //should add 1 for crc....
	SET_HILO(packet->section_length, packet_length);
	// Add channelrefs and submit data.
	for (std::vector<eServiceReferenceDVB>::const_iterator serviceRef = serviceRefs.begin();
		serviceRef != serviceRefs.end();
		++serviceRef)
	{
		eDVBChannelID chid;
		serviceRef->getChannelID(chid);
		SET_HILO(packet->service_id, serviceRef->getServiceID().get());
		SET_HILO(packet->transport_stream_id, chid.transport_stream_id.get());
		SET_HILO(packet->original_network_id, chid.original_network_id.get());
		sectionRead(data, EPG_IMPORT, 0);
	}
}
#undef SET_HILO


void eEPGCache::setEpgHistorySeconds(time_t seconds)
{
	historySeconds = seconds;
}

void eEPGCache::setEpgSources(unsigned int mask)
{
	enabledSources = mask;
}

unsigned int eEPGCache::getEpgSources()
{
	return enabledSources;
}

static const char* getStringFromPython(ePyObject obj)
{
	char *result = 0;
	if (PyString_Check(obj))
	{
		result = PyString_AS_STRING(obj);
	}
	return result;
}

void eEPGCache::importEvent(ePyObject serviceReference, ePyObject list)
{
	importEvents(serviceReference, list);
}

//here we get a python tuple of tuples ;)
// consider it an array of objects with the following data
// 1. start time (long)
// 2. duration (int)
// 3. event title (string)
// 4. short description (string)
// 5. extended description (string)
// 6. event type (byte)
void eEPGCache::importEvents(ePyObject serviceReferences, ePyObject list)
{
	std::vector<eServiceReferenceDVB> refs;

	if (PyString_Check(serviceReferences))
	{
		char *refstr;
		refstr = PyString_AS_STRING(serviceReferences);
	        if (!refstr)
	        {
        	        eDebug("[EPG:import] serviceReference string is 0, aborting");
                	return;
	        }
		refs.push_back(eServiceReferenceDVB(refstr));
	}
	else if (PyList_Check(serviceReferences))
	{
		int nRefs = PyList_Size(serviceReferences);
		for (int i = 0; i < nRefs; ++i)
		{
			PyObject* item = PyList_GET_ITEM(serviceReferences, i);
			char *refstr;
	                refstr = PyString_AS_STRING(item);
	                if (!refstr)
        	        {
                	        eDebug("[EPG:import] a serviceref item is not a string");
                        }
			else
		        {
		                refs.push_back(eServiceReferenceDVB(refstr));
			}
		}
	}
	else
	{
		eDebug("[EPG:import] serviceReference string is neither string nor list, aborting");
		return;
	}

	bool isTuple = PyTuple_Check(list);
	if (!isTuple && !PyList_Check(list))
	{

		eDebug("[EPG:import] argument 'list' is neither list nor tuple.");
		return;
	}

	int numberOfEvents = isTuple ? PyTuple_Size(list) : PyList_Size(list);

	for (int i = 0; i < numberOfEvents;  ++i)
	{
		ePyObject singleEvent = isTuple ? PyTuple_GET_ITEM(list, i) : PyList_GET_ITEM(list, i);
		if (!PyTuple_Check(singleEvent))
		{
			eDebug("[EPG:import] eventdata tuple does not pass PyTuple_Check, aborting");
			return;
		}
		int tupleSize = PyTuple_Size(singleEvent);
		if (tupleSize < 5)
		{
			eDebug("[EPG:import] eventdata tuple does not contain enough fields, aborting");
			return;
		}

		long start = PyLong_AsLong(PyTuple_GET_ITEM(singleEvent, 0));
		long duration = PyInt_AsLong(PyTuple_GET_ITEM(singleEvent, 1));
		const char *title = getStringFromPython(PyTuple_GET_ITEM(singleEvent, 2));
		const char *short_summary = getStringFromPython(PyTuple_GET_ITEM(singleEvent, 3));
		const char *long_description = getStringFromPython(PyTuple_GET_ITEM(singleEvent, 4));
		char event_type = (char) PyInt_AsLong(PyTuple_GET_ITEM(singleEvent, 5));

		Py_BEGIN_ALLOW_THREADS;
		submitEventData(refs, start, duration, title, short_summary, long_description, event_type);
		Py_END_ALLOW_THREADS;
	}
}


// here we get a python tuple
// the first entry in the tuple is a python string to specify the format of the returned tuples (in a list)
//   I = Event Id
//   B = Event Begin Time
//   D = Event Duration
//   T = Event Title
//   S = Event Short Description
//   P = Event Parental Rating
//   W = Event Content Description
//   E = Event Extended Description
//   R = Service Reference
//   N = Service Name
//   n = Short Service Name
//  the second tuple entry is the MAX matches value
//  the third tuple entry is the type of query
//     0 = search for similar broadcastings (SIMILAR_BROADCASTINGS_SEARCH)
//     1 = search events with exactly title name (EXACT_TITLE_SEARCH)
//     2 = search events with text in title name (PARTIAL_TITLE_SEARCH)
//     3 = search events starting with title name (START_TITLE_SEARCH)
//  when type is 0 (SIMILAR_BROADCASTINGS_SEARCH)
//   the fourth is the servicereference string
//   the fifth is the eventid
//  when type > 0 (*_TITLE_SEARCH)
//   the fourth is the search text
//   the fifth is
//     0 = case sensitive (CASE_CHECK)
//     1 = case insensitive (NO_CASECHECK)

PyObject *eEPGCache::search(ePyObject arg)
{
	ePyObject ret;
	std::deque<uint32_t> descr;
	int eventid = -1;
	const char *argstring=0;
	char *refstr=0;
	int argcount=0;
	int querytype=-1;
	bool needServiceEvent=false;
	int maxmatches=0;
	int must_get_service_name = 0;
	bool must_get_service_reference = false;

	if (PyTuple_Check(arg))
	{
		int tuplesize=PyTuple_Size(arg);
		if (tuplesize > 0)
		{
			ePyObject obj = PyTuple_GET_ITEM(arg,0);
			if (PyString_Check(obj))
			{
#if PY_VERSION_HEX < 0x02060000
				argcount = PyString_GET_SIZE(obj);
#else
				argcount = PyString_Size(obj);
#endif
				argstring = PyString_AS_STRING(obj);
				for (int i=0; i < argcount; ++i)
					switch(argstring[i])
					{
					case 'S':
					case 'E':
					case 'T':
					case 'P':
					case 'W':
						needServiceEvent=true;
						break;
					case 'N':
						must_get_service_name = 1;
						break;
					case 'n':
						must_get_service_name = 2;
						break;
					case 'R':
						must_get_service_reference = true;
						break;
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
				ePyObject obj = PyTuple_GET_ITEM(arg, 3);
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
							// search short and extended event descriptors
							for (uint8_t i = 0; i < evData->n_crc; ++i)
							{
								uint32_t crc = evData->crc_list[i];
								DescriptorMap::iterator it =
									eventData::descriptors.find(crc);
								if (it != eventData::descriptors.end())
								{
									uint8_t *descr_data = it->second.data;
									switch(descr_data[0])
									{
									case 0x4D ... 0x4E:
										descr.push_back(crc);
										break;
									default:
										break;
									}
								}
							}
						}
						if (descr.empty())
							eDebug("event not found");
					}
					else
					{
						PyErr_SetString(PyExc_StandardError, "type error");
						eDebug("tuple arg 4 is not a valid service reference string");
						return NULL;
					}
				}
				else
				{
					PyErr_SetString(PyExc_StandardError, "type error");
					eDebug("tuple arg 4 is not a string");
					return NULL;
				}
			}
			else if (tuplesize > 4 && (querytype > 0) )
			{
				ePyObject obj = PyTuple_GET_ITEM(arg, 3);
				if (PyString_Check(obj))
				{
					int casetype = PyLong_AsLong(PyTuple_GET_ITEM(arg, 4));
					const char *str = PyString_AS_STRING(obj);
#if PY_VERSION_HEX < 0x02060000
					int textlen = PyString_GET_SIZE(obj);
#else
					int textlen = PyString_Size(obj);
#endif
					switch (querytype)
					{
						case 1:
							eDebug("lookup events with '%s' as title (%s)", str, casetype?"ignore case":"case sensitive");
							break;
						case 2:
							eDebug("lookup events with '%s' in title (%s)", str, casetype?"ignore case":"case sensitive");
							break;
						case 3:
							eDebug("lookup events, title starting with '%s' (%s)", str, casetype?"ignore case":"case sensitive");
							break;
					}
					singleLock s(cache_lock);
					std::string title;
					for (DescriptorMap::iterator it(eventData::descriptors.begin());
						it != eventData::descriptors.end(); ++it)
					{
						uint8_t *data = it->second.data;
						if ( data[0] == 0x4D ) // short event descriptor
						{
							const char *titleptr = (const char*)&data[6];
							int title_len = data[5];
							if (data[6] < 0x20)
							{
								/* custom encoding */
								title = convertDVBUTF8((unsigned char*)titleptr, title_len, 0x40, 0);
								titleptr = title.data();
								title_len = title.length();
							}
							if (title_len < textlen)
								/*Doesn't fit, so cannot match anything */
								continue;
							if (querytype == 1)
							{
								/* require exact title match */
								if (title_len != textlen)
									continue;
							}
							else if (querytype == 3)
							{
								/* Do a "startswith" match by pretending the text isn't that long */
								title_len = textlen;
							}
							if (casetype)
							{
								while (title_len >= textlen)
								{
									if (!strncasecmp(titleptr, str, textlen))
									{
										descr.push_back(it->first);
										break;
									}
									title_len--;
									titleptr++;
								}
							}
							else
							{
								while (title_len >= textlen)
								{
									if (!memcmp(titleptr, str, textlen))
									{
										descr.push_back(it->first);
										break;
									}
									title_len--;
									titleptr++;
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
				eDebug("tuple arg 3(%d) is not a known querytype(0..3)", querytype);
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

	if (!descr.empty())
	{
		int maxcount=maxmatches;
		eServiceReferenceDVB ref(refstr?(const eServiceReferenceDVB&)handleGroup(eServiceReference(refstr)):eServiceReferenceDVB(""));
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
			timeMap &evmap = cit->second.second;
			// check all events
			for (timeMap::iterator evit(evmap.begin()); evit != evmap.end() && maxcount; ++evit)
			{
				if (querytype == 0)
				{
					/* ignore the current event, when looking for similar events */
					if (evit->second->getEventID() == eventid)
						continue;
				}
				// check if any of our descriptor used by this event
				unsigned int cnt = 0;
				for (uint8_t i = 0; i < evit->second->n_crc; ++i)
				{
					uint32_t crc32 = evit->second->crc_list[i];
					for (std::deque<uint32_t>::const_iterator it = descr.begin();
						it != descr.end(); ++it)
					{
						if (*it == crc32)  // found...
						{
							++cnt;
							if (querytype)
							{
								/* we need only one match, when we're not looking for similar broadcasting events */
								i = evit->second->n_crc;
								break;
							}
						}
					}
				}
				if ( (querytype == 0 && cnt == descr.size()) ||
					 ((querytype > 0) && cnt != 0) )
				{
					const uniqueEPGKey &service = cit->first;
					std::vector<eServiceReference> refs;
					eDVBDB::getInstance()->searchAllReferences(refs, service.tsid, service.onid, service.sid);
					for (unsigned int i = 0; i < refs.size(); i++)
					{
						eServiceReference ref = refs[i];
						if (ref.valid())
						{
							ePyObject service_name;
							ePyObject service_reference;
						// create servive event
							eServiceEvent ptr;
							const eventData *ev_data=0;
							if (needServiceEvent)
							{
								if (lookupEventId(ref, evit->second->getEventID(), ev_data))
									eDebug("event not found !!!!!!!!!!!");
								else
								{
									const eServiceReferenceDVB &dref = (const eServiceReferenceDVB&)ref;
									Event ev((uint8_t*)ev_data->get());
									ptr.parseFrom(&ev, (dref.getTransportStreamID().get()<<16)|dref.getOriginalNetworkID().get());
								}
							}
						// create service name
							if (must_get_service_name && !service_name)
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

										if (must_get_service_name == 1)
										{
											size_t pos;
											// filter short name brakets
											while((pos = name.find("\xc2\x86")) != std::string::npos)
												name.erase(pos,2);
											while((pos = name.find("\xc2\x87")) != std::string::npos)
												name.erase(pos,2);
										}
										else
											name = buildShortName(name);

										if (name.length())
											service_name = PyString_FromString(name.c_str());
									}
								}
								if (!service_name)
									service_name = PyString_FromString("<n/a>");
							}
						// create servicereference string
							if (must_get_service_reference && !service_reference)
								service_reference = PyString_FromString(ref.toString().c_str());
						// create list
							if (!ret)
								ret = PyList_New(0);
						// create tuple
							ePyObject tuple = PyTuple_New(argcount);
						// fill tuple
							ePyObject tmp = ePyObject();
							fillTuple(tuple, argstring, argcount, service_reference, ev_data ? &ptr : 0, service_name, tmp, evit->second);
							PyList_Append(ret, tuple);
							Py_DECREF(tuple);
							if (service_name)
								Py_DECREF(service_name);
							if (service_reference)
								Py_DECREF(service_reference);
							--maxcount;
						}
					}
				}
			}
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
		Py_RETURN_NONE;

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
											messages.send(Message(Message::got_mhw2_channel_pid, ref, pid));
										}
									}
									else if(!memcmp((const char *)buffer+2, "FICHAS", 6))
									{
										eServiceReferenceDVB ref;
										if (!pmthandler->getServiceReference(ref))
										{
											int pid = (*es)->getPid();
											messages.send(Message(Message::got_mhw2_summary_pid, ref, pid));
										}
									}
									else if(!memcmp((const char *)buffer+2, "GENEROS", 7))
									{
										eServiceReferenceDVB ref;
										if (!pmthandler->getServiceReference(ref))
										{
											int pid = (*es)->getPid();
											messages.send(Message(Message::got_mhw2_title_pid, ref, pid));
										}
									}
								}
								break;
							default:
								break;
						}
					}
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
					if (!pmthandler->getServiceReference(ref))
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
	uint8_t data[5];
	time_t tm;
	date_time( const date_time &a )
	{
		memcpy(data, a.data, 5);
		tm = a.tm;
	}
	date_time( const uint8_t data[5])
	{
		memcpy(this->data, data, 5);
		tm = parseDVBtime(data);
	}
	date_time()
	{
	}
	const uint8_t& operator[](int pos) const
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

void eEPGCache::privateSectionRead(const uniqueEPGKey &current_service, const uint8_t *data)
{
	contentMap &content_time_table = content_time_tables[current_service];
	singleLock s(cache_lock);
	std::map< date_time, std::list<uniqueEPGKey>, less_datetime > start_times;
	std::pair<eventMap,timeMap> &eventDBitem = eventDB[current_service];
	eventMap &evMap = eventDBitem.first;
	timeMap &tmMap = eventDBitem.second;
	int ptr = 8;
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

	uint8_t duration[3];
	memcpy(duration, data+ptr, 3);
	ptr+=3;
	int duration_sec =
		fromBCD(duration[0])*3600+fromBCD(duration[1])*60+fromBCD(duration[2]);

	const uint8_t *descriptors[65];
	const uint8_t **pdescr = descriptors;

	int descriptors_length = (data[ptr++]&0x0F) << 8;
	descriptors_length |= data[ptr++];
	while ( descriptors_length > 1 )
	{
		int descr_type = data[ptr];
		int descr_len = data[ptr+1];
		descriptors_length -= 2;
		if (descriptors_length >= descr_len)
		{
			descriptors_length -= descr_len;
			if ( descr_type == 0xf2 && descr_len > 5)
			{
				ptr+=2;
				int tsid = data[ptr++] << 8;
				tsid |= data[ptr++];
				int onid = data[ptr++] << 8;
				onid |= data[ptr++];
				int sid = data[ptr++] << 8;
				sid |= data[ptr++];

// WORKAROUND for wrong transmitted epg data (01.10.2007)
				if ( onid == 0x85 )
				{
					switch( (tsid << 16) | sid )
					{
						case 0x01030b: sid = 0x1b; tsid = 4; break;  // Premiere Win
						case 0x0300f0: sid = 0xe0; tsid = 2; break;
						case 0x0300f1: sid = 0xe1; tsid = 2; break;
						case 0x0300f5: sid = 0xdc; break;
						case 0x0400d2: sid = 0xe2; tsid = 0x11; break;
						case 0x1100d3: sid = 0xe3; break;
						case 0x0100d4: sid = 0xe4; tsid = 4; break;
					}
				}
////////////////////////////////////////////

				uniqueEPGKey service( sid, onid, tsid );
				descr_len -= 6;
				while( descr_len > 2 )
				{
					uint8_t datetime[5];
					datetime[0] = data[ptr++];
					datetime[1] = data[ptr++];
					int tmp_len = data[ptr++];
					descr_len -= 3;
					if (descr_len >= tmp_len)
					{
						descr_len -= tmp_len;
						while( tmp_len > 2 )
						{
							memcpy(datetime+2, data+ptr, 3);
							ptr += 3;
							tmp_len -= 3;
							start_times[datetime].push_back(service);
						}
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
	}
	ASSERT(pdescr <= &descriptors[65]);
	uint8_t event[4098];
	eit_event_struct *ev_struct = (eit_event_struct*) event;
	ev_struct->running_status = 0;
	ev_struct->free_CA_mode = 1;
	memcpy(event+7, duration, 3);
	ptr = 12;
	const uint8_t **d=descriptors;
	while ( d < pdescr )
	{
		memcpy(event+ptr, *d, ((*d)[1])+2);
		ptr+=(*d++)[1];
		ptr+=2;
	}
	ASSERT(ptr <= 4098);
	for ( std::map< date_time, std::list<uniqueEPGKey> >::iterator it(start_times.begin()); it != start_times.end(); ++it )
	{
		time_t now = ::time(0);
		if ( (it->first.tm + duration_sec) < now )
			continue;
		memcpy(event+2, it->first.data, 5);
		int bptr = ptr;
		int cnt=0;
		for (std::list<uniqueEPGKey>::iterator i(it->second.begin()); i != it->second.end(); ++i)
		{
			event[bptr++] = 0x4A;
			uint8_t *len = event+(bptr++);
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
		uint16_t event_id = 0;
		while( evMap.find(event_id) != evMap.end() )
			++event_id;
		event[0] = (event_id & 0xFF00) >> 8;
		event[1] = (event_id & 0xFF);
		time_event_map[it->first.tm]=std::pair<time_t, uint16_t>(stime, event_id);
		eventData *d = new eventData( ev_struct, bptr, PRIVATE );
		evMap[event_id] = d;
		tmMap[stime] = d;
		ASSERT(bptr <= 4098);
	}
}

void eEPGCache::channel_data::startPrivateReader()
{
	eDVBSectionFilterMask mask;
	memset(&mask, 0, sizeof(mask));
	mask.pid = m_PrivatePid;
	mask.flags = eDVBSectionFilterMask::rfCRC;
	mask.data[0] = 0xA0;
	mask.mask[0] = 0xFF;
	eDebug("[EPGC] start privatefilter for pid %04x and version %d", m_PrivatePid, m_PrevVersion);
	if (m_PrevVersion != -1)
	{
		mask.data[3] = m_PrevVersion << 1;
		mask.mask[3] = 0x3E;
		mask.mode[3] = 0x3E;
	}
	seenPrivateSections.clear();
	if (!m_PrivateConn)
		m_PrivateReader->connectRead(slot(*this, &eEPGCache::channel_data::readPrivateData), m_PrivateConn);
	m_PrivateReader->start(mask);
}

void eEPGCache::channel_data::readPrivateData( const uint8_t *data)
{
	if ( seenPrivateSections.find(data[6]) == seenPrivateSections.end() )
	{
		cache->privateSectionRead(m_PrivateService, data);
		seenPrivateSections.insert(data[6]);
	}
	if ( seenPrivateSections.size() == (unsigned int)(data[7] + 1) )
	{
		eDebug("[EPGC] private finished");
		eDVBChannelID chid = channel->getChannelID();
		int tmp = chid.original_network_id.get();
		tmp |= 0x80000000; // we use highest bit as private epg indicator
		chid.original_network_id = tmp;
		cache->channelLastUpdated[chid] = ::time(0);
		m_PrevVersion = (data[5] & 0x3E) >> 1;
		startPrivateReader();
	}
}

#endif // ENABLE_PRIVATE_EPG

#ifdef ENABLE_MHW_EPG
void eEPGCache::channel_data::cleanupMHW()
{
	m_MHWTimeoutTimer->stop();
	m_channels.clear();
	m_themes.clear();
	m_titles.clear();
	m_program_ids.clear();
}

uint8_t *eEPGCache::channel_data::delimitName( uint8_t *in, uint8_t *out, int len_in )
{
	// Names in mhw structs are not strings as they are not '\0' terminated.
	// This function converts the mhw name into a string.
	// Constraint: "length of out" = "length of in" + 1.
	int i;
	for ( i=0; i < len_in; i++ )
		out[i] = in[i];

	i = len_in - 1;
	while ( ( i >=0 ) && ( out[i] == 0x20 ) )
		i--;

	out[i+1] = 0;
	return out;
}

void eEPGCache::channel_data::timeMHW2DVB( u_char hours, u_char minutes, u_char *return_time)
// For time of day
{
	return_time[0] = toBCD( hours );
	return_time[1] = toBCD( minutes );
	return_time[2] = 0;
}

void eEPGCache::channel_data::timeMHW2DVB( int minutes, u_char *return_time)
{
	timeMHW2DVB( int(minutes/60), minutes%60, return_time );
}

void eEPGCache::channel_data::timeMHW2DVB( u_char day, u_char hours, u_char minutes, u_char *return_time)
// For date plus time of day
{
	char tz_saved[1024];
	// Remove offset in mhw time.
	uint8_t local_hours = hours;
	if ( hours >= 16 )
		local_hours -= 4;
	else if ( hours >= 8 )
		local_hours -= 2;

	// As far as we know all mhw time data is sent in central Europe time zone.
	// So, temporarily set timezone to western europe
	time_t dt = ::time(0);

	char *old_tz = getenv( "TZ" );
	if (old_tz)
		strcpy(tz_saved, old_tz);
	putenv((char*)"TZ=CET-1CEST,M3.5.0/2,M10.5.0/3");
	tzset();

	tm localnow;
	localtime_r(&dt, &localnow);

	if (day == 7)
		day = 0;
	if ( day + 1 < localnow.tm_wday )		// day + 1 to prevent old events to show for next week.
		day += 7;
	if (local_hours <= 5)
		day++;

	dt += 3600*24*(day - localnow.tm_wday);	// Shift dt to the recording date (local time zone).
	dt += 3600*(local_hours - localnow.tm_hour);  // Shift dt to the recording hour.

	tm recdate;
	gmtime_r( &dt, &recdate );   // This will also take care of DST.

	if ( old_tz == NULL )
		unsetenv( "TZ" );
	else
		setenv("TZ", tz_saved, 1);
	tzset();

	// Calculate MJD according to annex in ETSI EN 300 468
	int l=0;
	if ( recdate.tm_mon <= 1 )	// Jan or Feb
		l=1;
	int mjd = 14956 + recdate.tm_mday + int( (recdate.tm_year - l) * 365.25) +
		int( (recdate.tm_mon + 2 + l * 12) * 30.6001);

	return_time[0] = (mjd & 0xFF00)>>8;
	return_time[1] = mjd & 0xFF;

	timeMHW2DVB( recdate.tm_hour, minutes, return_time+2 );
}

void eEPGCache::channel_data::storeMHWTitle(std::map<uint32_t, mhw_title_t>::iterator itTitle, std::string sumText, const uint8_t *data)
// data is borrowed from calling proc to save memory space.
{
	uint8_t name[34];

	// For each title a separate EIT packet will be sent to eEPGCache::sectionRead()
	bool isMHW2 = itTitle->second.mhw2_mjd_hi || itTitle->second.mhw2_mjd_lo ||
		itTitle->second.mhw2_duration_hi || itTitle->second.mhw2_duration_lo;

	eit_t *packet = (eit_t *) data;
	packet->table_id = 0x50;
	packet->section_syntax_indicator = 1;

	packet->service_id_hi = m_channels[ itTitle->second.channel_id - 1 ].channel_id_hi;
	packet->service_id_lo = m_channels[ itTitle->second.channel_id - 1 ].channel_id_lo;
	packet->version_number = 0;	// eEPGCache::sectionRead() will dig this for the moment
	packet->current_next_indicator = 0;
	packet->section_number = 0;	// eEPGCache::sectionRead() will dig this for the moment
	packet->last_section_number = 0;	// eEPGCache::sectionRead() will dig this for the moment
	packet->transport_stream_id_hi = m_channels[ itTitle->second.channel_id - 1 ].transport_stream_id_hi;
	packet->transport_stream_id_lo = m_channels[ itTitle->second.channel_id - 1 ].transport_stream_id_lo;
	packet->original_network_id_hi = m_channels[ itTitle->second.channel_id - 1 ].network_id_hi;
	packet->original_network_id_lo = m_channels[ itTitle->second.channel_id - 1 ].network_id_lo;
	packet->segment_last_section_number = 0; // eEPGCache::sectionRead() will dig this for the moment
	packet->segment_last_table_id = 0x50;

	uint8_t *title = isMHW2 ? ((uint8_t*)(itTitle->second.title))-4 : (uint8_t*)itTitle->second.title;
	std::string prog_title = (char *) delimitName( title, name, isMHW2 ? 35 : 23 );
	int prog_title_length = prog_title.length();

	int packet_length = EIT_SIZE + EIT_LOOP_SIZE + EIT_SHORT_EVENT_DESCRIPTOR_SIZE +
		prog_title_length + 1;

	eit_event_t *event_data = (eit_event_t *) (data + EIT_SIZE);
	event_data->event_id_hi = (( itTitle->first ) >> 8 ) & 0xFF;
	event_data->event_id_lo = ( itTitle->first ) & 0xFF;

	if (isMHW2)
	{
		u_char *data = (u_char*) event_data;
		data[2] = itTitle->second.mhw2_mjd_hi;
		data[3] = itTitle->second.mhw2_mjd_lo;
		data[4] = itTitle->second.mhw2_hours;
		data[5] = itTitle->second.mhw2_minutes;
		data[6] = itTitle->second.mhw2_seconds;
		timeMHW2DVB( HILO(itTitle->second.mhw2_duration), data+7 );
	}
	else
	{
		timeMHW2DVB( itTitle->second.dh.day, itTitle->second.dh.hours, itTitle->second.ms.minutes,
		(u_char *) event_data + 2 );
		timeMHW2DVB( HILO(itTitle->second.duration), (u_char *) event_data+7 );
	}

	event_data->running_status = 0;
	event_data->free_CA_mode = 0;
	int descr_ll = EIT_SHORT_EVENT_DESCRIPTOR_SIZE + 1 + prog_title_length;

	eit_short_event_descriptor_struct *short_event_descriptor =
		(eit_short_event_descriptor_struct *) ( (u_char *) event_data + EIT_LOOP_SIZE);
	short_event_descriptor->descriptor_tag = EIT_SHORT_EVENT_DESCRIPTOR;
	short_event_descriptor->descriptor_length = EIT_SHORT_EVENT_DESCRIPTOR_SIZE +
		prog_title_length - 1;
	short_event_descriptor->language_code_1 = 'e';
	short_event_descriptor->language_code_2 = 'n';
	short_event_descriptor->language_code_3 = 'g';
	short_event_descriptor->event_name_length = prog_title_length;
	u_char *event_name = (u_char *) short_event_descriptor + EIT_SHORT_EVENT_DESCRIPTOR_SIZE;
	memcpy(event_name, prog_title.c_str(), prog_title_length);

	// Set text length
	event_name[prog_title_length] = 0;

	if ( sumText.length() > 0 )
	// There is summary info
	{
		unsigned int sum_length = sumText.length();
		if ( sum_length + short_event_descriptor->descriptor_length <= 0xff )
		// Store summary in short event descriptor
		{
			// Increase all relevant lengths
			event_name[prog_title_length] = sum_length;
			short_event_descriptor->descriptor_length += sum_length;
			packet_length += sum_length;
			descr_ll += sum_length;
			sumText.copy( (char *) event_name+prog_title_length+1, sum_length );
		}
		else
		// Store summary in extended event descriptors
		{
			int remaining_sum_length = sumText.length();
			int nbr_descr = int(remaining_sum_length/247) + 1;
			for ( int i=0; i < nbr_descr; i++)
			// Loop once per extended event descriptor
			{
				eit_extended_descriptor_struct *ext_event_descriptor = (eit_extended_descriptor_struct *) (data + packet_length);
				sum_length = remaining_sum_length > 247 ? 247 : remaining_sum_length;
				remaining_sum_length -= sum_length;
				packet_length += 8 + sum_length;
				descr_ll += 8 + sum_length;

				ext_event_descriptor->descriptor_tag = EIT_EXTENDED_EVENT_DESCRIPOR;
				ext_event_descriptor->descriptor_length = sum_length + 6;
				ext_event_descriptor->descriptor_number = i;
				ext_event_descriptor->last_descriptor_number = nbr_descr - 1;
				ext_event_descriptor->iso_639_2_language_code_1 = 'e';
				ext_event_descriptor->iso_639_2_language_code_2 = 'n';
				ext_event_descriptor->iso_639_2_language_code_3 = 'g';
				u_char *the_text = (u_char *) ext_event_descriptor + 8;
				the_text[-2] = 0;
				the_text[-1] = sum_length;
				sumText.copy( (char *) the_text, sum_length, sumText.length() - sum_length - remaining_sum_length );
			}
		}
	}

	if (!isMHW2)
	{
		// Add content descriptor
		u_char *descriptor = (u_char *) data + packet_length;
		packet_length += 4;
		descr_ll += 4;

		int content_id = 0;
		std::string content_descr = (char *) delimitName( m_themes[itTitle->second.theme_id].name, name, 15 );
		if ( content_descr.find( "FILM" ) != std::string::npos )
			content_id = 0x10;
		else if ( content_descr.find( "SPORT" ) != std::string::npos )
			content_id = 0x40;

		descriptor[0] = 0x54;
		descriptor[1] = 2;
		descriptor[2] = content_id;
		descriptor[3] = 0;
	}

	event_data->descriptors_loop_length_hi = (descr_ll & 0xf00)>>8;
	event_data->descriptors_loop_length_lo = (descr_ll & 0xff);

	packet->section_length_hi =  ((packet_length - 3)&0xf00)>>8;
	packet->section_length_lo =  (packet_length - 3)&0xff;

	// Feed the data to eEPGCache::sectionRead()
	cache->sectionRead( data, MHW, this );
}

void eEPGCache::channel_data::startMHWTimeout(int msec)
{
	m_MHWTimeoutTimer->start(msec,true);
	m_MHWTimeoutet=false;
}

void eEPGCache::channel_data::startMHWReader(uint16_t pid, uint8_t tid)
{
	m_MHWFilterMask.pid = pid;
	m_MHWFilterMask.data[0] = tid;
	m_MHWReader->start(m_MHWFilterMask);
//	eDebug("start 0x%02x 0x%02x", pid, tid);
}

void eEPGCache::channel_data::startMHWReader2(uint16_t pid, uint8_t tid, int ext)
{
	m_MHWFilterMask2.pid = pid;
	m_MHWFilterMask2.data[0] = tid;
	if (ext != -1)
	{
		m_MHWFilterMask2.data[1] = ext;
		m_MHWFilterMask2.mask[1] = 0xFF;
//		eDebug("start 0x%03x 0x%02x 0x%02x", pid, tid, ext);
	}
	else
	{
		m_MHWFilterMask2.data[1] = 0;
		m_MHWFilterMask2.mask[1] = 0;
//		eDebug("start 0x%02x 0x%02x", pid, tid);
	}
	m_MHWReader2->start(m_MHWFilterMask2);
}

void eEPGCache::channel_data::readMHWData(const uint8_t *data)
{
	if ( m_MHWReader2 )
		m_MHWReader2->stop();

	if ( state > 1 || // aborted
		// have si data.. so we dont read mhw data
		(haveData & (SCHEDULE|SCHEDULE_OTHER|VIASAT)) )
	{
		eDebug("[EPGC] mhw aborted %d", state);
	}
	else if (m_MHWFilterMask.pid == 0xD3 && m_MHWFilterMask.data[0] == 0x91)
	// Channels table
	{
		int len = ((data[1]&0xf)<<8) + data[2] - 1;
		int record_size = sizeof( mhw_channel_name_t );
		int nbr_records = int (len/record_size);

		m_channels.resize(nbr_records);
		for ( int i = 0; i < nbr_records; i++ )
		{
			mhw_channel_name_t *channel = (mhw_channel_name_t*) &data[4 + i*record_size];
			m_channels[i]=*channel;
		}
		haveData |= MHW;

		eDebug("[EPGC] mhw %d channels found", m_channels.size());

		// Channels table has been read, start reading the themes table.
		startMHWReader(0xD3, 0x92);
		return;
	}
	else if (m_MHWFilterMask.pid == 0xD3 && m_MHWFilterMask.data[0] == 0x92)
	// Themes table
	{
		int len = ((data[1]&0xf)<<8) + data[2] - 16;
		int record_size = sizeof( mhw_theme_name_t );
		int nbr_records = int (len/record_size);
		int idx_ptr = 0;
		uint8_t next_idx = (uint8_t) *(data + 3 + idx_ptr);
		uint8_t idx = 0;
		uint8_t sub_idx = 0;
		for ( int i = 0; i < nbr_records; i++ )
		{
			mhw_theme_name_t *theme = (mhw_theme_name_t*) &data[19 + i*record_size];
			if ( i >= next_idx )
			{
				idx = (idx_ptr<<4);
				idx_ptr++;
				next_idx = (uint8_t) *(data + 3 + idx_ptr);
				sub_idx = 0;
			}
			else
				sub_idx++;

			m_themes[idx+sub_idx] = *theme;
		}
		eDebug("[EPGC] mhw %d themes found", m_themes.size());
		// Themes table has been read, start reading the titles table.
		startMHWReader(0xD2, 0x90);
		startMHWTimeout(4000);
		return;
	}
	else if (m_MHWFilterMask.pid == 0xD2 && m_MHWFilterMask.data[0] == 0x90)
	// Titles table
	{
		mhw_title_t *title = (mhw_title_t*) data;
		uint8_t name[24];
		std::string prog_title = (char *) delimitName( title->title, name, 23 );

		if ( title->channel_id == 0xFF || prog_title.substr(0,7) == "BIENTOT" )	// Separator or BIENTOT record
			return;	// Continue reading of the current table.
		else
		{
			// Create unique key per title
			uint32_t title_id = ((title->channel_id)<<16)|((title->dh.day)<<13)|((title->dh.hours)<<8)|
				(title->ms.minutes);
			uint32_t program_id = ((title->program_id_hi)<<24)|((title->program_id_mh)<<16)|
				((title->program_id_ml)<<8)|(title->program_id_lo);

			if ( m_titles.find( title_id ) == m_titles.end() )
			{
				startMHWTimeout(4000);
				title->mhw2_mjd_hi = 0;
				title->mhw2_mjd_lo = 0;
				title->mhw2_duration_hi = 0;
				title->mhw2_duration_lo = 0;
				m_titles[ title_id ] = *title;
				if ( (title->ms.summary_available) && (m_program_ids.find(program_id) == m_program_ids.end()) )
					// program_ids will be used to gather summaries.
					m_program_ids.insert(std::pair<uint32_t,uint32_t>(program_id,title_id));
				return;	// Continue reading of the current table.
			}
			else if (!checkMHWTimeout())
				return;
		}
		if ( !m_program_ids.empty())
		{
			// Titles table has been read, there are summaries to read.
			// Start reading summaries, store corresponding titles on the fly.
			startMHWReader(0xD3, 0x90);
			eDebug("[EPGC] mhw %d titles(%d with summary) found",
				m_titles.size(),
				m_program_ids.size());
			startMHWTimeout(4000);
			return;
		}
	}
	else if (m_MHWFilterMask.pid == 0xD3 && m_MHWFilterMask.data[0] == 0x90)
	// Summaries table
	{
		mhw_summary_t *summary = (mhw_summary_t*) data;

		// Create unique key per record
		uint32_t program_id = ((summary->program_id_hi)<<24)|((summary->program_id_mh)<<16)|
			((summary->program_id_ml)<<8)|(summary->program_id_lo);
		int len = ((data[1]&0xf)<<8) + data[2];

		// ugly workaround to convert const __u8* to char*
		char *tmp=0;
		memcpy(&tmp, &data, sizeof(void*));
		tmp[len+3] = 0;	// Terminate as a string.

		std::multimap<uint32_t, uint32_t>::iterator itProgid( m_program_ids.find( program_id ) );
		if ( itProgid == m_program_ids.end() )
		{ /*	This part is to prevent to looping forever if some summaries are not received yet.
			There is a timeout of 4 sec. after the last successfully read summary. */
			if (!m_program_ids.empty() && !checkMHWTimeout())
				return;	// Continue reading of the current table.
		}
		else
		{
			std::string the_text = (char *) (data + 11 + summary->nb_replays * 7);

			unsigned int pos=0;
			while((pos = the_text.find("\r\n")) != std::string::npos)
				the_text.replace(pos, 2, " ");

			// Find corresponding title, store title and summary in epgcache.
			std::map<uint32_t, mhw_title_t>::iterator itTitle( m_titles.find( itProgid->second ) );
			if ( itTitle != m_titles.end() )
			{
				startMHWTimeout(4000);
				storeMHWTitle( itTitle, the_text, data );
				m_titles.erase( itTitle );
			}
			m_program_ids.erase( itProgid );
			if ( !m_program_ids.empty() )
				return;	// Continue reading of the current table.
		}
	}
	eDebug("[EPGC] mhw finished(%ld) %d summaries not found",
		::time(0),
		m_program_ids.size());
	// Summaries have been read, titles that have summaries have been stored.
	// Now store titles that do not have summaries.
	for (std::map<uint32_t, mhw_title_t>::iterator itTitle(m_titles.begin()); itTitle != m_titles.end(); itTitle++)
		storeMHWTitle( itTitle, "", data );
	isRunning &= ~MHW;
	m_MHWConn=0;
	if ( m_MHWReader )
		m_MHWReader->stop();
	if (haveData)
		finishEPG();
}

void eEPGCache::channel_data::readMHWData2(const uint8_t *data)
{
	int dataLen = (((data[1]&0xf) << 8) | data[2]) + 3;

	if ( m_MHWReader )
		m_MHWReader->stop();

	if ( state > 1 || // aborted
		// have si data.. so we dont read mhw data
		(haveData & (SCHEDULE|SCHEDULE_OTHER|VIASAT)) )
	{
		eDebug("[EPGC] mhw2 aborted %d", state);
	}
	else if (m_MHWFilterMask2.pid == m_mhw2_channel_pid && m_MHWFilterMask2.data[0] == 0xC8 && m_MHWFilterMask2.data[1] == 0)
	// Channels table
	{
		int num_channels = data[120];
		m_channels.resize(num_channels);
		if(dataLen > 120)
		{
			int ptr = 121 + 8 * num_channels;
			if( dataLen > ptr )
			{
				for( int chid = 0; chid < num_channels; ++chid )
				{
					ptr += ( data[ptr] & 0x0f ) + 1;
					if( dataLen < ptr )
						goto abort;
				}
			}
			else
				goto abort;
		}
		else
			goto abort;
		// data seems consistent...
		const uint8_t *tmp = data+121;
		for (int i=0; i < num_channels; ++i)
		{
			mhw_channel_name_t channel;
			channel.network_id_hi = *(tmp++);
			channel.network_id_lo = *(tmp++);
			channel.transport_stream_id_hi = *(tmp++);
			channel.transport_stream_id_lo = *(tmp++);
			channel.channel_id_hi = *(tmp++);
			channel.channel_id_lo = *(tmp++);
			m_channels[i]=channel;
//			eDebug("%d(%02x) %04x: %02x %02x", i, i, (channel.channel_id_hi << 8) | channel.channel_id_lo, *tmp, *(tmp+1));
			tmp+=2;
		}
		for (int i=0; i < num_channels; ++i)
		{
			mhw_channel_name_t &channel = m_channels[i];
			int channel_name_len=*(tmp++)&0x0f;
			int x=0;
			for (; x < channel_name_len; ++x)
				channel.name[x]=*(tmp++);
			channel.name[x+1]=0;
//			eDebug("%d(%02x) %s", i, i, channel.name);
		}
		haveData |= MHW;
		eDebug("[EPGC] mhw2 %d channels found", m_channels.size());
	}
	else if (m_MHWFilterMask2.pid == m_mhw2_channel_pid && m_MHWFilterMask2.data[0] == 0xC8 && m_MHWFilterMask2.data[1] == 1)
	{
		// Themes table
		eDebug("[EPGC] mhw2 themes nyi");
	}
	else if (m_MHWFilterMask2.pid == m_mhw2_title_pid && m_MHWFilterMask2.data[0] == 0xe6)
	// Titles table
	{
		int pos=18;
		bool valid=false;
		bool finish=false;

//		eDebug("%02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x",
//			data[3], data[4], data[5], data[6], data[7], data[8], data[9], data[10],
//			data[11], data[12], data[13], data[14], data[15], data[16], data[17] );

		while( pos < dataLen && !valid)
		{
			pos += 18;
			pos += (data[pos] & 0x3F) + 4;
			if( pos == dataLen )
				valid = true;
		}

		if (!valid)
		{
			if (dataLen > 18)
				eDebug("mhw2 title table invalid!!");
			if (checkMHWTimeout())
				goto abort;
			if (!m_MHWTimeoutTimer->isActive())
				startMHWTimeout(5000);
			return; // continue reading
		}

		// data seems consistent...
		mhw_title_t title;
		pos = 18;
		while (pos < dataLen)
		{
//			eDebugNoNewLine("    [%02x] %02x %02x %02x %02x %02x %02x %02x %02x %02x %02x [%02x %02x %02x %02x %02x %02x %02x] LL - DESCR - ",
//				data[pos], data[pos+1], data[pos+2], data[pos+3], data[pos+4], data[pos+5], data[pos+6], data[pos+7],
//				data[pos+8], data[pos+9], data[pos+10], data[pos+11], data[pos+12], data[pos+13], data[pos+14], data[pos+15], data[pos+16], data[pos+17]);
			title.channel_id = data[pos]+1;
			title.mhw2_mjd_hi = data[pos+11];
			title.mhw2_mjd_lo = data[pos+12];
			title.mhw2_hours = data[pos+13];
			title.mhw2_minutes = data[pos+14];
			title.mhw2_seconds = data[pos+15];
			int duration = ((data[pos+16] << 8)|data[pos+17]) >> 4;
			title.mhw2_duration_hi = (duration&0xFF00) >> 8;
			title.mhw2_duration_lo = duration&0xFF;

			// Create unique key per title
			uint32_t title_id = (data[pos+7] << 24) | (data[pos+8] << 16) | (data[pos+9] << 8) | data[pos+10];

			uint8_t slen = data[pos+18] & 0x3f;
			uint8_t *dest = ((uint8_t*)title.title)-4;
			memcpy(dest, &data[pos+19], slen>35 ? 35 : slen);
			memset(dest+slen, 0, 35-slen);
			pos += 19 + slen;
//			eDebug("%02x [%02x %02x]: %s", data[pos], data[pos+1], data[pos+2], dest);

//			not used theme id (data[7] & 0x3f) + (data[pos] & 0x3f);
			uint32_t summary_id = (data[pos+1] << 8) | data[pos+2];

//			if (title.channel_id > m_channels.size())
//				eDebug("channel_id(%d %02x) to big!!", title.channel_id);

//			eDebug("pos %d prog_id %02x %02x chid %02x summary_id %04x dest %p len %d\n",
//				pos, title.program_id_ml, title.program_id_lo, title.channel_id, summary_id, dest, slen);

//			eDebug("title_id %08x -> summary_id %04x\n", title_id, summary_id);

			pos += 3;

			std::map<uint32_t, mhw_title_t>::iterator it = m_titles.find( title_id );
			if ( it == m_titles.end() )
			{
				startMHWTimeout(5000);
				m_titles[ title_id ] = title;
				if (summary_id != 0xFFFF)
				{
					bool add=true;
					std::multimap<uint32_t, uint32_t>::iterator it(m_program_ids.lower_bound(summary_id));
					while (it != m_program_ids.end() && it->first == summary_id)
					{
						if (it->second == title_id) {
							add=false;
							break;
						}
						++it;
					}
					if (add)
						m_program_ids.insert(std::pair<uint32_t,uint32_t>(summary_id,title_id));
				}
			}
			else
			{
				if ( !checkMHWTimeout() )
					continue;	// Continue reading of the current table.
				finish=true;
				break;
			}
		}
		if (finish)
		{
			eDebug("[EPGC] mhw2 %d titles(%d with summary) found", m_titles.size(), m_program_ids.size());
			if (!m_program_ids.empty())
			{
				// Titles table has been read, there are summaries to read.
				// Start reading summaries, store corresponding titles on the fly.
				startMHWReader2(m_mhw2_summary_pid, 0x96);
				startMHWTimeout(15000);
				return;
			}
		}
		else
			return;
	}
	else if (m_MHWFilterMask2.pid == m_mhw2_summary_pid && m_MHWFilterMask2.data[0] == 0x96)
	// Summaries table
	{
		if (!checkMHWTimeout())
		{
			int len, loop, pos, lenline;
			bool valid;
			valid = true;
			if( dataLen > 15 )
			{
				loop = data[14];
				pos = 15 + loop;
				if( dataLen > pos )
				{
					loop = data[pos] & 0x0f;
					pos += 1;
					if( dataLen > pos )
					{
						len = 0;
						for( ; loop > 0; --loop )
						{
							if( dataLen > (pos+len) )
							{
								lenline = data[pos+len];
								len += lenline + 1;
							}
							else
								valid=false;
						}
					}
				}
			}
			else
				return;  // continue reading

			if (valid)
			{
				// data seems consistent...
				uint32_t summary_id = (data[3]<<8)|data[4];
//				eDebug ("summary id %04x\n", summary_id);
//				eDebug("[%02x %02x] %02x %02x %02x %02x %02x %02x %02x %02x XX\n", data[3], data[4], data[5], data[6], data[7], data[8], data[9], data[10], data[11], data[12], data[13] );

				// ugly workaround to convert const __u8* to char*
				char *tmp=0;
				memcpy(&tmp, &data, sizeof(void*));

				len = 0;
				loop = data[14];
				pos = 15 + loop;
				loop = tmp[pos] & 0x0f;
				pos += 1;
				for( ; loop > 0; loop -- )
				{
					lenline = tmp[pos+len];
					tmp[pos+len] = ' ';
					len += lenline + 1;
				}
				if( len > 0 )
					tmp[pos+len] = 0;
				else
					tmp[pos+1] = 0;

				std::multimap<uint32_t, uint32_t>::iterator itProgId( m_program_ids.lower_bound(summary_id) );
				if ( itProgId == m_program_ids.end() || itProgId->first != summary_id)
				{ /*	This part is to prevent to looping forever if some summaries are not received yet.
					There is a timeout of 4 sec. after the last successfully read summary. */
					if ( !m_program_ids.empty() )
						return;	// Continue reading of the current table.
				}
				else
				{
					startMHWTimeout(15000);
					std::string the_text = (char *) (data + pos + 1);

//					eDebug ("summary id %04x : %s\n", summary_id, data+pos+1);

					while( itProgId != m_program_ids.end() && itProgId->first == summary_id )
					{
//						eDebug(".");
						// Find corresponding title, store title and summary in epgcache.
						std::map<uint32_t, mhw_title_t>::iterator itTitle( m_titles.find( itProgId->second ) );
						if ( itTitle != m_titles.end() )
						{
							storeMHWTitle( itTitle, the_text, data );
							m_titles.erase( itTitle );
						}
						m_program_ids.erase( itProgId++ );
					}
					if ( !m_program_ids.empty() )
						return;	// Continue reading of the current table.
				}
			}
			else
				return;  // continue reading
		}
	}
	if (isRunning & eEPGCache::MHW)
	{
		if ( m_MHWFilterMask2.pid == m_mhw2_channel_pid && m_MHWFilterMask2.data[0] == 0xC8 && m_MHWFilterMask2.data[1] == 0)
		{
			// Channels table has been read, start reading the themes table.
			startMHWReader2(m_mhw2_channel_pid, 0xC8, 1);
			return;
		}
		else if ( m_MHWFilterMask2.pid == m_mhw2_channel_pid && m_MHWFilterMask2.data[0] == 0xC8 && m_MHWFilterMask2.data[1] == 1)
		{
			// Themes table has been read, start reading the titles table.
			startMHWReader2(m_mhw2_title_pid, 0xe6);
			return;
		}
		else
		{
			// Summaries have been read, titles that have summaries have been stored.
			// Now store titles that do not have summaries.
			for (std::map<uint32_t, mhw_title_t>::iterator itTitle(m_titles.begin()); itTitle != m_titles.end(); itTitle++)
				storeMHWTitle( itTitle, "", data );
			eDebug("[EPGC] mhw2 finished(%ld) %d summaries not found",
				::time(0),
				m_program_ids.size());
		}
	}
abort:
	isRunning &= ~MHW;
	m_MHWConn2=0;
	if ( m_MHWReader2 )
		m_MHWReader2->stop();
	if (haveData)
		finishEPG();
}
#endif
