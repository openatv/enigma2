#ifndef __lib_service_servicedab_h
#define __lib_service_servicedab_h

#include <atomic>
#include <cstdio>
#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <vector>

#include <lib/base/message.h>
#include <lib/base/thread.h>
#include <lib/dvb/idvb.h>
#include <lib/service/dabtsadapter.h>
#include <lib/service/iservice.h>

class eDABDecoder;
typedef struct _GstElement GstElement;

enum { DAB_MAX_SCANNED_SERVICES = 64 };

struct eDABScannedService
{
	uint32_t serviceId;
	int bitrate;
	bool dabplus;
	char label[64];
};

/*
 * Native DAB-over-DVB proof of concept.
 *
 * A DAB service reference uses the following fields:
 *   data[0] parent DVB service type
 *   data[1] parent DVB SID
 *   data[2] parent DVB TSID
 *   data[3] parent DVB ONID
 *   data[4] parent DVB namespace
 *   data[5] DVB payload PID
 *   data[6] DAB service ID
 *   data[7] DAB ensemble ID
 *   path    dab://<destination-ip>:<destination-port>, dab://tsniv2ni,
 *           dab://ts2na12 or dab://ts2na
 *
 * All supported satellite encapsulations are normalised to ETI-NI inside the
 * worker before the shared FIC/MSC/audio/PAD decoder is called.
 */

struct eDABWorkerStats
{
	uint64_t bytes;
	uint64_t tsPackets;
	uint64_t syncErrors;
	uint64_t continuityErrors;
	uint64_t mpeSections;
	uint64_t udpPackets;
	uint64_t ediPackets;
	uint64_t afPackets;
	uint64_t etiFrames;
	uint64_t ficFrames;
	uint64_t mscFrames;
	uint64_t audioFrames;
	uint64_t crcErrors;
	uint64_t padPackets;
	uint64_t dlsLabels;
	uint64_t motSegments;
	uint64_t motDataGroups;
	uint64_t slides;
	uint64_t serviceRevision;
	uint16_t ensembleId;
	int serviceCount;
	eDABScannedService services[DAB_MAX_SCANNED_SERVICES];
	int slideFormat;
	int bitrate;
	bool serviceFound;
	bool dabplus;
	char serviceLabel[64];
	char ensembleLabel[64];
	char dynamicLabel[256];
	int error;

	eDABWorkerStats();
};

class eDABWorker : private eThread
{
public:
	typedef std::function<void(const uint8_t *, size_t, const uint8_t *, size_t, uint64_t, uint8_t)> AudioCallback;
	typedef std::function<void(const uint8_t *, size_t, int)> ImageCallback;

	eDABWorker(int fd, int pid, eDABTransport transport, uint32_t destinationIp, uint16_t destinationPort,
		uint32_t serviceId, uint16_t ensembleId, const AudioCallback &audioCallback,
		const ImageCallback &imageCallback,
		eFixedMessagePump<eDABWorkerStats> &pump);
	~eDABWorker();

	bool start();
	void stop();

private:
	void thread() override;
	void processInput(const uint8_t *data, size_t length);
	void processTSPacket(const uint8_t *packet);
	void processPayload(const uint8_t *payload, size_t length, bool unitStart);
	void appendSection(const uint8_t *data, size_t length);
	void parseNewSections(const uint8_t *data, size_t length);
	void processMPESection(const uint8_t *section, size_t length);
	void updateDecoderStats();
	void clearSection();
	void publish(bool force = false);

	int m_fd;
	int m_pid;
	eDABTransport m_transport;
	uint32_t m_destination_ip;
	uint16_t m_destination_port;
	eFixedMessagePump<eDABWorkerStats> &m_pump;
	std::atomic<bool> m_stop;
	bool m_started;
	int m_last_cc;
	uint64_t m_last_publish_ms;
	eDABWorkerStats m_stats;
	std::vector<uint8_t> m_input;
	std::vector<uint8_t> m_section;
	size_t m_section_expected;
	std::unique_ptr<eDABDecoder> m_decoder;
	std::unique_ptr<eDABTSAdapter> m_ts_adapter;
};

