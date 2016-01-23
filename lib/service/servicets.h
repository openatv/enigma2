#ifndef __servicets_h
#define __servicets_h

#include <lib/base/ioprio.h>
#include <lib/base/message.h>
#include <lib/service/iservice.h>
#include <lib/dvb/dvb.h>

class eStaticServiceTSInfo;

class eServiceFactoryTS: public iServiceHandler
{
DECLARE_REF(eServiceFactoryTS);
public:
	eServiceFactoryTS();
	virtual ~eServiceFactoryTS();
	enum { id = 0x1002 };

	// iServiceHandler
	RESULT play(const eServiceReference &, ePtr<iPlayableService> &ptr);
	RESULT record(const eServiceReference &, ePtr<iRecordableService> &ptr);
	RESULT list(const eServiceReference &, ePtr<iListableService> &ptr);
	RESULT info(const eServiceReference &, ePtr<iStaticServiceInformation> &ptr);
	RESULT offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr);
};

class TSAudioInfo {
DECLARE_REF(TSAudioInfo);
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


class eStreamThread;
class eServiceTS: public iPlayableService, public iPauseableService,
	public iServiceInformation, public iSeekableService,
	public iAudioTrackSelection, public iAudioChannelSelection, public Object
{
DECLARE_REF(eServiceTS);
public:
	virtual ~eServiceTS();

	// iPlayableService
	RESULT connectEvent(const Slot2<void,iPlayableService*,int> &event, ePtr<eConnection> &connection);
	RESULT start();
	RESULT stop();
	RESULT pause(ePtr<iPauseableService> &ptr);
	RESULT seek(ePtr<iSeekableService> &ptr);
	RESULT info(ePtr<iServiceInformation>&);

	// not implemented
	RESULT setTarget(int target) { return -1; };
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
	friend class eServiceFactoryTS;
	std::string m_filename;
	int m_vpid, m_apid;
	int m_destfd;
	ePtr<iDVBDemux> m_decodedemux;
	ePtr<iTSMPEGDecoder> m_decoder;
	ePtr<eStreamThread> m_streamthread;
	ePtr<TSAudioInfo> m_audioInfo;

	eServiceTS(const eServiceReference &url);
	int openHttpConnection(std::string url);

	Signal2<void,iPlayableService*,int> m_event;
	eFixedMessagePump<int> m_pump;
	void recv_event(int evt);
	void setAudioPid(int pid, int type);
};

class eStreamThread: public eThread, public Object {
DECLARE_REF(eStreamThread);
public:
	eStreamThread();
	virtual ~eStreamThread();
	void start(int srcfd, int destfd);
	void stop();
	bool running() { return m_running; }

	virtual void thread();
	virtual void thread_finished();

	RESULT getAudioInfo(ePtr<TSAudioInfo> &ptr);

	enum { evtEOS, evtSOS, evtReadError, evtWriteError, evtUser, evtStreamInfo };
	Signal1<void,int> m_event;
private:
	bool m_stop;
	bool m_running;
	int m_srcfd, m_destfd;
	ePtr<TSAudioInfo> m_audioInfo;
	eFixedMessagePump<int> m_messagepump;
	void recvEvent(const int &evt);
	bool scanAudioInfo(unsigned char buf[], int len);
	std::string getDescriptor(unsigned char buf[], int buflen, int type);
};

#endif
