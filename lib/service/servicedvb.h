#ifndef __servicedvb_h
#define __servicedvb_h

#include <lib/service/iservice.h>
#include <lib/dvb/idvb.h>

#include <lib/dvb/pmt.h>
#include <lib/dvb/eit.h>
#include <lib/dvb/teletext.h>
#include <lib/base/filepush.h>

class eServiceFactoryDVB: public iServiceHandler
{
DECLARE_REF(eServiceFactoryDVB);
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
	int compareLessEqual(const eServiceReference &a, const eServiceReference &b);
	
	RESULT startEdit(ePtr<iMutableServiceList> &);
	RESULT flushChanges();
	RESULT addService(eServiceReference &ref);
	RESULT removeService(eServiceReference &ref);
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

class eDVBServiceBase: public iFrontendInformation
{
protected:
	eDVBServicePMTHandler m_service_handler;
public:
		// iFrontendInformation
	int getFrontendInfo(int w);
	PyObject *getFrontendData(bool);
};

class eDVBServicePlay: public eDVBServiceBase,
		public iPlayableService, public iPauseableService, 
		public iSeekableService, public Object, public iServiceInformation, 
		public iAudioTrackSelection, public iAudioChannelSelection,
		public iSubserviceList, public iTimeshiftService,
		public iCueSheet
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
	PyObject *getInfoObject(int w);

		// iAudioTrackSelection	
	int getNumberOfTracks();
	RESULT selectTrack(unsigned int i);
	RESULT getTrackInfo(struct iAudioTrackInfo &, unsigned int n);

		// iAudioChannelSelection	
	int getCurrentChannel();
	RESULT selectChannel(int i);

		// iSubserviceList
	int getNumberOfSubservices();
	RESULT getSubservice(eServiceReference &subservice, unsigned int n);

		// iTimeshiftService
	RESULT startTimeshift();
	RESULT stopTimeshift();
	int isTimeshiftActive();
	RESULT activateTimeshift();

		// iCueSheet
	PyObject *getCutList();
	void setCutList(PyObject *);
	void setCutListEnable(int enable);
	
private:
	friend class eServiceFactoryDVB;
	eServiceReference m_reference;
	
	ePtr<eDVBService> m_dvb_service;
	
	ePtr<iTSMPEGDecoder> m_decoder;
	int m_is_primary;
	
		/* in timeshift mode, we essentially have two channels, and thus pmt handlers. */
	eDVBServicePMTHandler m_service_handler_timeshift;
	eDVBServiceEITHandler m_event_handler;
	
	eDVBServicePlay(const eServiceReference &ref, eDVBService *service);
	
		/* events */
	void gotNewEvent();
	
	void serviceEvent(int event);
	void serviceEventTimeshift(int event);
	Signal2<void,iPlayableService*,int> m_event;
	
		/* pvr */
	int m_is_pvr, m_is_paused, m_timeshift_enabled, m_timeshift_active;
	int m_first_program_info;
	
	std::string m_timeshift_file;
	int m_timeshift_fd;
	
	ePtr<iDVBDemux> m_decode_demux;
	
	int m_current_audio_stream;
	int selectAudioStream(int n);
	
		/* timeshift */
	ePtr<iDVBTSRecorder> m_record;
	std::set<int> m_pids_active;

	void updateTimeshiftPids();
	void switchToLive();
	void switchToTimeshift();
	
	void updateDecoder();
	
	int m_skipmode;
	
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
	
		/* teletext subtitles */
	ePtr<eDVBTeletextParser> m_teletext_parser;
};

#endif
