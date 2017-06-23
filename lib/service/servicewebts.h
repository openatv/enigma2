#ifndef __servicewebts_h
#define __servicewebts_h

#include <lib/base/ioprio.h>
#include <lib/base/message.h>
#include <lib/service/iservice.h>
#include <lib/dvb/dvb.h>

#define PRIVATE_STREAM1  0xBD
#define PRIVATE_STREAM2  0xBF

#define AUDIO_STREAM_S   0xC0
#define AUDIO_STREAM_E   0xDF

#define VIDEO_STREAM_S   0xE0
#define VIDEO_STREAM_E   0xEF

#define TS_SIZE          188
#define IN_SIZE		 65424

#define PID_MASK_HI      0x1F


class eStaticServiceWebTSInfo;

class eServiceFactoryWebTS: public iServiceHandler
{
DECLARE_REF(eServiceFactoryWebTS);
public:
	eServiceFactoryWebTS();
	virtual ~eServiceFactoryWebTS();
	enum { id = 0x1012 };

	// iServiceHandler
	RESULT play(const eServiceReference &, ePtr<iPlayableService> &ptr);
	RESULT record(const eServiceReference &, ePtr<iRecordableService> &ptr);
	RESULT list(const eServiceReference &, ePtr<iListableService> &ptr);
	RESULT info(const eServiceReference &, ePtr<iStaticServiceInformation> &ptr);
	RESULT offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr);
private:
	ePtr<eStaticServiceWebTSInfo> m_service_info;
};

class eStaticServiceWebTSInfo: public iStaticServiceInformation
{
	DECLARE_REF(eStaticServiceWebTSInfo);
	friend class eServiceFactoryWebTS;
	eStaticServiceWebTSInfo();
public:
	RESULT getName(const eServiceReference &ref, std::string &name);
	int getLength(const eServiceReference &ref);
	int getInfo(const eServiceReference &ref, int w);
	int isPlayable(const eServiceReference &ref, const eServiceReference &ignore, bool simulate) { return 1; }
	long long getFileSize(const eServiceReference &ref);
	RESULT getEvent(const eServiceReference &ref, ePtr<eServiceEvent> &ptr, time_t start_time);
};

class TSAudioInfoWeb {
DECLARE_REF(TSAudioInfoWeb);
public:
	struct StreamInfo {
		int pid;
		int type;
		std::string language; /* iso639 */
		std::string description;
	};
	std::vector<StreamInfo> audioStreams;
	void addAudio(int pid, std::string lang, std::string desc, int type);
};


class eStreamThreadWeb;
class eServiceWebTS: public iPlayableService, public iPauseableService,
	public iServiceInformation, public iSeekableService,
	public iAudioTrackSelection, public iAudioChannelSelection, public sigc::trackable
{
DECLARE_REF(eServiceWebTS);
public:
	virtual ~eServiceWebTS();

	// iPlayableService
	RESULT connectEvent(const sigc::slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection);
	RESULT start();
	RESULT stop();
	RESULT pause(ePtr<iPauseableService> &ptr);
	RESULT seek(ePtr<iSeekableService> &ptr);
	RESULT info(ePtr<iServiceInformation>&);

	// not implemented
	RESULT setTarget(int target, bool noaudio = false) { return -1; };
	RESULT setSlowMotion(int ratio) { return -1; };
	RESULT setFastForward(int ratio) { return -1; };
	RESULT audioChannel(ePtr<iAudioChannelSelection> &ptr) { ptr = this; return 0; };
	RESULT audioTracks(ePtr<iAudioTrackSelection> &ptr) { ptr = this; return 0; };
	RESULT frontendInfo(ePtr<iFrontendInformation> &ptr) { ptr = 0; return -1; };
	RESULT subServices(ePtr<iSubserviceList> &ptr) { ptr = 0; return -1; };
	RESULT timeshift(ePtr<iTimeshiftService> &ptr) { ptr = 0; return -1; };
	RESULT cueSheet(ePtr<iCueSheet> &ptr) { ptr = 0; return -1; };
	RESULT subtitle(ePtr<iSubtitleOutput> &ptr) { ptr = 0; return -1; };
	RESULT audioDelay(ePtr<iAudioDelay> &ptr) { ptr = 0; return -1; };
	RESULT rdsDecoder(ePtr<iRdsDecoder> &ptr) { ptr = 0; return -1; };
	RESULT stream(ePtr<iStreamableService> &ptr) { ptr = 0; return -1; };
	RESULT streamed(ePtr<iStreamedService> &ptr) { ptr = 0; return -1; };
	RESULT keys(ePtr<iServiceKeys> &ptr) { ptr = 0; return -1; };

	// iPausableService
	RESULT pause();
	RESULT unpause();


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

	// iAudioTrackSelection
	int getNumberOfTracks();
	RESULT selectTrack(unsigned int i);
	SWIG_VOID(RESULT) getTrackInfo(struct iAudioTrackInfo &, unsigned int n);
	int getCurrentTrack();

	// iAudioChannelSelection
	int getCurrentChannel() { return iAudioChannelSelection_ENUMS::STEREO; };
	RESULT selectChannel(int i) { return 0; };

private:
	friend class eServiceFactoryWebTS;
	eServiceReference m_reference;
	std::string m_filename;
	int m_vpid, m_apid;
	int m_destfd;
	ePtr<iDVBDemux> m_decodedemux;
	ePtr<iTSMPEGDecoder> m_decoder;
	ePtr<eStreamThreadWeb> m_streamthread;
	ePtr<TSAudioInfoWeb> m_audioInfo;

	eServiceWebTS(const eServiceReference &url);
	int openHttpConnection(std::string url);

	sigc::signal2<void,iPlayableService*,int> m_event;
	eFixedMessagePump<int> m_pump;
	void recv_event(int evt);
	void setAudioPid(int pid, int type);
};

class eStreamThreadWeb: public eThread, public sigc::trackable {
DECLARE_REF(eStreamThreadWeb);
public:
	eStreamThreadWeb();
	virtual ~eStreamThreadWeb();
	void start(int srcfd, int destfd);
	void stop();
	bool running() { return m_running; }

	virtual void thread();
	virtual void thread_finished();

	RESULT getAudioInfo(ePtr<TSAudioInfoWeb> &ptr);

	enum { evtEOS, evtSOS, evtReadError, evtWriteError, evtUser, evtStreamInfo };
	sigc::signal1<void,int> m_event;
private:
	bool m_stop;
	bool m_running;
	int m_srcfd, m_destfd;
	ePtr<TSAudioInfoWeb> m_audioInfo;
	eFixedMessagePump<int> m_messagepump;
	void recvEvent(const int &evt);
	bool scanAudioInfo(unsigned char buf[], int len);
	std::string getDescriptor(unsigned char buf[], int buflen, int type);
};

#endif
