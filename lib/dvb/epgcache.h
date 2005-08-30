#ifndef __epgcache_h_
#define __epgcache_h_

#include <vector>
#include <list>
#include <ext/hash_map>
#include <ext/hash_set>

#include <errno.h>

#include <lib/dvb/eit.h>
#include <lib/dvb/lowlevel/eit.h>
#include <lib/dvb/idvb.h>
#include <lib/dvb/demux.h>
#include <lib/dvb/dvbtime.h>
#include <lib/base/ebase.h>
#include <lib/base/thread.h>
#include <lib/base/message.h>

#define CLEAN_INTERVAL 60000    //  1 min
#define UPDATE_INTERVAL 3600000  // 60 min
#define ZAP_DELAY 2000          // 2 sek

#define HILO(x) (x##_hi << 8 | x##_lo)

class eventData;
class eServiceReferenceDVB;

struct uniqueEPGKey
{
	int sid, onid, tsid;
	uniqueEPGKey( const eServiceReferenceDVB &ref )
		:sid( ref.type != eServiceReference::idInvalid ? ref.getServiceID().get() : -1 )
		,onid( ref.type != eServiceReference::idInvalid ? ref.getOriginalNetworkID().get() : -1 )
		,tsid( ref.type != eServiceReference::idInvalid ? ref.getTransportStreamID().get() : -1 )
	{
	}
	uniqueEPGKey()
		:sid(-1), onid(-1), tsid(-1)
	{
	}
	uniqueEPGKey( int sid, int onid, int tsid )
		:sid(sid), onid(onid), tsid(tsid)
	{
	}
	bool operator <(const uniqueEPGKey &a) const
	{
		return memcmp( &sid, &a.sid, sizeof(int)*3)<0;
	}
	operator bool() const
	{ 
		return !(sid == -1 && onid == -1 && tsid == -1); 
	}
	bool operator==(const uniqueEPGKey &a) const
	{
		return !memcmp( &sid, &a.sid, sizeof(int)*3);
	}
	struct equal
	{
		bool operator()(const uniqueEPGKey &a, const uniqueEPGKey &b) const
		{
			return !memcmp( &a.sid, &b.sid, sizeof(int)*3);
		}
	};
};

//eventMap is sorted by event_id
#define eventMap std::map<__u16, eventData*>
//timeMap is sorted by beginTime
#define timeMap std::map<time_t, eventData*>

#define channelMapIterator std::map<iDVBChannel*, channel_data*>::iterator
#define updateMap std::map<eDVBChannelID, time_t>

struct hash_uniqueEPGKey
{
	inline size_t operator()( const uniqueEPGKey &x) const
	{
		return (x.onid << 16) | x.tsid;
	}
};

#define tidMap std::set<__u32>
#if defined(__GNUC__) && ((__GNUC__ == 3 && __GNUC_MINOR__ >= 1) || __GNUC__ == 4 )  // check if gcc version >= 3.1
	#define eventCache __gnu_cxx::hash_map<uniqueEPGKey, std::pair<eventMap, timeMap>, hash_uniqueEPGKey, uniqueEPGKey::equal>
#else // for older gcc use following
	#define eventCache std::hash_map<uniqueEPGKey, std::pair<eventMap, timeMap>, hash_uniqueEPGKey, uniqueEPGKey::equal >
#endif

#define descriptorPair std::pair<int,__u8*>
#define descriptorMap std::map<__u32, descriptorPair >

class eventData
{
 	friend class eEPGCache;
private:
	__u8* EITdata;
	int ByteSize;
	static descriptorMap descriptors;
public:
	int type;
	static int CacheSize;
	static void load(FILE *);
	static void save(FILE *);
	eventData(const eit_event_struct* e, int size, int type);
	~eventData();
	const eit_event_struct* get() const;
	operator const eit_event_struct*() const
	{
		return get();
	}
	int getEventID()
	{
		return (EITdata[0] << 8) | EITdata[1];
	}
	time_t getStartTime()
	{
		return parseDVBtime(EITdata[2], EITdata[3], EITdata[4], EITdata[5], EITdata[6]);
	}
	int getDuration()
	{
		return fromBCD(EITdata[7])*3600+fromBCD(EITdata[8])*60+fromBCD(EITdata[9]);
	}
};

