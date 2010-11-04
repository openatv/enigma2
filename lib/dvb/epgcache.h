#ifndef __epgcache_h_
#define __epgcache_h_

#define ENABLE_PRIVATE_EPG 1
//#define ENABLE_MHW_EPG 1

#ifndef SWIG

/* Test for gcc >= maj.min, as per __GNUC_PREREQ in glibc */
#if defined (__GNUC__) && defined (__GNUC_MINOR__)
#define __GNUC_PREREQ(maj, min) \
	  ((__GNUC__ << 16) + __GNUC_MINOR__ >= ((maj) << 16) + (min))
#else
#define __GNUC_PREREQ(maj, min)  0
#endif

#include <vector>
#include <list>
#if 0 && __GNUC_PREREQ(4,3)
#include <unordered_map>
#include <unordered_set>
#else
#include <ext/hash_map>
#include <ext/hash_set>
#endif

#include <errno.h>

#include <lib/dvb/eit.h>
#include <lib/dvb/lowlevel/eit.h>
#ifdef ENABLE_MHW_EPG
#include <lib/dvb/lowlevel/mhw.h>
#endif
#include <lib/dvb/idvb.h>
#include <lib/dvb/demux.h>
#include <lib/dvb/dvbtime.h>
#include <lib/base/ebase.h>
#include <lib/base/thread.h>
#include <lib/base/message.h>
#include <lib/service/event.h>
#include <lib/python/python.h>

#define CLEAN_INTERVAL 60000    //  1 min
#define UPDATE_INTERVAL 3600000  // 60 min
#define ZAP_DELAY 2000          // 2 sek

#define HILO(x) (x##_hi << 8 | x##_lo)

class eventData;
class eServiceReferenceDVB;
class eDVBServicePMTHandler;

