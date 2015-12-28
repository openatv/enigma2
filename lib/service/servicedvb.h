#ifndef __servicedvb_h
#define __servicedvb_h

#include <lib/service/iservice.h>
#include <lib/dvb/idvb.h>

#include <lib/dvb/pmt.h>
#include <lib/dvb/eit.h>
#include <lib/dvb/subtitle.h>
#include <lib/dvb/teletext.h>
#include <lib/dvb/radiotext.h>

class eStaticServiceDVBInformation;
class eStaticServiceDVBBouquetInformation;

class eServiceFactoryDVB: public iServiceHandler
{
	DECLARE_REF(eServiceFactoryDVB);
	ePtr<eStaticServiceDVBInformation> m_StaticServiceDVBInfo;
	ePtr<eStaticServiceDVBBouquetInformation> m_StaticServiceDVBBouquetInfo;
public:
	eServiceFactoryDVB();
	virtual ~eServiceFactoryDVB();
	enum { id = 0x1 };

		// iServiceHandler
	RESULT play(const eServiceReference &, ePtr<iPlayableService> &ptr);
	RESULT record(const eServiceReference &, ePtr<iRecordableService> &ptr);
	RESULT list(const eServiceReference &, ePtr<iListableService> &ptr);
	RESULT info(const eServiceReference &, ePtr<iStaticServiceInformation> &ptr);
	RESULT offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr);
private:
	RESULT lookupService(ePtr<eDVBService> &ptr, const eServiceReference &ref);
};

class eBouquet;

class eDVBServiceList: public iListableService, public iMutableServiceList
{
	DECLARE_REF(eDVBServiceList);
public:
	virtual ~eDVBServiceList();
	PyObject *getContent(const char* formatstr, bool sorted=false);
	RESULT getContent(std::list<eServiceReference> &list, bool sorted=false);
	RESULT getNext(eServiceReference &ptr);
	inline int compareLessEqual(const eServiceReference &a, const eServiceReference &b);

	RESULT startEdit(ePtr<iMutableServiceList> &);
	RESULT flushChanges();
	RESULT addService(eServiceReference &ref, eServiceReference before);
	RESULT removeService(eServiceReference &ref, bool renameBouquet=true);
	RESULT moveService(eServiceReference &ref, int pos);
	RESULT setListName(const std::string &name);
private:
	RESULT startQuery();
	eServiceReference m_parent;
	friend class eServiceFactoryDVB;
	eDVBServiceList(const eServiceReference &parent);
	ePtr<iDVBChannelListQuery> m_query;

		/* for editing purposes. WARNING: lifetime issue! */
	eBouquet *m_bouquet;
};

inline int eDVBServiceList::compareLessEqual(const eServiceReference &a, const eServiceReference &b)
{
	return m_query->compareLessEqual((const eServiceReferenceDVB&)a, (const eServiceReferenceDVB&)b);
}

class eDVBServiceBase: public iFrontendInformation
{
protected:
	static bool tryFallbackTuner(eServiceReferenceDVB &service,
			bool &is_stream, bool is_pvr, bool simulate);

	eDVBServicePMTHandler m_service_handler;
public:
		// iFrontendInformation
	int getFrontendInfo(int w);
	ePtr<iDVBFrontendData> getFrontendData();
	ePtr<iDVBFrontendStatus> getFrontendStatus();
	ePtr<iDVBTransponderData> getTransponderData(bool);
};