class eEPGCache: public eMainloop, private eThread, public Object
{
	DECLARE_REF(eEPGCache)
	struct channel_data: public Object
	{
		channel_data(eEPGCache*);
		eEPGCache *cache;
		eTimer abortTimer, zapTimer;
		__u8 state, isRunning, haveData, can_delete;
		ePtr<eDVBChannel> channel;
		ePtr<eConnection> m_stateChangedConn, m_NowNextConn, m_ScheduleConn, m_ScheduleOtherConn;
		ePtr<iDVBSectionReader> m_NowNextReader, m_ScheduleReader, m_ScheduleOtherReader;
		tidMap seenSections[3], calcedSections[3];
		void readData(const __u8 *data);
		void startChannel();
		void startEPG();
		bool finishEPG();
		void abortEPG();
		void abortNonAvail();
	};
public:
	enum {NOWNEXT=1, SCHEDULE=2, SCHEDULE_OTHER=4};
	struct Message
	{
		enum
		{
			flush,
			startChannel,
			leaveChannel,
			pause,
			restart,
			updated,
			isavail,
			quit,
			timeChanged
		};
		int type;
		iDVBChannel *channel;
		uniqueEPGKey service;
		union {
			int err;
			time_t time;
			bool avail;
		};
		Message()
			:type(0), time(0) {}
		Message(int type)
			:type(type) {}
		Message(int type, bool b)
			:type(type), avail(b) {}
		Message(int type, iDVBChannel *channel, int err=0)
			:type(type), channel(channel), err(err) {}
		Message(int type, const eServiceReferenceDVB& service, int err=0)
			:type(type), service(service), err(err) {}
		Message(int type, time_t time)
			:type(type), time(time) {}
	};
	eFixedMessagePump<Message> messages;
private:
	friend class channel_data;
	static eEPGCache *instance;

	eTimer cleanTimer;
	std::map<iDVBChannel*, channel_data*> m_knownChannels;
	ePtr<eConnection> m_chanAddedConn;

	eventCache eventDB;
	updateMap channelLastUpdated;
	static pthread_mutex_t cache_lock, channel_map_lock;

	void thread();  // thread function

// called from epgcache thread
	void save();
	void load();
	void sectionRead(const __u8 *data, int source, channel_data *channel);
	void gotMessage(const Message &message);
	void flushEPG(const uniqueEPGKey & s=uniqueEPGKey());
	void cleanLoop();

// called from main thread
	void timeUpdated();
	void DVBChannelAdded(eDVBChannel*);
	void DVBChannelStateChanged(iDVBChannel*);
	void DVBChannelRunning(iDVBChannel *);
public:
	static RESULT getInstance(ePtr<eEPGCache> &ptr);
	eEPGCache();
	~eEPGCache();

	// called from main thread
	inline void Lock();
	inline void Unlock();

	// result Event * must be deleted by caller of lookupEvent
	inline RESULT lookupEvent(const eServiceReferenceDVB &service, int event_id, Event *& );
	inline RESULT lookupEvent(const eServiceReferenceDVB &service, time_t , Event *& );

	// methods for faster use.. but not thread save ..
	// Lock and Unlock should be used !!
	RESULT lookupEvent(const eServiceReferenceDVB &service, int event_id, const eventData *& );
	RESULT lookupEvent(const eServiceReferenceDVB &service, time_t , const eventData *& );

	inline RESULT getEventMap(const eServiceReferenceDVB &service, const eventMap *& );
	inline RESULT getTimeMap(const eServiceReferenceDVB &service, const timeMap *& );
};

TEMPLATE_TYPEDEF(ePtr<eEPGCache>,eEPGCachePtr);

inline RESULT eEPGCache::lookupEvent(const eServiceReferenceDVB &service, time_t t, Event *& result )
{
	const eventData *data=0;
	RESULT ret = lookupEvent(service, t, data);
	if ( !ret && data )
		result = new Event((uint8_t*)data->get());
	return ret;
}

inline RESULT eEPGCache::lookupEvent(const eServiceReferenceDVB &service, int event_id, Event *& result)
{
	const eventData *data=0;
	RESULT ret = lookupEvent(service, event_id, data);
	if ( !ret && data )
		result = new Event((uint8_t*)data->get());
	return ret;
}

inline RESULT eEPGCache::getEventMap(const eServiceReferenceDVB &service, const eventMap *& result)
{
	eventCache::iterator It = eventDB.find( service );
	if ( It != eventDB.end() && It->second.first.size() )
	{
		result=&(It->second.first);
		return 0;
	}
	else
		result=0;
	return -1;
}

inline RESULT eEPGCache::getTimeMap(const eServiceReferenceDVB &service, const timeMap *& result)
{
	eventCache::iterator It = eventDB.find( service );
	if ( It != eventDB.end() && It->second.second.size() )
	{
		result=&(It->second.second);
		return 0;
	}
	else
		result=0;
	return -1;
}

inline void eEPGCache::Lock()
{
	pthread_mutex_lock(&cache_lock);
}

inline void eEPGCache::Unlock()
{
	pthread_mutex_unlock(&cache_lock);
}

#endif
