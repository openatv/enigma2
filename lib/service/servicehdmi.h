#ifndef __servicehdmi_h
#define __servicehdmi_h

#include <lib/base/message.h>
#include <lib/service/iservice.h>
#include <lib/service/servicedvb.h>

class eStaticServiceHDMIInfo;

class eServiceFactoryHDMI: public iServiceHandler
{
	DECLARE_REF(eServiceFactoryHDMI);
public:
	eServiceFactoryHDMI();
	virtual ~eServiceFactoryHDMI();
	enum { id = 0x2000 };

	RESULT play(const eServiceReference &, ePtr<iPlayableService> &ptr);
	RESULT record(const eServiceReference &, ePtr<iRecordableService> &ptr);
	RESULT list(const eServiceReference &, ePtr<iListableService> &ptr);
	RESULT info(const eServiceReference &, ePtr<iStaticServiceInformation> &ptr);
	RESULT offlineOperations(const eServiceReference &, ePtr<iServiceOfflineOperations> &ptr);
private:
	ePtr<eStaticServiceHDMIInfo> m_service_info;
};

class eStaticServiceHDMIInfo: public iStaticServiceInformation
{
	DECLARE_REF(eStaticServiceHDMIInfo);
	friend class eServiceFactoryHDMI;
	eStaticServiceHDMIInfo();
public:
	RESULT getName(const eServiceReference &ref, std::string &name);
	int getLength(const eServiceReference &ref);
	int getInfo(const eServiceReference &ref, int w);
	int isPlayable(const eServiceReference &ref, const eServiceReference &ignore, bool simulate) { return 1; }
	long long getFileSize(const eServiceReference &ref);
};

class eServiceHDMI: public iPlayableService, public iServiceInformation, public sigc::trackable
{
	DECLARE_REF(eServiceHDMI);
public:
	virtual ~eServiceHDMI();

	RESULT connectEvent(const sigc::slot2<void, iPlayableService*, int> &event, ePtr<eConnection> &connection);
	RESULT start();
	RESULT stop();
	RESULT setTarget(int target, bool noaudio);

	RESULT pause(ePtr<iPauseableService> &ptr) { ptr = 0; return -1; }
	RESULT seek(ePtr<iSeekableService> &ptr) { ptr = 0; return -1; }
	RESULT audioTracks(ePtr<iAudioTrackSelection> &ptr) { ptr = 0; return -1; }
	RESULT audioChannel(ePtr<iAudioChannelSelection> &ptr) { ptr = 0; return -1; }
	RESULT subtitle(ePtr<iSubtitleOutput> &ptr) { ptr = 0; return -1; }
	RESULT audioDelay(ePtr<iAudioDelay> &ptr) { ptr = 0; return -1; }

	RESULT frontendInfo(ePtr<iFrontendInformation> &ptr) { ptr = 0; return -1; }
	RESULT subServices(ePtr<iSubserviceList> &ptr) { ptr = 0; return -1; }
	RESULT timeshift(ePtr<iTimeshiftService> &ptr) { ptr = 0; return -1; }
	RESULT cueSheet(ePtr<iCueSheet> &ptr) { ptr = 0; return -1; }

	RESULT rdsDecoder(ePtr<iRdsDecoder> &ptr) { ptr = 0; return -1; }
	RESULT keys(ePtr<iServiceKeys> &ptr) { ptr = 0; return -1; }
	RESULT stream(ePtr<iStreamableService> &ptr) { ptr = 0; return -1; }
	RESULT streamed(ePtr<iStreamedService> &ptr) { ptr = 0; return -1; }

	RESULT info(ePtr<iServiceInformation>&);

	RESULT getName(std::string &name);
	int getInfo(int w);
	std::string getInfoString(int w);
	ePtr<iServiceInfoContainer> getInfoObject(int w);

	void setQpipMode(bool value, bool audio) { }

private:
	friend class eServiceFactoryHDMI;
	eServiceHDMI(eServiceReference ref);
	sigc::signal2<void,iPlayableService*, int> m_event;
	eServiceReference m_ref;
	int m_decoder_index;
	bool m_noaudio;
	ePtr<iTSMPEGDecoder> m_decoder;
};

class eServiceHDMIRecord: public eDVBServiceBase, public iRecordableService, public sigc::trackable
{
	DECLARE_REF(eServiceHDMIRecord);
public:
	eServiceHDMIRecord(const eServiceReference &ref);
	RESULT connectEvent(const sigc::slot2<void,iRecordableService*,int> &event, ePtr<eConnection> &connection);
	RESULT prepare(const char *filename, time_t begTime, time_t endTime, int eit_event_id, const char *name, const char *descr, const char *tags, bool descramble, bool recordecm, int packetsize);
	RESULT prepareStreaming(bool descramble = true, bool includeecm = false);
	RESULT start(bool simulate=false);
	RESULT stop();
	RESULT getError(int &error) { error = m_error; return 0; }
	RESULT frontendInfo(ePtr<iFrontendInformation> &ptr);
	RESULT stream(ePtr<iStreamableService> &ptr);
	RESULT subServices(ePtr<iSubserviceList> &ptr);
	RESULT getFilenameExtension(std::string &ext) { ext = ".ts"; return 0; };

private:
	enum { stateIdle, statePrepared, stateRecording };
	bool m_simulate;
	int m_state;
	eDVBRecordFileThread *m_thread;
	eServiceReference m_ref;

	int m_recording, m_error;
	std::string m_filename;

	int m_target_fd;
	int m_encoder_fd;

	int doPrepare();
	int doRecord();

	/* events */
	sigc::signal2<void,iRecordableService*,int> m_event;

	/* recorder events */
	void recordEvent(int event);
};

#endif
