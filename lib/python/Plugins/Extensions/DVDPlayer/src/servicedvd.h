#ifndef __servicedvd_h
#define __servicedvd_h

#include <lib/base/message.h>
#include <lib/base/ebase.h>
#include <lib/base/thread.h>
#include <lib/service/iservice.h>

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

class eServiceDVD: public iPlayableService, public iPauseableService, public iSeekableService, public iAudioTrackSelection,
	public iServiceInformation, public iSubtitleOutput, public iServiceKeys, public iCueSheet, public eThread, public Object
{
	friend class eServiceFactoryDVD;
	DECLARE_REF(eServiceDVD);
public:
	virtual ~eServiceDVD();
		// not implemented (yet)
	RESULT audioChannel(ePtr<iAudioChannelSelection> &ptr) { ptr = 0; return -1; }
	RESULT audioTracks(ePtr<iAudioTrackSelection> &ptr);
	RESULT frontendInfo(ePtr<iFrontendInformation> &ptr) { ptr = 0; return -1; }
	RESULT subServices(ePtr<iSubserviceList> &ptr) { ptr = 0; return -1; }
	RESULT timeshift(ePtr<iTimeshiftService> &ptr) { ptr = 0; return -1; }
	RESULT audioDelay(ePtr<iAudioDelay> &ptr) { ptr = 0; return -1; }
	RESULT rdsDecoder(ePtr<iRdsDecoder> &ptr) { ptr = 0; return -1; }
	RESULT stream(ePtr<iStreamableService> &ptr) { ptr = 0; return -1; }
	RESULT streamed(ePtr<iStreamedService> &ptr) { ptr = 0; return -1; }
	RESULT cueSheet(ePtr<iCueSheet> &ptr);

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

		// iSeekableService
	RESULT getLength(pts_t &len);
	RESULT seekTo(pts_t to);
	RESULT seekRelative(int direction, pts_t to);
	RESULT getPlayPosition(pts_t &pos);
	RESULT setTrickmode(int trick=0);
	RESULT isCurrentlySeekable();
	RESULT seekChapter(int chapter);
	RESULT seekTitle(int title);

		// iServiceInformation
	RESULT getName(std::string &name);
	int getInfo(int w);
	std::string getInfoString(int w);
	virtual PyObject *getInfoObject(int w);

		// iCueSheet
	PyObject *getCutList();
	void setCutList(SWIG_PYOBJECT(ePyObject));
	void setCutListEnable(int enable);

			// iAudioTrackSelection	
	int getNumberOfTracks();
	RESULT selectTrack(unsigned int i);
	RESULT getTrackInfo(struct iAudioTrackInfo &, unsigned int n);
	int getCurrentTrack();

	// iServiceKeys
	RESULT keyPressed(int key);

private:
	eServiceDVD(eServiceReference ref);

	void gotMessage(int); // message from dvdlib
	void gotThreadMessage(const int &); // message from dvd thread

		// eThread
	void thread();
	void thread_finished();

	eServiceReference m_ref;

	Signal2<void,iPlayableService*,int> m_event;

	struct ddvd *m_ddvdconfig;
	ePtr<gPixmap> m_pixmap;
	eSubtitleWidget *m_subtitle_widget;

	enum
	{
		stIdle, stRunning, stMenu, stStopped
	};

	int m_state;
	int m_current_trick;

	char m_ddvd_titlestring[96];

	ePtr<eSocketNotifier> m_sn;
	eFixedMessagePump<int> m_pump;

	pts_t m_cue_pts;
	struct ddvd_resume m_resume_info;

	void loadCuesheet();
	void saveCuesheet();

	int m_width, m_height, m_aspect, m_framerate, m_progressive;
};

#endif
