#ifndef __epgtransponderdatareader_h_
#define __epgtransponderdatareader_h_

#ifdef AUSTRALIA
/* Restart EPG data capture */
#define UPDATE_INTERVAL (5 * 60 * 1000)  // Australian EIT EPG is very dynamic, updates can come less than a minute apart
/* Time to wait after tuning in before EPG data capturing starts */
#define ZAP_DELAY (500)                  // 1/2 second (want to grab EPG data before timeshift starts)
#else
/* Restart EPG data capture */
#define UPDATE_INTERVAL 3600000  // 60 min
/* Time to wait after tuning in before EPG data capturing starts */
#define ZAP_DELAY 2000          // 2 sec
#endif

#include <tr1/unordered_map>

#ifdef ENABLE_OPENTV
#include <lib/dvb/opentv.h>
#include <lib/base/huffman.h>
#endif
#include <lib/dvb/epgcache.h>
#include <lib/base/thread.h>
#include <lib/base/message.h>

class eDVBServicePMTHandler;
class eEPGChannelData;

typedef std::map<eDVBChannelID, time_t> updateMap;
typedef std::map<iDVBChannel*, eEPGChannelData*> ChannelMap;

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

class eEPGTransponderDataReader: public eMainloop, private eThread, public sigc::trackable
{
	DECLARE_REF(eEPGTransponderDataReader)
public:
	eEPGTransponderDataReader();
	~eEPGTransponderDataReader();

	static pthread_mutex_t known_channel_lock;
	static pthread_mutex_t last_channel_update_lock;

	struct Message
	{
		enum
		{
			quit,
			startChannel,
			leaveChannel,
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
			int pid;
		};
		Message()
			:type(0) {}
		Message(int type)
			:type(type) {}
		Message(int type, iDVBChannel *channel, int err=0)
			:type(type), channel(channel), err(err) {}
		Message(int type, const eServiceReference& service, int err=0)
			:type(type), service(service), err(err) {}
	};
	eFixedMessagePump<Message> m_messages;

	static eEPGTransponderDataReader *getInstance() { return instance; }

	void restartReader();

#ifdef ENABLE_PRIVATE_EPG
	void PMTready(eDVBServicePMTHandler *pmthandler);
#else
	void PMTready(eDVBServicePMTHandler *pmthandler) {}
#endif

private:
	friend class eEPGCache;
	friend class eEPGChannelData;

	static eEPGTransponderDataReader *instance;
	bool m_running;

	ChannelMap m_knownChannels;
	ePtr<eConnection> m_chanAddedConn;
	updateMap m_channelLastUpdated;

	std::map<std::string,int> customeitpids;

	void thread();  // thread function
	void startThread();

	void gotMessage(const Message &message);

	// called from main thread
	void DVBChannelAdded(eDVBChannel*);
	void DVBChannelStateChanged(iDVBChannel*);
	void DVBChannelRunning(iDVBChannel *);
};

#endif