struct uniqueEPGKey
{
	int sid, onid, tsid;
	uniqueEPGKey( const eServiceReference &ref )
		:sid( ref.type != eServiceReference::idInvalid ? ((eServiceReferenceDVB&)ref).getServiceID().get() : -1 )
		,onid( ref.type != eServiceReference::idInvalid ? ((eServiceReferenceDVB&)ref).getOriginalNetworkID().get() : -1 )
		,tsid( ref.type != eServiceReference::idInvalid ? ((eServiceReferenceDVB&)ref).getTransportStreamID().get() : -1 )
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
#if 0 && __GNUC_PREREQ(4,3)
	#define eventCache std::unordered_map<uniqueEPGKey, std::pair<eventMap, timeMap>, hash_uniqueEPGKey, uniqueEPGKey::equal>
	#ifdef ENABLE_PRIVATE_EPG
		#define contentTimeMap std::unordered_map<time_t, std::pair<time_t, __u16> >
		#define contentMap std::unordered_map<int, contentTimeMap >
		#define contentMaps std::unordered_map<uniqueEPGKey, contentMap, hash_uniqueEPGKey, uniqueEPGKey::equal >
	#endif
#elif __GNUC_PREREQ(3,1)
	#define eventCache __gnu_cxx::hash_map<uniqueEPGKey, std::pair<eventMap, timeMap>, hash_uniqueEPGKey, uniqueEPGKey::equal>
	#ifdef ENABLE_PRIVATE_EPG
		#define contentTimeMap __gnu_cxx::hash_map<time_t, std::pair<time_t, __u16> >
		#define contentMap __gnu_cxx::hash_map<int, contentTimeMap >
		#define contentMaps __gnu_cxx::hash_map<uniqueEPGKey, contentMap, hash_uniqueEPGKey, uniqueEPGKey::equal >
	#endif
#else // for older gcc use following
	#define eventCache std::hash_map<uniqueEPGKey, std::pair<eventMap, timeMap>, hash_uniqueEPGKey, uniqueEPGKey::equal >
	#ifdef ENABLE_PRIVATE_EPG
		#define contentTimeMap std::hash_map<time_t, std::pair<time_t, __u16> >
		#define contentMap std::hash_map<int, contentTimeMap >
		#define contentMaps std::hash_map<uniqueEPGKey, contentMap, hash_uniqueEPGKey, uniqueEPGKey::equal>
	#endif
#endif

#define descriptorPair std::pair<int,__u8*>
#define descriptorMap std::map<__u32, descriptorPair >

class eventData
{
	friend class eEPGCache;
private:
	__u8* EITdata;
	__u8 ByteSize;
	__u8 type;
	static descriptorMap descriptors;
	static __u8 data[4108];
	static int CacheSize;
	static void load(FILE *);
	static void save(FILE *);
public:
	eventData(const eit_event_struct* e=NULL, int size=0, int type=0);
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
#endif

class eEPGCache: public eMainloop, private eThread, public Object
{
#ifndef SWIG
	DECLARE_REF(eEPGCache)
	struct channel_data: public Object
	{
		pthread_mutex_t channel_active;
		channel_data(eEPGCache*);
		eEPGCache *cache;
		ePtr<eTimer> abortTimer, zapTimer;
		int prevChannelState;
		int state;
		__u8 isRunning, haveData;
		ePtr<eDVBChannel> channel;
		ePtr<eConnection> m_stateChangedConn, m_NowNextConn, m_ScheduleConn, m_ScheduleOtherConn, m_ViasatConn;
		ePtr<iDVBSectionReader> m_NowNextReader, m_ScheduleReader, m_ScheduleOtherReader, m_ViasatReader;
		tidMap seenSections[4], calcedSections[4];
#ifdef ENABLE_PRIVATE_EPG
		ePtr<eTimer> startPrivateTimer;
		int m_PrevVersion;
		int m_PrivatePid;
		uniqueEPGKey m_PrivateService;
		ePtr<eConnection> m_PrivateConn;
		ePtr<iDVBSectionReader> m_PrivateReader;
		std::set<__u8> seenPrivateSections;
		void readPrivateData(const __u8 *data);
		void startPrivateReader();
#endif
#ifdef ENABLE_MHW_EPG
		std::vector<mhw_channel_name_t> m_channels;
		std::map<__u8, mhw_theme_name_t> m_themes;
		std::map<__u32, mhw_title_t> m_titles;
		std::multimap<__u32, __u32> m_program_ids;
		ePtr<eConnection> m_MHWConn, m_MHWConn2;
		ePtr<iDVBSectionReader> m_MHWReader, m_MHWReader2;
		eDVBSectionFilterMask m_MHWFilterMask, m_MHWFilterMask2;
		ePtr<eTimer> m_MHWTimeoutTimer;
		__u16 m_mhw2_channel_pid, m_mhw2_title_pid, m_mhw2_summary_pid;
		bool m_MHWTimeoutet;
		void MHWTimeout() { m_MHWTimeoutet=true; }
		void readMHWData(const __u8 *data);
		void readMHWData2(const __u8 *data);
		void startMHWReader(__u16 pid, __u8 tid);
		void startMHWReader2(__u16 pid, __u8 tid, int ext=-1);
		void startTimeout(int msek);
		bool checkTimeout() { return m_MHWTimeoutet; }
		void cleanup();
		__u8 *delimitName( __u8 *in, __u8 *out, int len_in );
		void timeMHW2DVB( u_char hours, u_char minutes, u_char *return_time);
		void timeMHW2DVB( int minutes, u_char *return_time);
		void timeMHW2DVB( u_char day, u_char hours, u_char minutes, u_char *return_time);
		void storeTitle(std::map<__u32, mhw_title_t>::iterator itTitle, std::string sumText, const __u8 *data);
#endif
		void readData(const __u8 *data);
		void readDataViasat(const __u8 *data);
		void startChannel();
		void startEPG();
		bool finishEPG();
		void abortEPG();
		void abortNonAvail();
	};
	bool FixOverlapping(std::pair<eventMap,timeMap> &servicemap, time_t TM, int duration, const timeMap::iterator &tm_it, const uniqueEPGKey &service);
public:
	enum {PRIVATE=0, NOWNEXT=1, SCHEDULE=2, SCHEDULE_OTHER=4
#ifdef ENABLE_MHW_EPG
	,MHW=8
#endif
	,VIASAT=16
	};
	struct Message
	{
		enum
		{
			flush,
			startChannel,
			leaveChannel,
			quit,
			got_private_pid,
			got_mhw2_channel_pid,
			got_mhw2_title_pid,
			got_mhw2_summary_pid,
			timeChanged
		};
		int type;
		iDVBChannel *channel;
		uniqueEPGKey service;
		union {
			int err;
			time_t time;
			bool avail;
			int pid;
		};
		Message()
			:type(0), time(0) {}
		Message(int type)
			:type(type) {}
		Message(int type, bool b)
			:type(type), avail(b) {}
		Message(int type, iDVBChannel *channel, int err=0)
			:type(type), channel(channel), err(err) {}
		Message(int type, const eServiceReference& service, int err=0)
			:type(type), service(service), err(err) {}
		Message(int type, time_t time)
			:type(type), time(time) {}
	};
	eFixedMessagePump<Message> messages;
private:
	friend class channel_data;
	static eEPGCache *instance;

