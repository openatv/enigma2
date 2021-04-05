#ifndef __epgchanneldata_h_
#define __epgchanneldata_h_

#include <lib/dvb/eit.h>
#include <lib/dvb/epgcache.h>
#include <lib/dvb/lowlevel/eit.h>
#include <lib/base/ebase.h>

#ifdef ENABLE_MHW_EPG
#include <lib/dvb/lowlevel/mhw.h>
#endif
#ifdef ENABLE_FREESAT
#include <bitset>
class freesatEITSubtableStatus;
#endif

#define MjdToEpochTime(x) (((x##_hi << 8 | x##_lo)-40587)*86400)
#define BcdTimeToSeconds(x) ((3600 * ((10*((x##_h & 0xF0)>>4)) + (x##_h & 0xF))) + (60 * ((10*((x##_m & 0xF0)>>4)) + (x##_m & 0xF))) + ((10*((x##_s & 0xF0)>>4)) + (x##_s & 0xF)))

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

typedef std::set<uint32_t> tidMap;

class eEPGTransponderDataReader;
struct uniqueEPGKey;

class eEPGChannelData: public sigc::trackable
{
	friend class eEPGTransponderDataReader;
	friend class eEPGCache;

	pthread_mutex_t channel_active;
	eEPGChannelData(eEPGTransponderDataReader*);
	eEPGTransponderDataReader *epgReader;
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
	void log_add (const char *message, ...);
#endif
#ifdef ENABLE_ATSC
	int m_atsc_eit_index;
	std::map<uint16_t, uint16_t> m_ATSC_VCT_map;
	std::map<uint32_t, std::string> m_ATSC_ETT_map;
	struct atsc_event
	{
		uint16_t eventId;
		uint32_t startTime;
		uint32_t lengthInSeconds;
		std::string title;
	};
	std::map<uint32_t, struct atsc_event> m_ATSC_EIT_map;
	ePtr<iDVBSectionReader> m_ATSC_VCTReader, m_ATSC_MGTReader, m_ATSC_EITReader, m_ATSC_ETTReader;
	ePtr<eConnection> m_ATSC_VCTConn, m_ATSC_MGTConn, m_ATSC_EITConn, m_ATSC_ETTConn;
	void ATSC_checkCompletion();
	void ATSC_VCTsection(const uint8_t *d);
	void ATSC_MGTsection(const uint8_t *d);
	void ATSC_EITsection(const uint8_t *d);
	void ATSC_ETTsection(const uint8_t *d);
	void cleanupATSC();
#endif
#ifdef ENABLE_OPENTV
	typedef std::tr1::unordered_map<uint32_t, std::string> OpenTvDescriptorMap;
	int m_OPENTV_EIT_index;
	uint16_t m_OPENTV_pid;
	uint32_t m_OPENTV_crc32;
	uint32_t opentv_title_crc32;
	bool huffman_dictionary_read;
	struct opentv_channel
	{
		uint16_t originalNetworkId;
		uint16_t transportStreamId;
		uint16_t serviceId;
		uint8_t serviceType;
	};
	struct opentv_event
	{
		uint16_t eventId;
		uint32_t startTime;
		uint32_t duration;
		uint32_t title_crc;
	};
	OpenTvDescriptorMap m_OPENTV_descriptors_map;
	std::map<uint16_t, struct opentv_channel> m_OPENTV_channels_map;
	std::map<uint32_t, struct opentv_event> m_OPENTV_EIT_map;
	ePtr<eTimer> m_OPENTV_Timer;
	ePtr<iDVBSectionReader> m_OPENTV_ChannelsReader, m_OPENTV_TitlesReader, m_OPENTV_SummariesReader;
	ePtr<eConnection> m_OPENTV_ChannelsConn, m_OPENTV_TitlesConn, m_OPENTV_SummariesConn;
	void OPENTV_checkCompletion(const uint32_t data_crc);
	void OPENTV_ChannelsSection(const uint8_t *d);
	void OPENTV_TitlesSection(const uint8_t *d);
	void OPENTV_SummariesSection(const uint8_t *d);
	void cleanupOPENTV();
#endif
	void readData(const uint8_t *data, int source);
	void startChannel();
	void startEPG();
	void finishEPG();
	void abortEPG();
	void abortNonAvail();
};
#endif