class eStaticServiceDABInfo : public iStaticServiceInformation
{
	DECLARE_REF(eStaticServiceDABInfo);

public:
	eStaticServiceDABInfo();
	RESULT getName(const eServiceReference &ref, std::string &name) override;
	int getLength(const eServiceReference &ref) override;
	int getInfo(const eServiceReference &ref, int w) override;
	std::string getInfoString(const eServiceReference &ref, int w) override;
	int isPlayable(const eServiceReference &ref, const eServiceReference &ignore, bool simulate) override;
};

class eServiceFactoryDAB : public iServiceHandler
{
	DECLARE_REF(eServiceFactoryDAB);

public:
	enum { id = eServiceReference::idServiceDAB };

	eServiceFactoryDAB();
	~eServiceFactoryDAB() override;

	RESULT play(const eServiceReference &ref, ePtr<iPlayableService> &ptr) override;
	RESULT record(const eServiceReference &ref, ePtr<iRecordableService> &ptr) override;
	RESULT list(const eServiceReference &ref, ePtr<iListableService> &ptr) override;
	RESULT info(const eServiceReference &ref, ePtr<iStaticServiceInformation> &ptr) override;
	RESULT offlineOperations(const eServiceReference &ref, ePtr<iServiceOfflineOperations> &ptr) override;

private:
	ePtr<eStaticServiceDABInfo> m_service_info;
};

class eServiceDAB : public iPlayableService, public iServiceInformation, public iRdsDecoder, public sigc::trackable
{
	DECLARE_REF(eServiceDAB);

public:
	explicit eServiceDAB(const eServiceReference &ref);
	~eServiceDAB() override;

	RESULT connectEvent(const sigc::slot<void(iPlayableService *, int)> &event, ePtr<eConnection> &connection) override;
	RESULT start() override;
	RESULT stop() override;
	RESULT setTarget(int target, bool noaudio = false) override;
	RESULT seek(ePtr<iSeekableService> &ptr) override;
	RESULT pause(ePtr<iPauseableService> &ptr) override;
	RESULT info(ePtr<iServiceInformation> &ptr) override;
	RESULT audioTracks(ePtr<iAudioTrackSelection> &ptr) override;
	RESULT audioChannel(ePtr<iAudioChannelSelection> &ptr) override;
	RESULT subServices(ePtr<iSubserviceList> &ptr) override;
	RESULT frontendInfo(ePtr<iFrontendInformation> &ptr) override;
	RESULT timeshift(ePtr<iTimeshiftService> &ptr) override;
	RESULT tap(ePtr<iTapService> &ptr) override;
	RESULT cueSheet(ePtr<iCueSheet> &ptr) override;
	RESULT subtitle(ePtr<iSubtitleOutput> &ptr) override;
	RESULT audioDelay(ePtr<iAudioDelay> &ptr) override;
	RESULT rdsDecoder(ePtr<iRdsDecoder> &ptr) override;
	RESULT stream(ePtr<iStreamableService> &ptr) override;
	RESULT streamed(ePtr<iStreamedService> &ptr) override;
	RESULT keys(ePtr<iServiceKeys> &ptr) override;
	void setQpipMode(bool value, bool audio) override;

	RESULT getName(std::string &name) override;
	int getInfo(int w) override;
	std::string getInfoString(int w) override;