	ePtr<eTimer> cleanTimer;
	std::map<iDVBChannel*, channel_data*> m_knownChannels;
	ePtr<eConnection> m_chanAddedConn;

	eventCache eventDB;
	updateMap channelLastUpdated;
	static pthread_mutex_t cache_lock, channel_map_lock;

#ifdef ENABLE_PRIVATE_EPG
	contentMaps content_time_tables;
#endif

	void thread();  // thread function

// called from epgcache thread
	int m_running;
	char m_filename[1024];
	void save();
	void load();
#ifdef ENABLE_PRIVATE_EPG
	void privateSectionRead(const uniqueEPGKey &, const __u8 *);
#endif
	void sectionRead(const __u8 *data, int source, channel_data *channel);
	void gotMessage(const Message &message);
	void flushEPG(const uniqueEPGKey & s=uniqueEPGKey());
	void cleanLoop();

// called from main thread
	void timeUpdated();
	void DVBChannelAdded(eDVBChannel*);
	void DVBChannelStateChanged(iDVBChannel*);
	void DVBChannelRunning(iDVBChannel *);

	timeMap::iterator m_timemap_cursor, m_timemap_end;
	int currentQueryTsidOnid; // needed for getNextTimeEntry.. only valid until next startTimeQuery call
#else
	eEPGCache();
	~eEPGCache();
#endif // SWIG
public:
	static eEPGCache *getInstance() { return instance; }
#ifndef SWIG
	eEPGCache();
	~eEPGCache();

#ifdef ENABLE_PRIVATE_EPG
	void PMTready(eDVBServicePMTHandler *pmthandler);
#else
	void PMTready(eDVBServicePMTHandler *pmthandler) {}
#endif

#endif
	// must be called once!
	void setCacheFile(const char *filename);

	// called from main thread
	inline void Lock();
	inline void Unlock();

	// at moment just for one service..
	RESULT startTimeQuery(const eServiceReference &service, time_t begin=-1, int minutes=-1);

#ifndef SWIG
	// eventData's are plain entrys out of the cache.. it's not safe to use them after cache unlock
	// but its faster in use... its not allowed to delete this pointers via delete or free..
	RESULT lookupEventId(const eServiceReference &service, int event_id, const eventData *&);
	RESULT lookupEventTime(const eServiceReference &service, time_t, const eventData *&, int direction=0);
	RESULT getNextTimeEntry(const eventData *&);

	// eit_event_struct's are plain dvb eit_events .. it's not safe to use them after cache unlock
	// its not allowed to delete this pointers via delete or free..
	RESULT lookupEventId(const eServiceReference &service, int event_id, const eit_event_struct *&);
	RESULT lookupEventTime(const eServiceReference &service, time_t , const eit_event_struct *&, int direction=0);
	RESULT getNextTimeEntry(const eit_event_struct *&);

	// Event's are parsed epg events.. it's safe to use them after cache unlock
	// after use this Events must be deleted (memleaks)
	RESULT lookupEventId(const eServiceReference &service, int event_id, Event* &);
	RESULT lookupEventTime(const eServiceReference &service, time_t, Event* &, int direction=0);
	RESULT getNextTimeEntry(Event *&);
#endif
	enum {
		SIMILAR_BROADCASTINGS_SEARCH,
		EXAKT_TITLE_SEARCH,
		PARTIAL_TITLE_SEARCH
	};
	enum {
		CASE_CHECK,
		NO_CASE_CHECK
	};
	PyObject *lookupEvent(SWIG_PYOBJECT(ePyObject) list, SWIG_PYOBJECT(ePyObject) convertFunc=(PyObject*)0);
	PyObject *search(SWIG_PYOBJECT(ePyObject));

	// eServiceEvent are parsed epg events.. it's safe to use them after cache unlock
	// for use from python ( members: m_start_time, m_duration, m_short_description, m_extended_description )
	SWIG_VOID(RESULT) lookupEventId(const eServiceReference &service, int event_id, ePtr<eServiceEvent> &SWIG_OUTPUT);
	SWIG_VOID(RESULT) lookupEventTime(const eServiceReference &service, time_t, ePtr<eServiceEvent> &SWIG_OUTPUT, int direction=0);
	SWIG_VOID(RESULT) getNextTimeEntry(ePtr<eServiceEvent> &SWIG_OUTPUT);
};

#ifndef SWIG
inline void eEPGCache::Lock()
{
	pthread_mutex_lock(&cache_lock);
}

inline void eEPGCache::Unlock()
{
	pthread_mutex_unlock(&cache_lock);
}
#endif

#endif
