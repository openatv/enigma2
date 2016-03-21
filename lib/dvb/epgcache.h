#ifndef __epgcache_h_
#define __epgcache_h_

#define ENABLE_PRIVATE_EPG 1
#define ENABLE_MHW_EPG 1
#define ENABLE_FREESAT 1
#define ENABLE_NETMED 1
#define ENABLE_VIRGIN 1

#ifndef SWIG

#include <vector>
#include <list>
#include <tr1/unordered_map>

#include <errno.h>

#include <lib/dvb/eit.h>
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

#define MjdToEpochTime(x) (((x##_hi << 8 | x##_lo)-40587)*86400)
#define BcdTimeToSeconds(x) ((3600 * ((10*((x##_h & 0xF0)>>4)) + (x##_h & 0xF))) + \
							(60 * ((10*((x##_m & 0xF0)>>4)) + (x##_m & 0xF))) + \
							((10*((x##_s & 0xF0)>>4)) + (x##_s & 0xF)))

#ifdef ENABLE_MHW_EPG

#define FILE_EQUIV "/etc/mhw_Equiv.epg"
#define FILE_CHANNELS "/etc/mhw_Chann.epg"
#define FILE_LOG "/tmp/mhw_Log.epg"

#define EPG_REPLAY_LEN 8

typedef struct epg_replay {
	u_char channel_id							:8;
	u_char replay_mjd_hi						:8;
	u_char replay_mjd_lo						:8;
	u_char replay_time_h						:8;
	u_char replay_time_m						:8;
	u_char replay_time_s						:8;
	u_char reserv1								:8;
#if BYTE_ORDER == BIG_ENDIAN
	u_char last									:1;
	u_char										:1;
	u_char vo									:1;
	u_char vm									:1;
	u_char										:3;
	u_char subtitles							:1;
#else
	u_char subtitles							:1;
	u_char										:3;
	u_char vm									:1;
	u_char vo									:1;
	u_char										:1;
	u_char last									:1;
#endif
} epg_replay_t;

typedef struct {
	u_char original_nid_hi;
	u_char original_nid_lo;
	u_char original_tid_hi;
	u_char original_tid_lo;
	u_char original_sid_hi;
	u_char original_sid_lo;
	u_char equiv_nid_hi;
	u_char equiv_nid_lo;
	u_char equiv_tid_hi;
	u_char equiv_tid_lo;
	u_char equiv_sid_hi;
	u_char equiv_sid_lo;
} mhw_channel_equiv_t;
#endif

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
		if (sid < a.sid)
			return true;
		if (sid != a.sid)
			return false;
		if (onid < a.onid)
			return true;
		if (onid != a.onid)
			return false;
		return (tsid < a.tsid);
	}
	operator bool() const
	{
		return !(sid == -1 && onid == -1 && tsid == -1);
	}
	bool operator==(const uniqueEPGKey &a) const
	{
		return (tsid == a.tsid) && (onid == a.onid) && (sid == a.sid);
	}
	struct equal
	{
		bool operator()(const uniqueEPGKey &a, const uniqueEPGKey &b) const
		{
			return (a.tsid == b.tsid) && (a.onid == b.onid) && (a.sid == b.sid);
		}
	};
};

//eventMap is sorted by event_id
typedef std::map<uint16_t, eventData*> eventMap;
//timeMap is sorted by beginTime
typedef std::map<time_t, eventData*> timeMap;

typedef std::map<eDVBChannelID, time_t> updateMap;

struct hash_uniqueEPGKey
{
	inline size_t operator()( const uniqueEPGKey &x) const
	{
		return (x.onid << 16) | x.tsid;
	}
};

struct EventCacheItem {
	eventMap byEvent;
	timeMap byTime;
};

typedef std::set<uint32_t> tidMap;

typedef std::tr1::unordered_map<uniqueEPGKey, EventCacheItem, hash_uniqueEPGKey, uniqueEPGKey::equal> eventCache;
#ifdef ENABLE_PRIVATE_EPG
	typedef std::tr1::unordered_map<time_t, std::pair<time_t, uint16_t> > contentTimeMap;
	typedef std::tr1::unordered_map<int, contentTimeMap > contentMap;
	typedef std::tr1::unordered_map<uniqueEPGKey, contentMap, hash_uniqueEPGKey, uniqueEPGKey::equal > contentMaps;
#endif

#endif

#ifdef ENABLE_FREESAT
#include <bitset>
class freesatEITSubtableStatus
{
private:
	u_char version;
	uint16_t sectionMap[32];
	void initMap(uint8_t maxSection);

public:
	freesatEITSubtableStatus(u_char version, uint8_t maxSection);
	bool isSectionPresent(uint8_t sectionNo);
	void seen(uint8_t sectionNo, uint8_t maxSegmentSection);
	bool isVersionChanged(u_char testVersion);
	void updateVersion(u_char newVersion, uint8_t maxSection);
	bool isCompleted();
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
		unsigned int isRunning, haveData;
		ePtr<eDVBChannel> channel;
		ePtr<eConnection> m_stateChangedConn, m_NowNextConn, m_ScheduleConn, m_ScheduleOtherConn, m_ViasatConn;
		ePtr<iDVBSectionReader> m_NowNextReader, m_ScheduleReader, m_ScheduleOtherReader, m_ViasatReader;
		tidMap seenSections[4], calcedSections[4];
#ifdef ENABLE_VIRGIN
		ePtr<eConnection> m_VirginNowNextConn, m_VirginScheduleConn;
		ePtr<iDVBSectionReader> m_VirginNowNextReader, m_VirginScheduleReader;
#endif
#ifdef ENABLE_NETMED
		ePtr<eConnection> m_NetmedScheduleConn, m_NetmedScheduleOtherConn;
		ePtr<iDVBSectionReader> m_NetmedScheduleReader, m_NetmedScheduleOtherReader;
#endif
#ifdef ENABLE_FREESAT
		ePtr<eConnection> m_FreeSatScheduleOtherConn, m_FreeSatScheduleOtherConn2;
		ePtr<iDVBSectionReader> m_FreeSatScheduleOtherReader, m_FreeSatScheduleOtherReader2;
		std::map<uint32_t, freesatEITSubtableStatus> m_FreeSatSubTableStatus;
		uint32_t m_FreesatTablesToComplete;
		void readFreeSatScheduleOtherData(const uint8_t *data);
		void cleanupFreeSat();
#endif
#ifdef ENABLE_PRIVATE_EPG
		ePtr<eTimer> startPrivateTimer;
		int m_PrevVersion;
		int m_PrivatePid;
		uniqueEPGKey m_PrivateService;
		ePtr<eConnection> m_PrivateConn;
		ePtr<iDVBSectionReader> m_PrivateReader;
		std::set<uint8_t> seenPrivateSections;
		void readPrivateData(const uint8_t *data);
		void startPrivateReader();
#endif
#ifdef ENABLE_MHW_EPG
		std::vector<mhw_channel_name_t> m_channels;
		std::vector<mhw_channel_equiv_t> m_equiv;
		std::map<uint8_t, mhw_theme_name_t> m_themes;
		std::map<uint32_t, mhw_title_t> m_titles;
		std::multimap<uint32_t, uint32_t> m_program_ids;
		ePtr<eConnection> m_MHWConn, m_MHWConn2;
		ePtr<iDVBSectionReader> m_MHWReader, m_MHWReader2;
		eDVBSectionFilterMask m_MHWFilterMask, m_MHWFilterMask2;
		ePtr<eTimer> m_MHWTimeoutTimer;
		uint16_t m_mhw2_channel_pid, m_mhw2_title_pid, m_mhw2_summary_pid;
		bool m_MHWTimeoutet;
		void MHWTimeout() { m_MHWTimeoutet=true; }
		void readMHWData(const uint8_t *data);
		void readMHWData2(const uint8_t *data);
		void readMHWData2_old(const uint8_t *data);
		void startMHWReader(uint16_t pid, uint8_t tid);
		void startMHWReader2(uint16_t pid, uint8_t tid, int ext=-1);
		void startMHWTimeout(int msek);
		bool checkMHWTimeout() { return m_MHWTimeoutet; }
		void cleanupMHW();
		uint8_t *delimitName( uint8_t *in, uint8_t *out, int len_in );
		void timeMHW2DVB( u_char hours, u_char minutes, u_char *return_time);
		void timeMHW2DVB( int minutes, u_char *return_time);
		void timeMHW2DVB( u_char day, u_char hours, u_char minutes, u_char *return_time);
		void storeMHWTitle(std::map<uint32_t, mhw_title_t>::iterator itTitle, std::string sumText, const uint8_t *data);
		void GetEquiv(void);
		int nb_equiv;
		bool log_open ();
		void log_close();
		void log_add (char *message, ...);
#endif
		void readData(const uint8_t *data, int source);
		void startChannel();
		void startEPG();
		void finishEPG();
		void abortEPG();
		void abortNonAvail();
	};
	bool FixOverlapping(EventCacheItem &servicemap, time_t TM, int duration, const timeMap::iterator &tm_it, const uniqueEPGKey &service);
public:
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
	friend class eventData;
	static eEPGCache *instance;

	typedef std::map<iDVBChannel*, channel_data*> ChannelMap;

	ePtr<eTimer> cleanTimer;
	ChannelMap m_knownChannels;
	ePtr<eConnection> m_chanAddedConn;

	unsigned int enabledSources;
	unsigned int historySeconds;
	unsigned int maxdays;

	std::vector<int> onid_blacklist;
	std::map<std::string,int> customeitpids;
	eventCache eventDB;
	updateMap channelLastUpdated;
	std::string m_filename;
	bool m_running;

#ifdef ENABLE_PRIVATE_EPG
	contentMaps content_time_tables;
#endif

	void thread();  // thread function

#ifdef ENABLE_PRIVATE_EPG
	void privateSectionRead(const uniqueEPGKey &, const uint8_t *);
#endif
	void sectionRead(const uint8_t *data, int source, channel_data *channel);
	void gotMessage(const Message &message);
	void cleanLoop();

// called from main thread
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

	void crossepgImportEPGv21(std::string dbroot);
	void save();
	void load();
	void timeUpdated();
	void flushEPG(const uniqueEPGKey & s=uniqueEPGKey());
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

	// at moment just for one service..
	RESULT startTimeQuery(const eServiceReference &service, time_t begin=-1, int minutes=-1);

#ifndef SWIG
private:
	// For internal use only. Acquire the cache lock before calling.
	RESULT lookupEventId(const eServiceReference &service, int event_id, const eventData *&);
	RESULT lookupEventTime(const eServiceReference &service, time_t, const eventData *&, int direction=0);

public:
	/* Only used by servicedvbrecord.cpp to write the EIT file */
	RESULT saveEventToFile(const char* filename, const eServiceReference &service, int eit_event_id, time_t begTime, time_t endTime);

	// Events are parsed epg events.. it's safe to use them after cache unlock
	// after use the Event pointer must be released using "delete".
	RESULT lookupEventId(const eServiceReference &service, int event_id, Event* &);
	RESULT lookupEventTime(const eServiceReference &service, time_t, Event* &, int direction=0);
	RESULT getNextTimeEntry(Event *&);
#endif
	enum {
		SIMILAR_BROADCASTINGS_SEARCH,
		EXAKT_TITLE_SEARCH,
		PARTIAL_TITLE_SEARCH,
		START_TITLE_SEARCH
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

	enum {PRIVATE=0, NOWNEXT=1, SCHEDULE=2, SCHEDULE_OTHER=4
#ifdef ENABLE_MHW_EPG
	,MHW=8
#endif
#ifdef ENABLE_FREESAT
	,FREESAT_NOWNEXT=16
	,FREESAT_SCHEDULE=32
	,FREESAT_SCHEDULE_OTHER=64
#endif
	,VIASAT=256
#ifdef ENABLE_NETMED
	,NETMED_SCHEDULE=512
	,NETMED_SCHEDULE_OTHER=1024
#endif
#ifdef ENABLE_VIRGIN
	,VIRGIN_NOWNEXT=2048
	,VIRGIN_SCHEDULE=4096
#endif
	,EPG_IMPORT=0x80000000
	};
	void setEpgmaxdays(unsigned int epgmaxdays);
	void setEpgHistorySeconds(time_t seconds);
	void setEpgSources(unsigned int mask);
	unsigned int getEpgSources();
	unsigned int getEpgmaxdays();

	void submitEventData(const std::vector<eServiceReferenceDVB>& serviceRefs, long start, long duration, const char* title, const char* short_summary, const char* long_description, char event_type);

	void importEvents(SWIG_PYOBJECT(ePyObject) serviceReferences, SWIG_PYOBJECT(ePyObject) list);
	void importEvent(SWIG_PYOBJECT(ePyObject) serviceReference, SWIG_PYOBJECT(ePyObject) list);
};

#endif