	// iRdsDecoder -- DAB Dynamic Label uses the existing Enigma2 radio text UI.
	std::string getText(int x = RadioText) override;
	void showRassSlidePicture() override;
	void showRassInteractivePic(int page, int subpage) override;
	ePyObject getRassInteractiveMask() override;

private:
	eServiceReferenceDVB parentReference() const;
	bool parseTransport(eDABTransport &transport, uint32_t &ip, uint16_t &port) const;
	bool startTap();
	void stopTap();
	void parentEvent(iPlayableService *service, int event);
	void workerMessage(const eDABWorkerStats &stats);
	bool startAudioPipeline();
	void stopAudioPipeline();
	void pushAudio(const uint8_t *data, size_t length, uint64_t durationNs, uint8_t config);
	void setAudioCaps(uint8_t config);
	static void audioQueueOverrun(GstElement *queue, void *userData);
	void storeSlide(const uint8_t *data, size_t length, int format);
	std::string slidePath() const;
	void pollAudioBus();

	eServiceReference m_reference;
	ePtr<iPlayableService> m_parent;
	ePtr<iTapService> m_parent_tap;
	ePtr<eConnection> m_parent_event_connection;
	sigc::signal<void(iPlayableService *, int)> m_event;
	eFixedMessagePump<eDABWorkerStats> m_worker_pump;
	std::unique_ptr<eDABWorker> m_worker;
	int m_socket[2];
	bool m_running;
	bool m_tap_running;
	bool m_input_seen;
	bool m_audio_seen;
	int m_parent_state;
	uint64_t m_last_bytes;
	uint64_t m_transfer_bps;
	eDABWorkerStats m_stats;
	GstElement *m_audio_pipeline;
	GstElement *m_audio_source;
	GstElement *m_audio_queue;
	FILE *m_audio_capture;
	uint64_t m_audio_next_pts;
	uint8_t m_audio_format;
	bool m_audio_caps_set;
	std::atomic<uint64_t> m_audio_queue_overruns;
	uint64_t m_reported_audio_queue_overruns;
	std::string m_slide_jpeg_path;
	std::string m_slide_png_path;
};

class eServiceDABRecord : public iRecordableService, public sigc::trackable
{
	DECLARE_REF(eServiceDABRecord);

public:
	explicit eServiceDABRecord(const eServiceReference &ref);
	~eServiceDABRecord() override;

	RESULT connectEvent(const sigc::slot<void(iRecordableService *, int)> &event, ePtr<eConnection> &connection) override;
	RESULT getError(int &error) override;
	RESULT prepare(const char *filename, time_t begTime, time_t endTime, int eitEventId,
		const char *name, const char *description, const char *tags,
		bool descramble, bool recordEcm, int packetSize) override;
	RESULT prepareStreaming(bool descramble, bool includeEcm) override;
	RESULT start(bool simulate = false) override;
	RESULT stop() override;
	RESULT frontendInfo(ePtr<iFrontendInformation> &ptr) override;
	RESULT stream(ePtr<iStreamableService> &ptr) override;
	RESULT subServices(ePtr<iSubserviceList> &ptr) override;
	RESULT getServiceType(int &serviceType) override;
	RESULT getFilenameExtension(std::string &extension) override;

private:
	enum State { stateIdle, statePrepared, stateRecording };

	eServiceReferenceDVB parentReference() const;
	bool parseTransport(eDABTransport &transport, uint32_t &ip, uint16_t &port) const;
	bool prepareParent();
	bool startTap();
	void stopTap();
	void parentEvent(iPlayableService *service, int event);
	void workerMessage(const eDABWorkerStats &stats);
	void writeAudio(const uint8_t *data, size_t length);
	void reportFailure(int error, int event);

	eServiceReference m_reference;
	ePtr<iPlayableService> m_parent;
	ePtr<iTapService> m_parent_tap;
	ePtr<eConnection> m_parent_event_connection;
	sigc::signal<void(iRecordableService *, int)> m_event;
	eFixedMessagePump<eDABWorkerStats> m_worker_pump;
	std::unique_ptr<eDABWorker> m_worker;
	int m_socket[2];
	int m_file_fd;
	State m_state;
	bool m_simulate;
	bool m_tuned;
	bool m_tap_running;
	bool m_running_event_sent;
	bool m_write_error_reported;
	std::atomic<int> m_write_error;
	int m_error;
	uint64_t m_written_bytes;
	std::string m_filename;
};

#endif
