#ifndef __servicemp3_h
#define __servicemp3_h

#define HAVE_XINE
#ifdef HAVE_XINE
#include <lib/base/message.h>
#include <lib/service/iservice.h>

#include <xine.h>
#include <xine/xineutils.h>

class eStaticServiceXineInfo;

class eServiceFactoryXine: public iServiceHandler
{
	DECLARE_REF(eServiceFactoryXine);
public:
	eServiceFactoryXine();
	virtual ~eServiceFactoryXine();
	enum { id = 0x1010 };

		// iServiceHandler
	RESULT play(const eServiceReference &, ePtr<iPlayableService> &ptr);
	RESULT record(const eServiceReference &, ePtr<iRecordableService> &ptr);
	RESULT list(const eServiceReference &, ePtr<iListableService> &ptr);
	RESULT info(const eServiceReference &, ePtr<iStaticServiceInformation> &ptr);
	RESULT offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr);
private:
	ePtr<eStaticServiceXineInfo> m_service_info;
};

class eStaticServiceXineInfo: public iStaticServiceInformation
{
	DECLARE_REF(eStaticServiceXineInfo);
	friend class eServiceFactoryXine;
	eStaticServiceXineInfo();
public:
	RESULT getName(const eServiceReference &ref, std::string &name);
	int getLength(const eServiceReference &ref);
};

typedef struct _GstElement GstElement;

class eServiceXine: public iPlayableService, public iPauseableService,
	public iServiceInformation, public iSeekableService, public Object
{
	DECLARE_REF(eServiceXine);
public:
	virtual ~eServiceXine();

		// iPlayableService
	RESULT connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection);
	RESULT start();
	RESULT stop();
	RESULT setTarget(int target);

	RESULT pause(ePtr<iPauseableService> &ptr);
	RESULT setSlowMotion(int ratio);
	RESULT setFastForward(int ratio);

	RESULT seek(ePtr<iSeekableService> &ptr);

		// not implemented (yet)
	RESULT audioChannel(ePtr<iAudioChannelSelection> &ptr) { ptr = 0; return -1; }
	RESULT audioTracks(ePtr<iAudioTrackSelection> &ptr) { ptr = 0; return -1; }
	RESULT frontendInfo(ePtr<iFrontendInformation> &ptr) { ptr = 0; return -1; }
	RESULT subServices(ePtr<iSubserviceList> &ptr) { ptr = 0; return -1; }
	RESULT timeshift(ePtr<iTimeshiftService> &ptr) { ptr = 0; return -1; }
	RESULT cueSheet(ePtr<iCueSheet> &ptr) { ptr = 0; return -1; }
	RESULT subtitle(ePtr<iSubtitleOutput> &ptr) { ptr = 0; return -1; }
	RESULT audioDelay(ePtr<iAudioDelay> &ptr) { ptr = 0; return -1; }
	RESULT rdsDecoder(ePtr<iRdsDecoder> &ptr) { ptr = 0; return -1; }
	RESULT keys(ePtr<iServiceKeys> &ptr) { ptr = 0; return -1; }

		// iPausableService
	RESULT pause();
	RESULT unpause();

	RESULT info(ePtr<iServiceInformation>&);

		// iSeekableService
	RESULT getLength(pts_t &SWIG_OUTPUT);
	RESULT seekTo(pts_t to);
	RESULT seekRelative(int direction, pts_t to);
	RESULT getPlayPosition(pts_t &SWIG_OUTPUT);
	RESULT setTrickmode(int trick);
	RESULT isCurrentlySeekable();

		// iServiceInformation
	RESULT getName(std::string &name);
	int getInfo(int w);
	std::string getInfoString(int w);
private:
	friend class eServiceFactoryXine;
	std::string m_filename;
	eServiceXine(const char *filename);
	Signal2<void,iPlayableService*,int> m_event;

	xine_stream_t *stream;
	xine_video_port_t *vo_port;
	xine_audio_port_t *ao_port;
	xine_event_queue_t *event_queue;

	enum
	{
		stError, stIdle, stRunning, stStopped,
	};
	int m_state;

	static void eventListenerWrap(void *user_data, const xine_event_t *event);
	void eventListener(const xine_event_t *event);


	eFixedMessagePump<int> m_pump;
};
#endif

#endif