class eDVBServicePlay: public eDVBServiceBase,
		public iPlayableService, public iPauseableService,
		public iSeekableService, public Object, public iServiceInformation,
		public iAudioTrackSelection, public iAudioChannelSelection,
		public iSubserviceList, public iTimeshiftService,
		public iCueSheet, public iSubtitleOutput, public iAudioDelay,
		public iRdsDecoder, public iStreamableService,
		public iStreamedService
{
	DECLARE_REF(eDVBServicePlay);
public:
	virtual ~eDVBServicePlay();

		// iPlayableService
	RESULT connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection);
	RESULT start();
	RESULT stop();
	RESULT setTarget(int target);

	RESULT seek(ePtr<iSeekableService> &ptr);
	RESULT pause(ePtr<iPauseableService> &ptr);
	RESULT info(ePtr<iServiceInformation> &ptr);
	RESULT audioChannel(ePtr<iAudioChannelSelection> &ptr);
	RESULT audioTracks(ePtr<iAudioTrackSelection> &ptr);
	RESULT frontendInfo(ePtr<iFrontendInformation> &ptr);
	RESULT subServices(ePtr<iSubserviceList> &ptr);
	RESULT timeshift(ePtr<iTimeshiftService> &ptr);
	RESULT cueSheet(ePtr<iCueSheet> &ptr);
	RESULT subtitle(ePtr<iSubtitleOutput> &ptr);
	RESULT audioDelay(ePtr<iAudioDelay> &ptr);
	RESULT rdsDecoder(ePtr<iRdsDecoder> &ptr);
	RESULT keys(ePtr<iServiceKeys> &ptr) { ptr = 0; return -1; }

		// iStreamedService
	RESULT streamed(ePtr<iStreamedService> &ptr);
	ePtr<iStreamBufferInfo> getBufferCharge();
	int setBufferSize(int size);


		// iPauseableService
	RESULT pause();
	RESULT unpause();
	RESULT setSlowMotion(int ratio);
	RESULT setFastForward(int ratio);

		// iSeekableService
	RESULT getLength(pts_t &len);
	RESULT seekTo(pts_t to);
	RESULT seekRelative(int direction, pts_t to);
	RESULT getPlayPosition(pts_t &pos);
	RESULT setTrickmode(int trick=0);
	RESULT isCurrentlySeekable();

		// iServiceInformation
	RESULT getName(std::string &name);
	RESULT getEvent(ePtr<eServiceEvent> &evt, int nownext);
	int getInfo(int w);
	std::string getInfoString(int w);
	ePtr<iDVBTransponderData> getTransponderData();
	void getAITApplications(std::map<int, std::string> &aitlist);
	void getCaIds(std::vector<int> &caids, std::vector<int> &ecmpids);

		// iAudioTrackSelection
	int getNumberOfTracks();
	RESULT selectTrack(unsigned int i);
	RESULT getTrackInfo(struct iAudioTrackInfo &, unsigned int n);
	int getCurrentTrack();

		// iAudioChannelSelection
	int getCurrentChannel();
	RESULT selectChannel(int i);

		// iRdsDecoder
	std::string getText(int i=0);
	void showRassSlidePicture();
	void showRassInteractivePic(int page, int subpage);
	ePyObject getRassInteractiveMask();

		// iSubserviceList
	int getNumberOfSubservices();
	RESULT getSubservice(eServiceReference &subservice, unsigned int n);

		// iTimeshiftService
	RESULT startTimeshift();
	RESULT stopTimeshift(bool swToLive=true);
	int isTimeshiftActive();
	int isTimeshiftEnabled();
	RESULT activateTimeshift();
	RESULT setNextPlaybackFile(const char *fn);
	RESULT saveTimeshiftFile();
	std::string getTimeshiftFilename();
	void switchToLive();

		// iCueSheet
	PyObject *getCutList();
	void setCutList(SWIG_PYOBJECT(ePyObject));
	void setCutListEnable(int enable);

		// iSubtitleOutput
	RESULT enableSubtitles(iSubtitleUser *user, SubtitleTrack &track);
	RESULT disableSubtitles();
	RESULT getSubtitleList(std::vector<SubtitleTrack> &sublist);
	RESULT getCachedSubtitle(SubtitleTrack &track);

		// iAudioDelay
	int getAC3Delay();
	int getPCMDelay();
	void setAC3Delay(int);
	void setPCMDelay(int);

		// iStreamableService
	RESULT stream(ePtr<iStreamableService> &ptr);
	ePtr<iStreamData> getStreamingData();

