#ifndef __epgcache_h_
#define __epgcache_h_

#ifndef SWIG

#include <vector>
#include <list>
#include <ext/hash_map>

// check if gcc version >= 3.4
#if defined(__GNUC__) && ((__GNUC__ == 3 && __GNUC_MINOR__ >= 4) || __GNUC__ == 4 )
#else
#include <ext/stl_hash_fun.h>
#endif
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

#define tmpMap std::map<uniqueEPGKey, std::pair<time_t, int> >

#if defined(__GNUC__) && ((__GNUC__ == 3 && __GNUC_MINOR__ >= 1) || __GNUC__ == 4 )  // check if gcc version >= 3.1
	#define eventCache __gnu_cxx::hash_map<uniqueEPGKey, std::pair<eventMap, timeMap>, __gnu_cxx::hash<uniqueEPGKey>, uniqueEPGKey::equal>
	#define updateMap __gnu_cxx::hash_map<uniqueEPGKey, time_t, __gnu_cxx::hash<uniqueEPGKey>, uniqueEPGKey::equal >
	namespace __gnu_cxx
#else // for older gcc use following
	#define eventCache std::hash_map<uniqueEPGKey, std::pair<eventMap, timeMap>, std::hash<uniqueEPGKey>, uniqueEPGKey::equal >
	#define updateMap std::hash_map<uniqueEPGKey, time_t, std::hash<uniqueEPGKey>, uniqueEPGKey::equal >
	namespace std
#endif
{
template<> struct hash<uniqueEPGKey>
{
	inline size_t operator()( const uniqueEPGKey &x) const
	{
		int v=(x.onid^x.sid);
		v^=v>>8;
		return v&0xFF;
	}
};
}

class eventData
{
 	friend class eEPGCache;
private:
	__u8* EITdata;
	int ByteSize;
public:
	int type;
	static int CacheSize;
	eventData(const eit_event_struct* e, int size, int type)
	:ByteSize(size), type(type)
	{
		CacheSize+=size;
		EITdata = new __u8[size];
		if (e)
			memcpy(EITdata, (__u8*) e, size);
	}
	~eventData()
	{
		CacheSize-=ByteSize;
		delete [] EITdata;
	}
	operator const eit_event_struct*() const
	{
		return (const eit_event_struct*) EITdata;
	}
	const eit_event_struct* get() const
	{
		return (const eit_event_struct*) EITdata;
	}
	int getEventID()
	{
		return HILO( ((const eit_event_struct*) EITdata)->event_id );
	}
	time_t getStartTime()
	{
		return parseDVBtime(
			EITdata[2], EITdata[3],
			EITdata[4], EITdata[5], EITdata[6]);
	}
};
#else
	#include <lib/base/smartptr.h>
#endif

class eEPGCache: public eMainloop, private eThread, public Object
{
	DECLARE_REF(eEPGCache)
public:
#ifndef SWIG
	enum {NOWNEXT, SCHEDULE, SCHEDULE_OTHER};
	struct Message
	{
		enum
		{
			flush,
			startService,
			leaveChannel,
			pause,
			restart,
			updated,
			isavail,
			quit,
			timeChanged,
			leaveChannelFinished
		};
		int type;
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
		Message(int type, const eServiceReferenceDVB& service, int err=0)
			:type(type), service(service), err(err) {}
		Message(int type, time_t time)
			:type(type), time(time) {}
	};
	eFixedMessagePump<Message> messages;
	eFixedMessagePump<Message> back_messages;
private:
	static pthread_mutex_t cache_lock;
	eServiceReferenceDVB next_service;
	uniqueEPGKey current_service;
	int paused;

	int state;
	__u8 isRunning, haveData;

	ePtr<iDVBChannel> m_currentChannel;
	ePtr<eConnection> m_NowNextConn, m_ScheduleConn, m_ScheduleOtherConn;
	ePtr<iDVBSectionReader> m_NowNextReader, m_ScheduleReader, m_ScheduleOtherReader;

	int sectionRead(const __u8 *data, int source);
	void readNowNextData(const __u8 *data);
	void readScheduleData(const __u8 *data);
	void readScheduleOtherData(const __u8 *data);

	static eEPGCache *instance;

	eventCache eventDB;
	updateMap serviceLastUpdated;
	tmpMap temp;
	eTimer CleanTimer;
	eTimer zapTimer;
	eTimer abortTimer;
	bool finishEPG();
	void abortNonAvail();
	void flushEPG(const uniqueEPGKey & s=uniqueEPGKey());
	void startEPG();

	void changedService(const uniqueEPGKey &);
	void abortEPG();

	void cleanLoop();
	void pauseEPG();
	void restartEPG();
	void thread();
	void gotMessage(const Message &message);
	void gotBackMessage(const Message &message);
	void timeUpdated();
	void save();
	void load();
	void leaveChannel(iDVBChannel *);
#endif
public:
	static RESULT getInstance(ePtr<eEPGCache> &ptr);
	// called from other thread context !!
	void startCache(const eServiceReferenceDVB &);
	Event *lookupEvent(const eServiceReferenceDVB &service, int event_id, bool plain=false );
	Event *lookupEvent(const eServiceReferenceDVB &service, time_t=0, bool plain=false );
#ifndef SWIG
	eEPGCache();
	~eEPGCache();

	inline void Lock();
	inline void Unlock();

	const eventMap* getEventMap(const eServiceReferenceDVB &service);
	const timeMap* getTimeMap(const eServiceReferenceDVB &service);
	tmpMap* getUpdatedMap() { return &temp; }

	Signal1<void, bool> EPGAvail;
	Signal0<void> EPGUpdated;
#endif
};

TEMPLATE_TYPEDEF(ePtr<eEPGCache>,eEPGCachePtr);

inline const eventMap* eEPGCache::getEventMap(const eServiceReferenceDVB &service)
{
	eventCache::iterator It = eventDB.find( service );
	if ( It != eventDB.end() && It->second.first.size() )
		return &(It->second.first);
	else
		return 0;
}

inline const timeMap* eEPGCache::getTimeMap(const eServiceReferenceDVB &service)
{
	eventCache::iterator It = eventDB.find( service );
	if ( It != eventDB.end() && It->second.second.size() )
		return &(It->second.second);
	else
		return 0;
}

inline void eEPGCache::readNowNextData( const __u8 *data)
{
	if ( !data || state == 2 )
		m_NowNextReader->stop();
	else
		sectionRead(data, eEPGCache::NOWNEXT);
}

inline void eEPGCache::readScheduleData(const __u8 *data)
{
	if ( !data || state == 2 )
		m_ScheduleReader->stop();
	else
		sectionRead(data, eEPGCache::SCHEDULE);
}

inline void eEPGCache::readScheduleOtherData(const __u8 *data)
{
	if ( !data || state == 2 )
		m_ScheduleOtherReader->stop();
	else
		sectionRead(data, eEPGCache::SCHEDULE_OTHER);
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
