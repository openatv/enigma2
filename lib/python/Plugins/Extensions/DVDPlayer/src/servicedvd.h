#ifndef __servicedvd_h
#define __servicedvd_h

#include <lib/base/message.h>
#include <lib/base/ebase.h>
#include <lib/base/thread.h>
#include <lib/service/iservice.h>

#define cue

class eSubtitleWidget;
class gPixmap;
class eStaticServiceDVDInfo;

class eServiceFactoryDVD: public iServiceHandler
{
DECLARE_REF(eServiceFactoryDVD);
public:
	eServiceFactoryDVD();
	virtual ~eServiceFactoryDVD();
	enum { id = 0x1111 };

		// iServiceHandler
	RESULT play(const eServiceReference &, ePtr<iPlayableService> &ptr);
	RESULT record(const eServiceReference &, ePtr<iRecordableService> &ptr);
	RESULT list(const eServiceReference &, ePtr<iListableService> &ptr);
	RESULT info(const eServiceReference &, ePtr<iStaticServiceInformation> &ptr);
	RESULT offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr);
};

class eServiceDVD: public iPlayableService, public iPauseableService, public iSeekableService,
	public iServiceInformation, public iSubtitleOutput, public iServiceKeys, public eThread, public Object
#ifdef cue
, public iCueSheet
#endif
{
	friend class eServiceFactoryDVD;
DECLARE_REF(eServiceDVD);
public:
	virtual ~eServiceDVD();
		// not implemented (yet)
	RESULT audioChannel(ePtr<iAudioChannelSelection> &ptr) { ptr = 0; return -1; }
	RESULT audioTracks(ePtr<iAudioTrackSelection> &ptr) { ptr = 0; return -1; }
	RESULT frontendInfo(ePtr<iFrontendInformation> &ptr) { ptr = 0; return -1; }
	RESULT subServices(ePtr<iSubserviceList> &ptr) { ptr = 0; return -1; }
	RESULT timeshift(ePtr<iTimeshiftService> &ptr) { ptr = 0; return -1; }
	RESULT audioDelay(ePtr<iAudioDelay> &ptr) { ptr = 0; return -1; }
	RESULT rdsDecoder(ePtr<iRdsDecoder> &ptr) { ptr = 0; return -1; }
	RESULT stream(ePtr<iStreamableService> &ptr) { ptr = 0; return -1; }
#ifdef cue
	RESULT cueSheet(ePtr<iCueSheet> &ptr);
#else
	RESULT cueSheet(ePtr<iCueSheet> &ptr) { ptr = 0; return -1; }
#endif

		// iPlayableService
	RESULT connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection);
	RESULT start();
	RESULT stop();
	RESULT setTarget(int target);
	RESULT info(ePtr<iServiceInformation> &ptr);
	RESULT pause(ePtr<iPauseableService> &ptr);
	RESULT subtitle(ePtr<iSubtitleOutput> &ptr);
	RESULT seek(ePtr<iSeekableService> &ptr);
	RESULT keys(ePtr<iServiceKeys> &ptr);

		// iPausableService
	RESULT pause();
	RESULT unpause();
	RESULT setSlowMotion(int ratio);
	RESULT setFastForward(int ratio);

		// iSubtitleOutput
	RESULT enableSubtitles(eWidget *parent, SWIG_PYOBJECT(ePyObject) entry);
	RESULT disableSubtitles(eWidget *parent);
	PyObject *getSubtitleList();
	PyObject *getCachedSubtitle();

#if 1
		// iSeekableService
	RESULT getLength(pts_t &len);
	RESULT seekTo(pts_t to);
	RESULT seekRelative(int direction, pts_t to);
	RESULT getPlayPosition(pts_t &pos);
	RESULT setTrickmode(int trick=0);
	RESULT isCurrentlySeekable();
	RESULT seekChapter(int chapter);
#endif

		// iServiceInformation
	RESULT getName(std::string &name);
	int getInfo(int w);
	std::string getInfoString(int w);
	virtual PyObject *getInfoObject(int w);

#ifdef cue
		// iCueSheet
	PyObject *getCutList();
	void setCutList(SWIG_PYOBJECT(ePyObject));
	void setCutListEnable(int enable);
#endif
		// iServiceKeys
	RESULT keyPressed(int key);
private:
	eServiceDVD(const char *filename);

	void gotMessage(int); // message from dvdlib
	void gotThreadMessage(const int &); // message from dvd thread

		// eThread
	void thread();
	void thread_finished();

	std::string m_filename;

	Signal2<void,iPlayableService*,int> m_event;

	struct ddvd *m_ddvdconfig;
	ePtr<gPixmap> m_pixmap;
	eSubtitleWidget *m_subtitle_widget;

	enum
	{
		stIdle, stRunning, stStopped,
	};

	int m_state;
	int m_current_trick;

	pts_t m_doSeekTo;
	int m_seekTitle;
	char m_ddvd_titlestring[96];

	eSocketNotifier m_sn;
	eFixedMessagePump<int> m_pump;

#ifdef cue
// 	ePtr<eCueSheet> m_cue;
// 
// 	struct cueEntry
// 	{
// 		pts_t where;
// 		unsigned int what;
// 		
// 		bool operator < (const struct cueEntry &o) const
// 		{
// 			return where < o.where;
// 		}
// 		cueEntry(const pts_t &where, unsigned int what) :
// 			where(where), what(what)
// 		{
// 		}
// 	};
	
// 	std::multiset<cueEntry> m_cue_entries;
	int m_cuesheet_changed, m_cutlist_enabled;
	pts_t m_cue_pts;
	
	void loadCuesheet();
	void saveCuesheet();
	
// 	void cutlistToCuesheet();
#endif
};

#endif
