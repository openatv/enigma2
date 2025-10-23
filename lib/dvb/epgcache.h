#ifndef __epgcache_h_
#define __epgcache_h_

#define ENABLE_PRIVATE_EPG 1
#define ENABLE_MHW_EPG 1
#define ENABLE_FREESAT 1
#define ENABLE_NETMED 1
#define ENABLE_VIRGIN 1
#define ENABLE_ATSC 1
#define ENABLE_OPENTV 1

#ifndef SWIG

#include <vector>
#include <tr1/unordered_map>

#include <lib/dvb/idvb.h>
#include <lib/dvb/dvbtime.h>
#include <lib/base/thread.h>
#include <lib/base/message.h>
#include <lib/service/event.h>
#include <lib/python/python.h>

struct eventData;
class eServiceReferenceDVB;
class eEPGChannelData;
class eEPGTransponderDataReader;

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
	int sources;
	EventCacheItem(): sources(0) {}
};

typedef std::tr1::unordered_map<uniqueEPGKey, EventCacheItem, hash_uniqueEPGKey, uniqueEPGKey::equal> eventCache;
#ifdef ENABLE_PRIVATE_EPG
	typedef std::tr1::unordered_map<time_t, std::pair<time_t, uint16_t> > contentTimeMap;
	typedef std::tr1::unordered_map<int, contentTimeMap > contentMap;
	typedef std::tr1::unordered_map<uniqueEPGKey, contentMap, hash_uniqueEPGKey, uniqueEPGKey::equal > contentMaps;
#endif

#endif

#ifndef SWIG

struct eit_parental_rating {
	u_char	country_code[3];
	u_char	rating;
};
#endif

class eEPGCache: public eMainloop, private eThread, public sigc::trackable
{
#ifndef SWIG
	DECLARE_REF(eEPGCache)

public:
	struct Message
	{
		enum
		{
			flush,
			quit,
			timeChanged
		};
		int type;
		uniqueEPGKey service;
		union {
			int err;
		};
		Message()
			:type(0) {}
		Message(int type)
			:type(type) {}
		Message(int type, const eServiceReference& service, int err=0)
			:type(type), service(service), err(err) {}
	};
	eFixedMessagePump<Message> messages;

private:
	friend struct eventData;
	friend class eEPGChannelData;
	friend class eEPGTransponderDataReader;
	static eEPGCache *instance;

	unsigned int historySeconds;
	unsigned int maxdays;

	std::vector<int> onid_blacklist;
	eventCache eventDB;
	std::string m_filename;
	bool m_running;
	unsigned int m_enabledEpgSources;
	ePtr<eTimer> cleanTimer;
	bool load_epg;
	PSignal0<void> epgCacheStarted;
	bool m_debug;
	bool m_saveepg;
	bool m_icetv_enabled;

#ifdef ENABLE_PRIVATE_EPG
	contentMaps content_time_tables;
#endif

	void thread();  // thread function

#ifdef ENABLE_PRIVATE_EPG
	void privateSectionRead(const uniqueEPGKey &, const uint8_t *);
#endif
	void sectionRead(const uint8_t *data, int source, eEPGChannelData *channel);

	void gotMessage(const Message &message);
	void cleanLoop();
	void submitEventData(const std::vector<int>& sids, const std::vector<eDVBChannelID>& chids, long start, long duration, const char* title, const char* short_summary, const char* long_description, char event_type, uint16_t event_id, int source);
	void submitEventData(const std::vector<int>& sids, const std::vector<eDVBChannelID>& chids, long start, long duration, const char* title, const char* short_summary, const char* long_description, std::vector<uint8_t> event_types, std::vector<eit_parental_rating> parental_ratings, uint16_t event_id, int source);
	void clearCompleteEPGCache();

	eServiceReferenceDVB *m_timeQueryRef;
	time_t m_timeQueryBegin;
	int m_timeQueryMinutes;
	int m_timeQueryCount;  // counts the returned events; getNextTimeEntry returns always the m_timeQueryCount'th event
#else
	eEPGCache();
	~eEPGCache();
#endif // SWIG
public:
	static eEPGCache *getInstance() { return instance; }

	void setDebug(bool enabled) { m_debug = enabled; }
	void setSave(bool enabled) { m_saveepg = enabled; }

	void crossepgImportEPGv21(std::string dbroot);
	void clear();
	void save();
	void load();
	void timeUpdated();
	void flushEPG(int sid, int onid, int tsid);
	void flushEPG(const uniqueEPGKey & s=uniqueEPGKey(), bool lock = true);
#ifndef SWIG
	eEPGCache();
	~eEPGCache();

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

	// Events are parsed epg events.. it's safe to use them after cache unlock
	// after use the Event pointer must be released using "delete".
	RESULT lookupEventId(const eServiceReference &service, int event_id, Event* &);
	RESULT lookupEventTime(const eServiceReference &service, time_t, Event* &, int direction=0);
	RESULT getNextTimeEntry(Event *&);
#endif
	/* Used by servicedvbrecord.cpp, time shift, etc. to write the EIT file */
	RESULT saveEventToFile(const char* filename, const eServiceReference &service, int eit_event_id, time_t begTime, time_t endTime);

	enum {
		SIMILAR_BROADCASTINGS_SEARCH,
		EXAKT_TITLE_SEARCH,
		PARTIAL_TITLE_SEARCH,
		START_TITLE_SEARCH,
		END_TITLE_SEARCH,
		PARTIAL_DESCRIPTION_SEARCH,
		CRID_SEARCH
	};
	enum {
		CRID_EPISODE = 1,
		CRID_SERIES = 2
	};
	enum {
		CASE_CHECK,
		NO_CASE_CHECK,
		REGEX_CHECK
	};
	PyObject *lookupEvent(SWIG_PYOBJECT(ePyObject) list, SWIG_PYOBJECT(ePyObject) convertFunc=(PyObject*)0);
	const char* casetypestr(int value);
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
#ifdef ENABLE_ATSC
	,ATSC_EIT=8192
#endif
#ifdef ENABLE_OPENTV
	,OPENTV=16384
#endif
	,EPG_IMPORT=0x80000000
	};
	void setEpgmaxdays(unsigned int epgmaxdays);
	void setEpgHistorySeconds(time_t seconds);
	void setEpgSources(unsigned int mask);
	unsigned int getEpgSources();
	unsigned int getEpgmaxdays();


	void submitEventData(const std::vector<eServiceReferenceDVB>& serviceRefs, long start, long duration, const char* title, const char* short_summary, const char* long_description, std::vector<uint8_t> event_types, std::vector<eit_parental_rating> parental_ratings, uint16_t event_id=0);

	void importEvents(SWIG_PYOBJECT(ePyObject) serviceReferences, SWIG_PYOBJECT(ePyObject) list);
	void importEvent(SWIG_PYOBJECT(ePyObject) serviceReference, SWIG_PYOBJECT(ePyObject) list);
};

#endif