protected:
	friend class eServiceFactoryDVB;
	eServiceReference m_reference;

	ePtr<eDVBService> m_dvb_service;

	ePtr<iTSMPEGDecoder> m_decoder;
	int m_decoder_index;
	int m_have_video_pid;
	int m_tune_state;

		/* in timeshift mode, we essentially have two channels, and thus pmt handlers. */
	eDVBServicePMTHandler m_service_handler_timeshift;
	eDVBServiceEITHandler m_event_handler;
	int m_current_audio_pid;

	eDVBServicePlay(const eServiceReference &ref, eDVBService *service);

		/* events */
	void gotNewEvent(int error);

	void serviceEvent(int event);
	void serviceEventTimeshift(int event);
	Signal2<void,iPlayableService*,int> m_event;

	bool m_is_stream;

		/* pvr */
	bool m_is_pvr;
	int m_is_paused, m_timeshift_enabled, m_timeshift_active, m_timeshift_changed, m_save_timeshift;
	int m_first_program_info;

	std::string m_timeshift_file, m_timeshift_file_next;
	int m_timeshift_fd;
	ePtr<iDVBDemux> m_decode_demux;

	int m_current_audio_stream;
	int selectAudioStream(int n = -1);
	RESULT setFastForward_internal(int ratio, bool final_seek=false);

		/* timeshift */
	ePtr<iDVBTSRecorder> m_record;
	std::set<int> m_pids_active;

	void updateTimeshiftPids();

	void resetTimeshift(int start);
	void switchToTimeshift();

	void updateDecoder(bool sendSeekableStateChanged=false);

	int m_skipmode;
	int m_fastforward;
	int m_slowmotion;

		/* cuesheet */

	ePtr<eCueSheet> m_cue;

	struct cueEntry
	{
		pts_t where;
		unsigned int what;

		bool operator < (const struct cueEntry &o) const
		{
			return where < o.where;
		}
		cueEntry(const pts_t &where, unsigned int what) :
			where(where), what(what)
		{
		}
	};

	std::multiset<cueEntry> m_cue_entries;
	int m_cuesheet_changed, m_cutlist_enabled;

	void loadCuesheet();
	void saveCuesheet();

	void cutlistToCuesheet();

	iSubtitleUser *m_subtitle_widget;

		/* teletext subtitles */
	ePtr<eDVBTeletextParser> m_teletext_parser;
	void newSubtitleStream();
	ePtr<eConnection> m_new_subtitle_stream_connection;
	void newSubtitlePage(const eDVBTeletextSubtitlePage &p);
	ePtr<eConnection> m_new_subtitle_page_connection;
	std::list<eDVBTeletextSubtitlePage> m_subtitle_pages;

		/* dvb subtitles */
	ePtr<eDVBSubtitleParser> m_subtitle_parser;
	void newDVBSubtitlePage(const eDVBSubtitlePage &p);
	ePtr<eConnection> m_new_dvb_subtitle_page_connection;
	std::list<eDVBSubtitlePage> m_dvb_subtitle_pages;

	ePtr<eTimer> m_subtitle_sync_timer;
	void checkSubtitleTiming();

	ePtr<eTimer> m_nownext_timer;
	void updateEpgCacheNowNext();

		/* radiotext */
	ePtr<eDVBRdsDecoder> m_rds_decoder;
	ePtr<eConnection> m_rds_decoder_event_connection;
	void rdsDecoderEvent(int);

	ePtr<eConnection> m_video_event_connection;
	void video_event(struct iTSMPEGDecoder::videoEvent);

	virtual ePtr<iTsSource> createTsSource(eServiceReferenceDVB &ref, int packetsize = 188);
};

class eStaticServiceDVBBouquetInformation: public iStaticServiceInformation
{
	DECLARE_REF(eStaticServiceDVBBouquetInformation);
	eServiceReference m_playable_service;
public:
	eServiceReference &getPlayableService() { return m_playable_service; }
	RESULT getName(const eServiceReference &ref, std::string &name);
	int getLength(const eServiceReference &ref);
	int isPlayable(const eServiceReference &ref, const eServiceReference &ignore, bool simulate);
	RESULT getEvent(const eServiceReference &ref, ePtr<eServiceEvent> &ptr, time_t start_time);
};

#endif
